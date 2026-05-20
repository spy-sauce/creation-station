-- Copyright 2026 VibeSpace LLC
-- Licensed under the Apache License, Version 2.0

-- VibeSpace Talent Agent — Init Migration
-- Extensions and Enums

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ─── Domain Enums ───────────────────────────────────────────────────────────

-- Job source (ATS platforms)
CREATE TYPE job_source AS ENUM (
    'greenhouse', 'lever', 'ashby', 'workday'
);

-- Crawl run status
CREATE TYPE crawl_run_status AS ENUM (
    'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED'
);

-- Application pipeline status (state machine)
CREATE TYPE application_pipeline_status AS ENUM (
    'QUEUED',
    'PARSING',
    'TAILORING',
    'RESEARCHING',
    'COMPOSING',
    'AWAITING_REVIEW',
    'APPROVED',
    'REJECTED',
    'SUBMITTED',
    'SENT',
    'TRACKED',
    'FAILED',
    'REQUIRES_MANUAL'
);

-- Agent execution status
CREATE TYPE agent_status AS ENUM (
    'QUEUED',
    'DISPATCHED',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'RETRYING',
    'DEAD'
);

-- Contact confidence level
CREATE TYPE contact_confidence AS ENUM (
    'HIGH', 'MEDIUM', 'LOW'
);

-- Remote preference
CREATE TYPE remote_preference AS ENUM (
    'remote_only', 'hybrid', 'onsite', 'flexible'
);

-- Outreach email status
CREATE TYPE outreach_status AS ENUM (
    'DRAFT', 'SENT', 'BOUNCED', 'REPLIED'
);

-- ─── Shared Trigger Function ────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
