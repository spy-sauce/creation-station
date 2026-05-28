# NUTRIENTS.md — Talent Agent Frozen Contracts

> Frozen contract surface for the Talent Agent organism.
> Stack: `nextjs-fastapi-supabase` (fallback — real stack is React 19 + Vite 8 + FastAPI + PostgreSQL)
> Security tier: `startup`

---

## CONTRACT APPENDIX (verbatim → NUTRIENTS.md)

This appendix is the frozen contract surface for any organism on the nextjs-fastapi-supabase stack. It exists to block the contract-drift class of failure: missing runtime deps, component prop drift, inconsistent styling, ad-hoc icon usage, and duplicate exports.

> The mycelium planner MUST copy every subsection below verbatim into the matching section of NUTRIENTS.md. No paraphrasing. No placeholders. No `#TODO`. Sections C and E are partly verbatim (universal rules) and partly planner-generated (organism-specific rows the planner appends from the agent decomposition). Leaves reading NUTRIENTS treat these as frozen contracts — amendments only via FRUIT_READY contract-amendment line, never silent edits.

### A. Dependency Manifest

Single source of truth for runtime deps. Default owner is `frontend-agent` (web) or `api-agent` (Python). A biome that needs a package not on this list MUST emit `+dep:<pkg>@<ver> reason:<one-line>` on its FRUIT_READY line, or the orchestrator rejects the harvest.

**Frontend (Next.js 14, App Router):**
- next@^14.2.0 — owner: frontend-agent
- react@^18.3.0 — owner: frontend-agent
- react-dom@^18.3.0 — owner: frontend-agent
- typescript@^5.4.0 — owner: frontend-agent
- @supabase/supabase-js@^2.39.0 — owner: frontend-agent
- @supabase/ssr@^0.1.0 — owner: frontend-agent
- tailwindcss@^3.4.0 — owner: frontend-agent
- class-variance-authority@^0.7.0 — owner: frontend-agent
- clsx@^2.1.0 — owner: frontend-agent
- tailwind-merge@^2.2.0 — owner: frontend-agent
- lucide-react@^0.330.0 — owner: frontend-agent
- @radix-ui/react-* — owner: frontend-agent (per-component pin in package.json)
- stripe@^14.0.0 — owner: payments-agent
- @stripe/stripe-js@^3.0.0 — owner: payments-agent

**Backend (FastAPI, Python 3.11+):**
- fastapi>=0.110 — owner: api-agent
- uvicorn[standard]>=0.27 — owner: api-agent
- pydantic>=2.6 — owner: api-agent
- supabase>=2.4 — owner: api-agent
- python-jose[cryptography]>=3.3 — owner: auth-agent
- stripe>=8.0 — owner: payments-agent
- httpx>=0.26 — owner: api-agent

Frontend is locked to Next.js App Router (NOT Pages Router). Backend is locked to FastAPI (NOT Express, NOT Flask).

### B. Component Prop Contracts (TypeScript, frozen)

Full TS interfaces for every shared primitive in `components/ui/`. Frozen: leaves cannot add, remove, or rename props. The frontend-agent biome MUST ship exactly these signatures. If a consumer biome needs a prop not listed, it amends the contract via FRUIT_READY contract-amendment line — never inlines a workaround.

```ts
import type { ButtonHTMLAttributes, InputHTMLAttributes, HTMLAttributes, ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

export type Variant = 'default' | 'primary' | 'secondary' | 'ghost' | 'destructive' | 'outline';
export type Size = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: LucideIcon;
  rightIcon?: LucideIcon;
  asChild?: boolean;
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  leftIcon?: LucideIcon;
  rightIcon?: LucideIcon;
}

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: 'default' | 'elevated' | 'outlined' | 'flat';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export interface AvatarProps {
  src?: string;
  alt?: string;
  fallback?: string;  // initials
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  shape?: 'circle' | 'square';
  className?: string;
}

export interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'destructive';
  size?: 'sm' | 'md';
  className?: string;
}

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}
```

### C. Symbol Ownership Matrix (baseline rows — planner appends organism rows)

Every shared symbol has exactly ONE owner biome. No biome exports a symbol another biome has claimed. If a biome needs a symbol it does not own, it imports — never re-declares.

The rows below are stack-universal — they exist in every nextjs-fastapi-supabase organism. The planner MUST append organism-specific rows below this baseline (entity types, hooks, page-level components) derived from the brief.

| Symbol | Owner biome | File path |
|---|---|---|
| `createServerClient`, `createBrowserClient` | frontend-agent | `lib/supabase.ts` |
| `Button`, `ButtonProps` | frontend-agent | `components/ui/button.tsx` |
| `Input`, `InputProps` | frontend-agent | `components/ui/input.tsx` |
| `Card`, `CardProps` | frontend-agent | `components/ui/card.tsx` |
| `Avatar`, `AvatarProps` | frontend-agent | `components/ui/avatar.tsx` |
| `Badge`, `BadgeProps` | frontend-agent | `components/ui/badge.tsx` |
| `Dialog`, `DialogProps` | frontend-agent | `components/ui/dialog.tsx` |
| `Spinner`, `SpinnerProps` | frontend-agent | `components/ui/spinner.tsx` |
| `cn` (className merge) | frontend-agent | `lib/utils.ts` |
| `Variant`, `Size` | frontend-agent | `components/ui/types.ts` |
| `Settings` (Pydantic) | api-agent | `api/config.py` |
| `get_supabase_client` | api-agent | `api/lib/supabase.py` |
| `SessionUser` (Pydantic) | auth-agent | `api/auth/models.py` |
| `get_current_user` (FastAPI dependency) | auth-agent | `api/auth/deps.py` |

