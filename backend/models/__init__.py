# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
SQLAlchemy ORM models for the Talent Agent system.

Exports all model classes and enums for use throughout the application.
Import all models so SQLAlchemy metadata.create_all picks them up.
"""

# Base and mixins
from backend.models.base import BaseModel, TimestampMixin  # noqa: F401

# Auth models
from backend.models.auth import User, MagicLink  # noqa: F401

# Discovery models and enums
from backend.models.discovery import (  # noqa: F401
    Candidate,
    DiscoveredJob,
    ScoredJob,
    DailyDigest,
    CrawlRun,
    JobSource,
    RemotePreference,
    CrawlRunStatus,
)

# Application models and enums
from backend.models.application import (  # noqa: F401
    ParsedJD,
    TailoredResume,
    CompanyIntel,
    Contact,
    OutreachEmail,
    ApplicationPipeline,
    CRMEvent,
    ApplicationPipelineStatus,
    ContactConfidence,
    OutreachStatus,
)

__all__ = [
    # Base
    "BaseModel",
    "TimestampMixin",
    # Auth
    "User",
    "MagicLink",
    # Discovery
    "Candidate",
    "DiscoveredJob",
    "ScoredJob",
    "DailyDigest",
    "CrawlRun",
    "JobSource",
    "RemotePreference",
    "CrawlRunStatus",
    # Application
    "ParsedJD",
    "TailoredResume",
    "CompanyIntel",
    "Contact",
    "OutreachEmail",
    "ApplicationPipeline",
    "CRMEvent",
    "ApplicationPipelineStatus",
    "ContactConfidence",
    "OutreachStatus",
]
