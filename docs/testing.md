# Testing

## Backend - 26 tests, all passing as of this build

```bash
cd backend && pytest tests/ -v
```

| File | Covers |
|---|---|
| `test_qubo.py` | QUBO dimensions, matrix symmetry, the one-hot penalty gap property (derived and verified, not just asserted), shortfall probability bounds, safety-level monotonicity in confidence |
| `test_annealing.py` | Incremental energy tracking vs. brute-force recomputation (200 random flips), SA convergence on a toy problem, the refinement pass never worsening energy, and a direct reproduction of the one-hot barrier bug we found + confirmation of its fix |
| `test_forecast.py` | Empty-input handling, daily aggregation correctness, horizon scaling, time-of-day profile normalization |
| `test_validation.py` | Severe-shortfall detection, no-false-positive on a covered corridor, hash-chain tamper detection |
| `test_api_optimization.py` | Full integration tests via FastAPI `TestClient` against an isolated SQLite test database - health, auth, dashboard, a real end-to-end optimization run, the QUBO inspector, agent Q&A (including the "no hallucinated regulation" guarantee), audit chain validity, and the full stress-test battery |

Known harmless warnings on this run: a few upstream deprecation notices from `pydantic`, `passlib`, and `python-jose`'s internal `datetime.utcnow()` usage - none originate from this codebase's own code.

## Frontend

```bash
cd frontend && npm run build
```
Verified to produce a clean production build (`dist/`) with no errors. No frontend unit/e2e test suite (Playwright, etc.) is included in this build - a real gap relative to the source spec's request, noted honestly in `docs/limitations.md` rather than faked with a trivial "renders without crashing" test that wouldn't add real confidence.

## What "actually run the project" meant for this build

Per the README and `docs/limitations.md`: every claim of "this works" in this document set was backed by an actual command run against actual code during this build - the seed script's row counts, the optimization run's real energy/liquidity numbers, the pytest pass count, and the frontend build output are all real, current output, not illustrative placeholders. The one exception, clearly flagged everywhere it's relevant, is `docker compose up --build`, which needs a Docker daemon this build environment didn't have.
