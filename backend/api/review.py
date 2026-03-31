# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def status():
    """Review dashboard status stub."""
    return {"engine": "review", "status": "ready"}
