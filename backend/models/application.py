# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
SQLAlchemy ORM models for the Application Engine.

Tables:
  - parsed_jds: Structured JD parsing output
  - application_pipelines: Pipeline state machine (QUEUED → SENT)
  - tailored_resumes: Resume rewrites for specific jobs
  - company_intel: Company research artifacts
  - contacts: Discovered recipient contacts
  - outreach_emails: Draft outreach emails
  - crm_events: Append-only event log per pipeline
"""

import uuid
from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

from backend.database import Base


# ─── Enums ───────────────────────────────────────────────────────────────────


class ApplicationPipelineStatus(str, enum.Enum):
    """Application pipeline state machine."""
    QUEUED = "QUEUED"
    PARSING = "PARSING"
    TAILORING = "TAILORING"
    RESEARCHING = "RESEARCHING"
    COMPOSING = "COMPOSING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    SENT = "SENT"
    TRACKED = "TRACKED"
    FAILED = "FAILED"
    REQUIRES_MANUAL = "REQUIRES_MANUAL"


class ContactConfidence(str, enum.Enum):
    """Contact confidence level."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class OutreachStatus(str, enum.Enum):
    """Outreach email status."""
    DRAFT = "DRAFT"
    SENT = "SENT"
    BOUNCED = "BOUNCED"
    REPLIED = "REPLIED"


# ─── Parsed JD ───────────────────────────────────────────────────────────────


class ParsedJD(Base):
    """Cached structured parse of a job description."""

    __tablename__ = "parsed_jds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discovered_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    required_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    preferred_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    seniority_level: Mapped[Optional[str]] = mapped_column(String(100))
    team_context: Mapped[Optional[str]] = mapped_column(Text)
    key_responsibilities: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    culture_signals: Mapped[Optional[dict]] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )
    tech_stack: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    pain_points: Mapped[Optional[str]] = mapped_column(Text)
    tone: Mapped[Optional[str]] = mapped_column(String(50))
    comp_mentioned: Mapped[Optional[str]] = mapped_column(String(255))
    red_flags: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    application_instructions: Mapped[Optional[str]] = mapped_column(Text)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ─── Application Pipeline ────────────────────────────────────────────────────


class ApplicationPipeline(Base):
    """Full pipeline state for a single job application."""

    __tablename__ = "application_pipelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discovered_jobs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        server_default="QUEUED",
        nullable=False,
    )
    current_step: Mapped[Optional[str]] = mapped_column(String(100))
    approval_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    screenshots: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tailored_resume: Mapped[Optional["TailoredResume"]] = relationship(
        back_populates="pipeline", uselist=False, cascade="all, delete-orphan"
    )
    company_intel: Mapped[Optional["CompanyIntel"]] = relationship(
        back_populates="pipeline", uselist=False, cascade="all, delete-orphan"
    )
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )
    outreach_email: Mapped[Optional["OutreachEmail"]] = relationship(
        back_populates="pipeline", uselist=False, cascade="all, delete-orphan"
    )
    crm_events: Mapped[list["CRMEvent"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )


# ─── Tailored Resume ─────────────────────────────────────────────────────────


class TailoredResume(Base):
    """Version-controlled tailored resume for a specific job application."""

    __tablename__ = "tailored_resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("application_pipelines.id", ondelete="CASCADE"),
        nullable=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    original_text: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    tailored_text: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    full_text: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    change_log: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    gap_analysis: Mapped[Optional[str]] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    pipeline: Mapped[Optional["ApplicationPipeline"]] = relationship(
        back_populates="tailored_resume"
    )


# ─── Company Intel ───────────────────────────────────────────────────────────


class CompanyIntel(Base):
    """Cached company research for a pipeline or standalone cache."""

    __tablename__ = "company_intel"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("application_pipelines.id", ondelete="CASCADE"),
        nullable=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255))
    about: Mapped[Optional[str]] = mapped_column(Text)
    recent_news: Mapped[Optional[str]] = mapped_column(Text)
    tech_stack: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    engineering_culture: Mapped[Optional[str]] = mapped_column(Text)
    glassdoor_signals: Mapped[Optional[str]] = mapped_column(Text)
    growth_stage: Mapped[Optional[str]] = mapped_column(String(100))
    team_size: Mapped[Optional[str]] = mapped_column(String(100))
    notable_facts: Mapped[Optional[str]] = mapped_column(Text)
    cache_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    researched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    pipeline: Mapped[Optional["ApplicationPipeline"]] = relationship(
        back_populates="company_intel"
    )


# ─── Contact ─────────────────────────────────────────────────────────────────


class Contact(Base):
    """A contact person discovered for a company."""

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("application_pipelines.id", ondelete="CASCADE"), nullable=True
    )
    company_intel_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    confidence: Mapped[str] = mapped_column(
        String(20),
        server_default="LOW",
        nullable=False,
    )
    fallback_email: Mapped[Optional[str]] = mapped_column(String(255))
    source: Mapped[Optional[str]] = mapped_column(String(100))
    found_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    pipeline: Mapped[Optional["ApplicationPipeline"]] = relationship(
        back_populates="contacts"
    )


# ─── Outreach Email ──────────────────────────────────────────────────────────


class OutreachEmail(Base):
    """Draft outreach email — moves to SENT only after Review Dashboard approval."""

    __tablename__ = "outreach_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("application_pipelines.id", ondelete="CASCADE"),
        nullable=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    subject: Mapped[str] = mapped_column(String(500), server_default="", nullable=False)
    subject_variants: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tone_used: Mapped[Optional[str]] = mapped_column(String(100))
    hook_used: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        server_default="DRAFT",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    pipeline: Mapped[Optional["ApplicationPipeline"]] = relationship(
        back_populates="outreach_email"
    )


# ─── CRM Event ───────────────────────────────────────────────────────────────


class CRMEvent(Base):
    """Immutable timeline event for a job application."""

    __tablename__ = "crm_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_pipelines.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, server_default="{}")
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    pipeline: Mapped["ApplicationPipeline"] = relationship(back_populates="crm_events")
