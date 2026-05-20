# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Discovery Engine — the job discovery and scoring pipeline.

This module provides:
  - DiscoveryOrchestrator: Main entry point for daily discovery runs
  - IdentityProfiler: Builds rich identity models from candidate profiles
  - ArchetypeGenerator: Expands profiles into search manifests
  - CrawlerAgent: Crawls job boards and career pages
  - RelevanceScorer: Scores jobs against candidate profiles
  - DigestBuilder: Compiles scored jobs into daily digests

Schemas:
  - CandidateSchema, IdentityProfileSchema, SearchManifestSchema
  - DiscoveredJobSchema, ScoredJobSchema, ScoreBreakdown
  - DailyDigestSchema
"""

from backend.agents.discovery.orchestrator import DiscoveryOrchestrator
from backend.agents.discovery.identity_profiler import IdentityProfiler
from backend.agents.discovery.archetype_generator import ArchetypeGenerator
from backend.agents.discovery.crawler_agent import CrawlerAgent
from backend.agents.discovery.relevance_scorer import RelevanceScorer
from backend.agents.discovery.digest_builder import DigestBuilder
from backend.agents.discovery.schemas import (
    CandidateSchema,
    IdentityProfileSchema,
    IdentityProfile,
    SearchManifestSchema,
    DiscoveredJobSchema,
    ScoreBreakdown,
    ScoredJobSchema,
    DailyDigestSchema,
)

__all__ = [
    # Classes
    "DiscoveryOrchestrator",
    "IdentityProfiler",
    "ArchetypeGenerator",
    "CrawlerAgent",
    "RelevanceScorer",
    "DigestBuilder",
    # Schemas
    "CandidateSchema",
    "IdentityProfileSchema",
    "IdentityProfile",
    "SearchManifestSchema",
    "DiscoveredJobSchema",
    "ScoreBreakdown",
    "ScoredJobSchema",
    "DailyDigestSchema",
]
