# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
SQLAlchemy ORM models for the Application Engine.

Table layout:
  discovered_jobs → parsed_jds
  candidates + discovered_jobs → tailored_resumes
  company_intel → contacts
  candidates + discovered_jobs → outreach_emails → contacts
  candidates + discovered_jobs → application_pipelines → tailored_resumes + outreach_emails
  application_pipelines → application_results
  application_pipelines → crm_events
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from backend.database import Base


class ParsedJD(Base):
    """Cached structured parse of a job description. Reused if job is re-processed."""

    __tablename__ = "parsed_jds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("discovered_jobs.id"), unique=True, nullable=False)
    required_skills: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    preferred_skills: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    seniority_level: Mapped[Optional[str]] = mapped_column(String(100))
    tech_stack: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    key_responsibilities: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    pain_points: Mapped[Optional[str]] = mapped_column(Text)
    culture_signals: Mapped[Optional[dict]] = mapped_column(JSON)
    tone: Mapped[Optional[str]] = mapped_column(String(50))
    comp_mentioned: Mapped[Optional[str]] = mapped_column(String(255))
    red_flags: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    application_instructions: Mapped[Optional[str]] = mapped_column(Text)
    team_context: Mapped[Optional[str]] = mapped_column(Text)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TailoredResume(Base):
    """Version-controlled tailored resume for a specific job application."""

    __tablename__ = "tailored_resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("discovered_jobs.id"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    change_log: Mapped[Optional[str]] = mapped_column(Text)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompanyIntel(Base):
    """Cached company research. TTL: 7 days — don't re-scrape within a week."""

    __tablename__ = "company_intel"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255))
    about: Mapped[Optional[str]] = mapped_column(Text)
    recent_news: Mapped[Optional[str]] = mapped_column(Text)
    tech_stack: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    engineering_culture: Mapped[Optional[str]] = mapped_column(Text)
    glassdoor_signals: Mapped[Optional[str]] = mapped_column(Text)
    growth_stage: Mapped[Optional[str]] = mapped_column(String(100))
    team_size: Mapped[Optional[str]] = mapped_column(String(100))
    notable_facts: Mapped[Optional[str]] = mapped_column(Text)
    cache_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    contacts: Mapped[list["Contact"]] = relationship(back_populates="company_intel")


class Contact(Base):
    """A contact person discovered for a company (hiring manager, eng lead, etc.)."""

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_intel_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("company_intel.id"))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    confidence: Mapped[str] = mapped_column(String(20), default="LOW")
    source: Mapped[Optional[str]] = mapped_column(String(100))
    fallback_email: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company_intel: Mapped[Optional["CompanyIntel"]] = relationship(back_populates="contacts")


class OutreachEmail(Base):
    """Draft outreach email — moves to SENT only after Review Dashboard approval."""

    __tablename__ = "outreach_emails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("discovered_jobs.id"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("contacts.id"))
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    subject_variants: Mapped[Optional[list]] = mapped_column(JSON)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tone_used: Mapped[Optional[str]] = mapped_column(String(100))
    hook_used: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApplicationPipeline(Base):
    """Full pipeline state for a single job application — tracks every step."""

    __tablename__ = "application_pipelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("discovered_jobs.id"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(100), default="QUEUED", index=True)
    current_step: Mapped[Optional[str]] = mapped_column(String(100))
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("tailored_resumes.id"))
    email_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("outreach_emails.id"))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmation_number: Mapped[Optional[str]] = mapped_column(String(255))
    screenshot_dir: Mapped[Optional[str]] = mapped_column(String(500))
    error_log: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ApplicationResult(Base):
    """Outcome record for a form submission attempt."""

    __tablename__ = "application_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application_pipelines.id"), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("discovered_jobs.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # SUCCESS | FAILED | REQUIRES_MANUAL
    confirmation_number: Mapped[Optional[str]] = mapped_column(String(255))
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(500))
    fields_completed: Mapped[Optional[list]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    fallback_url: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CRMEvent(Base):
    """Immutable timeline event for a job application — tracks every significant state change."""

    __tablename__ = "crm_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application_pipelines.id"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("discovered_jobs.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
