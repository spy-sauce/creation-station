# HYPHA-AGENT-MANAGER

> HYPHA tag: `TA/AGENTS`

## Goal

Own the agentic management layer that wraps each application sub-agent as an autonomous Claude `tool_use` worker. Provides dependency-graph dispatching, retry-with-backoff, crash-safe execution records, and per-agent status pub/sub.

## Scope

### In Scope
- `AgentStatus` enum (QUEUED, DISPATCHED, RUNNING, COMPLETED, FAILED, RETRYING, DEAD)
- `SubAgentDefinition` dataclass (name, description, system_prompt, tools, model, max_tokens, max_retries, timeout_seconds, dependencies)
- `AgentExecutionRecord` Pydantic model (execution_id, status, input_payload, output_payload, error, attempt, started/completed, duration_ms, token_usage)
- `SubAgentRegistry` — registers + retrieves definitions, resolves dependency tiers, ships with defaults for the 6 application sub-agents (`jd_parser`, `resume_tailor`, `company_intel`, `contact_finder`, `outreach_composer`, `auto_apply`)
- `SubAgentRunner` — executes a single agent via Claude tool_use agentic loop with retry + exp backoff
- `PipelineDispatcher` — runs tiers concurrently within a semaphore, threads outputs into dependent agents' context
- `AgentManager` — top-level facade (`run_application_pipeline`, `run_single_agent`, `list_agents`, `get_execution_plan`); registers tool handlers that bridge Claude tool_use → real agent code
- Pub/sub channel `agent.status.subagent` for per-execution events; `agent.status.application` for `PIPELINE_STATUS` events

### Out of Scope
- The per-agent business logic (lives in `application-engine` modules; this biome calls them as tool handlers)
- HTTP API to dispatch agents directly (could be added in api-surface; not in this freeze)
- Persistence of `AgentExecutionRecord` to Postgres (currently in-memory + pub/sub only — adding a table is a follow-up)
- Cross-biome agent registry (only application sub-agents are registered; adding discovery agents is a future leaf)

## Inputs

- application-engine: real agent classes (`JDParser`, `ResumeTailor`, `CompanyIntelAgent`, `ContactFinder`, `OutreachComposer`, `AutoApplyAgent`) and their Pydantic schemas
- discovery-engine: `IdentityProfiler.build_profile` (used by tailor + outreach handlers), `CandidateSchema`
- `backend/database.py`: `get_db`, Redis client
- `backend/config.py`: `anthropic_api_key`, `max_parallel_applications`

## Outputs (Deliverables)

Existing file locked at HEAD:
- `backend/agents/application/agent_manager.py`

Internal contracts:
- `AgentManager.run_application_pipeline(pipeline_id, job_data, candidate_data, agents=None, on_agent_complete=None) -> dict[str, AgentExecutionRecord]`
- `AgentManager.run_single_agent(agent_name, input_payload, pipeline_id) -> AgentExecutionRecord`
- `AgentManager.get_execution_plan(agent_names=None) -> list[list[str]]` — tier preview
- Tool-use bridge handlers: `parse_job_description`, `tailor_resume`, `research_company`, `find_contact`, `compose_outreach`, `fill_application`
- Event channel `agent.status.subagent` payload: `{event: "SUBAGENT_STATUS", execution_id, agent_name, pipeline_id, status, attempt, duration_ms}`

## Acceptance Criteria

- [ ] `AgentManager(db, redis_client)` initializes without exception; registry contains all 6 default agents
- [ ] `get_execution_plan(default_agents)` returns tiers `[["jd_parser"], ["resume_tailor", "company_intel"], ["contact_finder"], ["outreach_composer"]]` (auto_apply excluded from default)
- [ ] `get_dependency_order` raises `ValueError("Circular dependency detected…")` if a circular reference is introduced
- [ ] Calling `run_single_agent("jd_parser", {…}, pipeline_id)` returns an `AgentExecutionRecord` with `status="COMPLETED"` and an `output_payload`
- [ ] On Claude tool_use that fails: runner retries up to `max_retries`, with backoff `2^attempt` seconds, then marks `DEAD`
- [ ] Every status transition publishes to `agent.status.subagent` (`DISPATCHED`, `RUNNING`, `RETRYING`, `COMPLETED`, `FAILED`, `DEAD`)
- [ ] `PipelineDispatcher` aborts the pipeline if any agent in a tier reaches `FAILED` or `DEAD`, publishing a `PIPELINE_STATUS` failure event with `failed_agents` + `completed_tier`
- [ ] Pipeline dispatcher concurrency is bounded by `settings.max_parallel_applications` (or a constructor override)
- [ ] Tool handler exceptions are caught and returned as `is_error: true` tool results — Claude can recover or fail gracefully
- [ ] Agentic loop exits cleanly after `max_iterations=10` without crashing, returning `{error: "Max agentic loop iterations reached"}`
- [ ] `list_agents()` returns metadata for all 6 default agents (name, description, dependencies, model, max_retries, timeout_seconds)
- [ ] All Claude calls in this biome use `claude-sonnet-4-20250514`
- [ ] `ruff check backend/agents/application/agent_manager.py` clean

## Notes

- This biome holds the **only Claude tool_use loop in the codebase**. Other agents call Claude directly via `messages.create` without tools. The tool_use loop here is the agentic mechanism — preserve the protocol.
- The two execution paths (direct call via `ApplicationOrchestrator` vs. Claude tool_use via `AgentManager`) both exist intentionally — the orchestrator path is the canonical Phase 1 path; agent_manager is the agentic-experiment path. Both must continue to work.
- Output JSON parsing falls back to `{"result": final_text}` on `JSONDecodeError` — downstream tool handlers should handle the raw-text case if they need structured output.
- The `_register_defaults` system prompts are part of the frozen contract. Changing them requires a brief amendment.
- `dispatch_pipeline` builds context by accumulating `{agent_name}_output` keys — downstream agents see prior outputs via that naming.
- Tool handlers in `_register_tool_handlers` reconstruct Pydantic schemas from the input dict (e.g., `ParsedJDSchema(**input_data["parsed_jd"])`). Schema drift will break tool handlers — schema-core is the gate.
- Pub/sub event names are stable surface; the dashboard subscribes by exact channel + event-discriminator.
