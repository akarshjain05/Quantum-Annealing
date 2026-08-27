# Deployment

## Local (no Docker) - the path actually tested in this build

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python3 -m app.seed.seed_data
uvicorn app.main:app --reload --port 8000
```
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Services (`docker-compose.yml`): `frontend`, `backend`, `postgres`, `redis` (provisioned for future async job scaling, not required by the current synchronous solve path). `docker-compose.dev.yml` mounts source directories for hot-reload during development.

**This path was written and reviewed but not executed end-to-end in the sandbox this project was built in** (no Docker daemon / image registry access there) - see the README's honesty note. Verify it on real infrastructure before depending on it for a live demo.

## Environment variables

See `.env.example` (root and `backend/`). The important ones:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./nostroq.db` | Set to a `postgresql+psycopg2://...` URL for production |
| `SECRET_KEY` | dev placeholder | **Must** be changed before any real deployment |
| `LLM_PROVIDER` / `*_API_KEY` | required | Required for the LLM-backed agent to function |
| `RANDOM_SEED` | `42` | Controls deterministic synthetic data generation |

## Production considerations (not implemented, noted honestly)

- Point `DATABASE_URL` at a managed Postgres instance; run `alembic upgrade head` as a release step rather than relying on `create_all`.
- Put the backend behind a reverse proxy (nginx/Caddy/cloud load balancer) for TLS termination, security headers, and rate limiting - none of which this build implements itself (`docs/security.md`).
- Serve the frontend's `npm run build` output as static files from the same proxy or a CDN, rather than `vite preview`.
- Generic-Linux-VM, Render-style PaaS, and AWS are all viable - nothing in this codebase is cloud-specific. No specific cloud deployment has been tested.
