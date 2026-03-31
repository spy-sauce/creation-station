-- VibeSpace Talent Agent — Init Migration
-- Extensions

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Pipeline status enum
CREATE TYPE pipeline_status AS ENUM (
    'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'DEAD'
);

-- Job status enum
CREATE TYPE job_status AS ENUM (
    'DISCOVERED', 'SCORED', 'APPROVED', 'SKIPPED', 'APPLIED', 'INTERVIEWING', 'OFFERED', 'REJECTED'
);
