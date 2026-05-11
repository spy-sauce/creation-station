# HYPHA-APPLICATION-ENGINE

> HYPHA tag: `TA/APPLY`

## Goal

Own the autonomous application pipeline that, for each approved job, runs JD parsing → resume tailoring + company research (parallel) → contact discovery → outreach composition → human-review pause → form submission. Pauses at `AWAITING_REVIEW` until the Review Dashboard approves.

## Scope

### In Scope
- `JDParser` — structured JD signals via Claude (skills, seniority, tech_stack, culture, tone, pain_points, comp, red_flags, application_instructions)
- `ResumeTailor` — Claude-driven resume rewrite grounded in parsed JD + identity profile; gap-aware (no fabrication); change_log
- `CompanyIntelAgent` — company research (about, recent_news, tech_stack, engineering_culture, growth_stage, team_size, notable_facts)
- `ContactFinder` — recipient discovery with HIGH/MEDIUM/LOW confidence + fallback email
- `OutreachComposer` — 150–200-word cold email with 3 subject-line variants, DRAFT state
- `AutoApplyAgent` — Playwright async ATS form filling (Greenhouse / Lever / Workday / Ashby); requires explicit `APPROVED` status to submit; screenshots every major step
- `CRM` — append-only CRM event log per pipeline (`update_pipeline_status`, `log`)
- `ApplicationOrchestrator` — coordinator with `asyncio.gather(resume, intel)` for the parallel step; pause-and-resume across `start()` and `submit()`
- Status state machine per brief §2: `QUEUED → PARSING → TAILORING → RESEARCHING → COMPOSING → AWAITING_REVIEW → APPROVED|REJECTED → SUBMITTED → SENT → TRACKED`
- Events on `agent.status.application` (channel: `_STATUS_CHANNEL`)

### Out of Scope
- The Claude sub-agent dispatcher (`AgentManager`) — owned by agent-manager biome, even though the file lives in `application/`
- Real-time crawling of new jobs (discovery-engine owns)
- Human approval surface (review-dashboard owns)
- Email send (the outreach email stays DRAFT; sending is a future deliverable, not in this freeze)

## Inputs

- schema-core: ORM models (`ApplicationPipeline`, `ParsedJD`, `TailoredResume`, `CompanyIntel`, `Contact`, `CRMEvent`) and matching Pydantic schemas
- discovery-engine: `IdentityProfiler.build_profile`, `CandidateSchema`, `DiscoveredJob` / `ScoredJob`
- `backend/database.py`: `get_db`, Redis client
- `backend/config.py`: `anthropic_api_key`, `max_parallel_applications`
- Anthropic SDK + Playwright async

## Outputs (Deliverables)

Existing files locked at HEAD:
- `backend/agents/application/__init__.py`
- `backend/agents/application/schemas.py`
- `backend/agents/application/jd_parser.py`
- `backend/agents/application/resume_tailor.py`
- `backend/agents/application/company_intel.py`
- `backend/agents/application/contact_finder.py`
- `backend/agents/application/outreach_composer.py`
- `backend/agents/application/auto_apply.py`
- `backend/agents/application/crm.py`
- `backend/agents/application/orchestrator.py`

Internal contracts:
- `ApplicationOrchestrator.start(job_id, candidate_id) -> ApplicationPipelineSchema` — runs through to `AWAITING_REVIEW`
- `ApplicationOrchestrator.submit(pipeline_id) -> None` — runs AutoApply only if pipeline `status == "APPROVED"`
- Pub/sub event shape: `{event: "APPLICATION_STATUS", pipeline_id, candidate_id, status}` on `agent.status.application`
- AutoApply must return `REQUIRES_MANUAL` if CAPTCHA detected — never bypass

## Acceptance Criteria

- [ ] `start(job_id, candidate_id)` on a seeded scored_job completes through `AWAITING_REVIEW` without exceptions
- [ ] An `application_pipelines` row is created on start with `status="QUEUED"`, then walks through `PARSING → TAILORING → RESEARCHING → COMPOSING → AWAITING_REVIEW`
- [ ] `resume_tailor` and `company_intel` run concurrently — log line `application_orchestrator.parallel_complete` appears once both finish
- [ ] On any sub-agent exception, pipeline transitions to `FAILED`, CRM event `PIPELINE_FAILED` logged with `error`, exception re-raises
- [ ] `start()` returns a fully populated `ApplicationPipelineSchema` including `parsed_jd`, `tailored_resume`, `company_intel`, `contact`, `outreach_email`
- [ ] `submit()` refuses to run unless `pipeline.status == "APPROVED"` (raises `ValueError`)
- [ ] CRM events logged: `JD_PARSED`, `RESUME_TAILORED`, `COMPANY_RESEARCHED`, `CONTACT_FOUND`, `EMAIL_DRAFTED`, `SUBMITTED`, `PIPELINE_FAILED` (and any future ones registered through `CRM.log`)
- [ ] `OutreachComposer` output is 150–200 words, contains 3 subject lines, status stays `DRAFT`
- [ ] `ResumeTailor` change_log lists every section touched; full_text never invents employers, dates, titles, or metrics
- [ ] `ContactFinder` assigns `confidence: HIGH | MEDIUM | LOW` and populates `fallback_email` for LOW
- [ ] `AutoApplyAgent` returns `REQUIRES_MANUAL` on CAPTCHA detection; submission is gated on human approval
- [ ] Redis pub/sub publishes `APPLICATION_STATUS` events on every status transition
- [ ] All Claude calls use `claude-sonnet-4-20250514`
- [ ] No `print()` anywhere in the biome
- [ ] `pytest tests/application/ -v` passes (empty dir exists; tests are a leaf-level deliverable)
- [ ] `ruff check backend/agents/application/` clean

## Notes

- The `agent_manager.py` module lives in this directory but is owned by HYPHA-AGENT-MANAGER. Treat it as an inbound dependency from a sibling biome.
- `submit()` reconstructs a `TailoredResumeSchema` from the persisted ORM row — keep this read-path stable.
- `OutreachComposer` rules in §5 of the brief are hard: never "I hope this finds you well," never "I'm reaching out because…". Enforced by the system prompt; a leaf changing the prompt requires brief amendment.
- The Application status machine includes states (`SENT`, `TRACKED`) that AutoApply does not currently transition to. Reaching those states is a follow-up (email-send + reply-tracking), not in this freeze.
- Two `Optional` typing imports in `auto_apply.py` and elsewhere are intentional — Pydantic v2 with `Optional[X]` and `X | None` mix in this codebase; freeze the mix as-is.
- `_publish_status` helper in `orchestrator.py:325-336` is the canonical pub/sub pattern — copy it (don't re-invent) when adding event publishes elsewhere.
