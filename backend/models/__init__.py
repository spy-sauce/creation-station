# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

# Import all models so SQLAlchemy metadata.create_all picks them up
from backend.models.base import BaseModel  # noqa: F401
from backend.models.auth import User, MagicLink  # noqa: F401
from backend.models.discovery import (  # noqa: F401
    Candidate, DiscoveredJob, ScoredJob, DailyDigest, CrawlRun,
)
from backend.models.application import (  # noqa: F401
    ParsedJD, TailoredResume, CompanyIntel, Contact,
    OutreachEmail, ApplicationPipeline, ApplicationResult, CRMEvent,
)
