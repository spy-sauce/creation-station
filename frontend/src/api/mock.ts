/**
 * Typed mock layer for the API client.
 *
 * Enabled when VITE_MOCK=true. Returns seeded fixture data that matches the
 * FastAPI response shapes (per the .ts API module interfaces) so the dashboard
 * and auth flows are fully navigable without a live backend. NOT for production.
 *
 * The mock seam lives inside apiClient.request (see client.ts): it matches on
 * HTTP method + URL pathname and returns the RAW backend response shape. This
 * means downstream transform logic (e.g. verifyToken storing the JWT and
 * reshaping the user) runs against mock data exactly as it would against the
 * real backend.
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import type { AuthUser } from './auth'
import type {
  DailyDigest,
  DigestSummary,
  DiscoveryStats,
  ScoredJob,
  TriggerRunResponse,
} from './discovery'
import type {
  ApplicationPipeline,
  ApproveResponse,
  ListApplicationsResponse,
  RejectResponse,
} from './applications'
import type { CandidateRow, ListCandidatesResponse } from './candidates'

// ─── Constants ──────────────────────────────────────────────────────────────

const CANDIDATE_ID = '00000000-0000-4000-8000-000000000001'
const USER_ID = '00000000-0000-4000-8000-000000000002'
const MOCK_TOKEN = 'mock-jwt-token-demo'

/**
 * Simulated network latency so loading states are observable in the demo.
 */
function delay(ms = 220): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ─── Raw backend response shapes (pre-transform) ─────────────────────────────

/**
 * Raw /auth/verify response — matches VerifyResponse in auth.ts.
 * verifyToken() consumes this and reshapes into VerifyResult.
 */
interface RawVerifyResponse {
  access_token: string
  token_type: 'bearer'
  user_id: string
  email: string
  is_onboarded: boolean
}

/**
 * Raw /auth/request-link response — matches RequestLinkResponse in auth.ts.
 */
interface RawRequestLinkResponse {
  message: string
  magic_link?: string
  token?: string
}

/**
 * Raw /onboarding/resume response — matches backend ResumeUploadResponse.
 */
interface RawResumeUploadResponse {
  candidate_id: string
  text_length: number
  preview: string
}

/**
 * Raw /onboarding/profile response — matches backend ProfileResponse.
 */
interface RawProfileResponse {
  candidate_id: string
  is_onboarded: boolean
}

/**
 * Raw /onboarding/status response — matches backend OnboardingStatusResponse.
 */
interface RawOnboardingStatusResponse {
  is_onboarded: boolean
  has_resume: boolean
  has_profile: boolean
  candidate_id: string | null
}

// ─── Fixtures ────────────────────────────────────────────────────────────────

const MOCK_USER: AuthUser = {
  id: USER_ID,
  email: 'alex@example.com',
  name: 'Alex Morgan',
  is_onboarded: true,
  candidate_id: CANDIDATE_ID,
  created_at: '2026-03-01T09:00:00Z',
}

