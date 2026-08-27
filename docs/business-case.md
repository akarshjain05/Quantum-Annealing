# Business Case

## Problem
Banks and payment institutions operating cross-border corridors pre-fund nostro accounts to guarantee settlement. Because demand, timing, and correspondent behavior are uncertain, the safe default is over-provisioning - capital that sits idle rather than earning a return or funding other activity.

## Current banking workflow
Most treasury desks rely on static buffers (a fixed multiple of historical average demand, or mean plus a fixed number of standard deviations) reviewed periodically, manually, and conservatively - because getting it wrong in the "too little" direction risks a settlement failure, which is a much more visible and costly event than idle capital.

## Capital inefficiency
The gap between a static buffer and a risk-aware, corridor-specific optimum is exactly the capital this system targets. In one real run during this build, the gap was measured at ~22% of total nostro liquidity across 11 corridors - illustrative of *the kind of number this class of problem can produce*, not a claim about any real institution's actual numbers, which this system currently lacks access to.

## Proposed solution
Formulate the allocation decision as a QUBO, solve it with simulated annealing today (quantum-ready by construction for tomorrow), and wrap it in an agentic layer that keeps regulation, observed practice, and model assumptions separated, with independent validation, human approval, and a full audit trail.

## Economic benefit
Directly: reduced opportunity cost on released capital (`AnnualOpportunityCostSaved = CapitalReleased x OpportunityCostRate`, computed and shown per-corridor in this build). Indirectly: faster, more defensible treasury decision cycles, and an audit trail that reduces the operational burden of demonstrating why a given liquidity level was chosen.

## Buyer
Treasury and correspondent-banking teams at banks and payment institutions operating multi-currency corridors; eventually, institutions operating through GIFT City's IFSC infrastructure specifically, where the regulatory environment is explicitly being built to support this kind of financial infrastructure innovation.

## Business model
NostroQ is **a software product, not a bespoke consulting service**. Our rate card scales cleanly with software usage—priced either by the number of active corridors optimized, total AUM passing through the engine, or per-seat licenses for treasury teams. We never bill hourly or per "report delivered." 

The core value prop relies on self-service software operated by the customer:
1. **Self-service configuration**: Banks configure their own corridors, weights, and risk tolerances directly in the **Optimizer** and **Scenarios** UI. We do not manually tune models per client.
2. **Customer-driven execution**: The bank's treasury desk clicks "Optimize." The QUBO/SA/QAOA engine runs entirely within their tenant—we never touch their data or manually execute their runs.
3. **Standardized onboarding**: Integration is handled via standard data connectors (e.g., Account Aggregator-style JSON schemas or standard SWIFT MT700 feeds), eliminating the need for bespoke integration engineering per bank.

## Implementation model
On-premise or private-cloud deployment given the sensitivity of the underlying data (nostro balances, payment flows). Because NostroQ is a product, the IP compounds across the network: our QUBO formulations, the deterministic agent orchestrator, and the audit hash chain are reusable, ownable software assets. As the platform encounters more customer data in shadow mode or production, our baseline calibrations and solver configurations improve for all users. This compounding software value strictly separates NostroQ as a scalable product rather than a services shop.

## Risks
- **Model risk** if a recommendation is acted on without the human review this system requires.
- **Data integration risk** - real value depends on real transaction and account data, which requires real integration work.
- **Regulatory risk** - see `docs/sandbox-readiness.md` for what would need review before any real use.
- **Adoption risk** - treasury teams are (rightly) conservative; trust has to be earned via the explainability and audit features this build prioritizes, not asserted.

## Go-to-market
Start narrow: a single institution, a small number of corridors, shadow-mode operation (recommendations shown alongside the existing process, not replacing it) to build a track record before any live use.

## GIFT City opportunity
GIFT City's IFSC status and the IFSCA's stated interest in fintech innovation (via programs like GIFT IFIH) make it a plausible early environment for exactly this kind of infrastructure to be evaluated under sandbox conditions before wider adoption - see `docs/sandbox-readiness.md`.

## Expansion opportunity
Beyond single-bank corridor optimization: correspondent banks, payment institutions, treasury platforms, and financial infrastructure providers more broadly (Phase 8 in `docs/roadmap.md` - multi-institution liquidity network optimization).

*No third-party market-size statistics are cited in this document; none were sourced during this build, and inventing them would undermine the rest of this document set's commitment to not overclaiming.*
