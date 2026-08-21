# NostroQ: Technical Whitepaper

## 1. Abstract
NostroQ formulates cross-border nostro liquidity pre-funding as a Quadratic Unconstrained Binary Optimization (QUBO) problem, solved today via a from-scratch simulated annealing implementation and designed to be portable to quantum annealing hardware without reformulation. An agentic decision-support layer sits alongside the optimizer, keeping formal regulation, observed settlement practice, and internal model assumptions explicitly separated. This document synthesizes the full system; deep-dive detail lives in the companion docs referenced throughout.

## 2. The problem
Cross-border payment settlement requires pre-funded nostro balances across currencies and correspondent relationships, because settlement flows, currency demand, cut-off windows, holidays, and time zones are uncertain. Banks respond by over-provisioning, trapping capital.

## 3. Why pre-funded liquidity is expensive
Idle nostro balances earn no return and carry an opportunity cost proportional to the bank's cost of capital or alternative deployment yield (`OpportunityCost_i = L_i * r_i`, annualized). At scale across many corridors, the aggregate opportunity cost of conservative static buffering is material - see `docs/business-case.md` for the economic framing and `docs/qubo-mathematics.md` §4-5 for how this build models it per-corridor.

## 4. Existing cross-border liquidity practice
Static buffer (mean demand + a fixed multiple of standard deviation) or a fixed multiplier of forecast demand, reviewed periodically and manually. Both baselines are implemented in this build (`optimization/engine.py::static_buffer_liquidity`, `rule_based_liquidity`) specifically so the QUBO/SA result can be compared against them honestly rather than against a strawman.

## 5. Proposed architecture
See `docs/architecture.md` for full diagrams. In short: corridor forecasts feed a QUBO builder, solved by simulated annealing, refined via a coordinate-descent pass (§9 below), independently validated, compared against baselines, and turned into structured explanations - all persisted with a tamper-evident audit trail.

## 6. Demand forecasting
`forecasting/forecast.py` blends a 14-day moving average and an EWMA (alpha=0.3) over synthetic transaction history, with empirical volatility from a 30-day lookback. Deliberately simple and legible rather than a black-box production forecaster - see `docs/limitations.md`.

## 7. QUBO formulation
Binary variables `x_{i,k}` select a discrete liquidity bucket per corridor. Full derivation - one-hot constraint expansion, why every cost term becomes linear once discretized, the assembled objective - in `docs/qubo-mathematics.md` §1-3, §7.

## 8. Constraint modeling
The one-hot constraint (exactly one bucket per corridor) is the only quadratic-structure constraint in the current formulation; all cost/risk/shortfall terms reduce to linear (diagonal) coefficients once evaluated at each bucket's fixed value (`docs/qubo-mathematics.md` §3). Post-hoc validation (`optimization/engine.py::validate_solution`) independently checks the solver's output against the safety requirement rather than trusting it.

## 9. Simulated annealing
Metropolis acceptance with geometric cooling, incremental energy tracking verified against brute-force recomputation (`tests/test_annealing.py`). We found and fixed a real pathology during this build's own testing - a penalty-based one-hot encoding creates a two-hot energy barrier between valid states that the cooling schedule can get stuck behind - documented with the fix in `docs/qubo-mathematics.md` §6. This is, to our knowledge, an honest account of a real bug rather than a sanitized description of an idealized solver.

## 10. Quantum-readiness
No quantum hardware is used. The QUBO matrix this code constructs is the exact input format a quantum annealer would require; "quantum-ready" refers to that structural fact, not to any performance or execution claim. See `docs/limitations.md` and `docs/roadmap.md` Phase 7.

## 11. Agentic intelligence
A deterministic, tool-calling orchestrator (`agent/orchestrator.py`) - intent detection, real tool calls against the live database and optimizer, template-composed answers. Requires zero LLM API keys to function; an optional LLM-phrasing enhancement hook exists but is untested in this build. Full design in `docs/agent-architecture.md`.

## 12. Regulatory vs. operational corpus
Three explicitly separated knowledge categories - `REGULATION`, `SETTLEMENT_PRACTICE`, `MODEL_ASSUMPTION` - each carrying source metadata (name, jurisdiction, date, confidence, citation), never merged. Every REGULATION item seeded in this build is a labeled synthetic placeholder; the agent is hard-coded to say so. `docs/agent-architecture.md`, `docs/sandbox-readiness.md`.

## 13. Risk management
Settlement shortfall probability modeled illustratively as `Phi((mu-L)/sigma)` (`docs/qubo-mathematics.md` §5) - explicitly not a validated risk model. Loss-given-shortfall and FX/operational cost parameters are seeded per-corridor and exposed as adjustable weights in the optimizer UI/API.

## 14. Stress testing
8 predefined shock scenarios (demand +10/25/50%, volatility +20/50%, a combined shock, confidence raised to 99.9%, a holiday-style combined shock), each a genuine re-optimization against shocked inputs, not a lookup table (`api/stress_tests.py`).

## 15. Explainability
Every recommendation carries a structured explanation generated from the optimizer's actual outputs - expected demand, volatility, safety requirement, current vs. recommended balance, opportunity cost, risk-before/after - never independently generated by a language model (`optimization/engine.py::generate_explanation`).

## 16. Human-in-the-loop
Every run requires an explicit Approve / Reject / Request Recalculation decision, logged with actor, timestamp, and reason (`api/optimization.py::approve_run`). The UI states plainly that this is a decision-support prototype and no live financial transaction is executed.

## 17. Auditability
A SHA-256 hash chain (`audit/chain.py`) - explicitly not called a blockchain - where each entry incorporates the previous entry's hash. `GET /api/audit/verify` recomputes and checks the entire chain; `tests/test_validation.py::test_hash_chain_detects_tampering` confirms it actually detects a tampered entry.

## 18. GIFT City relevance
Positioned as infrastructure for banks, treasury teams, correspondent banking teams, and payment operators active in or around the GIFT City IFSC ecosystem - see `docs/business-case.md` and `docs/sandbox-readiness.md`. No claim of existing integration with GIFT City production rails is made anywhere in this codebase.

## 19. Sandbox readiness
Self-assessed against the kind of criteria an IFSCA Innovation Sandbox review would plausibly examine - problem definition, risk controls, human oversight, data lineage, auditability - in `docs/sandbox-readiness.md`. No claim of actual sandbox approval or endorsement is made.

## 20. Limitations
Synthetic data only; a simplified illustrative risk model; classical (not quantum) execution; no live banking rail integration; discretized (not continuous) liquidity levels; a deliberately-scoped subset of a larger specification. Full, itemized list in `docs/limitations.md`.

## 21. Future work
See `docs/roadmap.md` - cross-corridor coupling (which would break the current block-diagonal QUBO structure and require a more general refinement strategy), sandbox integration, real data integration, production-grade forecasting and risk modeling, quantum hardware experimentation, and multi-institution liquidity network optimization.
