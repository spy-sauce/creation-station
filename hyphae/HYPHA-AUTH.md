# HYPHA-AUTH

> HYPHA tag: `TA/AUTH`

## Goal

Own the passwordless magic-link authentication flow and JWT-based session for the entire API surface. Provide the `get_current_user` FastAPI dependency that every protected endpoint consumes.

## Scope

### In Scope
- Magic link generation (48-byte URL-safe token), persistence, expiry, single-use enforcement
- JWT issuance (`HS256`, 7-day expiry) and validation
- `/auth/request-link`, `/auth/verify`, `/auth/me` endpoints
- `get_current_user` dependency for downstream routers
- Dev-mode magic link return in response body when `DEBUG=true`
- Last-login tracking on `users.last_login_at`
- User-record creation on first `/request-link` for a new email

### Out of Scope
- Production email delivery integration (open question — TODO in code)
- OAuth providers (Google/Facebook/Spotify) — not in this product
- Role-based access control beyond authenticated-or-not (multi-tenant deferred)
- Frontend session storage (review-dashboard owns)

## Inputs

- schema-core: `User`, `MagicLink` ORM models and migration `003_auth.sql`
- `backend/config.py` settings: `jwt_secret`, `magic_link_expiry_minutes`, `debug`
- `backend/database.py`: `get_db` async session dependency

## Outputs (Deliverables)

Existing files locked at HEAD:
- `backend/api/auth.py` — router + JWT helpers + `get_current_user` dependency
- `backend/migrations/003_auth.sql` (delegated to schema-core for ownership; auth biome consumes it)
- `backend/models/auth.py` (likewise)

Frontend-side touchpoints (owned by review-dashboard, contract owned here):
- `POST /api/v1/auth/request-link { email }` → `{ message, magic_link?, token? }`
- `POST /api/v1/auth/verify { token }` → `{ access_token, token_type: "bearer", user_id, email, is_onboarded }`
- `GET /api/v1/auth/me` → `{ id, email, name, is_onboarded, candidate_id, created_at }`

## Acceptance Criteria

- [ ] `POST /auth/request-link` with a new email creates a `users` row and a `magic_links` row, returns `200`
- [ ] `POST /auth/request-link` with an existing email reuses the user and issues a fresh magic link
- [ ] In `DEBUG=true`, the response includes `magic_link` (URL) and `token` (raw) for dev clicking
- [ ] In `DEBUG=false`, the response contains only `{ message }` — no token leakage
- [ ] `POST /auth/verify` with a valid unused, unexpired token returns a JWT and marks the link `is_used=true`
- [ ] Using a token twice returns `401 "This link has already been used"`
- [ ] Using an expired token returns `401 "This link has expired"`
- [ ] Using a non-existent token returns `401 "Invalid or expired link"`
- [ ] `GET /auth/me` with a valid Bearer JWT returns the current user payload
- [ ] `GET /auth/me` without a Bearer token returns `401 "Not authenticated"`
- [ ] `GET /auth/me` with an expired JWT returns `401 "Token expired"`
- [ ] `get_current_user` blocks if `user.is_active=false` with `401 "User not found or inactive"`
- [ ] `last_login_at` updates on every successful `/verify`
- [ ] `users.candidate_id` is settable but optional — auth flow does not require it
- [ ] Logged events use structlog: `auth.user_created`, `auth.magic_link_created`, `auth.login_success` (PII redaction enforced)
- [ ] `ruff check backend/api/auth.py` clean

## Notes

- The magic link URL is built from `request.headers.get('origin', 'http://localhost:5173')` — frontend origin drives it, not server config. Document this assumption in `HANDOFF.md` so the staging/prod CORS allowlist matches.
- `jwt.ExpiredSignatureError` and `jwt.InvalidTokenError` are explicitly caught; any other JWT exception will 500 by design — investigate root cause rather than catching `Exception`.
- The `request.base_url` build is unused (legacy line) — leave it; not a behavioral change.
- Production email is the largest known TODO in this HYPHA. Default unblocks cultivation, but blocks production rollout. See brief Open Questions.
- No CSRF tokens — JWT-in-Authorization-header avoids the cookie CSRF surface.
- A future agency-role layer would extend this biome via a `roles` table + role claims in JWT; do NOT scaffold for it now.
