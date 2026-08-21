# Section 8 Submission: NostroQ 1-Pager

## 1. Team & Track
**Team:** NostroQ 
**Track:** Track 2: Quantum-inspired nostro/vostro liquidity engine

## 2. Problem
Banks and payment institutions operating cross-border corridors pre-fund nostro accounts to guarantee settlement. Because payment demand, settlement windows, and correspondent behavior are uncertain, treasury desks rely on static, overly conservative buffers. This over-provisioning traps capital that could otherwise be deployed productively, while generic optimizers fail to capture the discrete nature of liquidity buckets and the strict regulatory/practice separation required in treasury operations.

## 3. What You Built
A quantum-ready liquidity intelligence platform that models nostro pre-funding allocation as a QUBO (Quadratic Unconstrained Binary Optimization) problem. What is implemented is real:
* A from-scratch bit-flip simulated annealing (SA) classical solver with a coordinate-descent refinement pass to fix known two-hot energy barrier pathologies.
* Real quantum simulator execution via QAOA on Qiskit Aer, benchmarked directly against the classical SA and brute-force baselines.
* A deterministic agentic layer that strictly separates formal regulation, observed settlement practice, and internal model assumptions—operating with zero LLM API keys required.
* A tamper-evident SHA-256 audit hash chain for every run and human approval.

## 4. Architecture Snapshot
* **Frontend:** React / Vite / Tailwind UI.
* **Backend:** FastAPI, SQLAlchemy (SQLite/Postgres), Alembic.
* **Optimization Engine:** Corridor forecasts -> QUBO builder -> Simulated Annealing / QAOA solvers -> Coordinate-descent Refinement -> Independent Post-hoc Validation.
* **Agent Orchestrator:** Deterministic intent routing and tool-calling with dual-corpus knowledge segregation.
* **Audit Layer:** Tamper-evident SHA-256 hash chain capturing decisions and configurations.

## 5. Who Pays & Why Now
**Buyer Persona:** Treasury heads and correspondent-banking desk leads at IBU (IFSC Banking Unit) banks and cross-border payment institutions operating out of GIFT City. 
**Why Now:** The academic groundwork for quantum financial optimization is mature (e.g., Veselý 2022 on QAOA FX portfolio optimization; Giron et al. 2023 on HSBC collateral optimization), proving the viability of these formulations. Concurrently, GIFT City's IFSC environment and the IFSCA's active push for fintech sandboxing (via GIFT IFIH) create the perfect near-term regulatory proving ground to safely evaluate quantum-inspired treasury infrastructure.

## 6. Regulatory Pathway
Positioned specifically for the **IFSCA Innovation Sandbox**. The system is built around risk controls a sandbox review requires:
* **No black box trust:** Independent post-hoc validation checks the solver's math before recommendations are made.
* **Human-in-the-loop:** Mandatory Approve/Reject/Request Recalculation workflows for all liquidity changes.
* **Explainability & Audit:** Tamper-evident hash chains and source-of-truth separation (Regulation vs. Practice).
* **Testing Phase:** Intended for initial shadow-mode operation—running alongside existing static buffers to build a defensible track record before live capital deployment.

## 7. Fake vs Real
**What's Real:** The entire optimization stack. The QUBO formulation, the simulated annealing solver, the QAOA Qiskit execution, the independent constraint validation, the 26 backend tests, the deterministic agent layer, and the audit hash chain are all fully implemented and running locally.
**What's Fake (Simulated):** The data. To remain safe and open-source, the transaction histories, risk parameters, and regulatory corpora are deterministically generated synthetic data. The system is not wired to a live payment rail.

## 8. What's Next
* **Phase 1 (Immediate):** IFSCA Sandbox integration via a `SandboxPaymentRailAdapter` to move from synthetic to shadow-mode real data.
* **Phase 2:** Actuarial/quantitative review of the internal shortfall risk modeling for production capital decisions.
* **Phase 3:** Transitioning from Qiskit Aer simulators to experimental runs on physical quantum annealing and gate-model hardware.
* **Phase 4:** Expanding from single-institution corridor optimization to multi-institution liquidity network optimization.
