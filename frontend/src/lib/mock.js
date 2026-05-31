// Mock layer — enabled when VITE_MOCK=true. Returns seeded fixture data that
// matches the FastAPI response shapes per NUTRIENTS.md API_CONTRACTS so the
// dashboard is fully navigable without a live backend. NOT for production.

const CANDIDATE_ID = '00000000-0000-4000-8000-000000000001'
const USER_ID = '00000000-0000-4000-8000-000000000002'
const MOCK_TOKEN = 'mock-jwt-token-demo'

const delay = (ms = 220) => new Promise(r => setTimeout(r, ms))

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function requestMagicLink(email) {
  await delay()
  return {
    message: 'Magic link generated (mock mode)',
    magic_link: `${window.location.origin}/auth/verify?token=mock-magic-link`,
    token: 'mock-magic-link',
    email,
  }
}

export async function verifyMagicLink(_token) {
  await delay()
  return {
    access_token: MOCK_TOKEN,
    token_type: 'bearer',
    user_id: USER_ID,
    email: 'alex@example.com',
    is_onboarded: true,
  }
}

export async function getMe() {
  await delay(80)
  return {
    id: USER_ID,
    email: 'alex@example.com',
    is_onboarded: true,
    candidate_id: CANDIDATE_ID,
    name: 'Alex Morgan',
  }
}

// ─── Onboarding ───────────────────────────────────────────────────────────────

export async function uploadResume(_file) {
  await delay(600)
  return {
    candidate_id: CANDIDATE_ID,
    extracted_text: 'Alex Morgan — Senior Software Engineer · Platform Systems. 8+ years building distributed systems at scale. Expertise in Python, FastAPI, async I/O, PostgreSQL, Kubernetes, and AI-integrated backends. Most recently led platform reliability at a Series-C SaaS company.',
    word_count: 412,
    extracted_skills: ['Python', 'FastAPI', 'Distributed Systems', 'Kubernetes', 'AI Systems', 'Java', 'Spring Boot'],
  }
}

export async function saveProfile(profile) {
  await delay()
  return { candidate_id: CANDIDATE_ID, ...profile, is_onboarded: true }
}

export async function getOnboardingStatus() {
  await delay(80)
  return { is_onboarded: true, has_resume: true, has_profile: true }
}

// ─── Discovery ────────────────────────────────────────────────────────────────

const MOCK_JOBS = [
  { id: 'job-001', title: 'Staff AI Engineer · Agent Systems', company: 'Anthropic', source: 'greenhouse', location: 'Remote · US', salary: '$280K – $360K', score: 94, scored_at: '2026-05-20T14:22:00Z', url: 'https://boards.greenhouse.io/anthropic/jobs/0001', match_reasons: ['Distributed systems depth (7+ yrs)', 'Python + FastAPI primary', 'AI agents experience', 'Remote-first stance'] },
  { id: 'job-002', title: 'Principal Engineer · Platform', company: 'Vercel', source: 'lever', location: 'Remote · Americas', salary: '$260K – $340K', score: 91, scored_at: '2026-05-20T14:21:00Z', url: 'https://jobs.lever.co/vercel/0002', match_reasons: ['Platform engineering scope', 'Async-first culture', 'TypeScript + React frontend', 'Edge compute'] },
  { id: 'job-003', title: 'Founding AI Engineer', company: 'Stripe', source: 'ashby', location: 'New York · NY', salary: '$300K + equity', score: 88, scored_at: '2026-05-20T14:20:00Z', url: 'https://jobs.ashbyhq.com/stripe/0003', match_reasons: ['Fintech background match', 'Founding-team scope', 'AI/ML integration work', 'Compensation aligned'] },
  { id: 'job-004', title: 'Senior Backend Engineer · Agent Orchestration', company: 'Replit', source: 'greenhouse', location: 'Remote · Global', salary: '$220K – $290K', score: 85, scored_at: '2026-05-20T14:19:00Z', url: 'https://boards.greenhouse.io/replit/0004', match_reasons: ['Agent orchestration focus', 'Python primary', 'Remote-global flexibility', 'Async I/O depth required'] },
  { id: 'job-005', title: 'Tech Lead · LLM Infrastructure', company: 'Notion', source: 'workday', location: 'San Francisco · CA', salary: '$270K – $340K', score: 82, scored_at: '2026-05-20T14:18:00Z', url: 'https://notion.wd1.myworkdayjobs.com/0005', match_reasons: ['Infra leadership scope', 'LLM systems expertise', 'Tech-lead seniority', 'SF in-office (hybrid OK)'] },
  { id: 'job-006', title: 'Distinguished AI Researcher', company: 'OpenAI', source: 'greenhouse', location: 'San Francisco · CA', salary: '$400K+ + equity', score: 79, scored_at: '2026-05-20T14:17:00Z', url: 'https://boards.greenhouse.io/openai/0006', match_reasons: ['Top-tier compensation', 'Research scope', 'Frontier-model work', 'May require publications'] },
  { id: 'job-007', title: 'Senior Engineer · Recruiting Tools', company: 'Linear', source: 'lever', location: 'Remote · US/EU', salary: '$210K – $280K', score: 76, scored_at: '2026-05-20T14:16:00Z', url: 'https://jobs.lever.co/linear/0007', match_reasons: ['Recruiting-adjacent domain', 'Small-team velocity', 'TypeScript primary', 'Remote globalish'] },
  { id: 'job-008', title: 'Backend Engineer · Pipeline Automation', company: 'Ramp', source: 'ashby', location: 'New York · NY', salary: '$240K – $310K', score: 72, scored_at: '2026-05-20T14:15:00Z', url: 'https://jobs.ashbyhq.com/ramp/0008', match_reasons: ['Fintech vertical match', 'Pipeline / orchestration focus', 'NYC office (open to relocate)', 'Python + Go stack'] },
]