const MOCK_SCORED_JOBS: ScoredJob[] = [
  {
    id: 'sj-001',
    discovered_job_id: 'job-001',
    candidate_id: CANDIDATE_ID,
    score_breakdown: {
      technical_match: 96,
      level_match: 92,
      culture_match: 90,
      industry_match: 95,
      growth_potential: 93,
      compensation_match: 97,
      composite: 94,
    },
    composite_score: 94,
    is_hot: true,
    reasoning:
      'Distributed systems depth (7+ yrs), Python + FastAPI primary, agent systems experience, remote-first stance.',
    scored_at: '2026-05-20T14:22:00Z',
    title: 'Staff AI Engineer · Agent Systems',
    company: 'Anthropic',
    location: 'Remote · US',
    url: 'https://boards.greenhouse.io/anthropic/jobs/0001',
  },
  {
    id: 'sj-002',
    discovered_job_id: 'job-002',
    candidate_id: CANDIDATE_ID,
    score_breakdown: {
      technical_match: 93,
      level_match: 90,
      culture_match: 88,
      industry_match: 89,
      growth_potential: 91,
      compensation_match: 94,
      composite: 91,
    },
    composite_score: 91,
    is_hot: true,
    reasoning:
      'Platform engineering scope, async-first culture, TypeScript + React frontend, edge compute.',
    scored_at: '2026-05-20T14:21:00Z',
    title: 'Principal Engineer · Platform',
    company: 'Vercel',
    location: 'Remote · Americas',
    url: 'https://jobs.lever.co/vercel/0002',
  },
  {
    id: 'sj-003',
    discovered_job_id: 'job-003',
    candidate_id: CANDIDATE_ID,
    score_breakdown: {
      technical_match: 88,
      level_match: 90,
      culture_match: 85,
      industry_match: 92,
      growth_potential: 89,
      compensation_match: 86,
      composite: 88,
    },
    composite_score: 88,
    is_hot: false,
    reasoning:
      'Fintech background match, founding-team scope, AI/ML integration work, compensation aligned.',
    scored_at: '2026-05-20T14:20:00Z',
    title: 'Founding AI Engineer',
    company: 'Stripe',
    location: 'New York · NY',
    url: 'https://jobs.ashbyhq.com/stripe/0003',
  },
  {
    id: 'sj-004',
    discovered_job_id: 'job-004',
    candidate_id: CANDIDATE_ID,
    score_breakdown: {
      technical_match: 86,
      level_match: 84,
      culture_match: 83,
      industry_match: 85,
      growth_potential: 87,
      compensation_match: 84,
      composite: 85,
    },
    composite_score: 85,
    is_hot: false,
    reasoning:
      'Agent orchestration focus, Python primary, remote-global flexibility, async I/O depth required.',
    scored_at: '2026-05-20T14:19:00Z',
    title: 'Senior Backend Engineer · Agent Orchestration',
    company: 'Replit',
    location: 'Remote · Global',
    url: 'https://boards.greenhouse.io/replit/0004',
  },
]

const MOCK_DIGEST: DailyDigest = {
  id: 'mock-digest-001',
  candidate_id: CANDIDATE_ID,
  run_date: '2026-05-20',
  top_picks: MOCK_SCORED_JOBS,
  hot_picks: MOCK_SCORED_JOBS.filter((j) => j.is_hot),
  new_companies: ['Anthropic', 'Vercel', 'Stripe', 'Replit'],
  total_jobs_discovered: 312,
  total_jobs_scored: 48,
  digest_summary:
    '4 strong matches today, 2 hot. Anthropic Staff AI Engineer leads at 94 — agent-systems work lines up almost exactly with recent experience.',
  created_at: '2026-05-20T14:00:00Z',
}

const MOCK_STATS: DiscoveryStats = {
  candidate_id: CANDIDATE_ID,
  total_runs: 47,
  total_discovered: 1284,
  total_scored: 612,
  last_run: '2026-05-20T14:00:00Z',
  recent_runs: [
    {
      id: 'run-047',
      started_at: '2026-05-20T14:00:00Z',
      completed_at: '2026-05-20T14:12:00Z',
      status: 'COMPLETED',
      jobs_discovered: 312,
      jobs_scored: 48,
    },
    {
      id: 'run-046',
      started_at: '2026-05-19T14:00:00Z',
      completed_at: '2026-05-19T14:11:00Z',
      status: 'COMPLETED',
      jobs_discovered: 287,
      jobs_scored: 44,
    },
    {
      id: 'run-045',
      started_at: '2026-05-18T14:00:00Z',
      completed_at: '2026-05-18T14:14:00Z',
      status: 'COMPLETED',
      jobs_discovered: 301,
      jobs_scored: 51,
    },
  ],
}

