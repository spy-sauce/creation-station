# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from fastapi import APIRouter
from backend.api import discovery, application, review

router = APIRouter(prefix="/api/v1")

router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
router.include_router(application.router, prefix="/application", tags=["application"])
router.include_router(review.router, prefix="/review", tags=["review"])
