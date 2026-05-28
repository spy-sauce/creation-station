# HYPHA-FRONTEND

> HYPHA tag: `TA/FRONTEND`
> Maps to Mycelium agent: `frontend-agent`

## Goal

Own the React 19 + Vite 8 + Tailwind 4 frontend: UI primitives, page components, routing, auth context, API client, and the full user-facing dashboard experience. This is the human gate for the entire Talent Agent system.

## Scope

### In Scope

- React 19 SPA with `react-router-dom` 7 routing
- Pages: `Landing`, `Login`, `VerifyAuth`, `Onboarding`, `Overview`, `Candidates`, `Pipeline`, `ReviewQueue`, `Analytics`, `Settings`
- Layout: `DashboardLayout` (sidebar + topbar shell)
- UI Primitives: `Button`, `Input`, `Card`, `Avatar`, `Badge`, `Dialog`, `Spinner`
- Components: `Sidebar`, `TopBar`, `StatCard`, `StatusBadge`
- Context: `AuthContext` for JWT + current user state
- API client: `lib/api.js` (Bearer token injection, base URL config via `VITE_API_BASE`)
- Tailwind 4 with design tokens from `DESIGN-CORE`
- Magic-link redirect handling on `/auth/verify?token=…`
- Vite dev server config (port 5173), production build
- Onboarding wizard: resume upload → profile form → land on Overview
- Review queue: detail panel with all artifact panes + Approve/Reject buttons
- Containerized via `frontend/Dockerfile` (nginx serving `dist/`)

### Out of Scope

- Real-time pub/sub streaming (polling at 5s; SSE/WebSocket is follow-up)
- Mobile responsive beyond table breakpoints (desktop-first)
- A11y audit pass (best-effort, not a freeze criterion)
- Internationalization / i18n
- Multi-theme switching (dark theme only)
- Multi-candidate / agency views (single-candidate MVP)
- Frontend tests (Playwright e2e is follow-up)

## Inputs

- `TA/DESIGN` (HYPHA-DESIGN-CORE): Design tokens, typography, color palette
- `TA/API` (HYPHA-API-SURFACE): All `/api/v1/*` endpoints
- `TA/AUTH` (HYPHA-AUTH): JWT shape, magic-link verify flow
- `TA/SCHEMA` (HYPHA-SCHEMA-CORE): Pydantic schemas (consumed via API responses)
- `NUTRIENTS.md`: Component prop contracts (§B), style system rules (§F)

## Outputs (Deliverables)

### Config & Build

- `frontend/index.html`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.js`
- `frontend/eslint.config.js`
- `frontend/start-dev.sh`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `frontend/.gitignore`

### Source

- `frontend/src/main.jsx` — app entry
- `frontend/src/App.jsx` — router setup
- `frontend/src/index.css` — Tailwind entry + design tokens

### Context & Lib

- `frontend/src/context/AuthContext.jsx`
- `frontend/src/lib/api.js`
- `frontend/src/lib/routes.js`

### Layouts

- `frontend/src/layouts/DashboardLayout.jsx`

### UI Primitives (components/ui/)

- `frontend/src/components/ui/button.jsx`
- `frontend/src/components/ui/input.jsx`
- `frontend/src/components/ui/card.jsx`
- `frontend/src/components/ui/avatar.jsx`
- `frontend/src/components/ui/badge.jsx`
- `frontend/src/components/ui/dialog.jsx`
- `frontend/src/components/ui/spinner.jsx`
- `frontend/src/components/ui/types.js`

### Domain Components

- `frontend/src/components/Sidebar.jsx`
- `frontend/src/components/TopBar.jsx`
- `frontend/src/components/StatCard.jsx`
- `frontend/src/components/StatusBadge.jsx`

### Pages

- `frontend/src/pages/Landing.jsx`
- `frontend/src/pages/Login.jsx`
- `frontend/src/pages/VerifyAuth.jsx`
- `frontend/src/pages/Onboarding.jsx`
- `frontend/src/pages/Overview.jsx`
- `frontend/src/pages/Candidates.jsx`
- `frontend/src/pages/Pipeline.jsx`
- `frontend/src/pages/ReviewQueue.jsx`
- `frontend/src/pages/Analytics.jsx`
- `frontend/src/pages/Settings.jsx`

### Design Documentation

- `frontend/src/design/CHEATSHEET.md`
- `frontend/src/design/tokens.reference.md`

### Static Assets

- `frontend/public/` (favicon, etc.)

## Acceptance Criteria

- [ ] `npm install && npm run dev` starts Vite on port 5173 without errors
- [ ] `npm run build` produces a clean `dist/` with no JSX/TS errors
- [ ] `npm run lint` passes
- [ ] `/` → `Landing` for unauthenticated; authenticated redirect to `/overview`
- [ ] `/login` calls `POST /auth/request-link`, displays dev-mode magic link when `DEBUG=true`
- [ ] `/auth/verify?token=…` stores JWT in `AuthContext`, redirects appropriately
- [ ] `/onboarding` is 2-step wizard: PDF upload → profile form → redirect to `/overview`
- [ ] All dashboard routes gated by `AuthContext` — unauthenticated → `/login`
- [ ] `/review-queue` shows pipelines at `AWAITING_REVIEW` with all four artifact panels
- [ ] Approve/Reject buttons call `/review/{id}/approve` and `/review/{id}/reject`
- [ ] `Sidebar` highlights active route; navigation works without full reloads
- [ ] All requests use `lib/api.js` with auto-injected `Authorization: Bearer <jwt>`
- [ ] No hex literals in JSX — all colors via CSS custom properties or Tailwind tokens
- [ ] `StatusBadge` renders distinct visuals for every status enum value
- [ ] `frontend/Dockerfile` produces nginx image serving `dist/` at port 80 with SPA rewrite
- [ ] Lucide-react is the only icon library — no heroicons, no react-icons

## Notes

- React 19's `use()` hook is available but not required; existing `useEffect` patterns are fine.
- The dev API base URL is `http://localhost:8000/api/v1`; set via `VITE_API_BASE` for staging/prod.
- `lib/api.js` is the ONLY legal place to construct fetch URLs. Pages call `api.get/post(…)`, never raw `fetch`.
- Review Queue is the highest-leverage surface in MVP — production-grade polish required.
- Analytics page is a shell — real metrics are out of scope; route must exist and not crash.
- This biome consumes `DESIGN-CORE` tokens; it does NOT extend or redefine them.
