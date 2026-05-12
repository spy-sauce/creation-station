# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Onboarding API — resume upload and candidate profile creation.

POST  /onboarding/resume       → upload resume PDF, extract text
POST  /onboarding/profile      → save candidate profile + preferences
GET   /onboarding/status       → check onboarding completion status
"""

import uuid
import os
import tempfile
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.api.auth import get_current_user
from backend.models.auth import User
from backend.models.discovery import Candidate

logger = structlog.get_logger(__name__)
router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ResumeUploadResponse(BaseModel):
    """Response after uploading and parsing a resume."""
    message: str
    candidate_id: str
    text_length: int
    preview: str  # First 500 chars of extracted text


class ProfilePayload(BaseModel):
    """Candidate profile data from the onboarding wizard."""
    name: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    personal_context: Optional[str] = None
    target_locations: Optional[list[str]] = None
    remote_preference: str = "flexible"
    min_compensation: Optional[int] = None
    excluded_companies: Optional[list[str]] = None
    excluded_industries: Optional[list[str]] = None


class ProfileResponse(BaseModel):
    """Response after saving candidate profile."""
    message: str
    candidate_id: str
    is_onboarded: bool


class OnboardingStatusResponse(BaseModel):
    """Current onboarding status."""
    is_onboarded: bool
    has_resume: bool
    has_profile: bool
    candidate_id: Optional[str] = None


# ─── PDF Text Extraction ────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text content from a PDF file using PyMuPDF."""
    import fitz  # PyMuPDF

    text_parts = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise ValueError("Could not extract any text from the PDF")
    return full_text


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/resume", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a resume PDF. Extracts text and creates/updates the candidate record.

    Accepts: application/pdf
    Max size: 10MB
    """
    # Validate file type
    if not file.content_type or "pdf" not in file.content_type.lower():
        raise HTTPException(
            status_code=422,
            detail="Only PDF files are accepted. Please upload a .pdf file.",
        )

    # Read file contents
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=422, detail="File too large. Max 10MB.")

    # Extract text from PDF
    try:
        resume_text = extract_text_from_pdf(contents)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("onboarding.pdf_extraction_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to extract text from PDF. Please try a different file.",
        )

    # Find or create candidate record
    result = await db.execute(
        select(Candidate).where(Candidate.email == current_user.email)
    )
    candidate = result.scalar_one_or_none()

    if candidate:
        candidate.resume_text = resume_text
    else:
        candidate = Candidate(
            email=current_user.email,
            name=current_user.name or current_user.email.split("@")[0],
            resume_text=resume_text,
        )
        db.add(candidate)
        await db.flush()

    # Link user to candidate
    current_user.candidate_id = candidate.id
    await db.commit()

    logger.info(
        "onboarding.resume_uploaded",
        user_id=str(current_user.id),
        candidate_id=str(candidate.id),
        text_length=len(resume_text),
    )

    return ResumeUploadResponse(
        message="Resume uploaded and parsed successfully",
        candidate_id=str(candidate.id),
        text_length=len(resume_text),
        preview=resume_text[:500],
    )


@router.post("/profile", response_model=ProfileResponse)
async def save_profile(
    payload: ProfilePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save candidate profile and preferences from the onboarding wizard.

    Requires resume to be uploaded first (candidate record must exist).
    """
    if not current_user.candidate_id:
        raise HTTPException(
            status_code=400,
            detail="Please upload your resume first before completing your profile.",
        )

    result = await db.execute(
        select(Candidate).where(Candidate.id == current_user.candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate record not found")

    # Update candidate fields
    candidate.name = payload.name
    candidate.linkedin_url = payload.linkedin_url
    candidate.github_url = payload.github_url
    candidate.personal_context = payload.personal_context
    candidate.target_locations = payload.target_locations
    candidate.remote_preference = payload.remote_preference
    candidate.min_compensation = payload.min_compensation
    candidate.excluded_companies = payload.excluded_companies
    candidate.excluded_industries = payload.excluded_industries

    # Update user
    current_user.name = payload.name
    current_user.is_onboarded = True

    await db.commit()

    logger.info(
        "onboarding.profile_saved",
        user_id=str(current_user.id),
        candidate_id=str(candidate.id),
    )

    return ProfileResponse(
        message="Profile saved. You're all set!",
        candidate_id=str(candidate.id),
        is_onboarded=True,
    )


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check the current user's onboarding completion status."""
    has_resume = False
    candidate_id = None

    if current_user.candidate_id:
        result = await db.execute(
            select(Candidate).where(Candidate.id == current_user.candidate_id)
        )
        candidate = result.scalar_one_or_none()
        if candidate:
            has_resume = bool(candidate.resume_text)
            candidate_id = str(candidate.id)

    return OnboardingStatusResponse(
        is_onboarded=current_user.is_onboarded,
        has_resume=has_resume,
        has_profile=current_user.is_onboarded,
        candidate_id=candidate_id,
    )
