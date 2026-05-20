# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
SQLAlchemy ORM models for the Discovery Engine.

Tables:
  - candidates: Job seeker profiles with resume, preferences, exclusions
  - discovered_jobs: Raw jobs from crawler sources
  - scored_jobs: Jobs scored against candidate profile (6-dim)
  - daily_digests: Compiled digest per candidate per day
  - crawl_runs: Crawler execution tracking
"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Boolean, Date, DateTime,
    ForeignKey, CheckConstraint, func, Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
import enum

from backend.database import Base


# ─── Enums ───────────────────────────────────────────────────────────────────

class JobSource(str, enum.Enum):
    """ATS platforms supported by the crawler."""
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"


class RemotePreference(str, enum.Enum):
    """Candidate remote work preference."""
    REMOTE_ONLY = "remote_only"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    FLEXIBLE = "flexible"


class CrawlRunStatus(str, enum.Enum):
    """Status of a crawl run."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ─── Candidate ───────────────────────────────────────────────────────────────

class Candidate(Base):
    """A candidate being managed by the Talent Agent system."""

    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    resume_text: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    github_url: Mapped[Optional[str]] = mapped_column(String(500))
    personal_context: Mapped[Optional[str]] = mapped_column(Text)
    target_locations: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    remote_preference: Mapped[RemotePreference] = mapped_column(
        Enum(RemotePreference, name="remote_preference", create_type=False),
        server_default="flexible",
        nullable=False,
    )
    min_compensation: Mapped[Optional[int]] = mapped_column(Integer)
    excluded_companies: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    excluded_industries: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    crawl_runs: Mapped[list["CrawlRun"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    daily_digests: Mapped[list["DailyDigest"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    scored_jobs: Mapped[list["ScoredJob"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


# ─── Discovered Job ──────────────────────────────────────────────────────────

class DiscoveredJob(Base):
    """A raw job posting discovered during a crawl run."""

    __tablename__ = "discovered_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[JobSource] = mapped_column(
        Enum(JobSource, name="job_source", create_type=False), nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    remote: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    scored_job: Mapped[Optional["ScoredJob"]] = relationship(
        back_populates="discovered_job", uselist=False
    )

    __table_args__ = (
        # Unique constraint on source + source_id
        {"extend_existing": True},
    )


# ─── Scored Job ──────────────────────────────────────────────────────────────

class ScoredJob(Base):
    """Scoring breakdown for a discovered job against a candidate's identity profile."""

    __tablename__ = "scored_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discovered_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discovered_jobs.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    technical_match: Mapped[int] = mapped_column(Integer, nullable=False)
    level_match: Mapped[int] = mapped_column(Integer, nullable=False)
    culture_match: Mapped[int] = mapped_column(Integer, nullable=False)
    industry_match: Mapped[int] = mapped_column(Integer, nullable=False)
    growth_potential: Mapped[int] = mapped_column(Integer, nullable=False)
    compensation_match: Mapped[int] = mapped_column(Integer, nullable=False)
    composite_score: Mapped[int] = mapped_column(Integer, nullable=False)
    is_hot: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    discovered_job: Mapped["DiscoveredJob"] = relationship(back_populates="scored_job")
    candidate: Mapped["Candidate"] = relationship(back_populates="scored_jobs")

    __table_args__ = (
        CheckConstraint("technical_match >= 0 AND technical_match <= 100"),
        CheckConstraint("level_match >= 0 AND level_match <= 100"),
        CheckConstraint("culture_match >= 0 AND culture_match <= 100"),
        CheckConstraint("industry_match >= 0 AND industry_match <= 100"),
        CheckConstraint("growth_potential >= 0 AND growth_potential <= 100"),
        CheckConstraint("compensation_match >= 0 AND compensation_match <= 100"),
        CheckConstraint("composite_score >= 0 AND composite_score <= 100"),
    )


# ─── Daily Digest ────────────────────────────────────────────────────────────

class DailyDigest(Base):
    """Compiled digest per candidate per day."""

    __tablename__ = "daily_digests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    top_picks: Mapped[list] = mapped_column(JSONB, server_default="[]", nullable=False)
    hot_picks: Mapped[list] = mapped_column(JSONB, server_default="[]", nullable=False)
    new_companies: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    total_jobs_discovered: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    total_jobs_scored: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped["Candidate"] = relationship(back_populates="daily_digests")


# ─── Crawl Run ───────────────────────────────────────────────────────────────

class CrawlRun(Base):
    """Audit log of every discovery crawl run."""

    __tablename__ = "crawl_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[CrawlRunStatus] = mapped_column(
        Enum(CrawlRunStatus, name="crawl_run_status", create_type=False),
        server_default="QUEUED",
        nullable=False,
    )
    jobs_discovered: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    jobs_scored: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_log: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped["Candidate"] = relationship(back_populates="crawl_runs")
