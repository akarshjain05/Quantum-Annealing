# Sandbox Readiness

NostroQ is a prototype **designed with future IFSCA Innovation Sandbox evaluation in mind**. It is **not currently approved, certified, or endorsed by IFSCA, RBI, or any regulator**, and nothing in this document or the product should be read as claiming otherwise. This is an engineering self-assessment against the kind of criteria a sandbox review would plausibly examine, written to demonstrate the team understands what such a review would look for.

## 1. What the product does
Recommends nostro pre-funding levels per currency corridor, using a QUBO-formulated optimization solved via simulated annealing, informed by demand forecasts, risk parameters, and a knowledge base that separates formal regulation from observed settlement practice from internal model assumptions.

## 2. Which financial activity it supports
Treasury/liquidity management decision support for cross-border correspondent banking relationships. It does not itself move money, initiate payments, or interact with any payment rail.

## 3. Which risks it introduces
- **Model risk**: an incorrect recommendation could lead a treasury team to under- or over-fund a corridor if acted on without review.
- **Data risk**: forecasts and requirements are only as good as the transaction history and risk parameters behind them; this build's data is entirely synthetic.
- **Explainability risk**: a black-box recommendation that isn't understood by its user is itself a governance risk, independent of whether the recommendation is numerically correct.
- **Over-reliance risk**: automation bias - a human approver rubber-stamping recommendations without genuine review.

## 4. How those risks are controlled
- **Independent validation** (`optimization/engine.py::validate_solution`) never trusts the solver's output; violations are surfaced, not hidden, and a run with severe violations is marked `INVALID` rather than presented as a clean recommendation.
- **Structured, non-hallucinated explanations** generated from the actual model outputs for every recommendation (§25 of the source spec; `engine.py::generate_explanation`).
- **Mandatory human-in-the-loop**: every run requires an explicit Approve / Reject / Request Recalculation action, logged with actor, timestamp, and reason, before it's treated as decided.
- **Baseline comparison**: every QUBO/SA result is shown next to three independently-computed baselines, so a reviewer isn't taking the optimizer's word for its own improvement.
- **Source-of-truth separation**: REGULATION / SETTLEMENT_PRACTICE / MODEL_ASSUMPTION are never merged, and the agent explicitly refuses to claim a synthetic item is a real regulation.

## 5. What data is used
100% synthetic demonstration data, generated deterministically from a fixed random seed (`backend/app/seed/seed_data.py`). No real customer, account, transaction, or regulatory data appears anywhere in this repository. Every screen that shows this data carries a visible "Synthetic demonstration data" notice.

## 6. How decisions are logged
Every optimization run and every human approval decision is appended to a SHA-256 hash chain (`audit/chain.py`) where each entry's hash incorporates the previous entry's hash. `GET /api/audit/verify` recomputes the entire chain and reports whether it's intact - a genuinely tamper-evident (not tamper-*proof*, and not a blockchain) audit log.

## 7. How a human can override recommendations
The Optimizer page's Approve / Reject / Request Recalculation controls are the override mechanism; no recommendation is acted on without one of these being recorded. "Request Recalculation" explicitly supports the case where a human disagrees with the model's assumptions and wants a re-run with different parameters.

## 8. How model outputs can be audited
- Every run records `model_version`, `qubo_version`, `forecast_version`, `knowledge_version`, and `random_seed` for reproducibility.
- The QUBO Inspector (`/qubo`) lets a reviewer rebuild and inspect the *exact* formulation used for any past run, deterministically, from its stored parameters.
- `docs/qubo-mathematics.md` documents every modeling choice, including a real bug we found in our own solver and how we fixed it - see its §6.

## 9. How the prototype could be tested safely
- Run entirely against synthetic data with no external system connectivity (current state).
- Layer in a `SandboxPaymentRailAdapter` (interface documented, not implemented - `docs/roadmap.md`) that talks to a sandbox environment rather than production rails, with all the same validation/audit/approval machinery already in place.
- Shadow-mode operation: run recommendations alongside a bank's existing static-buffer process without acting on them, and compare over a real observation period before any live use.

## 10. What would still require regulatory/legal review before any real use
- Every item in the REGULATION corpus needs replacing with actual, cited, jurisdiction-specific regulatory text, reviewed by qualified counsel/compliance - not generated or interpreted by this system.
- The illustrative shortfall-risk model (`docs/qubo-mathematics.md` §5) is not a validated risk model and would need actuarial/quantitative risk review before being relied upon for capital decisions.
- Data governance, retention, and access-control requirements for real transaction and account data are entirely out of scope of this prototype and would need to be designed against the applicable IFSC/IFSCA framework.
- Any actual connection to a payment rail, sandbox or otherwise, requires its own security review independent of this codebase.