const MOCK_PIPELINES: ApplicationPipeline[] = [
  {
    id: 'pipe-001',
    candidate_id: CANDIDATE_ID,
    job_id: 'job-001',
    status: 'AWAITING_REVIEW',
    parsed_jd: {
      id: 'jd-001',
      job_id: 'job-001',
      required_skills: ['Python', 'Distributed Systems', 'LLM Integration'],
      preferred_skills: ['FastAPI', 'Kubernetes'],
      seniority_level: 'Staff',
      tech_stack: ['Python', 'FastAPI', 'PostgreSQL', 'Redis'],
      culture_signals: ['Research-driven', 'Safety-focused', 'Remote-first'],
      tone: 'Thoughtful, mission-driven',
      pain_points: ['Scaling agent orchestration', 'Observability of agent state'],
      compensation_range: '$280K – $360K',
      red_flags: [],
      application_instructions: 'Apply via Greenhouse with a short note.',
      parsed_at: '2026-05-20T14:32:00Z',
    },
    tailored_resume: {
      id: 'tr-001',
      pipeline_id: 'pipe-001',
      original_text: 'Alex Morgan — Senior Software Engineer · Platform Systems...',
      tailored_text:
        'Alex Morgan — Staff-level Engineer · Agent Systems & Distributed Platforms...',
      change_log: [
        'Emphasized agent-orchestration work',
        'Surfaced distributed systems depth',
        'Trimmed legacy enterprise specifics',
      ],
      gap_analysis:
        'Strong technical and level match. No frontier-model publication history, but production agent systems experience compensates.',
      created_at: '2026-05-20T14:34:00Z',
    },
    company_intel: {
      id: 'ci-001',
      pipeline_id: 'pipe-001',
      company_name: 'Anthropic',
      about: 'AI safety company building Claude. Founded 2021. Constitutional AI focus.',
      recent_news: ['Claude Opus 4.8 released', 'Series C extension at $7.3B valuation'],
      tech_stack: ['Python', 'PyTorch', 'Kubernetes'],
      engineering_culture: 'Research-driven, safety-first, high autonomy.',
      growth_stage: 'Series C · late',
      team_size: '500-1000',
      notable_facts: ['Founded by former OpenAI researchers', 'Constitutional AI pioneer'],
      researched_at: '2026-05-20T14:36:00Z',
    },
    contact: {
      id: 'ct-001',
      pipeline_id: 'pipe-001',
      name: 'Dario Amodei',
      title: 'CEO',
      email: 'dario@anthropic.com',
      linkedin_url: 'linkedin.com/in/dario-amodei',
      confidence: 'HIGH',
      fallback_email: 'careers@anthropic.com',
      source: 'company_directory',
      found_at: '2026-05-20T14:38:00Z',
    },
    outreach_email: {
      id: 'oe-001',
      pipeline_id: 'pipe-001',
      subject_lines: [
        'Re: Staff AI Engineer · Agent Systems',
        'Agent orchestration — 20 minutes?',
      ],
      body: 'Hi Dario,\n\nI came across the Staff AI Engineer · Agent Systems role and it lines up almost exactly with what I have been building for the last two years — multi-agent orchestration systems with explicit lifecycle states and human-in-the-loop approval gates.\n\n8+ years building distributed systems before this. I would love 20 minutes to talk.\n\nBest,\nAlex Morgan',
      status: 'DRAFT',
      created_at: '2026-05-20T14:40:00Z',
    },
    approval_timestamp: null,
    submitted_at: null,
    screenshots: [],
    created_at: '2026-05-20T14:30:00Z',
    updated_at: '2026-05-20T14:42:00Z',
  },
  {
    id: 'pipe-002',
    candidate_id: CANDIDATE_ID,
    job_id: 'job-002',
    status: 'AWAITING_REVIEW',
    parsed_jd: null,
    tailored_resume: null,
    company_intel: {
      id: 'ci-002',
      pipeline_id: 'pipe-002',
      company_name: 'Vercel',
      about: 'Frontend cloud platform. Next.js maintainers. Edge-first compute.',
      recent_news: ['Series E at $3.25B'],
      tech_stack: ['TypeScript', 'Go', 'Rust'],
      engineering_culture: 'Async-first, ship-fast.',
      growth_stage: 'Series E · late',
      team_size: '500-800',
      notable_facts: ['Next.js maintainers'],
      researched_at: '2026-05-20T14:30:00Z',
    },
    contact: {
      id: 'ct-002',
      pipeline_id: 'pipe-002',
      name: 'Guillermo Rauch',
      title: 'CEO',
      email: 'rauchg@vercel.com',
      linkedin_url: 'linkedin.com/in/rauchg',
      confidence: 'MEDIUM',
      fallback_email: null,
      source: 'public_profile',
      found_at: '2026-05-20T14:31:00Z',
    },
    outreach_email: null,
    approval_timestamp: null,
    submitted_at: null,
    screenshots: [],
    created_at: '2026-05-20T14:28:00Z',
    updated_at: '2026-05-20T14:41:00Z',
  },
  {
    id: 'pipe-003',
    candidate_id: CANDIDATE_ID,
    job_id: 'job-003',
    status: 'SUBMITTED',
    parsed_jd: null,
    tailored_resume: null,
    company_intel: null,
    contact: null,
    outreach_email: null,
    approval_timestamp: '2026-05-20T13:40:00Z',
    submitted_at: '2026-05-20T13:48:00Z',
    screenshots: [],
    created_at: '2026-05-20T13:00:00Z',
    updated_at: '2026-05-20T13:48:00Z',
  },
  {
    id: 'pipe-004',
    candidate_id: CANDIDATE_ID,
    job_id: 'job-004',
    status: 'SENT',
    parsed_jd: null,
    tailored_resume: null,
    company_intel: null,
    contact: null,
    outreach_email: null,
    approval_timestamp: '2026-05-19T17:10:00Z',
    submitted_at: '2026-05-19T17:22:00Z',
    screenshots: [],
    created_at: '2026-05-19T17:00:00Z',
    updated_at: '2026-05-19T17:22:00Z',
  },
  {
    id: 'pipe-005',
    candidate_id: CANDIDATE_ID,
    job_id: 'job-005',
    status: 'REJECTED',
    parsed_jd: null,
    tailored_resume: null,
    company_intel: null,
    contact: null,
    outreach_email: null,
    approval_timestamp: null,
    submitted_at: null,
    screenshots: [],
    created_at: '2026-05-19T10:00:00Z',
    updated_at: '2026-05-19T10:12:00Z',
  },
]

