# HYPHA-API-STREAMING

> HYPHA tag: `TA/API-STREAMING`
> Maps to Mycelium agent: `api-streaming-agent`

## Goal

Own the SSE (Server-Sent Events) endpoint that streams real-time agent status events to the frontend. This closes the observability loop: agents publish to Redis, the API subscribes and re-emits as SSE frames, the dashboard shows live progress.

## Scope

### In Scope

- `backend/api/events.py` — `GET /events/stream?channel=...` endpoint
- FastAPI `StreamingResponse` with `media_type="text/event-stream"`
- Redis pub/sub subscription within the request lifecycle
- Channel allowlist: `agent.status.discovery`, `agent.status.application`
- 15-second heartbeat (`:ping\n\n`) for connection loss detection
- Backpressure handling: drop messages if client falls >100 messages behind
- Auth: same `get_current_user` dependency as other routers

### Out of Scope

- WebSocket alternative (SSE is simpler, HTTP/2 multiplexes fine)
- Event persistence / replay (full event sourcing is iter-5)
- Multi-channel subscription in a single connection
- Client-side reconnection logic (handled in api-client-agent)
- Rate limiting on event stream (trust authenticated users)

## Inputs

- `api-agent`: FastAPI app router registration pattern
- `auth-agent`: `get_current_user` FastAPI dependency
- `obs-agent`: Redis pub/sub channel taxonomy (`agent.status.*`)
- `api-agent`: `get_redis` dependency for Redis client factory

## Outputs (Deliverables)

- `backend/api/events.py`

## Acceptance Criteria

- [ ] `GET /events/stream?channel=agent.status.discovery` returns `Content-Type: text/event-stream`
- [ ] Request requires valid JWT via `Authorization: Bearer` header
- [ ] 401 returned if JWT is missing, invalid, or expired
- [ ] 400 returned if `channel` is not in allowlist
- [ ] Each published Redis message appears as SSE frame: `data: {json}\n\n`
- [ ] Heartbeat `:ping\n\n` emitted every 15 seconds
- [ ] Backpressure: if client queue exceeds 100 messages, drop oldest and emit `event: slow_client\ndata: {"dropped": N}\n\n`
- [ ] `curl -N -H "Authorization: Bearer ${JWT}" http://localhost:8000/events/stream?channel=agent.status.discovery` streams events as published
- [ ] Triggering `DiscoveryOrchestrator.run` from another shell produces visible events on the open curl connection within 100ms
- [ ] Connection properly closed when client disconnects (no resource leaks)
- [ ] No `print()` anywhere — `structlog` only
- [ ] `ruff check backend/api/events.py` clean

## Notes

- Use `asyncio.Queue` for the per-connection message buffer. The Redis subscriber pushes to the queue, the SSE generator reads from it.
- The 100-message backpressure threshold is a heuristic. Log a warning when dropping messages so we can tune in production.
- SSE format is strict: `data: {json}\n\n` with exactly two newlines. The heartbeat is `:ping\n\n` (colon prefix = comment line, ignored by EventSource but keeps connection alive).
- The Redis subscription should be cancelled in a `finally` block to avoid orphaned subscriptions on client disconnect.
- FastAPI's `StreamingResponse` with `background` kwarg can handle the cleanup, but prefer explicit `try/finally` for clarity.
- The `slow_client` event is a best-effort signal. Clients can use it to show a "catching up" indicator, but the primary purpose is preventing server memory exhaustion.