export async function triggerDiscovery(_candidateId) {
  await delay(900)
  return { run_id: 'mock-run-001', status: 'started', message: 'Discovery run queued (mock)' }
}

export async function getDigest(_digestId) {
  await delay()
  return { digest_id: 'mock-digest-001', candidate_id: CANDIDATE_ID, jobs: MOCK_JOBS, total: MOCK_JOBS.length, generated_at: '2026-05-20T14:00:00Z' }
}

export async function getLatestDigest(_candidateId) {
  return getDigest('mock-digest-001')
}

export async function getDiscoveryStats(_candidateId) {
  await delay(80)
  return {
    runs_total: 47,
    runs_this_week: 7,
    jobs_discovered_total: 1284,
    jobs_discovered_this_week: 312,
    avg_score: 71.4,
    last_run_at: '2026-05-20T14:00:00Z',
    sources: { greenhouse: 521, lever: 389, ashby: 217, workday: 157 },
  }
}

export async function triggerDiscoveryRun(_candidateId, _dryRun) {
  return triggerDiscovery()
}

// ─── Application pipelines ────────────────────────────────────────────────────

const MOCK_PIPELINES = [
  { id: 'pipe-001', job_id: 'job-001', candidate_id: CANDIDATE_ID, status: 'AWAITING_REVIEW', created_at: '2026-05-20T14:30:00Z', updated_at: '2026-05-20T14:42:00Z', job: MOCK_JOBS[0], company: { name: 'Anthropic', industry: 'AI Research', size: '500-1000', funding: 'Series C · $7.3B', stage: 'late', summary: 'AI safety company building Claude. Founded 2021 by former OpenAI researchers. Constitutional AI focus.' }, contact: { name: 'Dario Amodei', title: 'CEO', email: 'dario@anthropic.com', linkedin: 'linkedin.com/in/dario-amodei', confidence: 0.94 }, resume_diff_summary: 'Tailored: emphasized agent-orchestration work, distributed systems depth, and LLM integration experience. Trimmed: legacy enterprise specifics.', outreach_subject: 'Re: Staff AI Engineer · Agent Systems', outreach_body: 'Hi Dario,\n\nI came across the Staff AI Engineer · Agent Systems role and it lines up almost exactly with what I\'ve been building for the last two years — multi-agent orchestration systems with explicit lifecycle states and human-in-the-loop approval gates.\n\nMost recent project: a 24/7 autonomous recruiting platform built on FastAPI + PostgreSQL + Redis + Playwright. Eight Claude-powered agents coordinating through a typed event bus, with every state transition observable. Production-grade error handling and PII redaction throughout.\n\n8+ years building distributed systems before this. I\'d love 20 minutes to talk about how the Agent Systems work at Anthropic is approaching the same problem space.\n\nBest,\nAlex Morgan' },
  { id: 'pipe-002', job_id: 'job-002', candidate_id: CANDIDATE_ID, status: 'AWAITING_REVIEW', created_at: '2026-05-20T14:28:00Z', updated_at: '2026-05-20T14:41:00Z', job: MOCK_JOBS[1], company: { name: 'Vercel', industry: 'Developer Tools', size: '500-800', funding: 'Series E · $3.25B', stage: 'late', summary: 'Frontend cloud platform. Next.js maintainers. Edge-first compute.' }, contact: { name: 'Guillermo Rauch', title: 'CEO', email: 'rauchg@vercel.com', linkedin: 'linkedin.com/in/rauchg', confidence: 0.91 }, resume_diff_summary: 'Tailored: highlighted edge compute and async I/O depth, TypeScript+React experience. Trimmed: backend-only history.', outreach_subject: 'Re: Principal Engineer · Platform', outreach_body: 'Hi Guillermo,\n\nThe Principal Engineer · Platform role is a precise match for my background — eight years of distributed-systems work with a strong recent shift into edge compute and async runtimes.\n\nLast year I led the migration of a 40M-request/day API tier from regional VMs to edge functions, which cut p99 latency by 62% and our compute bill by a third. I\'ve been a Vercel customer since v0 and have followed the platform\'s evolution carefully.\n\nHappy to share specifics over a 20-minute call.\n\nBest,\nAlex Morgan' },
  { id: 'pipe-003', job_id: 'job-003', candidate_id: CANDIDATE_ID, status: 'SUBMITTED', created_at: '2026-05-20T13:00:00Z', updated_at: '2026-05-20T13:48:00Z', job: MOCK_JOBS[2], company: { name: 'Stripe' }, contact: { name: 'John Collison', title: 'President', confidence: 0.88 } },
  { id: 'pipe-004', job_id: 'job-004', candidate_id: CANDIDATE_ID, status: 'SENT', created_at: '2026-05-19T17:00:00Z', updated_at: '2026-05-19T17:22:00Z', job: MOCK_JOBS[3], company: { name: 'Replit' } },
  { id: 'pipe-005', job_id: 'job-005', candidate_id: CANDIDATE_ID, status: 'REJECTED', created_at: '2026-05-19T10:00:00Z', updated_at: '2026-05-19T10:12:00Z', job: MOCK_JOBS[4], company: { name: 'Notion' } },
]