### D. Barrel File Ownership

Module ownership is enforced at the directory level. A biome may not write to a directory it does not own. Cross-biome imports go through public re-export points; never reach into a biome's internals.

| Path | Owner biome | Allowed exports |
|---|---|---|
| `components/ui/` | frontend-agent | All UI primitives. Other biomes import via `@/components/ui/<name>`. |
| `components/<domain>/` | (per-biome) | Domain-specific components owned by the biome named `<domain>`. |
| `lib/` | frontend-agent | Cross-cutting utilities (supabase clients, cn, formatters). |
| `hooks/` | frontend-agent | Re-exports from each biome's hook tree. |
| `types/` | frontend-agent | Sole source of truth for domain entity types. |
| `app/` | frontend-agent | Next.js routes. Other biomes provide page-level components consumed by route segments. |
| `api/` | api-agent | FastAPI app + per-domain routers. Each domain biome contributes `api/<domain>/router.py`. |
| `api/auth/` | auth-agent | All auth-related Python modules. |
| `api/lib/` | api-agent | Shared Python utilities (DB, logging, settings). |

Cardinal rule: a symbol appears in EXACTLY ONE module. Domain enums live in `types/`, NOT in component files.

### E. Allow-listed Identifiers (universal rules — planner appends organism enums and route map)

**Icons.** All icons MUST be `LucideIcon` from `lucide-react`. NEVER import from other icon libraries. NEVER inline SVGs in component code (use a static asset under `public/` if a custom glyph is needed and reference it via `<Image src=... />`).

```tsx
import { Check, X, Loader2 } from 'lucide-react';
<Check className="h-4 w-4" />
```

**Brand glyphs.** Brand logos (Google, GitHub, Stripe, etc.) live as SVG components in `components/brand/`, owned by frontend-agent. NEVER reference brand logos through Lucide.

**Domain enums.** Every domain enum (status, role, type, etc.) is owned by frontend-agent for the TS side (`types/`) and by the corresponding api-agent biome for the Python side (`api/<domain>/models.py`). Both sides MUST stay in sync; the contract amendment process covers both edits.

**Route names.** Next.js App Router uses file-based routing — route paths are file paths under `app/`. The planner appends the full route map below from the brief's page inventory. Cross-route navigation uses typed `Link href` literals or a `routes` constant exported from `lib/routes.ts`. Biomes do NOT inline route strings.

### F. Style System Rules

1. **NEVER hardcode hex colors in component code.** All colors come from Tailwind tokens defined in `tailwind.config.ts`. Theme tokens live in CSS variables. Rationale: hardcoded hex defeats the token system and prevents theme switching.

   ```tsx
   // GOOD
   <div className="bg-primary text-primary-foreground" />
   // BAD
   <div style={{ backgroundColor: '#7C5CFF' }} />
   ```

2. **Conditional className composition uses `cn` from `lib/utils.ts`** (clsx + tailwind-merge). Never inline string concatenation.

   ```tsx
   // GOOD
   <div className={cn('base-classes', active && 'bg-primary', disabled && 'opacity-50')} />
   // BAD
   <div className={`base-classes ${active ? 'bg-primary' : ''}`} />
   ```

3. **Class-Variance-Authority (cva) for primitive variants.** Every primitive that exposes a `variant` or `size` prop MUST implement them via `cva`. NEVER ad-hoc switch statements over variant strings.

4. **Server Components by default; Client Components only when needed.** Add `'use client'` only when the component uses state, effects, browser APIs, or event handlers. Rationale: Server Component default keeps bundle size down and aligns with App Router conventions.

5. **TypeScript strict mode.** No `any`. No `@ts-ignore` (use `@ts-expect-error` with a comment explaining why, or fix the type). No `as` casts on shared primitives.

6. **API responses are typed end-to-end.** FastAPI Pydantic models on the backend; matching TS interfaces on the frontend. NEVER consume an API response without a type. The api-agent biome owns the source-of-truth Pydantic models; frontend-agent owns the TS mirrors.

### G. Screen Ownership Matrix (universal rules — planner appends per-route table)

Next.js App Router uses file-based routing — there is no central RootNavigator to stub. Each route is a directory under `app/` with a `page.tsx` (and optionally `layout.tsx`, `loading.tsx`, `error.tsx`).

**Universal wiring rules:**

1. **Every route in the brief's route inventory MUST have a real `page.tsx` file.** Stubbing pages with `export default function Page() { return null; }` is FORBIDDEN — it produces the same black-screen failure mode as React Native's PlaceholderScreen anti-pattern. Either ship a real page or ship a visible placeholder showing the route name and "Page pending" copy.

2. **Each domain biome owns its own `app/<domain>/` subtree.** `frontend-agent` owns `app/(marketing)/`, layout files, and root-level files (`app/layout.tsx`, `app/page.tsx`); domain biomes own everything under their domain segment.

3. **Server vs client components**: routes default to Server Components. `'use client'` is required only when state, effects, or browser APIs are needed.

