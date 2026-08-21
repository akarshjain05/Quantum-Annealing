# Differentiation

| Approach | What it does | What it misses |
|---|---|---|
| **Traditional treasury rules** | Static buffer (e.g. mean + 2 std dev), fixed multiplier of forecast demand | Ignores confidence-level tradeoffs, corridor-specific cost structure, and doesn't adapt to shocks without manual re-work |
| **Forecast-only systems** | Predict demand, leave the allocation decision to a human | Forecasting is necessary but not sufficient - the actual allocation across discrete buckets, weighed against cost and risk, is a separate optimization problem |
| **AI chatbots (generic LLM wrapper)** | Natural-language Q&A over financial data | No structural guarantee against hallucination; typically can't distinguish "this is a rule" from "this is a guess" the way a dual-corpus, source-tagged system can; usually can't actually *recompute* a recommendation, only describe one |
| **Classical optimization (generic LP/MILP)** | Can solve the same discrete-choice problem in principle | Doesn't naturally extend toward the QUBO/quantum-annealing pathway; this build's QUBO formulation is the same shape a quantum annealer needs, at no extra modeling cost today |
| **Quantum optimization (hypothetical, today)** | The eventual destination for this formulation | Not yet practical at real problem scale/access/cost - claiming quantum execution today would be misleading. We say so explicitly (`docs/limitations.md`) |
| **NostroQ (this build)** | QUBO-formulated liquidity optimization, solved classically today, quantum-ready by construction; dual-corpus regulation/practice/assumption separation; independent validation; full audit trail; human approval required | Synthetic data, no live rail integration, a deliberately scoped subset of a much larger spec - see `docs/limitations.md` |

## The strongest differentiators, concretely

1. **Liquidity optimization, not payment tracking** - most cross-border fintech tooling focuses on payment status/tracking; this optimizes the capital sitting behind those payments.
2. **A genuinely real QUBO formulation**, not a marketing label on top of a simple heuristic - the math is documented equation-by-equation in `docs/qubo-mathematics.md`, including a bug we found in our own implementation and how we fixed it.
3. **Quantum-ready architecture** without a quantum-advantage claim - the Q matrix produced today is the exact input format a quantum annealer would need.
4. **Dual-corpus regulatory + settlement intelligence** - REGULATION, SETTLEMENT_PRACTICE, and MODEL_ASSUMPTION are never merged, anywhere, and the agent is hard-coded to refuse to claim a synthetic item is a real regulation.
5. **Explainability generated from structured model outputs**, not an LLM narrating a guess - every recommendation's explanation is built from the same numbers the optimizer actually computed.
6. **Stress testing and interactive scenario simulation** that genuinely re-optimize, not lookup tables of precomputed answers.
7. **Human approval required** before any recommendation is treated as decided, logged with actor/timestamp/reason.
8. **Auditability** via a real, verifiable SHA-256 hash chain, not just a database table someone could quietly edit.
9. **GIFT City / IFSC-oriented positioning** - the sandbox-readiness self-assessment (`docs/sandbox-readiness.md`) is written against what an actual regulatory review would examine, not generic "AI safety" language.
10. **Honesty as a feature** - this document set, the limitations doc, and the README's "deliberate simplifications" table exist because we think a fintech reviewer trusts a team more, not less, for stating precisely what is and isn't real.
11. **Scalable product vs. service model** - NostroQ is a self-serve software platform where banks control their own optimizations, parameterized via standardized integration schemas, with usage-based pricing. The IP (QUBO formulations, deterministic agents, hash chains) compounds across the network as assets—we are not a consulting shop selling bespoke engineering and billable hours.