export async function startApplication(_jobId, _candidateId) {
  await delay()
  return MOCK_PIPELINES[0]
}

export async function submitApplication(pipelineId) {
  await delay(800)
  const p = MOCK_PIPELINES.find(x => x.id === pipelineId) || MOCK_PIPELINES[0]
  return { ...p, status: 'SUBMITTED' }
}

export async function listApplications(opts = {}) {
  await delay()
  let filtered = MOCK_PIPELINES.slice()
  if (opts.status) filtered = filtered.filter(p => p.status === opts.status)
  return { items: filtered, total: filtered.length, limit: opts.limit || 50, offset: opts.offset || 0 }
}

export async function getPipeline(pipelineId) {
  await delay(100)
  return MOCK_PIPELINES.find(p => p.id === pipelineId) || MOCK_PIPELINES[0]
}

// ─── Review queue ─────────────────────────────────────────────────────────────

export async function getReviewQueue(_candidateId) {
  await delay()
  const awaiting = MOCK_PIPELINES.filter(p => p.status === 'AWAITING_REVIEW')
  return { items: awaiting, total: awaiting.length }
}

export async function approvePipeline(pipelineId) {
  await delay(500)
  return { id: pipelineId, status: 'APPROVED', approved_at: new Date().toISOString() }
}

export async function rejectPipeline(pipelineId, reason) {
  await delay(300)
  return { id: pipelineId, status: 'REJECTED', rejection_reason: reason || 'Not a fit', rejected_at: new Date().toISOString() }
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function getHealth() {
  await delay(40)
  return {
    status: 'ok',
    version: '0.3.0-iter3',
    git_sha: 'a80f00a',
    redis: 'ok',
    db: 'ok',
    mode: 'mock',
  }
}