const MOCK_CANDIDATES: CandidateRow[] = [
  { id: 'cand-001', name: 'Marcus Chen', title: 'Sr. ML Engineer', location: 'San Francisco, CA', status: 'active', discovered: 14, applied: 6, interviews: 2, added: 'Mar 15' },
  { id: 'cand-002', name: 'Aisha Patel', title: 'VP of Engineering', location: 'New York, NY', status: 'active', discovered: 22, applied: 9, interviews: 3, added: 'Mar 12' },
  { id: 'cand-003', name: 'Jordan Williams', title: 'Staff Software Engineer', location: 'Austin, TX', status: 'active', discovered: 18, applied: 7, interviews: 1, added: 'Mar 10' },
  { id: 'cand-004', name: 'Sarah Kim', title: 'Head of AI/ML', location: 'Seattle, WA', status: 'reviewing', discovered: 8, applied: 3, interviews: 1, added: 'Mar 8' },
  { id: 'cand-005', name: 'Dev Okonkwo', title: 'Platform Lead', location: 'Portland, OR', status: 'active', discovered: 11, applied: 4, interviews: 0, added: 'Mar 5' },
  { id: 'cand-006', name: 'Lisa Zhang', title: 'Engineering Manager', location: 'Los Angeles, CA', status: 'active', discovered: 16, applied: 8, interviews: 2, added: 'Mar 3' },
  { id: 'cand-007', name: 'Carlos Rivera', title: 'Principal Engineer', location: 'Chicago, IL', status: 'paused', discovered: 5, applied: 2, interviews: 0, added: 'Feb 28' },
  { id: 'cand-008', name: 'Emily Nguyen', title: 'Sr. Backend Engineer', location: 'Denver, CO', status: 'active', discovered: 20, applied: 10, interviews: 4, added: 'Feb 25' },
  { id: 'cand-009', name: 'Raj Krishnamurthy', title: 'CTO / Co-founder', location: 'Boston, MA', status: 'placed', discovered: 3, applied: 3, interviews: 2, added: 'Feb 20' },
]

