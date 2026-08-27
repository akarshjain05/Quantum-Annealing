# Docker End-to-End Verification

Tested on: **2026-08-24**
Environment: **Docker Desktop 28.5.1 (Linux aarch64)**

### Verification Steps
1. **Port Bindings**: Ensured `8000` (Backend), `5173` (Frontend), `5432` (Postgres), and `6379` (Redis) map correctly. *(Note: local Postgres conflicts were resolved by mapping appropriately).*
2. **Postgres Healthcheck Gating**: Verified that the `backend` container waits for `pg_isready -U nostroq` to succeed before executing the `alembic upgrade head && python -m app.seed.seed_data && uvicorn` boot chain.
3. **Frontend Build-Arg Inlining**: Verified that `VITE_API_URL` is correctly passed via `--build-arg`, stored as `ENV`, and completely inlined by `npm run build`, ensuring the shipped JS bundle points directly to `http://localhost:8000` from the browser.
4. **Dev Override**: Verified that `docker-compose.dev.yml` correctly merges the `build.context` when swapping out the Dockerfile for the hot-reloading dev container.
5. **Live Verification**: Logged in, executed a live optimization run through the QUBO solver, and verified the results rendered correctly via the frontend bundle.
