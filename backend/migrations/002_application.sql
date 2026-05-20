-- Copyright 2026 VibeSpace LLC
-- Licensed under the Apache License, Version 2.0

-- VibeSpace Talent Agent — Application Engine Schema

-- ─── Parsed JDs ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS parsed_jds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES discovered_jobs(id) ON DELETE CASCADE UNIQUE,
    required_skills TEXT[] DEFAULT '{}',
    preferred_skills TEXT[] DEFAULT '{}',
    seniority_level VARCHAR(100),
    tech_stack TEXT[] DEFAULT '{}',
    culture_signals TEXT[] DEFAULT '{}',
    tone VARCHAR(50),
    pain_points TEXT[] DEFAULT '{}',
    compensation_range VARCHAR(255),
    red_flags TEXT[] DEFAULT '{}',
    application_instructions TEXT,
    parsed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parsed_jds_job ON parsed_jds(job_id);

-- ─── Application Pipelines ──────────────────────────────────────────────────
-- Must be created before tables that reference it

CREATE TABLE IF NOT EXISTS application_pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES scored_jobs(id) ON DELETE CASCADE,
    status application_pipeline_status NOT NULL DEFAULT 'QUEUED',
    approval_timestamp TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    screenshots TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT application_pipelines_unique UNIQUE (candidate_id, job_id)
);

CREATE TRIGGER update_application_pipelines_updated_at
    BEFORE UPDATE ON application_pipelines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_application_pipelines_candidate ON application_pipelines(candidate_id);
CREATE INDEX IF NOT EXISTS idx_application_pipelines_status ON application_pipelines(status);
CREATE INDEX IF NOT EXISTS idx_application_pipelines_job ON application_pipelines(job_id);

-- ─── Tailored Resumes ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tailored_resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES application_pipelines(id) ON DELETE CASCADE UNIQUE,
    original_text TEXT NOT NULL,
    tailored_text TEXT NOT NULL,
    change_log TEXT[] DEFAULT '{}',
    gap_analysis TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tailored_resumes_pipeline ON tailored_resumes(pipeline_id);

-- ─── Company Intel ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS company_intel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES application_pipelines(id) ON DELETE CASCADE UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    about TEXT,
    recent_news TEXT[] DEFAULT '{}',
    tech_stack TEXT[] DEFAULT '{}',
    engineering_culture TEXT,
    growth_stage VARCHAR(100),
    team_size VARCHAR(100),
    notable_facts TEXT[] DEFAULT '{}',
    researched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER update_company_intel_updated_at
    BEFORE UPDATE ON company_intel
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_company_intel_pipeline ON company_intel(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_company_intel_company ON company_intel(company_name);

-- ─── Contacts ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES application_pipelines(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    linkedin_url VARCHAR(500),
    confidence contact_confidence NOT NULL DEFAULT 'LOW',
    fallback_email VARCHAR(255),
    source VARCHAR(100),
    found_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contacts_pipeline ON contacts(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_contacts_confidence ON contacts(confidence);

-- ─── Outreach Emails ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS outreach_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES application_pipelines(id) ON DELETE CASCADE UNIQUE,
    subject_lines TEXT[] NOT NULL DEFAULT '{}',
    body TEXT NOT NULL,
    status outreach_status NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outreach_emails_pipeline ON outreach_emails(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_status ON outreach_emails(status);

-- ─── CRM Events ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS crm_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES application_pipelines(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_events_pipeline ON crm_events(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_crm_events_type ON crm_events(event_type);
CREATE INDEX IF NOT EXISTS idx_crm_events_created ON crm_events(created_at DESC);
