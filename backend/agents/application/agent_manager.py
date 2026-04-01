# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Agent Manager — dispatches and coordinates application sub-agents via Claude Cloud.

This is the agentic management layer that wraps each application sub-agent
as an autonomous Claude-powered worker. Instead of direct method calls,
each agent is dispatched as an independent Claude API call with its own
system prompt, tool definitions, and execution context.

Architecture:
  AgentManager
    ├── SubAgentRegistry    ← defines available agents + their capabilities
    ├── SubAgentRunner      ← executes a single agent via Claude API tool_use loop
    ├── PipelineDispatcher  ← coordinates multi-agent pipelines with dependency graph
    └── AgentStateStore     ← persists agent state for resume/retry across processes

Execution model:
  1. Master agent receives a pipeline request
  2. Builds a dependency graph of sub-agent tasks
  3. Dispatches independent agents concurrently
  4. Each agent runs its own Claude agentic loop (prompt → tool_use → result)
  5. Results flow back through schemas, feeding dependent agents
  6. State is persisted at every step — crash-safe, resumable

Status per sub-agent:
  QUEUED → DISPATCHED → RUNNING → COMPLETED
                                → FAILED → RETRYING → COMPLETED
                                                    → DEAD
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

import redis.asyncio as aioredis
import structlog
from anthropic import AsyncAnthropic
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings

logger = structlog.get_logger(__name__)

_AGENT_STATUS_CHANNEL = "agent.status.subagent"


# ─── Agent Status ────────────────────────────────────────────────────────────


class AgentStatus(str, Enum):
    """Status lifecycle for each sub-agent execution."""

    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD = "DEAD"


# ─── Agent Definition ───────────────────────────────────────────────────────


@dataclass
class SubAgentDefinition:
    """
    Declares a sub-agent's identity, capabilities, and execution context.

    Each sub-agent gets its own Claude system prompt and tool definitions,
    making it a self-contained autonomous worker.
    """

    name: str
    description: str
    system_prompt: str
    tools: list[dict[str, Any]] = field(default_factory=list)
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_retries: int = 3
    timeout_seconds: int = 120
    dependencies: list[str] = field(default_factory=list)


# ─── Agent Execution Record ─────────────────────────────────────────────────


class AgentExecutionRecord(BaseModel):
    """Tracks a single sub-agent execution — persisted for observability and resume."""

    execution_id: UUID = None
    agent_name: str
    pipeline_id: UUID
    status: str = AgentStatus.QUEUED.value
    input_payload: dict = {}
    output_payload: Optional[dict] = None
    error: Optional[str] = None
    attempt: int = 1
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    token_usage: Optional[dict] = None

    def model_post_init(self, __context: Any) -> None:
        """Set execution_id if not provided."""
        if self.execution_id is None:
            self.execution_id = uuid4()


# ─── Sub-Agent Registry ─────────────────────────────────────────────────────