**Required table format** (planner generates from the brief's route inventory):

| Route | Owner biome | File path | Type |
|---|---|---|---|
| `/` | frontend-agent | `app/page.tsx` | server |
| `/login` | auth-agent | `app/(auth)/login/page.tsx` | client |
| `/dashboard` | frontend-agent | `app/dashboard/page.tsx` | server |
| ... (every route in the brief) | ... | ... | ... |

**Anti-pattern (FORBIDDEN):** empty pages returning `null`. If a page's logic isn't yet shipped, render a visible placeholder with the route path and a "Page pending" message on the theme background.

### H. Security Rules

Section H is the security contract surface for the nextjs-fastapi-supabase stack. Initial baseline — will tighten on first cultivation. Rules tagged with tiers: `[demo]` everywhere, `[startup]` startup+regulated, `[regulated]` regulated only, `[always-block]` blocks at every tier.

#### H.1 Secret Management

##### H.1.1 No hardcoded secrets in committed code [always-block]
Rule: No real API keys, tokens, or credentials in committed source. Exempt:
  literals containing `placeholder` matching demo-stub patterns.
Audit: `grep -rEn 'sk_live_|sk_test_|eyJ[A-Za-z0-9]{30,}|service_role|AKIA[0-9A-Z]{16}' src/ api/` excluding lines containing `placeholder` returns zero.
Violation: freeze-block at all tiers.

##### H.1.2 .env gitignored [demo]
Rule: `.env`, `.env.local`, `.env.production` listed in `.gitignore`. Only `.env.example` (no real values) committed.
Audit: parse `.gitignore`; `git ls-files` for .env* returns at most `.env.example`.
Violation: demo=advisory, startup+=freeze-block.

##### H.1.3 Server secrets never in client bundle [always-block]
Rule: Next.js client code (under `app/` or `components/` consumed by client components) MUST NOT reference secrets without `NEXT_PUBLIC_` prefix. Server-only secrets (no prefix) used only in Server Components, Server Actions, Route Handlers, or under `api/` (FastAPI).
Audit: in `'use client'`-annotated files, grep for env var references not starting with `NEXT_PUBLIC_`; must return zero.
Violation: freeze-block at all tiers.

#### H.2 Auth Flows

##### H.2.1 Sessions in httpOnly cookies, never localStorage [demo]
Rule: Auth tokens persisted as httpOnly + Secure + SameSite=Strict cookies. `localStorage`, `sessionStorage` for sessions are forbidden.
Audit: grep `localStorage.setItem` and `sessionStorage.setItem` in src/ near auth/session/token identifiers.
Violation: demo=advisory, startup+=freeze-block.

#### H.3 Database (RLS)

##### H.3.1 Every Supabase table has RLS enabled [always-block]
Rule: Every `CREATE TABLE` in migrations is followed by `ENABLE ROW LEVEL SECURITY` in the same file.
Audit: regex parse SQL migrations.
Violation: freeze-block at all tiers.

#### H.4 PII Handling

##### H.4.1 PII categories defined [demo]
Rule: NUTRIENTS.md §H.4 defines PII vocabulary (default: email, phone, address, payment, legal name, location, national IDs).
Audit: contract-vs-contract via audit prompt.
Violation: demo=advisory, startup+=freeze-block.

##### H.4.2 No PII in logs [demo]
Rule: `console.log`, `console.error`, server logger calls, and `Sentry.captureException` MUST NOT include PII identifiers.
Audit: regex grep for log calls containing PII identifier names.
Violation: demo=advisory, startup+=freeze-block.

(Other rules — H.2.2/H.2.3, H.3.2-5, H.4.3-5 — refine on first cultivation.)

---

## STACK-CANON OVERRIDE (Talent Agent specific)

**The verbatim contract appendix Section H above is partially NEGATED for this organism.**

This repo uses `--stack nextjs-fastapi-supabase` because no `fastapi-postgres` preset exists. The preset's rules conflict with this repo's actual stack. When the preset and this override conflict, **this override wins — always.**

### Negated Rules (do NOT enforce)

- **H.1.3 (`NEXT_PUBLIC_` prefix)** — NEGATED. This repo uses **React 19 + Vite 8**, NOT Next.js. Env vars use `VITE_*` prefix per Vite's `import.meta.env` convention.

- **H.2.1 (httpOnly cookies)** — NEGATED. JWT storage is **localStorage** per iter-2's resolved decision. `AuthContext` reads/writes localStorage directly, sets `Bearer` header in `lib/api.js`.

- **H.3.1 (Supabase RLS)** — NEGATED. This repo uses **raw PostgreSQL 15 via SQLAlchemy 2.0 async + Alembic**. No Supabase, no RLS policies.

### Positive Stack Canon

| Layer | Actual Stack |
|---|---|
| Frontend | React 19 · Vite 8 · Tailwind 4 · lucide-react · react-router-dom 7 |
| Backend | FastAPI · Python 3.12 · Pydantic v2 · SQLAlchemy 2.0 async · Alembic |
| Database | PostgreSQL 15 raw, via SQLAlchemy async engine |
| Auth | JWT HS256, 7d, stored in localStorage, sent as `Authorization: Bearer <token>` |
| Storage | Local FS (dev) / S3 (prod future) |
| Env vars | `VITE_*` for frontend, unprefixed for backend |

---

## ORGANISM-SPECIFIC EXTENSIONS

### C. Symbol Ownership Matrix (organism rows)

| Symbol | Owner biome | File path |
|---|---|---|
| `Candidate`, `CandidateSchema` | data-agent | `backend/models/discovery.py`, `backend/agents/discovery/schemas.py` |
| `DiscoveredJob`, `DiscoveredJobSchema` | data-agent | `backend/models/discovery.py`, `backend/agents/discovery/schemas.py` |
| `ScoredJob`, `ScoredJobSchema` | data-agent | `backend/models/discovery.py`, `backend/agents/discovery/schemas.py` |
| `DailyDigest`, `DailyDigestSchema` | data-agent | `backend/models/discovery.py`, `backend/agents/discovery/schemas.py` |
| `CrawlRun` | data-agent | `backend/models/discovery.py` |
| `ParsedJD`, `ParsedJDSchema` | data-agent | `backend/models/application.py`, `backend/agents/application/schemas.py` |
| `TailoredResume`, `TailoredResumeSchema` | data-agent | `backend/models/application.py`, `backend/agents/application/schemas.py` |
| `CompanyIntel`, `CompanyIntelSchema` | data-agent | `backend/models/application.py`, `backend/agents/application/schemas.py` |
| `Contact`, `ContactSchema` | data-agent | `backend/models/application.py`, `backend/agents/application/schemas.py` |
| `ApplicationPipeline`, `ApplicationPipelineSchema` | data-agent | `backend/models/application.py`, `backend/agents/application/schemas.py` |
| `CRMEvent` | data-agent | `backend/models/application.py` |
| `User`, `MagicLink` | data-agent | `backend/models/auth.py` |
| `IdentityProfileSchema` | data-agent | `backend/agents/discovery/schemas.py` |
| `SearchManifestSchema` | data-agent | `backend/agents/discovery/schemas.py` |
| `ScoreBreakdown` | data-agent | `backend/agents/discovery/schemas.py` |
| `OutreachEmailSchema` | data-agent | `backend/agents/application/schemas.py` |
| `AuthContext` | frontend-agent | `frontend/src/context/AuthContext.jsx` |
| `DashboardLayout` | frontend-agent | `frontend/src/layouts/DashboardLayout.jsx` |
| `Sidebar` | frontend-agent | `frontend/src/components/Sidebar.jsx` |
| `TopBar` | frontend-agent | `frontend/src/components/TopBar.jsx` |
| `StatCard` | frontend-agent | `frontend/src/components/StatCard.jsx` |
| `StatusBadge` | frontend-agent | `frontend/src/components/StatusBadge.jsx` |
| `api` (client) | frontend-agent | `frontend/src/lib/api.js` |
| `routes` | frontend-agent | `frontend/src/lib/routes.js` |
| `IdentityProfiler` | discover-agent | `backend/agents/discovery/identity_profiler.py` |
| `ArchetypeGenerator` | discover-agent | `backend/agents/discovery/archetype_generator.py` |
| `CrawlerAgent` | discover-agent | `backend/agents/discovery/crawler_agent.py` |
| `RelevanceScorer` | discover-agent | `backend/agents/discovery/relevance_scorer.py` |
| `DigestBuilder` | discover-agent | `backend/agents/discovery/digest_builder.py` |
| `DiscoveryOrchestrator` | discover-agent | `backend/agents/discovery/orchestrator.py` |
| `JDParser` | apply-agent | `backend/agents/application/jd_parser.py` |
| `ResumeTailor` | apply-agent | `backend/agents/application/resume_tailor.py` |
| `CompanyIntelAgent` | apply-agent | `backend/agents/application/company_intel.py` |
| `ContactFinder` | apply-agent | `backend/agents/application/contact_finder.py` |
| `OutreachComposer` | apply-agent | `backend/agents/application/outreach_composer.py` |
| `AutoApplyAgent` | apply-agent | `backend/agents/application/auto_apply.py` |
| `CRM` | apply-agent | `backend/agents/application/crm.py` |
| `ApplicationOrchestrator` | apply-agent | `backend/agents/application/orchestrator.py` |
| `AgentManager` | agents-agent | `backend/agents/application/agent_manager.py` |
| `SubAgentRegistry` | agents-agent | `backend/agents/application/agent_manager.py` |
| `SubAgentRunner` | agents-agent | `backend/agents/application/agent_manager.py` |
| `PipelineDispatcher` | agents-agent | `backend/agents/application/agent_manager.py` |
| `get_current_user` | auth-agent | `backend/api/auth.py` |

### E. Allow-listed Identifiers (organism extension)

#### Domain Enums

```typescript
// Job source enum
export type JobSource = 'greenhouse' | 'lever' | 'ashby' | 'workday';

// Crawl run status
export type CrawlRunStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';

// Application pipeline status (state machine)
export type ApplicationPipelineStatus =
  | 'QUEUED'
  | 'PARSING'
  | 'TAILORING'
  | 'RESEARCHING'
  | 'COMPOSING'
  | 'AWAITING_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUBMITTED'
  | 'SENT'
  | 'TRACKED'
  | 'FAILED'
  | 'REQUIRES_MANUAL';

// Agent status (lifecycle)
export type AgentStatus =
  | 'QUEUED'
  | 'DISPATCHED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'RETRYING'
  | 'DEAD';

// Contact confidence
export type ContactConfidence = 'HIGH' | 'MEDIUM' | 'LOW';

// Remote preference
export type RemotePreference = 'remote_only' | 'hybrid' | 'onsite' | 'flexible';

// Outreach status
export type OutreachStatus = 'DRAFT' | 'SENT' | 'BOUNCED' | 'REPLIED';
```

#### Route Map (React Router DOM, NOT Next.js App Router)

This organism uses React Router DOM with `react-router-dom@7`, NOT Next.js App Router. Routes are defined in `frontend/src/App.jsx`.

```typescript
// Route definitions (for lib/routes.js)
export const routes = {
  landing: '/',
  login: '/login',
  verifyAuth: '/auth/verify',
  onboarding: '/onboarding',
  overview: '/overview',
  candidates: '/candidates',
  pipeline: '/pipeline',
  reviewQueue: '/review-queue',
  analytics: '/analytics',
  settings: '/settings',
} as const;

export type RouteName = keyof typeof routes;
```

### G. Screen Ownership Matrix (organism routes)

**Note:** This organism uses React Router DOM (`react-router-dom@7`), NOT Next.js App Router. Routes are file-based under `frontend/src/pages/`.

| Route | Owner biome | File path | Type |
|---|---|---|---|
| `/` | frontend-agent | `frontend/src/pages/Landing.jsx` | client |
| `/login` | frontend-agent | `frontend/src/pages/Login.jsx` | client |
| `/auth/verify` | frontend-agent | `frontend/src/pages/VerifyAuth.jsx` | client |
| `/onboarding` | frontend-agent | `frontend/src/pages/Onboarding.jsx` | client |
| `/overview` | frontend-agent | `frontend/src/pages/Overview.jsx` | client |
| `/candidates` | frontend-agent | `frontend/src/pages/Candidates.jsx` | client |
| `/pipeline` | frontend-agent | `frontend/src/pages/Pipeline.jsx` | client |
| `/review-queue` | frontend-agent | `frontend/src/pages/ReviewQueue.jsx` | client |
| `/analytics` | frontend-agent | `frontend/src/pages/Analytics.jsx` | client |
| `/settings` | frontend-agent | `frontend/src/pages/Settings.jsx` | client |

---

## DATA_CONTRACTS

Full TypeScript interfaces for every domain entity. These mirror the Pydantic schemas in `backend/agents/*/schemas.py`.

```typescript
// === Discovery Domain ===

export interface Candidate {
  id: string; // UUID
  name: string;
  email: string;
  resume_text: string;
  linkedin_url: string | null;
  github_url: string | null;
  personal_context: string | null;
  target_locations: string[];
  remote_preference: RemotePreference;
  min_compensation: number | null;
  excluded_companies: string[];
  excluded_industries: string[];
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface IdentityProfile {
  archetypes: string[];
  leadership_level: 'IC' | 'Lead' | 'Manager' | 'Director' | 'VP' | 'C-Level';
  technical_skills: string[];
  soft_skills: string[];
  industry_experience: string[];
  notable_achievements: string[];
  career_trajectory: string;
  ideal_role_description: string;
  signals: Record<string, string>;
}

export interface SearchManifest {
  target_titles: string[];
  keywords: string[];
  excluded_titles: string[];
  excluded_companies: string[];
  excluded_industries: string[];
  location_filters: string[];
  remote_preference: RemotePreference;
  min_compensation: number | null;
}

export interface DiscoveredJob {
  id: string; // UUID
  source: JobSource;
  source_id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  url: string;
  posted_at: string | null; // ISO 8601
  salary_min: number | null;
  salary_max: number | null;
  remote: boolean;
  crawled_at: string; // ISO 8601
}

export interface ScoreBreakdown {
  technical_match: number; // 0-100
  level_match: number; // 0-100
  culture_match: number; // 0-100
  industry_match: number; // 0-100
  growth_potential: number; // 0-100
  compensation_match: number; // 0-100
}

export interface ScoredJob {
  id: string; // UUID
  discovered_job_id: string; // FK
  candidate_id: string; // FK
  score_breakdown: ScoreBreakdown;
  composite_score: number; // 0-100
  is_hot: boolean;
  reasoning: string;
  scored_at: string; // ISO 8601
}

export interface DailyDigest {
  id: string; // UUID
  candidate_id: string; // FK
  run_date: string; // YYYY-MM-DD
  top_picks: ScoredJob[];
  hot_picks: ScoredJob[];
  new_companies: string[];
  total_jobs_discovered: number;
  total_jobs_scored: number;
  created_at: string; // ISO 8601
}

export interface CrawlRun {
  id: string; // UUID
  candidate_id: string; // FK
  status: CrawlRunStatus;
  jobs_discovered: number;
  jobs_scored: number;
  started_at: string; // ISO 8601
  completed_at: string | null; // ISO 8601
  error_log: string | null;
}

// === Application Domain ===

export interface ParsedJD {
  id: string; // UUID
  job_id: string; // FK to discovered_jobs
  required_skills: string[];
  preferred_skills: string[];
  seniority_level: string;
  tech_stack: string[];
  culture_signals: string[];
  tone: string;
  pain_points: string[];
  compensation_range: string | null;
  red_flags: string[];
  application_instructions: string | null;
  parsed_at: string; // ISO 8601
}

export interface TailoredResume {
  id: string; // UUID
  pipeline_id: string; // FK
  original_text: string;
  tailored_text: string;
  change_log: string[];
  gap_analysis: string;
  created_at: string; // ISO 8601
}

export interface CompanyIntel {
  id: string; // UUID
  pipeline_id: string; // FK
  company_name: string;
  about: string;
  recent_news: string[];
  tech_stack: string[];
  engineering_culture: string;
  growth_stage: string;
  team_size: string | null;
  notable_facts: string[];
  researched_at: string; // ISO 8601
}

export interface Contact {
  id: string; // UUID
  pipeline_id: string; // FK
  name: string;
  title: string;
  email: string;
  linkedin_url: string | null;
  confidence: ContactConfidence;
  fallback_email: string | null;
  source: string;
  found_at: string; // ISO 8601
}

export interface OutreachEmail {
  id: string; // UUID
  pipeline_id: string; // FK
  subject_lines: string[]; // 3 variants
  body: string; // 150-200 words
  status: OutreachStatus;
  created_at: string; // ISO 8601
}

export interface ApplicationPipeline {
  id: string; // UUID
  candidate_id: string; // FK
  job_id: string; // FK to scored_jobs
  status: ApplicationPipelineStatus;
  parsed_jd: ParsedJD | null;
  tailored_resume: TailoredResume | null;
  company_intel: CompanyIntel | null;
  contact: Contact | null;
  outreach_email: OutreachEmail | null;
  approval_timestamp: string | null; // ISO 8601
  submitted_at: string | null; // ISO 8601
  screenshots: string[]; // paths to screenshot files
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface CRMEvent {
  id: string; // UUID
  pipeline_id: string; // FK
  event_type: string; // SCREAMING_SNAKE_CASE
  payload: Record<string, unknown>;
  created_at: string; // ISO 8601
}

// === Auth Domain ===

export interface User {
  id: string; // UUID
  email: string;
  name: string | null;
  is_active: boolean;
  is_onboarded: boolean;
  candidate_id: string | null; // FK
  last_login_at: string | null; // ISO 8601
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface MagicLink {
  id: string; // UUID
  user_id: string; // FK
  token: string; // 48-byte URL-safe
  expires_at: string; // ISO 8601
  is_used: boolean;
  created_at: string; // ISO 8601
}

// === Agent Execution ===

export interface AgentExecutionRecord {
  execution_id: string; // UUID
  agent_name: string;
  pipeline_id: string;
  status: AgentStatus;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  error: string | null;
  attempt: number;
  started_at: string; // ISO 8601
  completed_at: string | null; // ISO 8601
  duration_ms: number | null;
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  } | null;
}
```

---

## DESIGN_TOKENS

**Variant:** Top Shelf — Editorial Consulting (gold-on-black, seanyoung.biz-derived)

### Color Palette

```css
:root {
  /* Primary palette */
  --gold: #C9A227;
  --gold-dim: rgba(201, 162, 39, 0.7);
  --gold-faint: rgba(201, 162, 39, 0.15);

  /* Backgrounds */
  --bg-primary: #0A0A0A;
  --bg-secondary: #141414;
  --bg-tertiary: #1A1A1A;
  --bg-elevated: #1F1F1F;

  /* Text */
  --text-primary: #FAFAFA;
  --text-secondary: #A3A3A3;
  --text-muted: #737373;

  /* Borders */
  --border: rgba(255, 255, 255, 0.08);
  --border-hover: rgba(255, 255, 255, 0.15);

  /* Status colors */
  --status-success: #22C55E;
  --status-warning: #EAB308;
  --status-error: #EF4444;
  --status-info: #3B82F6;
  --status-pending: #A855F7;
  --status-hot: #F97316;

  /* Semantic */
  --accent: var(--gold);
  --accent-hover: #D4AF37;
  --destructive: #DC2626;
  --destructive-hover: #B91C1C;
}
```

### Typography Scale

```css
:root {
  /* Font families */
  --font-serif: 'Playfair Display', Georgia, serif;
  --font-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'DM Mono', 'Fira Code', monospace;

  /* Font sizes */
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */
  --text-3xl: 1.875rem;  /* 30px */
  --text-4xl: 2.25rem;   /* 36px */
  --text-5xl: 3rem;      /* 48px */

  /* Line heights */
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.75;

  /* Font weights */
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
}
```

### Typography Utility Classes

```css
/* Page headings — Playfair Display bold */
.t-serif-bold {
  font-family: var(--font-serif);
  font-weight: var(--font-bold);
  font-size: var(--text-5xl);
  line-height: var(--leading-tight);
  color: var(--text-primary);
}

/* Section headings — Playfair Display regular */
.t-serif {
  font-family: var(--font-serif);
  font-weight: var(--font-normal);
  font-size: var(--text-2xl);
  line-height: var(--leading-tight);
  color: var(--text-primary);
}

/* Labels — DM Sans uppercase tracking */
.t-label {
  font-family: var(--font-sans);
  font-weight: var(--font-medium);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

/* Gold accent labels */
.t-label-gold {
  font-family: var(--font-sans);
  font-weight: var(--font-medium);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gold);
}

/* Body text — DM Sans */
.t-body {
  font-family: var(--font-sans);
  font-weight: var(--font-normal);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--text-primary);
}

/* Mono / code */
.t-mono {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}
```

### Spacing Scale

```css
:root {
  --space-0: 0;
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
  --space-20: 5rem;     /* 80px */
  --space-24: 6rem;     /* 96px */
}
```

### Border Radii

```css
:root {
  --radius-none: 0;
  --radius-sm: 0.125rem;  /* 2px */
  --radius-md: 0.375rem;  /* 6px */
  --radius-lg: 0.5rem;    /* 8px */
  --radius-xl: 0.75rem;   /* 12px */
  --radius-full: 9999px;
}
```

### Shadows

```css
:root {
  /* Minimal shadows — editorial aesthetic prefers border over shadow */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);

  /* Glow effects for accent elements */
  --glow-gold: 0 0 20px rgba(201, 162, 39, 0.3);
}
```

### Motion / Transitions

```css
:root {
  /* Durations */
  --duration-fast: 150ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;

  /* Easing */
  --ease-default: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

/* Standard transition shorthand */
.transition-default {
  transition: all var(--duration-normal) var(--ease-default);
}
```

### Scrollbar Treatment

```css
/* Webkit scrollbars */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--border-hover);
}
```

### Selection Treatment

```css
::selection {
  background: var(--gold-faint);
  color: var(--gold);
}
```

---

## API_CONTRACTS

Full request/response shapes per endpoint.

### Auth Endpoints

#### POST /api/v1/auth/request-link

Request magic link for email.

```typescript
// Request
interface RequestLinkRequest {
  email: string;
}

// Response (200)
interface RequestLinkResponse {
  message: string;
  magic_link?: string; // Only in DEBUG=true
  token?: string; // Only in DEBUG=true
}
```

#### POST /api/v1/auth/verify

Verify magic link token, return JWT.

```typescript
// Request
interface VerifyRequest {
  token: string;
}

// Response (200)
interface VerifyResponse {
  access_token: string;
  token_type: 'bearer';
  user_id: string;
  email: string;
  is_onboarded: boolean;
}

// Error responses
// 401: "This link has already been used"
// 401: "This link has expired"
// 401: "Invalid or expired link"
```

#### GET /api/v1/auth/me

Get current authenticated user.

```typescript
// Headers: Authorization: Bearer <jwt>

// Response (200)
interface MeResponse {
  id: string;
  email: string;
  name: string | null;
  is_onboarded: boolean;
  candidate_id: string | null;
  created_at: string;
}

// Error responses
// 401: "Not authenticated"
// 401: "Token expired"
// 401: "User not found or inactive"
```

### Onboarding Endpoints

#### POST /api/v1/onboarding/resume

Upload resume PDF (multipart).

```typescript
// Request: multipart/form-data
// Field: file (PDF, max 10MB)

// Response (200)
interface ResumeUploadResponse {
  message: string;
  candidate_id: string;
  text_length: number;
  preview: string; // First 500 chars
}

// Error responses
// 422: "Only PDF files are accepted..."
// 422: "File too large. Max 10MB."
// 422: "Could not extract any text from the PDF"
```

#### POST /api/v1/onboarding/profile

Save candidate profile.

```typescript
// Request
interface ProfileRequest {
  name: string;
  linkedin_url?: string;
  github_url?: string;
  personal_context?: string;
  target_locations?: string[];
  remote_preference?: RemotePreference; // default: 'flexible'
  min_compensation?: number;
  excluded_companies?: string[];
  excluded_industries?: string[];
}

// Response (200)
interface ProfileResponse {
  message: string;
  candidate_id: string;
  is_onboarded: boolean;
}

// Error responses
// 400: "Please upload your resume first..."
```

#### GET /api/v1/onboarding/status

Get onboarding completeness.

```typescript
// Response (200)
interface OnboardingStatusResponse {
  is_onboarded: boolean;
  has_resume: boolean;
  has_profile: boolean;
  candidate_id?: string;
}
```

### Discovery Endpoints

#### POST /api/v1/discovery/trigger

Trigger discovery run for candidate.

```typescript
// Request
interface TriggerDiscoveryRequest {
  candidate_id: string;
  dry_run?: boolean; // default: false
}

// Response (200)
interface TriggerDiscoveryResponse {
  crawl_run_id: string;
  status: CrawlRunStatus;
  message: string;
}
```

#### GET /api/v1/discovery/digest/{digest_id}

Get daily digest by ID.

```typescript
// Response (200)
interface GetDigestResponse {
  digest: DailyDigest;
}

// Error responses
// 404: "Digest not found"
```

### Application Endpoints

#### POST /api/v1/application/start

Start application pipeline for a job.

```typescript
// Request
interface StartApplicationRequest {
  job_id: string; // scored_job ID
  candidate_id: string;
}

// Response (200)
interface StartApplicationResponse {
  pipeline: ApplicationPipeline;
}
```

#### POST /api/v1/application/submit/{pipeline_id}

Submit approved application.

```typescript
// Response (200)
interface SubmitApplicationResponse {
  pipeline_id: string;
  status: ApplicationPipelineStatus;
  message: string;
}

// Error responses
// 400: "Pipeline must be APPROVED before submission"
// 404: "Pipeline not found"
```

#### GET /api/v1/application/list

List application pipelines.

```typescript
// Query params
interface ListApplicationsQuery {
  candidate_id?: string;
  status?: ApplicationPipelineStatus;
  limit?: number; // default: 50
  offset?: number; // default: 0
}

// Response (200)
interface ListApplicationsResponse {
  pipelines: ApplicationPipeline[];
  total: number;
}
```

#### GET /api/v1/application/{pipeline_id}

Get pipeline details.

```typescript
// Response (200)
interface GetPipelineResponse {
  pipeline: ApplicationPipeline;
}

// Error responses
// 404: "Pipeline not found"
```

### Review Endpoints

#### GET /api/v1/review/queue

Get pipelines awaiting review.

```typescript
// Query params
interface ReviewQueueQuery {
  candidate_id?: string;
}

// Response (200)
interface ReviewQueueResponse {
  pipelines: ApplicationPipeline[]; // status = AWAITING_REVIEW
}
```

#### POST /api/v1/review/{pipeline_id}/approve

Approve pipeline for submission.

```typescript
// Response (200)
interface ApproveResponse {
  pipeline_id: string;
  status: 'APPROVED';
  approval_timestamp: string;
  message: string;
}

// Error responses
// 404: "Pipeline not found"
// 400: "Pipeline is not awaiting review"
```

#### POST /api/v1/review/{pipeline_id}/reject

Reject pipeline.

```typescript
// Request
interface RejectRequest {
  reason?: string;
}

// Response (200)
interface RejectResponse {
  pipeline_id: string;
  status: 'REJECTED';
  message: string;
}

// Error responses
// 404: "Pipeline not found"
// 400: "Pipeline is not awaiting review"
```

### Health Endpoint

#### GET /health

Service health check.

```typescript
// Response (200)
interface HealthResponse {
  status: 'ok';
  version: string; // semver
  git_sha: string;
  redis: 'ok' | 'down';
  db: 'ok' | 'down';
}
```

---

## H.4 PII Vocabulary (organism-specific)

PII categories that MUST be redacted from logs:

- `email` — candidate email, contact email, user email
- `phone` — any phone numbers
- `legal_name` — full legal name if distinct from display name
- `resume_text` — full resume content
- `personal_context` — candidate personal context field
- `linkedin_url` — LinkedIn profile URL
- `github_url` — GitHub profile URL
- `address` — physical addresses
- `compensation` — salary/compensation details

---

## ITER-4 CONTRACT EXTENSIONS

### C. Symbol Ownership Matrix (iter-4 additions)

| Symbol | Owner biome | File path |
|---|---|---|
| `celery_app` | scheduler-agent | `backend/scheduler/celery_app.py` |
| `daily_discovery_task` | scheduler-agent | `backend/scheduler/tasks.py` |
| `beat_schedule` | scheduler-agent | `backend/scheduler/beat.py` |
| `events_router` | api-streaming-agent | `backend/api/events.py` |
| `SSESubscriber` | api-streaming-agent | `backend/api/events.py` |
| `apiClient` | api-client-agent | `frontend/src/api/client.ts` |
| `requestMagicLink`, `verifyToken`, `refreshSession` | api-client-agent | `frontend/src/api/auth.ts` |
| `getTodayDigest`, `triggerDiscoveryRun`, `getJob` | api-client-agent | `frontend/src/api/discovery.ts` |
| `listApplications`, `approveApplication`, `rejectApplication` | api-client-agent | `frontend/src/api/applications.ts` |
| `subscribeAgentStatus` | api-client-agent | `frontend/src/api/events.ts` |
| `TalentAgentApiError` | api-client-agent | `frontend/src/api/client.ts` |
| `_publish_status` | discover-agent | `backend/agents/discovery/orchestrator.py` |

### E. Allow-listed Identifiers (iter-4 additions)

#### Discovery Event Types

```typescript
// Events published to agent.status.discovery
export type DiscoveryEventType =
  | 'RUN_STARTED'
  | 'CANDIDATE_LOADED'
  | 'PROFILE_BUILT'
  | 'MANIFEST_BUILT'
  | 'CRAWL_SOURCE_COMPLETE'  // includes {source, jobs_found}
  | 'CRAWL_COMPLETE'
  | 'SCORING_COMPLETE'
  | 'RUN_COMPLETE'
  | 'RUN_FAILED'
  | 'DAILY_TASK_DEAD';  // from scheduler on terminal failure

// Discovery status event payload
export interface DiscoveryStatusEvent {
  candidate_id: string;
  event: DiscoveryEventType;
  ts: string;  // ISO-8601 UTC
  source?: JobSource;  // present for CRAWL_SOURCE_COMPLETE
  jobs_found?: number;  // present for CRAWL_SOURCE_COMPLETE
  error?: string;  // present for RUN_FAILED, DAILY_TASK_DEAD
}
```

#### SSE Event Stream

```typescript
// Allowed channels for SSE streaming
export type AllowedSSEChannel =
  | 'agent.status.discovery'
  | 'agent.status.application';

// Slow client warning event
export interface SlowClientEvent {
  dropped: number;
}
```

#### Celery Task IDs

```typescript
// Daily discovery task ID format (for idempotency)
// Pattern: discovery-{candidate_id}-{YYYY-MM-DD}
export type DailyDiscoveryTaskId = `discovery-${string}-${string}`;
```

### API_CONTRACTS (iter-4 additions)

#### SSE Event Stream Endpoint

##### GET /events/stream

Stream real-time agent status events via Server-Sent Events.

```typescript
// Query params
interface EventStreamQuery {
  channel: AllowedSSEChannel;
}

// Headers required
// Authorization: Bearer <jwt>

// Response: text/event-stream
// Each message is: data: {json}\n\n
// Heartbeat every 15s: :ping\n\n
// On backpressure: event: slow_client\ndata: {"dropped": N}\n\n

// Error responses
// 400: "Invalid channel. Allowed: agent.status.discovery, agent.status.application"
// 401: "Not authenticated"
```

### DATA_CONTRACTS (iter-4 additions)

```typescript
// === Scheduler Domain ===

export interface CeleryTaskRecord {
  task_id: string;  // DailyDiscoveryTaskId format
  candidate_id: string;
  status: 'PENDING' | 'STARTED' | 'RETRY' | 'SUCCESS' | 'FAILURE';
  retries: number;
  started_at: string | null;  // ISO 8601
  completed_at: string | null;  // ISO 8601
  error_log: string | null;
}

// === API Client Domain ===

export interface TalentAgentApiErrorData {
  status: number;  // HTTP status code
  code: string;  // Backend error code if present
  message: string;  // User-facing message
}

// API client configuration
export interface ApiClientConfig {
  baseUrl: string;  // from VITE_API_BASE_URL
  storageKey: 'talent-agent-jwt';
}
```

### Iter-4 Dependency Additions

**Backend (requirements.txt):**
- celery>=5.3 — owner: scheduler-agent
- fakeredis>=2.20 — owner: tests-agent (dev only)

**Frontend (package.json devDependencies):**
- vitest>=1.0 — owner: tests-agent
