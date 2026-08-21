# Roadmap

Phased from where this build actually is today - not aspirational marketing.

**Phase 1 - Synthetic prototype (this build).** Real QUBO + simulated annealing over synthetic data, deterministic agent, full audit trail. Done.

**Phase 2 - Fast-follow completeness.** Remaining frontend pages (Regulatory Grounding, standalone Forecast, Settings), remaining doc depth, `docker compose up` verified end-to-end on real hardware, expanded pytest/frontend test coverage, CI pipeline.

**Phase 3 - Cross-corridor coupling.** Introduce genuine cross-corridor QUBO terms - shared collateral pools, joint FX netting across correlated corridors - which breaks the current block-diagonal structure (`docs/qubo-mathematics.md` §3) and requires generalizing the refinement pass from a one-shot per-block argmin into a proper iterative local search or reheating strategy.

**Phase 4 - Sandbox integration.** Build out the `SandboxPaymentRailAdapter` (interface only today) against an actual IFSCA/GIFT City sandbox environment once available; shadow-mode operation against a real bank's existing static-buffer process without acting on recommendations, to validate model quality before any live use.

**Phase 5 - Real data integration.** Replace synthetic transaction history with real (permissioned, governed) payment flow data; replace the synthetic REGULATION corpus with actual cited regulatory text, reviewed by qualified compliance counsel.

**Phase 6 - Production-grade forecasting.** Move beyond moving-average/EWMA to a proper time-series stack (gradient boosting or a lightweight neural forecaster) with backtesting against realized demand, and a validated (not illustrative) shortfall risk model built with input from quantitative risk / actuarial expertise.

**Phase 7 - Quantum hardware experimentation.** The QUBO formulation this build produces is already in the right shape. Concretely: benchmark the current formulation on a quantum annealer or QAOA circuit once corridor count and bucket granularity grow past what classical SA handles comfortably; compare solution quality and wall-clock time against the classical baseline honestly, including the (likely, at current problem sizes) result that classical SA remains competitive for a while yet.

**Phase 8 - Multi-bank / cross-institution optimization.** Extend from single-bank corridor optimization toward a liquidity-network view across multiple institutions operating in the same corridors - the point at which genuine network effects (and genuinely new privacy/competition considerations) start to matter, and where GIFT City's role as shared infrastructure becomes most relevant.

## Payment rail adapter (interface, not implemented)

```python
class PaymentRailAdapter:
    def get_balance(self, account_id: str) -> float: ...
    def initiate_transfer(self, ...) -> TransferResult: ...

class MockPaymentRailAdapter(PaymentRailAdapter):
    """What this build's demo effectively uses - synthetic data only."""

class SandboxPaymentRailAdapter(PaymentRailAdapter):
    """Phase 4 - talks to an actual regulatory/institutional sandbox."""

class FutureProductionPaymentRailAdapter(PaymentRailAdapter):
    """Phase 5+ - real production connectivity, real security review required."""
```
None of these classes exist in the current codebase yet - documented here as the intended shape, not shipped as unused scaffolding.
