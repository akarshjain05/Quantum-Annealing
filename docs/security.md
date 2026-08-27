# Security

## Implemented in this build

- **Rate Limiting** via `slowapi` (`app/main.py`, `app/api/deps.py`). The heaviest compute endpoints (e.g. quantum and classical optimization) are strictly capped via a token-bucket IP-based rate limiter (5 req/min) to prevent resource-exhaustion DOS.
- **Role-Based Access Control (RBAC)** via `RequireRole` (`app/api/deps.py`). Critical actions such as approving or rejecting liquidity optimizations are strictly gated behind `approver` or `admin` roles, bouncing unauthorized JWTs with a 403.

- **JWT authentication** (`core/security.py`) - HS256, 12-hour expiry, bearer-token scheme enforced on every non-health endpoint via `api/deps.py::get_current_user`.
- **Password hashing** via `passlib` + `bcrypt` (pinned to `bcrypt==4.0.1` specifically to avoid a known `passlib`/`bcrypt` version incompatibility - the same class of bug worth watching for in any project pairing these two libraries).
- **CORS** configured explicitly via `CORS_ORIGINS` in `config.py`, firmly rejecting unauthorized cross-origin requests regardless of environment.
- **Input validation** via Pydantic schemas (`app/schemas.py`) on every request body.
- **SQL injection protection** via the SQLAlchemy ORM throughout - no raw string-interpolated SQL anywhere in this codebase.
- **Request IDs and structured logging** - every request gets a short request ID, logged with method/path/status/duration; unhandled exceptions are caught and logged with that ID rather than leaking a stack trace to the client (`app/main.py` middleware).
- **No secrets committed** - `.env.example` serves as a template. The application strictly validates `SECRET_KEY` at boot and will fatally crash if deployed to production with the default development key.
- **Environment-variable-driven configuration** throughout (`pydantic-settings`), so secrets never need to live in code.

## Explicitly out of scope for this build


- **Security headers** (HSTS, CSP, etc.) - not set. Recommended at the reverse-proxy layer for any real deployment.
- **Secrets management** (Vault, cloud KMS, etc.) - out of scope; `.env` files are appropriate for local dev and this demo only.
- **Penetration testing / formal security review** - pending scheduling. This build represents a production-ready baseline architecture awaiting final external audit.

## Handling of sensitive data

No real financial, personal, or regulatory data exists anywhere in this repository - see `docs/limitations.md` and the "Synthetic demonstration data" notice shown on every screen. This significantly reduces (but does not eliminate - credentials and infrastructure config still matter) the security surface area of the demo itself.
