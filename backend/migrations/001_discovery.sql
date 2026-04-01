-- VibeSpace Talent Agent — Discovery Engine Schema

CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    resume_text TEXT,
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    personal_context TEXT,
    target_locations TEXT[],
    remote_preference VARCHAR(50) DEFAULT 'flexible',
    min_compensation INTEGER,
    excluded_companies TEXT[],
    excluded_industries TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS discovered_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id),
    title VARCHAR(500) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    url VARCHAR(1000) UNIQUE NOT NULL,
    url_hash VARCHAR(64) UNIQUE NOT NULL,
    description TEXT,
    source VARCHAR(100),
    posted_date TIMESTAMPTZ,
    status job_status DEFAULT 'DISCOVERED',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scored_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    composite_score INTEGER NOT NULL,
    technical_match INTEGER,
    level_match INTEGER,
    culture_match INTEGER,
    industry_match INTEGER,
    growth_potential INTEGER,
    compensation_match INTEGER,
    reasoning TEXT,
    is_hot BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id),
    run_date DATE NOT NULL,
    total_discovered INTEGER DEFAULT 0,
    total_scored INTEGER DEFAULT 0,
    top_picks JSONB,
    hot_picks JSONB,
    new_companies TEXT[],
    digest_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID REFERENCES candidates(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    jobs_discovered INTEGER DEFAULT 0,
    jobs_scored INTEGER DEFAULT 0,
    status pipeline_status DEFAULT 'RUNNING',
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discovered_jobs_candidate ON discovered_jobs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_discovered_jobs_url_hash ON discovered_jobs(url_hash);
CREATE INDEX IF NOT EXISTS idx_scored_jobs_candidate ON scored_jobs(candidate_id);
CREATE INDEX IF NOT EXISTS idx_scored_jobs_score ON scored_jobs(composite_score DESC);