class SubAgentRegistry:
    """
    Registry of all available sub-agents and their definitions.

    Each agent is declared with its system prompt, tool definitions,
    and dependency requirements. The registry is the source of truth
    for what agents exist and how they should be invoked.
    """

    def __init__(self) -> None:
        self._agents: dict[str, SubAgentDefinition] = {}
        self._register_defaults()

    def register(self, agent: SubAgentDefinition) -> None:
        """Register a sub-agent definition."""
        self._agents[agent.name] = agent
        logger.info("agent_registry.registered", agent=agent.name)

    def get(self, name: str) -> SubAgentDefinition:
        """Retrieve a registered agent definition by name."""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not registered. Available: {list(self._agents.keys())}")
        return self._agents[name]

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def get_dependency_order(self, agent_names: list[str]) -> list[list[str]]:
        """
        Resolve execution order from dependency graph.

        Returns a list of tiers — agents within a tier can run concurrently.
        Agents in tier N+1 depend on agents in tier N.
        """
        resolved: set[str] = set()
        tiers: list[list[str]] = []

        remaining = set(agent_names)
        while remaining:
            tier = []
            for name in list(remaining):
                agent = self.get(name)
                deps = set(agent.dependencies) & set(agent_names)
                if deps.issubset(resolved):
                    tier.append(name)
            if not tier:
                unresolved = {
                    n: self.get(n).dependencies for n in remaining
                }
                raise ValueError(f"Circular dependency detected: {unresolved}")
            for name in tier:
                remaining.discard(name)
                resolved.add(name)
            tiers.append(tier)

        return tiers

    def _register_defaults(self) -> None:
        """Register the standard application engine sub-agents."""

        self.register(SubAgentDefinition(
            name="jd_parser",
            description="Parses job descriptions into structured signals for resume tailoring",
            system_prompt=(
                "You are a JD parsing specialist. Extract structured signals from job descriptions: "
                "required skills, preferred skills, seniority level, team context, responsibilities, "
                "culture signals, tech stack, pain points, tone, compensation, red flags, and "
                "application instructions. Be precise — downstream agents depend on your accuracy."
            ),
            tools=[{
                "name": "parse_job_description",
                "description": "Extract structured data from a raw job description",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string", "description": "UUID of the job"},
                        "title": {"type": "string"},
                        "company": {"type": "string"},
                        "description": {"type": "string", "description": "Raw JD text"},
                    },
                    "required": ["job_id", "title", "company", "description"],
                },
            }],
            max_tokens=2048,
            dependencies=[],
        ))

        self.register(SubAgentDefinition(
            name="resume_tailor",
            description="Rewrites candidate resumes to align with specific job requirements",
            system_prompt=(
                "You are a resume tailoring specialist. Rewrite the candidate's resume to align "
                "with the target role. Rules: NEVER fabricate experience, titles, dates, or metrics. "
                "Mirror JD language naturally. Prioritize relevance over comprehensiveness. "
                "Flag skill gaps in change_log — never invent skills the candidate doesn't have."
            ),
            tools=[{
                "name": "tailor_resume",
                "description": "Rewrite a resume for a specific role based on parsed JD signals",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "candidate_resume": {"type": "string"},
                        "candidate_name": {"type": "string"},
                        "parsed_jd": {"type": "object", "description": "Structured JD signals"},
                        "identity_profile": {"type": "object", "description": "Candidate identity profile"},
                    },
                    "required": ["candidate_resume", "candidate_name", "parsed_jd"],
                },
            }],
            max_tokens=4096,
            dependencies=["jd_parser"],
        ))

        self.register(SubAgentDefinition(
            name="company_intel",
            description="Researches companies to provide real context for outreach",
            system_prompt=(
                "You are a company research specialist. Gather intelligence about the target "
                "company: what they do, recent news, tech stack, engineering culture, growth stage, "
                "team size, and notable facts. The 'notable_facts' field is critical — it becomes "
                "the hook for the outreach email. Make it specific and real."
            ),
            tools=[{
                "name": "research_company",
                "description": "Gather company intelligence from web sources",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "company_url": {"type": "string"},
                        "company_domain": {"type": "string"},
                    },
                    "required": ["company_name"],
                },
            }],
            max_tokens=4096,
            dependencies=["jd_parser"],
        ))

        self.register(SubAgentDefinition(
            name="contact_finder",
            description="Finds the right person to receive cold outreach at the target company",
            system_prompt=(
                "You are a contact discovery specialist. Find the right person to receive "
                "cold outreach — preferably the hiring manager or eng lead. Check the JD for "
                "named contacts first, then use email pattern discovery. Assign confidence: "
                "HIGH (verified), MEDIUM (pattern-matched), LOW (generic fallback). "
                "Never source from data brokers."
            ),
            tools=[{
                "name": "find_contact",
                "description": "Discover the right contact person at a company",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "company_domain": {"type": "string"},
                        "parsed_jd": {"type": "object"},
                        "company_intel": {"type": "object"},
                    },
                    "required": ["company_name"],
                },
            }],
            max_tokens=2048,
            dependencies=["company_intel"],
        ))

        self.register(SubAgentDefinition(
            name="outreach_composer",
            description="Writes cold emails that don't read like cold emails",
            system_prompt=(
                "You are a cold outreach specialist. Write emails that feel personal and real. "
                "Structure: Hook (1 sentence, specific company fact) → Bridge (1-2 sentences) → "
                "Value (2-3 sentences, proof of impact) → Ask (1 sentence, low-friction CTA). "
                "Rules: 150-200 words max. Never 'I hope this finds you well.' Never 'I'm "
                "reaching out because...' Generate 3 subject line variants. Output stays DRAFT."
            ),
            tools=[{
                "name": "compose_outreach",
                "description": "Compose a cold outreach email grounded in real context",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "parsed_jd": {"type": "object"},
                        "company_intel": {"type": "object"},
                        "contact": {"type": "object"},
                        "tailored_resume": {"type": "object"},
                        "candidate_name": {"type": "string"},
                        "candidate_email": {"type": "string"},
                    },
                    "required": ["parsed_jd", "company_intel", "contact", "tailored_resume",
                                 "candidate_name", "candidate_email"],
                },
            }],
            max_tokens=2048,
            dependencies=["resume_tailor", "contact_finder"],
        ))

        self.register(SubAgentDefinition(
            name="auto_apply",
            description="Navigates career pages and fills application forms via browser automation",
            system_prompt=(
                "You are a form submission specialist. Navigate ATS career pages (Greenhouse, "
                "Lever, Workday, Ashby) and fill application forms. CRITICAL: NEVER submit "
                "without explicit human approval. If CAPTCHA detected, mark as REQUIRES_MANUAL. "
                "Screenshot every major step for the audit trail."
            ),
            tools=[{
                "name": "fill_application",
                "description": "Navigate to a job URL and fill the application form",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "job_url": {"type": "string"},
                        "job_id": {"type": "string"},
                        "candidate_info": {"type": "object"},
                        "tailored_resume": {"type": "object"},
                    },
                    "required": ["job_url", "job_id", "candidate_info", "tailored_resume"],
                },
            }],
            max_tokens=2048,
            dependencies=["outreach_composer"],
        ))


