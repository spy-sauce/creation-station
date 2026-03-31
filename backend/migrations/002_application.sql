-- VibeSpace Talent Agent — Application Engine Schema

CREATE TABLE IF NOT EXISTS parsed_jds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id) UNIQUE,
    required_skills TEXT[],
    preferred_skills TEXT[],
    seniority_level VARCHAR(100),
    tech_stack TEXT[],
    culture_signals TEXT[],
    tone VARCHAR(50),
    key_responsibilities TEXT[],
    pain_points TEXT,
    comp_mentioned VARCHAR(255),
    red_flags TEXT[],
    application_instructions TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tailored_resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    summary TEXT,
    full_text TEXT NOT NULL,
    change_log TEXT,
    pdf_path VARCHAR(500),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS company_intel (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    about TEXT,
    recent_news TEXT,
    tech_stack TEXT[],
    engineering_culture TEXT,
    growth_stage VARCHAR(100),
    team_size VARCHAR(100),
    notable_facts TEXT,
    cache_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_intel_id UUID REFERENCES company_intel(id),
    name VARCHAR(255),
    title VARCHAR(255),
    email VARCHAR(255),
    linkedin_url VARCHAR(500),
    confidence VARCHAR(20) DEFAULT 'LOW',
    source VARCHAR(100),
    fallback_email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outreach_emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    contact_id UUID REFERENCES contacts(id),
    subject VARCHAR(500),
    body TEXT NOT NULL,
    tone_used VARCHAR(100),
    hook_used TEXT,
    status VARCHAR(50) DEFAULT 'DRAFT',
    sent_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS application_pipelines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES discovered_jobs(id),
    candidate_id UUID REFERENCES candidates(id),
    status VARCHAR(100) DEFAULT 'QUEUED',
    current_step VARCHAR(100),
    resume_id UUID REFERENCES tailored_resumes(id),
    email_id UUID REFERENCES outreach_emails(id),
    submitted_at TIMESTAMPTZ,
    confirmation_number VARCHAR(255),
    screenshot_dir VARCHAR(500),
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_intel_name ON company_intel(company_name);
CREATE INDEX IF NOT EXISTS idx_application_pipelines_status ON application_pipelines(status);
CREATE INDEX IF NOT EXISTS idx_outreach_emails_job ON outreach_emails(job_id);
