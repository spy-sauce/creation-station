# HYPHA-API-CLIENT

> HYPHA tag: `TA/API-CLIENT`
> Maps to Mycelium agent: `api-client-agent`

## Goal

Own the frontend API client layer that wires React pages to the FastAPI backend. This biome replaces mock data with real API calls, implements auth token injection, handles errors gracefully, and integrates the SSE event stream for real-time updates.

## Scope

### In Scope

- `frontend/src/api/client.ts` — single `apiClient` instance built on `fetch`
- Base URL from `import.meta.env.VITE_API_BASE_URL`
- JWT storage in `localStorage` under key `talent-agent-jwt`
- Auto-injection of `Authorization: Bearer ${jwt}` header on every request
- 401 handling: invalidate JWT, redirect to `/login`, surface toast
- Network error handling: surface `TalentAgentApiError` with `{status, code, message}`
- Auth API: `requestMagicLink(email)`, `verifyToken(token)`, `refreshSession()`
- Discovery API: `getTodayDigest()`, `triggerDiscoveryRun()`, `getJob(id)`
- Applications API: `listApplications()`, `approveApplication(id)`, `rejectApplication(id, reason)`
- Events API: `subscribeAgentStatus(channel, onMessage)` via EventSource
- Re-wire existing pages: `Overview.tsx`, `Pipeline.tsx`, `Analytics.tsx`, `ReviewQueue.tsx`, `ReviewDetail.tsx`

### Out of Scope

- Offline support / service worker caching
- Request deduplication / SWR-style caching
- Optimistic UI beyond immediate state updates
- Request retry with exponential backoff (server-side handles this)
- WebSocket fallback for SSE

## Inputs

- `api-agent`: Endpoint contracts from HYPHA-API-SURFACE
- `api-streaming-agent`: SSE endpoint `GET /events/stream?channel=...`
- `frontend-agent`: Existing page components and `AuthContext`
- `NUTRIENTS.md`: API_CONTRACTS section for request/response shapes

## Outputs (Deliverables)

- `frontend/src/api/client.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/api/discovery.ts`
- `frontend/src/api/applications.ts`
- `frontend/src/api/events.ts`
- `frontend/src/api/types.ts` (shared API types)
- `frontend/src/api/__tests__/client.test.ts`
- Updated: `frontend/src/pages/Overview.tsx`
- Updated: `frontend/src/pages/Pipeline.tsx`
- Updated: `frontend/src/pages/Analytics.tsx`
- Updated: `frontend/src/pages/ReviewQueue.tsx`
- Updated: `frontend/src/pages/ReviewDetail.tsx`

## Acceptance Criteria

- [ ] `npm run typecheck` clean — all API calls are fully typed
- [ ] Opening the frontend with backend running shows real digest data, not mocks
- [ ] Magic-link login flow works end-to-end: enter email → receive link → click → land on dashboard
- [ ] JWT is stored in `localStorage` under `talent-agent-jwt` after successful auth
- [ ] Every API request includes `Authorization: Bearer ${jwt}` header
- [ ] Clicking Approve in `ReviewDetail` fires `POST /applications/{id}/approve` and updates the row
- [ ] Clicking Reject in `ReviewDetail` opens confirmation, fires `POST /applications/{id}/reject`, updates the row
- [ ] 401 response invalidates JWT, redirects to `/login`, shows toast "Session expired"
- [ ] Network error (backend down) shows error toast and renders error state in affected component
- [ ] `subscribeAgentStatus('agent.status.discovery', callback)` opens EventSource, calls callback on each SSE data frame
- [ ] EventSource auto-reconnects on connection loss (browser native behavior)
- [ ] Killing the backend mid-session triggers an error toast on the next request
- [ ] Recovery: when backend comes back, subsequent requests succeed without page reload
- [ ] No hardcoded API URLs — all use `VITE_API_BASE_URL`
- [ ] No `console.log` — use frontend logging utility
- [ ] `npm run lint` clean

## Notes

- The `apiClient` should be a thin wrapper around `fetch` with auth header injection and error normalization. Do not introduce axios or other HTTP libraries.
- The `TalentAgentApiError` class should include: `status` (HTTP status code), `code` (backend error code if present), `message` (user-facing message).
- The `talent-agent-jwt` key matches what `AuthContext` expects. Coordinate with the existing auth flow.
- For SSE, use native `EventSource`. The `subscribeAgentStatus` function returns a cleanup function that calls `eventSource.close()`.
- Page rewiring should preserve existing layout and styling exactly. Only change the data source from mock to API.
- The `Analytics.tsx` page is currently a shell. Wire it to real endpoints if they exist; otherwise show "Coming soon" with the correct layout.
- Error states should render within the page layout, not as full-screen overlays. Use the existing error component patterns.
- The tests use `vitest` with `msw` or manual fetch mocking. Test the 401 → logout flow explicitly.
