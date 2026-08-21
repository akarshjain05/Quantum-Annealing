# Architecture

## System overview

```mermaid
flowchart TD
    FE["Frontend (React / Vite / Tailwind)"] -->|REST + JWT| API["FastAPI backend"]
    API --> DB[(SQLite dev / Postgres prod)]
    API --> OPT["Optimization engine"]
    API --> AGT["Agent orchestrator"]
    OPT --> QB["QUBO builder"]
    QB --> SA["Simulated annealing"]
    SA --> RF["One-hot refinement pass"]
    RF --> VAL["Independent validation"]
    VAL --> DB
    AGT --> TOOLS["Tools: liquidity snapshot, corridor data,
forecast, regulation lookup, practice lookup,
run optimizer, run scenario, audit history"]
    TOOLS --> DB
    OPT --> AUD["Audit hash chain"]
    AGT --> AUD
```

## Optimization pipeline detail

```mermaid
flowchart LR
    A[Corridor forecasts
mu, sigma per corridor] --> B[QUBO Builder
build_qubo]
    B --> C[Simulated Annealing
Metropolis + cooling]
    C --> D[One-hot Refinement
coordinate descent]
    D --> E[Validation
one-hot check, shortfall check]
    E --> F[Baseline comparison
static / rule-based / greedy]
    F --> G[Explanation generation
structured, deterministic]
    G --> H[Persist run + results]
    H --> I[Audit hash chain entry]
```

Future (not implemented - see `roadmap.md`):

```mermaid
flowchart LR
    QM[Same QUBO Model] --> QA[Quantum Annealer Adapter]
    QA --> QH[Quantum Hardware]
```

## Agent pipeline detail

```mermaid
flowchart LR
    Q[User question] --> ID[Intent detection
keyword-scored, deterministic]
    ID --> TC[Tool calls
DB queries + live re-optimization]
    TC --> COMP[Grounded answer composition
template-driven, not hallucinated]
    COMP --> SRC[Source labeling
REGULATION / SETTLEMENT_PRACTICE / MODEL_ASSUMPTION]
    SRC --> OUT[Response + sources + tools_used]
```

## Solver abstraction

`OptimizationSolver` is not a literal Python interface class in this build, but the calling contract in `optimization/engine.py::run_optimization()` is deliberately solver-agnostic: it takes a `QuboModel` and returns an assignment. Swapping `simulated_annealing()` for a future `quantum_annealing_solve()` would not require touching the QUBO construction, validation, baseline comparison, or explanation generation - only the solver call itself.

```
Optimization Request -> QUBO Builder -> QUBO Model -> Solver -> Solution -> Validation -> Recommendation
                                                          |
                                              [today: SimulatedAnnealingSolver]
                                              [future: QuantumAnnealingSolver]
```

## Payment rail connector abstraction

No production payment rail integration exists in this build (nor is one claimed). The concept is documented, not implemented, in `docs/roadmap.md` - a `PaymentRailAdapter` interface with `MockPaymentRailAdapter` (what a demo would use today), `SandboxPaymentRailAdapter`, and `FutureProductionPaymentRailAdapter` as the intended evolution path.

## Data flow: request to response

1. Frontend sends `POST /api/optimization/run` with JWT bearer token.
2. `api/optimization.py::corridor_inputs_from_db` pulls corridors, computes live forecasts from transaction history, reads risk parameters and current balances.
3. `optimization/engine.py::run_optimization` builds the QUBO, runs SA, refines, validates, computes baselines, generates explanations.
4. `persist_optimization_run` writes `OptimizationRun`, `OptimizationResult`, `OptimizationBaseline` rows and appends one entry to the audit hash chain.
5. Response includes everything the frontend needs to render KPIs, the convergence chart, before/after bars, and per-corridor explanations without a second round-trip.

## Deployment topology (Docker)

```mermaid
flowchart TD
    U[Browser] --> FE["frontend container
(vite build, static)"]
    U --> BE["backend container
(uvicorn, FastAPI)"]
    BE --> PG[(postgres container)]
    BE -.optional, not required for
sync demo-scale solves.-> RD[(redis container)]
```
