# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
SQLAlchemy ORM models for the Discovery Engine.

Table layout:
  candidates → identity_profiles → archetype_manifests
  candidates → discovered_jobs → scored_jobs → digest_jobs → daily_digests
  candidates → crawl_runs
"""

import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    String, Text, Integer, Boolean, Date, DateTime,
    ForeignKey, JSON, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from backend.database import Base


class Candidate(Base):
    """A candidate being managed by the Talent Agent system."""

    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    resume_text: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    github_url: Mapped[Optional[str]] = mapped_column(String(500))
    personal_context: Mapped[Optional[str]] = mapped_column(Text)
    target_locations: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    remote_preference: Mapped[str] = mapped_column(String(50), default="flexible")
    min_compensation: Mapped[Optional[int]] = mapped_column(Integer)
    excluded_companies: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    excluded_industries: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    discovered_jobs: Mapped[list["DiscoveredJob"]] = relationship(back_populates="candidate")
    crawl_runs: Mapped[list["CrawlRun"]] = relationship(back_populates="candidate")
    daily_digests: Mapped[list["DailyDigest"]] = relationship(back_populates="candidate")


class DiscoveredJob(Base):
    """A raw job posting discovered during a crawl run."""

    __tablename__ = "discovered_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(100))
    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="DISCOVERED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="discovered_jobs")
    scored_job: Mapped[Optional["ScoredJob"]] = relationship(back_populates="discovered_job", uselist=False)


class ScoredJob(Base):
    """Scoring breakdown for a discovered job against a candidate's identity profile."""

    __tablename__ = "scored_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("discovered_jobs.id"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    composite_score: Mapped[int] = mapped_column(Integer, nullable=False)
    technical_match: Mapped[Optional[int]] = mapped_column(Integer)
    level_match: Mapped[Optional[int]] = mapped_column(Integer)
    culture_match: Mapped[Optional[int]] = mapped_column(Integer)
    industry_match: Mapped[Optional[int]] = mapped_column(Integer)
    growth_potential: Mapped[Optional[int]] = mapped_column(Integer)
    compensation_match: Mapped[Optional[int]] = mapped_column(Integer)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    is_hot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    discovered_job: Mapped["DiscoveredJob"] = relationship(back_populates="scored_job")


class DailyDigest(Base):
    """Metadata and summary for a daily discovery run digest."""

    __tablename__ = "daily_digests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_discovered: Mapped[int] = mapped_column(Integer, default=0)
    total_scored: Mapped[int] = mapped_column(Integer, default=0)
    top_picks: Mapped[Optional[list]] = mapped_column(JSON)   # list of scored_job IDs + preview data
    hot_picks: Mapped[Optional[list]] = mapped_column(JSON)
    new_companies: Mapped[Optional[list]] = mapped_column(JSON)
    digest_summary: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="daily_digests")


class CrawlRun(Base):
    """Audit log of every discovery crawl run."""

    __tablename__ = "crawl_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    jobs_discovered: Mapped[int] = mapped_column(Integer, default=0)
    jobs_scored: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING")
    error_log: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="crawl_runs")
