# HYPHA-OBSERVABILITY

> HYPHA tag: `TA/OBS`

## Goal

Own the cross-cutting observability surface: structured logging configuration, the agent lifecycle state machine (canonical reference), the Redis pub/sub event taxonomy, and the CRM event log. Make every agent transition visible — in the logs, on the bus, and in the dashboard.

## Scope

### In Scope
- `structlog` config (JSON in non-dev, pretty in dev; PII redaction policy)
- Canonical agent lifecycle state machine (per repo CLAUDE.md and brief §2)
- Redis pub/sub channel taxonomy: `agent.status.discovery`, `agent.status.application`, `agent.status.subagent`
- Event payload schemas (JSON, with `event` discriminator)
- CRM event log (`CRMEvent` table + `CRM` class) — append-only, per-pipeline event stream
- `nutrient_audit` table (analogue from live-grid run7 brief) — if added; not yet present in this repo, optional follow-up
- Health endpoint contract (`GET /health` → `{status, version}`)
- PII redaction guarantees in all logged Claude prompt/response pairs

### Out of Scope
- External APM (Datadog, New Relic, Sentry) integration
- Metrics push (Prometheus) — pub/sub is the bus; metrics pipe is a follow-up
- Alerting (PagerDuty / Opsgenie) — out of scope
- Distributed tracing (OpenTelemetry) — design-for-compatible, not yet wired
- Frontend telemetry / RUM
- Cost tracking (token usage) beyond what `AgentExecutionRecord.token_usage` already captures

## Inputs

- discovery-engine: emits `agent.status.discovery` events
- application-engine: emits `agent.status.application` events + CRM rows
- agent-manager: emits `agent.status.subagent` events
- api-surface: serves `/health`
- schema-core: `CRMEvent` table

## Outputs (Deliverables)

Locked references (existing in code; this HYPHA documents and enforces):
- `structlog` usage across every agent module (`logger = structlog.get_logger(__name__)`)
- Redis publish helpers (`_publish_status` in `application/orchestrator.py:325-336` is canonical pattern)
- `CRM` class in `backend/agents/application/crm.py`
- `agent.status.subagent` payload in `agent_manager.py:570-582`
- `agent.status.application` payload (`APPLICATION_STATUS`, `PIPELINE_STATUS`) in `agent_manager.py:729-742`

This HYPHA does not own new files; it owns conventions that the other biomes must enforce.

## Acceptance Criteria

- [ ] Every agent module imports `structlog` and binds context via `logger.bind(…)` before multi-step logging
- [ ] No `print()` statements anywhere in `backend/`
- [ ] Every Redis pub/sub publish uses one of the three channels exactly: `agent.status.discovery`, `agent.status.application`, `agent.status.subagent`
- [ ] Every event payload is JSON with an `event` field (SCREAMING_SNAKE_CASE: `APPLICATION_STATUS`, `SUBAGENT_STATUS`, `PIPELINE_STATUS`, `DIGEST_READY`, …)
- [ ] Discovery orchestrator publishes a `DIGEST_READY` event on `agent.status.discovery` when a run completes (currently TODO — wire as a leaf inside discovery-engine)
- [ ] Every Claude API call logs `{model, max_tokens, prompt_tokens, completion_tokens}` at INFO; full prompt/response only at DEBUG
- [ ] PII (resume_text, candidate email, contact email, personal_context) is redacted from INFO logs
- [ ] Agent lifecycle transitions in `application_pipelines.status` always reflect a CRM event row (`update_pipeline_status` writes both)
- [ ] `GET /health` returns `{status: "ok", version}` where `version` is sourced from a config/env var (frozen contract for Digital Dash health-check)
- [ ] `ruff check` is clean across all agent modules wrt logging (e.g., no F401 unused `structlog` imports)
- [ ] Smoke test: pubsub-subscribe to all three channels, run a full discovery + application pipeline, observe events on each channel in expected order

## Notes

- This biome is **enforcement, not new code**. Most of the work is in code review: making sure every other biome's commits respect these conventions.
- PII redaction policy: never log resume text, candidate email, contact email, or personal_context at INFO or above. Use a `_redact` helper or omit the field entirely.
- The Discovery side does NOT yet publish pub/sub events (only the Application side does). Wiring this is a small TODO and a deliverable inside `HYPHA-DISCOVERY-ENGINE` — this HYPHA enforces the channel name and event shape.
- The CRM event log is the auditable source of truth for what each pipeline did. Keep it append-only; do not delete or update rows.
- Future: a sporenet-style dashboard could subscribe to all three channels and render a live run view. Not part of this freeze; design pub/sub payloads to be friendly to that future consumer (stable field names, no breaking renames).
- `nutrient_audit` is a useful pattern from live-grid run7 — if added later, lives here and is consumed by every cross-biome lifecycle event.
- This HYPHA is the natural integration point for a future Mycelium HYPHA NODE adapter: every event published here could become a SPORE on the Biome Bus. Design-for, do not wire.
