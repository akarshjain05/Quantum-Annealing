# NostroQ

**Quantum-ready liquidity intelligence for cross-border corridors.**

A decision-support prototype for the GIFT City / GIFT IFIH Young Builders' Program hackathon (theme: Cross-Border Payments). NostroQ models nostro pre-funding allocation as a QUBO (Quadratic Unconstrained Binary Optimization) problem, solves it today with a real, from-scratch simulated annealing implementation, and pairs it with a deterministic agentic layer that keeps formal regulation, observed settlement practice, and internal model assumptions clearly separated.

---

## The problem

Banks pre-fund nostro accounts across currencies and correspondent relationships to guarantee settlement. Because payment demand, settlement windows, cut-off times, and holidays are uncertain, banks over-provision - trapping capital that could otherwise be deployed. NostroQ treats "how much liquidity should sit in each corridor" as a combinatorial optimization problem rather than a static buffer rule.

## What's real here

- **A genuine QUBO formulation** (`backend/app/optimization/qubo.py`) over binary decision variables `x_{i,k}` (corridor *i* selects discrete liquidity bucket *k*), with a documented one-hot penalty derivation and a documented reason every cost term collapses to a linear (diagonal) coefficient once liquidity is discretized.
- **A from-scratch bit-flip simulated annealing solver** (`backend/app/optimization/annealing.py`) - Metropolis acceptance, geometric cooling, incremental energy tracking - verified against brute-force energy recomputation in `tests/test_annealing.py`.
- **Quantum execution via QAOA** (`backend/app/optimization/qaoa.py` and `backend/chunked_qaoa_benchmark.py`) - The QUBO is directly portable to quantum platforms. Rather than restricting quantum simulation to a small toy problem, we built a **graph-aware decomposition pipeline**. It programmatically chunks the massive production QUBO (e.g., 88 variables) along independent coupling boundaries, routing pieces <=18 qubits to Qiskit Aer's QAOA simulator, allowing us to safely process the entire live dataset while scaling horizontally.
- **A documented, fixed pathology and its fix**: naive penalty-based one-hot SA can get trapped behind a two-hot energy barrier and settle on a valid-but-suboptimal bucket. We found this during our own smoke-testing (see `docs/qubo-mathematics.md` §6), and fixed it with a coordinate-descent refinement pass that's provably exact given the current block-diagonal QUBO structure.
- **Independent post-hoc validation** - the app never trusts the solver blindly (`optimization/engine.py::validate_solution`).
- **Three real baselines** (static buffer, rule-based, greedy) computed and compared against every run, not just the QUBO result.
- **Real forecasting** from ~3,900 seeded synthetic transactions across 11 corridors (moving average + EWMA + empirical volatility).
- **8 real stress-test scenarios** and an interactive scenario simulator that actually re-optimizes.
- **An intelligent, tool-calling agent** - intent detection, real tool calls against the live DB/optimizer, grounded answers labeled by source type (REGULATION / SETTLEMENT_PRACTICE / MODEL_ASSUMPTION).
- **A tamper-evident SHA-256 hash chain** for the audit log (explicitly not called "blockchain"), with a working verification endpoint.
- **26 passing backend tests** (`pytest`), including one that directly reproduces and confirms the fix for the SA barrier bug above.



## Example output from an actual run in this build

```
Total nostro liquidity (11 corridors): $386.06M
QUBO variables: 88 (11 corridors x 8 liquidity buckets)
Simulated annealing: 8,000 iterations x 3 restarts, refined -> final energy -398.3
Optimized liquidity:  $300.00M
Capital released:     $86.06M  (~22.3% capital efficiency)
One corridor (USD_GBP) recommended to INCREASE, not decrease - the model
balances risk and cost per corridor rather than blindly shrinking everything.
```
Your numbers will vary slightly (synthetic data is randomized by a fixed seed, but weights/params are adjustable in the UI) - this is a real example, not a hardcoded target.

---

## Quick start (local, no Docker)

Backend defaults to **SQLite** - zero external services required to see the whole system work.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python3 -m app.seed.seed_data
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`. API docs (Swagger) at `http://localhost:8000/docs`.


## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Frontend: `http://localhost:5173` · Backend: `http://localhost:8000` · Swagger: `http://localhost:8000/docs`

## Running tests

```bash
cd backend && pytest tests/ -v   # 26 tests, all passing as of this build
cd frontend && npm run build     # production build verified clean
```

---

## Architecture

```
Frontend (React/Vite/Tailwind)
        |
FastAPI backend  --  Alembic-migrated schema (SQLite dev / Postgres prod)
        |
Optimization engine
  corridor forecasts -> QUBO builder -> simulated annealing -> refinement
  -> independent validation -> baseline comparison -> explanation generation
        |
Agent orchestrator (intent routing + tool calls, LLM-backed)
        |
Audit hash chain (every run, every approval)
```
Full diagrams: `docs/architecture.md`. Math: `docs/qubo-mathematics.md`. Agent design: `docs/agent-architecture.md`.

## Project structure

```
backend/app/
  core/            config, database, security (JWT + bcrypt)
  optimization/    qubo.py, annealing.py, engine.py  <- the real math
  forecasting/      demand forecasting from transaction history
  agent/           deterministic orchestrator, tools, dual-corpus knowledge seed
  audit/           SHA-256 hash chain
  api/             FastAPI routers
  seed/            synthetic data generator
backend/tests/     26 pytest tests
backend/alembic/   real, autogenerated + applied migration
frontend/src/
  pages/           Dashboard, Corridors, Optimizer, QuboInspector, Scenarios,
                    StressTests, Agent, Audit
  components/      Layout, KPI cards, source tags, settlement timeline
docs/              architecture, math, agent design, demo script, sandbox
                    readiness, limitations, roadmap, business case, and more
docker/            Dockerfiles + docker-compose.yml
```

## Documentation

### Business & Strategy
- [Business Case](docs/business-case.md) - Problem, solution, market opportunity
- [Commercial Horizon](docs/commercial-horizon.md) - Go-to-market, pricing, timeline
- [Funding & Sponsors](docs/funding-sponsors.md) - Who would fund this today

### Technical
- [Quantum Advantage](docs/quantum-advantage.md) - Honest assessment of quantum benefits
- [Sandbox Readiness](docs/sandbox-readiness.md) - Regulatory considerations
- [API Documentation](docs/api-examples.md) - API usage examples

### Data
- [Synthetic Data](data/README.md) - How data was generated
- All data is synthetic - no real banking data used

## Honest Disclosure

### What We Claim ✅
- QUBO formulation is mathematically correct
- Same formulation runs on quantum hardware without modification
- Classical and quantum solvers find equivalent solutions at demo scale
- Approach is designed for future quantum advantage

### What We Do NOT Claim ❌
- Current quantum advantage over classical methods
- Production-ready quantum optimization today
- Specific performance guarantees on quantum hardware

See [Quantum Advantage Assessment](docs/quantum-advantage.md) for detailed analysis.


## License

MIT - see `LICENSE`. Synthetic demo data only; no real financial, regulatory, or customer data is included anywhere in this repository.
