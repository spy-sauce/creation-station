-- Copyright 2026 VibeSpace LLC
-- Licensed under the Apache License, Version 2.0

-- VibeSpace Talent Agent — Discovery Engine Schema

-- ─── Candidates ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    resume_text TEXT,
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    personal_context TEXT,
    target_locations TEXT[] DEFAULT '{}',
    remote_preference remote_preference DEFAULT 'flexible',
    min_compensation INTEGER,
    excluded_companies TEXT[] DEFAULT '{}',
    excluded_industries TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ─── Discovered Jobs ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS discovered_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source job_source NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    description TEXT,
    url VARCHAR(1000) NOT NULL,
    posted_at TIMESTAMPTZ,
    salary_min INTEGER,
    salary_max INTEGER,
    remote BOOLEAN DEFAULT FALSE,
    crawled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT discovered_jobs_source_unique UNIQUE (source, source_id)
);

CREATE TRIGGER update_discovered_jobs_updated_at
    BEFORE UPDATE ON discovered_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_discovered_jobs_source ON discovered_jobs(source);
CREATE INDEX IF NOT EXISTS idx_discovered_jobs_company ON discovered_jobs(company);
CREATE INDEX IF NOT EXISTS idx_discovered_jobs_crawled_at ON discovered_jobs(crawled_at DESC);

-- ─── Scored Jobs ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scored_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discovered_job_id UUID NOT NULL REFERENCES discovered_jobs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    technical_match INTEGER NOT NULL CHECK (technical_match >= 0 AND technical_match <= 100),
    level_match INTEGER NOT NULL CHECK (level_match >= 0 AND level_match <= 100),
    culture_match INTEGER NOT NULL CHECK (culture_match >= 0 AND culture_match <= 100),
    industry_match INTEGER NOT NULL CHECK (industry_match >= 0 AND industry_match <= 100),
    growth_potential INTEGER NOT NULL CHECK (growth_potential >= 0 AND growth_potential <= 100),
    compensation_match INTEGER NOT NULL CHECK (compensation_match >= 0 AND compensation_match <= 100),
    composite_score INTEGER NOT NULL CHECK (composite_score >= 0 AND composite_score <= 100),
    is_hot BOOLEAN NOT NULL DEFAULT FALSE,
    reasoning TEXT NOT NULL,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT scored_jobs_unique UNIQUE (discovered_job_id, candidate_id)
);

CREATE INDEX IF NOT EXISTS idx_scored_jobs_candidate ON scored_jobs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_scored_jobs_composite ON scored_jobs(composite_score DESC);
CREATE INDEX IF NOT EXISTS idx_scored_jobs_hot ON scored_jobs(is_hot) WHERE is_hot = TRUE;

-- ─── Daily Digests ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS daily_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    run_date DATE NOT NULL,
    top_picks JSONB NOT NULL DEFAULT '[]',
    hot_picks JSONB NOT NULL DEFAULT '[]',
    new_companies TEXT[] DEFAULT '{}',
    total_jobs_discovered INTEGER NOT NULL DEFAULT 0,
    total_jobs_scored INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT daily_digests_unique UNIQUE (candidate_id, run_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_digests_candidate ON daily_digests(candidate_id);
CREATE INDEX IF NOT EXISTS idx_daily_digests_run_date ON daily_digests(run_date DESC);

-- ─── Crawl Runs ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    status crawl_run_status NOT NULL DEFAULT 'QUEUED',
    jobs_discovered INTEGER NOT NULL DEFAULT 0,
    jobs_scored INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_log TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_candidate ON crawl_runs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_crawl_runs_status ON crawl_runs(status);
