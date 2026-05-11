# HYPHA-REVIEW-DASHBOARD

> HYPHA tag: `TA/DASH`

## Goal

Own the React 19 + Vite 8 + Tailwind 4 frontend that humans use to onboard, monitor agents, and approve every application before submission. The human gate.

## Scope

### In Scope
- React 19 SPA with `react-router-dom` 7 routing
- Pages: `Landing`, `Login`, `VerifyAuth`, `Onboarding`, `Overview`, `Candidates`, `Pipeline`, `ReviewQueue`, `Analytics`, `Settings`
- Layout: `DashboardLayout` (sidebar + topbar shell)
- Components: `Sidebar`, `TopBar`, `StatCard`, `StatusBadge`
- Context: `AuthContext` for JWT + current user state
- API client: `lib/api.js` (Bearer token injection, base URL config)
- Tailwind 4 token system, lucide-react icons
- Magic-link redirect handling on `/auth/verify?token=…`
- Vite dev server config (port 5173), production build, eslint + react-hooks lint
- Containerized via `frontend/Dockerfile` (nginx serving `dist/`)
- Onboarding wizard: resume upload → profile form → land on Overview
- Review queue: detail panel showing parsed JD / tailored resume diff / company intel / contact / outreach email, with Approve / Reject buttons

### Out of Scope
- Real-time pub/sub streaming (initial version polls; SSE/WebSocket upgrade is a follow-up)
- Mobile responsive beyond table breakpoints (desktop-first)
- A11y audit pass (best-effort during build, not a freeze criterion)
- Internationalization
- Theme switching beyond Tailwind's defaults
- Multi-candidate / agency views (single-candidate MVP)

## Inputs

- api-surface: every endpoint under `/api/v1`
- auth: JWT shape, magic-link verify flow
- schema-core: every Pydantic schema rendered (the frontend reads via API; no direct DB binding)
- Dependencies (per `frontend/package.json`):
  - `react` ^19.2.4 + `react-dom` ^19.2.4
  - `react-router-dom` ^7.13.2
  - `lucide-react` ^1.7.0
  - `tailwindcss` ^4.2.2 + `@tailwindcss/vite` ^4.2.2
  - `vite` ^8.0.1 + `@vitejs/plugin-react` ^6.0.1
  - `eslint` ^9.39.4 + `eslint-plugin-react-hooks` ^7.0.1 + `eslint-plugin-react-refresh` ^0.5.2

## Outputs (Deliverables)

Existing files locked at HEAD:
- `frontend/index.html`
- `frontend/package.json` + `package-lock.json`
- `frontend/vite.config.js`
- `frontend/eslint.config.js`
- `frontend/start-dev.sh`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `frontend/.gitignore`
- `frontend/public/` (static assets)
- `frontend/src/`
  - `context/AuthContext.jsx`
  - `layouts/DashboardLayout.jsx`
  - `components/Sidebar.jsx`, `TopBar.jsx`, `StatCard.jsx`, `StatusBadge.jsx`
  - `pages/Landing.jsx`, `Login.jsx`, `VerifyAuth.jsx`, `Onboarding.jsx`, `Overview.jsx`, `Candidates.jsx`, `Pipeline.jsx`, `ReviewQueue.jsx`, `Analytics.jsx`, `Settings.jsx`
  - `lib/api.js`
  - `assets/`

## Acceptance Criteria

- [ ] `npm install && npm run dev` starts Vite on port 5173 without errors
- [ ] `npm run build` produces a clean `dist/` (no TS/JSX errors, no unresolved imports)
- [ ] `npm run lint` passes
- [ ] `/` → `Landing` for unauthenticated users; authenticated users redirect to `/overview`
- [ ] `/login` accepts an email, calls `POST /auth/request-link`, displays the dev-mode magic link in `DEBUG=true`
- [ ] `/auth/verify?token=…` calls `POST /auth/verify`, stores JWT in `AuthContext`, redirects to `/onboarding` if `is_onboarded=false`, else to `/overview`
- [ ] `/onboarding` is a 2-step wizard: PDF upload (multipart to `/onboarding/resume`) → profile form (POST to `/onboarding/profile`) → redirect to `/overview`
- [ ] `/overview`, `/candidates`, `/pipeline`, `/review-queue`, `/analytics`, `/settings` are gated by `AuthContext` — unauthenticated visits redirect to `/login`
- [ ] `/review-queue` lists pipelines with `status="AWAITING_REVIEW"` and renders detail panels for parsed JD, tailored resume (with diff vs. base resume), company intel, contact, outreach email
- [ ] Approve button posts to `/review/{id}/approve`; Reject button posts to `/review/{id}/reject` and refreshes the queue
- [ ] `Sidebar` highlights the active route; navigation works without full reloads
- [ ] All requests use `lib/api.js` which auto-injects `Authorization: Bearer <jwt>` from `AuthContext`
- [ ] Tailwind classes are scoped per design tokens (no hex literals in JSX)
- [ ] `StatusBadge` renders distinct visuals for every status enum value
- [ ] `frontend/Dockerfile` produces an nginx image that serves `dist/` at port 80 with the SPA routing rewrite

## Notes

- React 19 is intentional — `use()` hook is available for promise unwrapping where useful, but don't over-rotate; existing pages can stay on `useEffect` patterns.
- Vite 8 + `@vitejs/plugin-react` ^6 is a current-stable combination. Don't downgrade.
- The dev API base URL is `http://localhost:8000/api/v1`; configurable via `VITE_API_BASE` for staging/prod builds.
- Magic-link URL is built by the backend off the request `Origin` header — the frontend must always send `origin: http://localhost:5173` in dev and the deployed origin in prod (browser sets this automatically).
- `lib/api.js` is the only legal place to construct fetch URLs. Pages call `api.get/post(…)`, not raw `fetch`.
- The Review Queue UX is the highest-leverage surface in the MVP — every artifact must be inspectable side-by-side. Polish bar: production-grade.
- The Analytics page is a shell — populating real metrics is out of scope, but the route must exist and not crash.
- Lucide-react icons are the only icon library. No mixing.
- No tests in this freeze (frontend tests are deliberately out of scope; build-passes is the bar). Adding Playwright e2e is a follow-up.
