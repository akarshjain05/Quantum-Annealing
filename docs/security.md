# Security

## Implemented in this build

- **JWT authentication** (`core/security.py`) - HS256, 12-hour expiry, bearer-token scheme enforced on every non-health endpoint via `api/deps.py::get_current_user`.
- **Password hashing** via `passlib` + `bcrypt` (pinned to `bcrypt==4.0.1` specifically to avoid a known `passlib`/`bcrypt` version incompatibility - the same class of bug worth watching for in any project pairing these two libraries).
- **CORS** configured via `core/config.py::settings.ENV` (permissive in development, intended to be locked down to specific origins in production - `app/main.py`).
- **Input validation** via Pydantic schemas (`app/schemas.py`) on every request body.
- **SQL injection protection** via the SQLAlchemy ORM throughout - no raw string-interpolated SQL anywhere in this codebase.
- **Request IDs and structured logging** - every request gets a short request ID, logged with method/path/status/duration; unhandled exceptions are caught and logged with that ID rather than leaking a stack trace to the client (`app/main.py` middleware).
- **No secrets committed** - `.env.example` files exist at both `backend/` and repo root with placeholder values only; the real `SECRET_KEY` default is explicitly labeled `dev-only-secret-CHANGE-ME-before-any-real-deployment`.
- **Environment-variable-driven configuration** throughout (`pydantic-settings`), so secrets never need to live in code.

## Explicitly out of scope for this build

- **Rate limiting** - not implemented. A production deployment should add it (e.g. via a reverse proxy or `slowapi`) before exposing this beyond a local demo.
- **Security headers** (HSTS, CSP, etc.) - not set. Recommended at the reverse-proxy layer for any real deployment.
- **Secrets management** (Vault, cloud KMS, etc.) - out of scope; `.env` files are appropriate for local dev and this demo only.
- **Penetration testing / formal security review** - not performed. This is a hackathon prototype, not a reviewed production system.
- **Role-based authorization beyond a single `role` field** - the schema has a `role` column (`treasury_analyst` / `treasury_admin`) but no endpoint currently branches on it; every authenticated user can currently perform every action. A real deployment needs proper RBAC before multi-user use.

## Handling of sensitive data

No real financial, personal, or regulatory data exists anywhere in this repository - see `docs/limitations.md` and the "Synthetic demonstration data" notice shown on every screen. This significantly reduces (but does not eliminate - credentials and infrastructure config still matter) the security surface area of the demo itself.