// ─── Mock router ──────────────────────────────────────────────────────────────

/**
 * Mock match result. `matched: false` signals the seam to fall through to the
 * real network (no fixture for this endpoint).
 */
export interface MockResult {
  matched: boolean
  data?: unknown
}

const NOT_MATCHED: MockResult = { matched: false }

/**
 * Resolve a mock response for a given HTTP method + URL pathname.
 *
 * Matches on method + pathname only (query string and body are ignored unless
 * needed for filtering). Returns the RAW backend response shape so downstream
 * transforms (e.g. verifyToken) run normally.
 *
 * @param method - HTTP method (uppercased)
 * @param pathname - Request path, e.g. '/auth/me' (base URL already stripped)
 * @param search - Raw query string (e.g. '?status=active'), used for filtering
 * @returns A MockResult; if matched is false, the caller should hit the network
 */
export async function resolveMock(
  method: string,
  pathname: string,
  search = ''
): Promise<MockResult> {
  const m = method.toUpperCase()
  const params = new URLSearchParams(search)

  // ── Auth ──
  if (m === 'POST' && pathname === '/auth/request-link') {
    await delay()
    const res: RawRequestLinkResponse = {
      message: 'Magic link generated (mock mode)',
      magic_link: `${window.location.origin}/auth/verify?token=mock-magic-link`,
      token: 'mock-magic-link',
    }
    return { matched: true, data: res }
  }

  if (m === 'POST' && pathname === '/auth/verify') {
    await delay()
    const res: RawVerifyResponse = {
      access_token: MOCK_TOKEN,
      token_type: 'bearer',
      user_id: USER_ID,
      email: MOCK_USER.email,
      is_onboarded: MOCK_USER.is_onboarded,
    }
    return { matched: true, data: res }
  }

  if (m === 'GET' && pathname === '/auth/me') {
    await delay(80)
    return { matched: true, data: MOCK_USER }
  }

  // ── Onboarding ──
  if (m === 'POST' && pathname === '/onboarding/resume') {
    await delay(600)
    const res: RawResumeUploadResponse = {
      candidate_id: CANDIDATE_ID,
      text_length: 2418,
      preview:
        'Alex Morgan — Senior Software Engineer · Platform Systems. 8+ years building distributed systems at scale. Expertise in Python, FastAPI, async I/O, PostgreSQL, Kubernetes, and AI-integrated backends. Most recently led platform reliability at a Series-C SaaS company',
    }
    return { matched: true, data: res }
  }

  if (m === 'POST' && pathname === '/onboarding/profile') {
    await delay()
    const res: RawProfileResponse = { candidate_id: CANDIDATE_ID, is_onboarded: true }
    return { matched: true, data: res }
  }

  if (m === 'GET' && pathname === '/onboarding/status') {
    await delay(80)
    const res: RawOnboardingStatusResponse = {
      is_onboarded: true,
      has_resume: true,
      has_profile: true,
      candidate_id: CANDIDATE_ID,
    }
    return { matched: true, data: res }
  }

  // ── Discovery ──
  if (m === 'GET' && pathname.startsWith('/discovery/digests/')) {
    await delay()
    const summaries: DigestSummary[] = [
      {
        id: 'mock-digest-001',
        run_date: '2026-05-20',
        total_discovered: 312,
        total_scored: 48,
        digest_summary: MOCK_DIGEST.digest_summary ?? null,
        created_at: '2026-05-20T14:00:00Z',
      },
      {
        id: 'mock-digest-002',
        run_date: '2026-05-19',
        total_discovered: 287,
        total_scored: 44,
        digest_summary: '3 strong matches, 1 hot.',
        created_at: '2026-05-19T14:00:00Z',
      },
      {
        id: 'mock-digest-003',
        run_date: '2026-05-18',
        total_discovered: 301,
        total_scored: 51,
        digest_summary: '5 strong matches, 2 hot.',
        created_at: '2026-05-18T14:00:00Z',
      },
    ]
    return { matched: true, data: summaries }
  }

  if (m === 'GET' && pathname.startsWith('/discovery/digest/')) {
    await delay()
    return { matched: true, data: MOCK_DIGEST }
  }

  if (m === 'GET' && pathname.startsWith('/discovery/stats/')) {
    await delay(80)
    return { matched: true, data: MOCK_STATS }
  }

  if (m === 'POST' && pathname.startsWith('/discovery/run/')) {
    await delay(900)
    const res: TriggerRunResponse = {
      message: 'Discovery run queued (mock mode)',
      candidate_id: CANDIDATE_ID,
      dry_run: params.get('dry_run') === 'true',
    }
    return { matched: true, data: res }
  }

  // ── Applications ──
  if (m === 'GET' && pathname === '/application/list') {
    await delay()
    const statusFilter = params.get('status')
    const pipelines = statusFilter
      ? MOCK_PIPELINES.filter((p) => p.status === statusFilter)
      : MOCK_PIPELINES
    const res: ListApplicationsResponse = { pipelines, total: pipelines.length }
    return { matched: true, data: res }
  }

  if (m === 'GET' && pathname.startsWith('/application/')) {
    await delay(100)
    const id = pathname.split('/').pop()
    const pipeline = MOCK_PIPELINES.find((p) => p.id === id) ?? MOCK_PIPELINES[0]
    return { matched: true, data: pipeline }
  }

  // ── Review ──
  if (m === 'POST' && /^\/review\/[^/]+\/approve$/.test(pathname)) {
    await delay(500)
    const id = pathname.split('/')[2]
    const res: ApproveResponse = {
      pipeline_id: id,
      status: 'APPROVED',
      approval_timestamp: new Date().toISOString(),
      message: 'Pipeline approved (mock mode)',
    }
    return { matched: true, data: res }
  }

  if (m === 'POST' && /^\/review\/[^/]+\/reject$/.test(pathname)) {
    await delay(300)
    const id = pathname.split('/')[2]
    const res: RejectResponse = {
      pipeline_id: id,
      status: 'REJECTED',
      message: 'Pipeline rejected (mock mode)',
    }
    return { matched: true, data: res }
  }

  // ── Candidates (forward-compatible; no backend endpoint yet) ──
  if (m === 'GET' && pathname === '/candidates') {
    await delay()
    let items = MOCK_CANDIDATES.slice()
    const statusFilter = params.get('status')
    if (statusFilter && statusFilter !== 'all') {
      items = items.filter((c) => c.status === statusFilter)
    }
    const searchTerm = params.get('search')
    if (searchTerm) {
      const q = searchTerm.toLowerCase()
      items = items.filter(
        (c) =>
          c.name.toLowerCase().includes(q) || c.title.toLowerCase().includes(q)
      )
    }
    const res: ListCandidatesResponse = { items, total: items.length }
    return { matched: true, data: res }
  }

  return NOT_MATCHED
}
