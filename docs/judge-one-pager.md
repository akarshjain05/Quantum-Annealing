# NostroQ - Judge One-Pager

**Problem.** Banks over-provision nostro liquidity across cross-border corridors because settlement timing, demand, and correspondent behavior are uncertain - trapping capital that could otherwise be productive.

**Solution.** Model liquidity allocation as a QUBO. Solve it today with a real, from-scratch simulated annealing implementation. Pair it with a deterministic agent that keeps regulation, observed settlement practice, and model assumptions honestly separated - never merged, never hallucinated.

**Why now.** GIFT City's IFSC environment and the IFSCA's stated interest in fintech sandboxing make this a plausible near-term evaluation environment for exactly this kind of infrastructure. Furthermore, the academic groundwork is now mature: Veselý (Czech National Bank, 2022) recently demonstrated QAOA on IBM Qiskit for near-identical FX portfolio optimization, Giron et al. (HSBC, 2023) established the quantum analog for collateral optimization, and canonical formulations like Glover et al. (2018) provide rigorous grounding for our one-hot QUBO penalties.

**Technology.** FastAPI + SQLAlchemy + Alembic backend, React/Vite/Tailwind frontend, a real QUBO builder and bit-flip simulated annealing solver (not a rebranded generic optimizer), independent post-hoc validation, a tamper-evident SHA-256 audit hash chain, and an intelligent tool-calling LLM agent.

**The math, briefly.** Binary variables `x_{i,k}` select a discrete liquidity bucket per corridor; a one-hot penalty enforces exactly one bucket per corridor; every cost term (capital cost, shortfall risk, FX cost) collapses to a linear coefficient once liquidity is discretized, because it's evaluated at a fixed set of bucket values. Full derivation, including a real solver bug we found and fixed, in `docs/qubo-mathematics.md`.

**Financial impact (one real run from this build).** $386.06M current nostro liquidity across 11 corridors -> $300.00M optimized -> $86.06M released (~22.3% capital efficiency), with one corridor correctly flagged to *increase* rather than blindly shrink everything. Not a target we hit - what the model actually produced.

**GIFT City relevance.** Positioned explicitly as infrastructure for the IFSC ecosystem - correspondent banking, treasury, and cross-border payment operators - with a payment-rail adapter interface designed to evolve from mock -> sandbox -> production without re-architecting the optimization or audit core.

**Sandbox relevance.** `docs/sandbox-readiness.md` self-assesses against what an actual IFSCA Innovation Sandbox review would examine: risk controls, data lineage, human override, model auditability - without ever claiming approval that doesn't exist.

**Differentiation.** Real QUBO (not a label), quantum-ready by construction (not quantum-advantage marketing), dual-corpus regulation/practice separation, independent validation that doesn't trust the solver, mandatory human approval, verifiable audit trail. Full comparison in `docs/differentiation.md`.

**Roadmap.** Phase 1 (this build, synthetic + classical) -> sandbox integration -> real data -> production forecasting/risk modeling -> quantum hardware experimentation -> multi-institution liquidity network optimization. `docs/roadmap.md`.

**Honesty, as a feature.** This build is a deliberately-scoped, fully-real subset of a much larger specification. We say exactly what's real, what's simplified, and why - see the README and `docs/limitations.md`. We think that's a stronger signal to a technical judge than a bigger surface area with less underneath it.
