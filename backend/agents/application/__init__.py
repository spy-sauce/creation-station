# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Application Engine — autonomous job application pipeline.

Pipeline flow:
  JD parsing → resume tailoring + company research (parallel) → contact discovery →
  outreach composition → human review pause → form submission

Agents:
  - JDParser: Extracts structured signals from job descriptions
  - ResumeTailor: Rewrites resume to match specific roles
  - CompanyIntelAgent: Researches companies for outreach context
  - ContactFinder: Discovers recipients with confidence levels
  - OutreachComposer: Writes personalized cold emails
  - AutoApplyAgent: Fills ATS forms via Playwright
  - CRM: Logs application lifecycle events
  - ApplicationOrchestrator: Coordinates the full pipeline
"""

from backend.agents.application.schemas import (
    ParsedJDSchema,
    TailoredResumeSchema,
    CompanyIntelSchema,
    ContactSchema,
    OutreachEmailSchema,
    ApplicationResultSchema,
    ApplicationPipelineSchema,
    CRMEventSchema,
)
from backend.agents.application.jd_parser import JDParser
from backend.agents.application.resume_tailor import ResumeTailor
from backend.agents.application.company_intel import CompanyIntelAgent
from backend.agents.application.contact_finder import ContactFinder
from backend.agents.application.outreach_composer import OutreachComposer
from backend.agents.application.auto_apply import AutoApplyAgent
from backend.agents.application.crm import CRM
from backend.agents.application.orchestrator import ApplicationOrchestrator
from backend.agents.application.agent_manager import (
    AgentManager,
    AgentStatus,
    AgentExecutionRecord,
    SubAgentDefinition,
    SubAgentRegistry,
    SubAgentRunner,
    PipelineDispatcher,
)

__all__ = [
    # Schemas
    "ParsedJDSchema",
    "TailoredResumeSchema",
    "CompanyIntelSchema",
    "ContactSchema",
    "OutreachEmailSchema",
    "ApplicationResultSchema",
    "ApplicationPipelineSchema",
    "CRMEventSchema",
    # Agents
    "JDParser",
    "ResumeTailor",
    "CompanyIntelAgent",
    "ContactFinder",
    "OutreachComposer",
    "AutoApplyAgent",
    "CRM",
    "ApplicationOrchestrator",
    # Agent Manager (agents-agent biome)
    "AgentManager",
    "AgentStatus",
    "AgentExecutionRecord",
    "SubAgentDefinition",
    "SubAgentRegistry",
    "SubAgentRunner",
    "PipelineDispatcher",
]