# ─── Sub-Agent Runner ───────────────────────────────────────────────────────


class SubAgentRunner:
    """
    Executes a single sub-agent via Claude API tool_use agentic loop.

    Each sub-agent runs as an independent Claude conversation:
      1. System prompt sets the agent's role and constraints
      2. User message provides the task context and input data
      3. Claude responds with tool_use calls
      4. Runner executes tools and feeds results back
      5. Loop continues until Claude produces a final text response

    This is the core execution unit — crash-safe, retryable, and observable.
    """

    def __init__(
        self,
        claude: AsyncAnthropic,
        redis_client: aioredis.Redis,
        tool_handlers: dict[str, Callable] | None = None,
    ) -> None:
        self._claude = claude
        self._redis = redis_client
        self._tool_handlers: dict[str, Callable] = tool_handlers or {}

    def register_tool_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a callable that executes when Claude invokes a tool."""
        self._tool_handlers[tool_name] = handler

    async def run(
        self,
        agent_def: SubAgentDefinition,
        input_payload: dict[str, Any],
        pipeline_id: UUID,
        attempt: int = 1,
    ) -> AgentExecutionRecord:
        """
        Execute a sub-agent and return the execution record.

        Runs the Claude agentic loop: prompt → tool_use → result → repeat
        until the agent produces a final response or exhausts retries.

        Args:
            agent_def: The sub-agent definition from the registry
            input_payload: Context and data for this agent's task
            pipeline_id: Parent pipeline for tracking
            attempt: Current retry attempt number

        Returns:
            AgentExecutionRecord with status, output, and telemetry
        """
        record = AgentExecutionRecord(
            agent_name=agent_def.name,
            pipeline_id=pipeline_id,
            status=AgentStatus.DISPATCHED.value,
            input_payload=input_payload,
            attempt=attempt,
            started_at=datetime.now(timezone.utc),
        )
        log = logger.bind(
            agent=agent_def.name,
            pipeline_id=str(pipeline_id),
            attempt=attempt,
        )
        log.info("subagent_runner.dispatched")
        await self._publish_status(record)

        start_time = time.monotonic()

        try:
            record.status = AgentStatus.RUNNING.value
            await self._publish_status(record)

            # Build the initial messages for the agentic loop
            messages = [
                {
                    "role": "user",
                    "content": json.dumps(input_payload, default=str),
                },
            ]

            final_output = await self._agentic_loop(
                agent_def=agent_def,
                messages=messages,
                log=log,
            )

            record.status = AgentStatus.COMPLETED.value
            record.output_payload = final_output
            record.completed_at = datetime.now(timezone.utc)
            record.duration_ms = int((time.monotonic() - start_time) * 1000)

            log.info(
                "subagent_runner.completed",
                duration_ms=record.duration_ms,
            )

        except Exception as e:
            record.status = AgentStatus.FAILED.value
            record.error = str(e)
            record.completed_at = datetime.now(timezone.utc)
            record.duration_ms = int((time.monotonic() - start_time) * 1000)

            log.error(
                "subagent_runner.failed",
                error=str(e),
                duration_ms=record.duration_ms,
            )

            # Retry if attempts remain
            if attempt < agent_def.max_retries:
                record.status = AgentStatus.RETRYING.value
                await self._publish_status(record)
                backoff = 2 ** attempt
                log.info("subagent_runner.retrying", backoff_seconds=backoff)
                await asyncio.sleep(backoff)
                return await self.run(
                    agent_def=agent_def,
                    input_payload=input_payload,
                    pipeline_id=pipeline_id,
                    attempt=attempt + 1,
                )
            else:
                record.status = AgentStatus.DEAD.value
                log.error("subagent_runner.dead", attempts_exhausted=attempt)

        await self._publish_status(record)
        return record

    async def _agentic_loop(
        self,
        agent_def: SubAgentDefinition,
        messages: list[dict],
        log: Any,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """
        Run the Claude tool_use agentic loop until final response.

        Claude calls tools → we execute them → feed results back → repeat.
        Exits when Claude responds with text (no tool_use) or max iterations hit.
        """
        for iteration in range(max_iterations):
            log.info("subagent_runner.loop_iteration", iteration=iteration)

            response = await self._claude.messages.create(
                model=agent_def.model,
                max_tokens=agent_def.max_tokens,
                system=agent_def.system_prompt,
                tools=agent_def.tools,
                messages=messages,
            )

            # Check if Claude wants to use tools
            tool_use_blocks = [
                block for block in response.content
                if block.type == "tool_use"
            ]

            if not tool_use_blocks:
                # Final response — extract text content
                text_blocks = [
                    block.text for block in response.content
                    if block.type == "text"
                ]
                final_text = "\n".join(text_blocks)

                # Try to parse as JSON, fall back to raw text
                try:
                    return json.loads(final_text)
                except (json.JSONDecodeError, ValueError):
                    return {"result": final_text}

            # Execute each tool call and collect results
            tool_results = []
            for tool_block in tool_use_blocks:
                tool_name = tool_block.name
                tool_input = tool_block.input

                log.info(
                    "subagent_runner.tool_call",
                    tool=tool_name,
                    input_keys=list(tool_input.keys()) if isinstance(tool_input, dict) else None,
                )

                if tool_name in self._tool_handlers:
                    try:
                        result = await self._tool_handlers[tool_name](tool_input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": json.dumps(result, default=str),
                        })
                    except Exception as e:
                        log.error("subagent_runner.tool_error", tool=tool_name, error=str(e))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": json.dumps({"error": str(e)}),
                            "is_error": True,
                        })
                else:
                    # No handler — return the tool input as the result
                    # This allows Claude to "declare" structured output via tool_use
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(tool_input, default=str),
                    })

            # Append assistant response and tool results for next iteration
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        log.warning("subagent_runner.max_iterations", iterations=max_iterations)
        return {"error": "Max agentic loop iterations reached", "iterations": max_iterations}

    async def _publish_status(self, record: AgentExecutionRecord) -> None:
        """Publish sub-agent status event to Redis pub/sub."""
        payload = json.dumps({
            "event": "SUBAGENT_STATUS",
            "execution_id": str(record.execution_id),
            "agent_name": record.agent_name,
            "pipeline_id": str(record.pipeline_id),
            "status": record.status,
            "attempt": record.attempt,
            "duration_ms": record.duration_ms,
        })
        await self._redis.publish(_AGENT_STATUS_CHANNEL, payload)


# ─── Pipeline Dispatcher ────────────────────────────────────────────────────


class PipelineDispatcher:
    """
    Coordinates multi-agent pipelines with dependency-aware execution.

    Resolves the dependency graph into execution tiers, dispatches
    agents within each tier concurrently, and feeds outputs from
    completed agents into dependent agents as input context.

    This is the brains of the agentic management layer — it decides
    what runs when and wires data between agents.
    """

    def __init__(
        self,
        registry: SubAgentRegistry,
        runner: SubAgentRunner,
        redis_client: aioredis.Redis,
        max_concurrency: int | None = None,
    ) -> None:
        self._registry = registry
        self._runner = runner
        self._redis = redis_client
        self._max_concurrency = max_concurrency or settings.max_parallel_applications
        self._semaphore = asyncio.Semaphore(self._max_concurrency)

    async def dispatch_pipeline(
        self,
        pipeline_id: UUID,
        agent_names: list[str],
        initial_context: dict[str, Any],
        on_agent_complete: Callable | None = None,
    ) -> dict[str, AgentExecutionRecord]:
        """
        Execute a full pipeline of sub-agents respecting dependencies.

        Args:
            pipeline_id: Pipeline being executed
            agent_names: Which agents to run (subset of registry)
            initial_context: Starting data (candidate, job, etc.)
            on_agent_complete: Optional callback after each agent completes

        Returns:
            Dict mapping agent_name → AgentExecutionRecord
        """
        log = logger.bind(pipeline_id=str(pipeline_id))
        log.info(
            "pipeline_dispatcher.starting",
            agents=agent_names,
        )

        # Resolve execution order
        tiers = self._registry.get_dependency_order(agent_names)
        log.info("pipeline_dispatcher.tiers_resolved", tiers=tiers)

        # Accumulated results from all completed agents
        context = dict(initial_context)
        results: dict[str, AgentExecutionRecord] = {}

        for tier_idx, tier in enumerate(tiers):
            log.info(
                "pipeline_dispatcher.tier_start",
                tier=tier_idx,
                agents=tier,
            )

            # Dispatch all agents in this tier concurrently
            tasks = []
            for agent_name in tier:
                agent_def = self._registry.get(agent_name)
                task = asyncio.create_task(
                    self._dispatch_with_semaphore(
                        agent_def=agent_def,
                        input_payload=context,
                        pipeline_id=pipeline_id,
                    )
                )
                tasks.append((agent_name, task))

            # Await all agents in this tier
            for agent_name, task in tasks:
                record = await task
                results[agent_name] = record

                if record.status == AgentStatus.COMPLETED.value and record.output_payload:
                    # Merge output into context for downstream agents
                    context[f"{agent_name}_output"] = record.output_payload
                    log.info(
                        "pipeline_dispatcher.agent_completed",
                        agent=agent_name,
                        duration_ms=record.duration_ms,
                    )
                elif record.status in (AgentStatus.FAILED.value, AgentStatus.DEAD.value):
                    log.error(
                        "pipeline_dispatcher.agent_failed",
                        agent=agent_name,
                        error=record.error,
                    )

                if on_agent_complete:
                    await on_agent_complete(agent_name, record)

            # Check if any critical agent failed — abort pipeline if so
            failed = [
                name for name, rec in results.items()
                if rec.status in (AgentStatus.FAILED.value, AgentStatus.DEAD.value)
            ]
            if failed:
                log.error(
                    "pipeline_dispatcher.tier_failed",
                    tier=tier_idx,
                    failed_agents=failed,
                )
                # Publish pipeline failure
                await self._publish_pipeline_status(pipeline_id, "FAILED", {
                    "failed_agents": failed,
                    "completed_tier": tier_idx,
                })
                break

        log.info(
            "pipeline_dispatcher.complete",
            total_agents=len(results),
            completed=[n for n, r in results.items() if r.status == AgentStatus.COMPLETED.value],
            failed=[n for n, r in results.items() if r.status != AgentStatus.COMPLETED.value],
        )

        return results

    async def _dispatch_with_semaphore(
        self,
        agent_def: SubAgentDefinition,
        input_payload: dict[str, Any],
        pipeline_id: UUID,
    ) -> AgentExecutionRecord:
        """Run a sub-agent within the concurrency semaphore."""
        async with self._semaphore:
            return await self._runner.run(
                agent_def=agent_def,
                input_payload=input_payload,
                pipeline_id=pipeline_id,
            )

    async def _publish_pipeline_status(
        self,
        pipeline_id: UUID,
        status: str,
        details: dict | None = None,
    ) -> None:
        """Publish pipeline-level status to Redis pub/sub."""
        payload = json.dumps({
            "event": "PIPELINE_STATUS",
            "pipeline_id": str(pipeline_id),
            "status": status,
            "details": details or {},
        })
        await self._redis.publish("agent.status.application", payload)


# ─── Agent Manager (top-level facade) ───────────────────────────────────────


class AgentManager:
    """
    Top-level facade for the agentic management layer.

    Provides a clean interface for the API layer and orchestrator to dispatch
    sub-agent pipelines. Handles initialization of the registry, runner, and
    dispatcher, and exposes methods for common pipeline patterns.

    Usage:
        manager = AgentManager(db, redis_client)

        # Run the full application pipeline
        results = await manager.run_application_pipeline(
            pipeline_id=pipeline_id,
            job_data={...},
            candidate_data={...},
        )

        # Run a single agent
        record = await manager.run_single_agent(
            agent_name="jd_parser",
            input_payload={...},
            pipeline_id=pipeline_id,
        )
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: aioredis.Redis,
    ) -> None:
        self._db = db
        self._redis = redis_client
        self._claude = AsyncAnthropic(api_key=settings.anthropic_api_key)

        self._registry = SubAgentRegistry()
        self._runner = SubAgentRunner(
            claude=self._claude,
            redis_client=redis_client,
        )
        self._dispatcher = PipelineDispatcher(
            registry=self._registry,
            runner=self._runner,
            redis_client=redis_client,
        )

        # Wire up tool handlers that connect Claude's tool_use to real agent code
        self._register_tool_handlers()

    def _register_tool_handlers(self) -> None:
        """
        Connect Claude tool_use calls to real agent implementations.

        When Claude calls a tool like 'parse_job_description', the handler
        invokes the actual JDParser agent code and returns structured results.
        """
        from backend.agents.application.jd_parser import JDParser
        from backend.agents.application.resume_tailor import ResumeTailor
        from backend.agents.application.company_intel import CompanyIntelAgent
        from backend.agents.application.contact_finder import ContactFinder
        from backend.agents.application.outreach_composer import OutreachComposer
        from backend.agents.application.auto_apply import AutoApplyAgent

        jd_parser = JDParser(self._db, self._claude)
        resume_tailor = ResumeTailor(self._db, self._claude)
        company_intel = CompanyIntelAgent(self._db, self._redis, self._claude)
        contact_finder = ContactFinder(self._db)
        outreach_composer = OutreachComposer(self._db, self._claude)
        auto_apply = AutoApplyAgent()

        async def handle_parse_jd(input_data: dict) -> dict:
            """Execute JD parsing via the real JDParser agent."""
            from backend.agents.discovery.schemas import DiscoveredJobSchema, ScoredJobSchema, ScoreBreakdown
            job_schema = DiscoveredJobSchema(
                id=input_data["job_id"],
                candidate_id=input_data.get("candidate_id", "00000000-0000-0000-0000-000000000000"),
                title=input_data["title"],
                company=input_data["company"],
                description=input_data["description"],
                url=input_data.get("url", ""),
                url_hash=input_data.get("url_hash", ""),
                source=input_data.get("source", "cloud_agent"),
            )
            scored = ScoredJobSchema(
                job=job_schema,
                scores=ScoreBreakdown(),
                composite_score=70,
                reasoning="",
            )
            result = await jd_parser.parse(scored)
            return result.model_dump(mode="json")

        async def handle_tailor_resume(input_data: dict) -> dict:
            """Execute resume tailoring via the real ResumeTailor agent."""
            from backend.agents.application.schemas import ParsedJDSchema
            from backend.agents.discovery.schemas import CandidateSchema
            from backend.agents.discovery.identity_profiler import IdentityProfiler

            parsed_jd = ParsedJDSchema(**input_data["parsed_jd"])
            candidate = CandidateSchema(**input_data["candidate_info"])

            profiler = IdentityProfiler(self._redis, self._claude)
            profile = await profiler.build_profile(candidate)

            result = await resume_tailor.tailor(parsed_jd, candidate, profile)
            return result.model_dump(mode="json")

        async def handle_research_company(input_data: dict) -> dict:
            """Execute company research via the real CompanyIntelAgent."""
            result = await company_intel.research(
                company_name=input_data["company_name"],
                company_url=input_data.get("company_url"),
            )
            return result.model_dump(mode="json")

        async def handle_find_contact(input_data: dict) -> dict:
            """Execute contact discovery via the real ContactFinder."""
            from backend.agents.application.schemas import CompanyIntelSchema, ParsedJDSchema
            intel = CompanyIntelSchema(**input_data["company_intel"])
            parsed_jd = ParsedJDSchema(**input_data["parsed_jd"])
            result = await contact_finder.find(intel, parsed_jd)
            return result.model_dump(mode="json")

        async def handle_compose_outreach(input_data: dict) -> dict:
            """Execute outreach composition via the real OutreachComposer."""
            from backend.agents.application.schemas import (
                ParsedJDSchema, CompanyIntelSchema, ContactSchema, TailoredResumeSchema,
            )
            from backend.agents.discovery.identity_profiler import IdentityProfiler
            from backend.agents.discovery.schemas import CandidateSchema

            parsed_jd = ParsedJDSchema(**input_data["parsed_jd"])
            intel = CompanyIntelSchema(**input_data["company_intel"])
            contact = ContactSchema(**input_data["contact"])
            resume = TailoredResumeSchema(**input_data["tailored_resume"])

            # Build profile for outreach context
            candidate_data = input_data.get("candidate_info", {})
            candidate = CandidateSchema(**candidate_data) if candidate_data else None
            profile = None
            if candidate:
                profiler = IdentityProfiler(self._redis, self._claude)
                profile = await profiler.build_profile(candidate)

            result = await outreach_composer.compose(
                parsed_jd=parsed_jd,
                intel=intel,
                contact=contact,
                resume=resume,
                profile=profile,
                candidate_name=input_data.get("candidate_name", ""),
                candidate_email=input_data.get("candidate_email", ""),
                candidate_github=input_data.get("candidate_github"),
                candidate_linkedin=input_data.get("candidate_linkedin"),
            )
            return result.model_dump(mode="json")

        async def handle_fill_application(input_data: dict) -> dict:
            """Execute form filling via the real AutoApplyAgent."""
            from backend.agents.application.schemas import TailoredResumeSchema
            from backend.agents.discovery.schemas import CandidateSchema

            candidate = CandidateSchema(**input_data["candidate_info"])
            resume = TailoredResumeSchema(**input_data["tailored_resume"])

            result = await auto_apply.submit(
                job_url=input_data["job_url"],
                job_id=input_data["job_id"],
                pipeline_id=input_data.get("pipeline_id", "00000000-0000-0000-0000-000000000000"),
                candidate=candidate,
                resume=resume,
            )
            return result.model_dump(mode="json")

        # Register all handlers
        self._runner.register_tool_handler("parse_job_description", handle_parse_jd)
        self._runner.register_tool_handler("tailor_resume", handle_tailor_resume)
        self._runner.register_tool_handler("research_company", handle_research_company)
        self._runner.register_tool_handler("find_contact", handle_find_contact)
        self._runner.register_tool_handler("compose_outreach", handle_compose_outreach)
        self._runner.register_tool_handler("fill_application", handle_fill_application)

    async def run_application_pipeline(
        self,
        pipeline_id: UUID,
        job_data: dict[str, Any],
        candidate_data: dict[str, Any],
        agents: list[str] | None = None,
        on_agent_complete: Callable | None = None,
    ) -> dict[str, AgentExecutionRecord]:
        """
        Run the full application pipeline for an approved job.

        Dispatches all sub-agents in dependency order, feeding outputs
        between agents automatically.

        Args:
            pipeline_id: Pipeline ID for tracking
            job_data: Job details (id, title, company, description, url)
            candidate_data: Candidate details (name, email, resume, etc.)
            agents: Optional subset of agents to run (defaults to full pipeline)
            on_agent_complete: Optional callback after each agent finishes

        Returns:
            Dict mapping agent_name → AgentExecutionRecord
        """
        default_agents = [
            "jd_parser",
            "resume_tailor",
            "company_intel",
            "contact_finder",
            "outreach_composer",
        ]
        agent_names = agents or default_agents

        initial_context = {
            "job": job_data,
            "candidate_info": candidate_data,
            "pipeline_id": str(pipeline_id),
            **job_data,
        }

        return await self._dispatcher.dispatch_pipeline(
            pipeline_id=pipeline_id,
            agent_names=agent_names,
            initial_context=initial_context,
            on_agent_complete=on_agent_complete,
        )

    async def run_single_agent(
        self,
        agent_name: str,
        input_payload: dict[str, Any],
        pipeline_id: UUID,
    ) -> AgentExecutionRecord:
        """
        Run a single sub-agent in isolation.

        Useful for re-running a failed agent, testing, or ad-hoc execution.

        Args:
            agent_name: Name of the registered agent to run
            input_payload: Input data for the agent
            pipeline_id: Pipeline ID for tracking

        Returns:
            AgentExecutionRecord with full execution details
        """
        agent_def = self._registry.get(agent_name)
        return await self._runner.run(
            agent_def=agent_def,
            input_payload=input_payload,
            pipeline_id=pipeline_id,
        )

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents with their metadata."""
        agents = []
        for name in self._registry.list_agents():
            agent_def = self._registry.get(name)
            agents.append({
                "name": agent_def.name,
                "description": agent_def.description,
                "dependencies": agent_def.dependencies,
                "model": agent_def.model,
                "max_retries": agent_def.max_retries,
                "timeout_seconds": agent_def.timeout_seconds,
            })
        return agents

    def get_execution_plan(
        self, agent_names: list[str] | None = None
    ) -> list[list[str]]:
        """
        Preview the execution order without running anything.

        Returns tiers of agents — agents within a tier run concurrently.

        Args:
            agent_names: Which agents to plan for (defaults to full pipeline)

        Returns:
            List of tiers, where each tier is a list of agent names
        """
        default_agents = [
            "jd_parser",
            "resume_tailor",
            "company_intel",
            "contact_finder",
            "outreach_composer",
        ]
        names = agent_names or default_agents
        return self._registry.get_dependency_order(names)
