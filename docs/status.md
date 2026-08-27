# Project Status

This document is the single source of truth for the implementation status of major specification items. 
Statuses: `cut` | `stubbed` | `implemented-untested` | `implemented-tested` | `hardware-verified`

| Spec Item | Status | Notes |
|-----------|--------|-------|
| **Core Optimization Math** | `implemented-tested` | Full QUBO formulation, Cap/Netting penalties, SA barrier fixes in place. |
| **Forecasting Model** | `implemented-tested` | Day-of-week & EWMA baseline tested via 90-day rolling origin backtest. |
| **Risk Model (VaR)** | `implemented-tested` | Gaussian VaR (z=1.645) empirically validated. Loss-given-shortfall decomposed & sensitivity tested. |
| **Quantum Execution** | `stubbed` | Qiskit QAOA local simulator implemented. Real Braket/Rigetti hardware execution was cut. |
| **Agent Intent Routing** | `implemented-tested` | 100% deterministic offline TF-IDF + Rapidfuzz. LLM router is tested but optional. |
| **Frontend UI (15 pages)** | `implemented-tested` | All pages built and wired into the router. |
| **Infrastructure (Docker)** | `implemented-tested` | End-to-end verified with Compose, Postgres, and Vite build inlining. |
| **Regulatory Corpus** | `stubbed` | Synthetic placeholders used. `legal_reviewed` guard rail implemented in models. |
| **Redis / Celery** | `stubbed` | Wired in Compose but asynchronous job execution is currently unused. |
