# Talent Agent — Cultivation Brief (Iteration 2)

> Input to `mycelium plant`. Canonical spec the cultivation seeds from. This brief **locks the current state of the project at HEAD `a898d3a`** for HYPHA contract-freeze and adds the iter-2 deltas that close the Phase 1 end-to-end loop.
>
> Read `CLAUDE.md` (project), `/Users/spy/.claude/CLAUDE.md` (global VibeSpace context), and the existing `hyphae/HYPHA-*.md` contracts (10 files, frozen in commit `9e9aea0`) before acting on anything below.
>
> **Supersedes iter-1 brief at `9e9aea0`.** No architectural redesign — iter-2 activates what iter-1 scaffolded.

---

## What changed since iter-1

Iter-1 (commits up to `9e9aea0`) froze the brief and 10 HYPHA contracts against repo state. The hand-built code at `a898d3a` (current HEAD) brings reality in line with the iter-1 brief:

- **AUTH** built: passwordless magic link + JWT (`HS256`, 7d), `/auth/request-link`, `/auth/verify`, `/auth/me`, `get_current_user` dependency.
- **ONBOARD** built: PyMuPDF resume extract + `/onboarding/resume`, `/onboarding/profile`, `/onboarding/status`.
- **DASH** scaffolded: React 19 + Vite 8 + Tailwind 4 Review Dashboard (10 pages, 4 components, `AuthContext`, `DashboardLayout`, `lib/api.js`).
- **INFRA** built: backend `Dockerfile`, frontend `Dockerfile` + `nginx.conf`, `docker-compose.yml`, `Makefile`, `start.sh`/`stop.sh`, `deploy/setup-aws.sh`, `deploy/deploy.sh`, ECS task definitions, `digital-dash-pipeline.yml`.
- **CI**: Digital Dash pipeline spec live; `auto-commit.sh` Digital Dash-aware.

**Iter-1 ⇒ Iter-2 framing.** Iter-1 was "scaffold the org." Iter-2 is **focused activation**: take the iter-1 acceptance criteria 1–8 and make them actually pass end-to-end on a real candidate (Sean Young) targeting real job postings on real ATS hosts.

---

## What we're building (iter-2 scope)

**Talent Agent**, end-to-end loop activated for one candidate. The loop:

1. Discovery finds **real jobs** crawled from **all public ATS sources** the system supports — Greenhouse public boards, Lever public boards, Workday tenant boards, Ashby boards — for SPY's seeded identity profile.
2. Application engine, on approval, tailors a real resume, researches the real company, finds a real contact, composes a real outreach email, and **submits a real form** to the live ATS.
3. Magic-link auth sends real emails via **Resend**.
4. Digital Dash deploys backend + frontend to **AWS ECS Fargate staging** and reaches `/health` green.
5. Every agent transition is visible on the dashboard via Redis pub/sub.

"Done" for iter-2 = a real job, a real submission, a real `SENT` row, all reviewed by SPY — and a staging deployment reachable on the web.

---

## Why

Phase 1 closes when the loop runs unattended on real targets. Iter-1 made the wiring. Iter-2 lights it up. This is also a continued **dogfood pass for the mycelium framework on a Python/FastAPI/Postgres workload** — prior `ddp` runs targeted Expo/Supabase, so the framework surfaces gaps on this stack.

---

## Team + governance

Unchanged from iter-1.

- **Operator:** SPY (Sean Young, Space Cowboy #9) — Founder & CEO, VibeSpace LLC. Build authority.
- **Stream tag:** `TA/` · **Branch:** `TA/<kebab-desc>` · **Commit subject:** `[TA] <imperative>` · **PR title:** `[TA] <what shipped>`
- **HYPHA gate:** non-negotiable per global guardrails. No code written against an unfrozen spec. This brief + the existing `hyphae/HYPHA-*.md` files (10 of them) freeze together. **Iter-2 does not rewrite HYPHA contracts — it amends them with delivery deltas where iter-1 marked items as "stubbed" or "deferred."**

---

## Stack (locked — unchanged)

Inherits iter-1 §Stack verbatim. Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 async · PostgreSQL 15 · Redis 7 · Anthropic SDK (`claude-sonnet-4-20250514`, `max_tokens=4096`) · Playwright async · httpx · BeautifulSoup · PyMuPDF · JWT `HS256` · React 19 · Vite 8 · Tailwind 4 · lucide-react · react-router-dom 7 · Docker · AWS ECS Fargate (us-east-1) · ECR · AWS Secrets Manager · Digital Dash pipeline · structlog · pytest + pytest-asyncio · Apache 2.0.

**New dependency (justified):** `resend` Python SDK for magic-link email delivery. Documented in the AUTH biome's `FRUIT_READY` line.

---

## Architecture

Unchanged from iter-1. See iter-1 brief §Architecture and the 10 HYPHA contracts. Iter-2 adds **no new components** — it activates existing ones.

---

## Iter-2 deltas (per HYPHA)

This section is the iter-2 work plan. Each delta is amended into the named HYPHA contract during freeze. No HYPHA is rewritten end-to-end.

### TA/AUTH — magic-link email send
- Replace the dev-mode `magic_link` return-in-body with a **Resend** API send when `DEBUG=false`.
- New env var: `RESEND_API_KEY` (from AWS Secrets Manager in prod).
- New env var: `MAGIC_LINK_FROM_EMAIL` (default `auth@vibespace.io`).
- Magic-link email template lives in `backend/api/auth_emails.py` (single file, no jinja yet).
- When `DEBUG=true`, both: log the link AND attempt to send (so dev still has a fast path).
- On Resend API failure: log error, fall back to dev-mode return (don't 500 the request).

### TA/DISCOVER — real crawler sources
- Replace `crawler_agent` stub with a **multi-source real crawler** covering:
  - **Greenhouse public boards** — `https://boards.greenhouse.io/{slug}.json` (JSON API, no auth)
  - **Lever public boards** — `https://api.lever.co/v0/postings/{slug}?mode=json`
  - **Ashby public boards** — `https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true`
  - **Workday tenant boards** — Playwright crawl of `https://{tenant}.wd*.myworkdayjobs.com/{board}` (rate-limited, since these don't expose a clean JSON API)
- Slug discovery: maintain a curated list in `backend/agents/discovery/sources.yaml` — seed with ~50 company slugs across the four sources. (Future iteration: auto-discovery from a roles signal.)
- Per-source `httpx` rate limit: 2 req/sec, 0.5–2.0s jitter, User-Agent `VibeSpaceTalentAgent/1.0`, respect `robots.txt`.
- Crawler emits `DiscoveredJob` rows with `source` ∈ {`greenhouse`, `lever`, `ashby`, `workday`}.
- `RelevanceScorer` consumes real rows unchanged.

### TA/APPLY — real auto_apply across four ATS hosts
- `AutoApplyAgent` already supports Greenhouse/Lever/Workday/Ashby per HYPHA-APPLICATION-ENGINE. Iter-2 makes the Playwright selectors **production-quality** for each:
  - Greenhouse: standard form fields + file upload for resume
  - Lever: similar, plus single-page application handling
  - Workday: multi-step wizard navigation, save-and-continue handling
  - Ashby: SPA with React-Hook-Form selectors
- **Submission is real.** No `--dry-run` flag in normal mode. Submission requires `application_pipeline.status = APPROVED` AND human approval timestamp present.
- CAPTCHA detection: if Playwright sees a `recaptcha` iframe or Cloudflare challenge, transition to `REQUIRES_MANUAL`, screenshot, notify dashboard. No CAPTCHA solving.
- Screenshots at every major step (`backend/agents/application/auto_apply_screens/<pipeline_id>/step-NN.png`).
- Per-host fixture YAML (`backend/agents/application/ats_selectors.yaml`) keyed by source + form variant; falls back to generic selectors.

### TA/DASH — wire frontend ↔ backend end-to-end
- `AuthContext`: actually call `POST /auth/request-link`, handle the `/auth/verify?token=…` redirect, store JWT in **localStorage** (per Open Question default), set Bearer header in `lib/api.js`.
- Onboarding wizard: actually POST to `/onboarding/resume` (multipart) and `/onboarding/profile`.
- Overview, Pipeline, ReviewQueue: actually consume `/api/v1/discovery/digest/{candidate_id}`, `/api/v1/application/pipelines`, `/api/v1/review/queue`.
- ReviewQueue detail panel: render the four artifact panes (parsed JD, tailored resume diff, company intel, outreach draft) + contact card. Approve/Reject buttons call `/review/{id}/approve` and `/review/{id}/reject`.
- Polling cadence: 5s on ReviewQueue and Pipeline pages; manual refresh elsewhere. (SSE/WebSocket upgrade stays a follow-up.)

### TA/OBS — observability activation
- Land the `structlog` config module: `backend/logging_config.py`. JSON output in prod (when `DEBUG=false`), pretty-printer in dev.
- PII redaction filter: redact `email`, `phone`, `legal_name` in any logged Claude prompt/response payload before emission.
- Redis pub/sub publisher singleton: `backend/events/publisher.py` with `publish(channel, payload)`. Used by Discovery, Application, AgentManager.
- Subscriber (server-side) for the future SSE bridge: skeleton only, not consumed by frontend yet.
- `/health` endpoint returns `{status, version, git_sha, redis: ok|down, db: ok|down}`.

### TA/INFRA — deploy to AWS staging
- Run `deploy/setup-aws.sh` once against the target AWS account (Open Question — see below). Idempotent.
- `deploy/deploy.sh staging backend a898d3a` succeeds end-to-end; same for `frontend`.
- ECS service health checks pass; ALB `/health` returns 200.
- Secrets in AWS Secrets Manager: `ANTHROPIC_API_KEY`, `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`, `RESEND_API_KEY`.
- Digital Dash pipeline runs lint → test → build → deploy-staging → health-check. Deploy-prod stays gated on manual approval — out of iter-2 scope.

### TA/SCHEMA — no migration changes
Schema is locked. If a delta accidentally requires a column add, that's a brief amendment, not a leaf-level change.

### TA/AGENTS, TA/API, TA/ONBOARD — no scope change
Already complete from iter-1's manual build. Cultivation verifies conformance to HYPHA contracts and patches any drift.

---

## Domain entities

Unchanged. Source of truth: `backend/migrations/000–003_*.sql` and `backend/models/`. Locked at HEAD `a898d3a`.

---

## Biome split

Unchanged from iter-1. Same 10 biomes, same `blocked_by` graph. See iter-1 brief §Biome split or `hyphae/HYPHA-*.md`. Iter-2's work is amended into existing biomes; no new biome added.

---

## Frozen contract surfaces

Per iter-1 brief §0–§12. Locked verbatim. Iter-2-specific amendments:

- **§7 (Auth + JWT)** — adds Resend integration. Magic-link email body: short template, plain text + minimal HTML, contains the click URL + 15-min expiry note.
- **§9 (Claude API)** — adds: every Claude call wrapped in `structlog.contextvars.bind_contextvars(agent=..., pipeline_id=...)` so logs carry agent context.
- **§10 (External scraping)** — extended to the four crawler sources with per-source rate limits as listed in TA/DISCOVER delta.
- **§12 (Pipeline result codes)** — staging deploy is now in scope; prod deploy gate stays manual.

---

## API surface

Unchanged. All under `/api/v1`. Iter-2 adds no new endpoints — it implements consumers of the ones iter-1 declared.

---

## Acceptance criteria (cultivation done)

The cultivation is "ready to harvest" when, on a clean checkout of HEAD post-cultivation, SPY can:

1. `make up` → backend healthy at `/health` (now returns `{status, version, git_sha, redis, db}`), Postgres + Redis containers up.
2. Open the dashboard, request a magic link → **a real email arrives in SPY's inbox via Resend**, click → land on Onboarding.
3. Upload SPY's resume PDF → see extracted text preview → fill profile → land on Overview.
4. Trigger Discovery for SPY's candidate → **real jobs from Greenhouse + Lever + Ashby + Workday** populate the digest, scored 6-dim.
5. Open ReviewQueue → see a pipeline at `AWAITING_REVIEW` with all four artifact panels populated and a contact card.
6. Approve → pipeline → `SUBMITTED` → **AutoApply submits the real form against a real public ATS posting** → status `SENT`. Screenshots saved.
7. `./deploy/deploy.sh staging backend a898d3a` succeeds; ALB `/health` returns 200; Digital Dash pipeline green through deploy-staging.
8. Every agent transition visible on the dashboard via Redis pub/sub (polled at 5s).

Code quality bar: `ruff check backend/` clean, `pytest tests/ -v` green (now including application-engine smoke tests), `npm run build` clean.

---

## Out of scope (iter-2)

Updated from iter-1. Removed: production magic-link email (now in scope), real ATS auto_apply (now in scope), real crawler sources (now in scope). Remaining non-goals:

- Multi-candidate concurrent processing (still single-candidate MVP)
- Agency dashboard / white-label / multi-tenant (still design-only via `candidate_id` FK)
- CAPTCHA solving (Playwright detects → `REQUIRES_MANUAL`)
- Stripe / PESO billing
- Mycelium `BaseAgent` NODE wrappers (still aspirational)
- Bloom identity-card integration (still reserved)
- Background `framework_watcher` / `pattern_extractor` agents (still empty scaffold)
- Push notifications (still in-app banners only)
- Mobile app (still web dashboard only)
- Production ECS deploy with manual approval (staging is in scope; prod gate stays manual)
- SSE/WebSocket realtime dashboard streaming (polling stays)
- A11y / i18n / mobile responsive beyond table breakpoints
- Automated crawler-source slug discovery (curated YAML in iter-2)
- ATS auth/login automation (still public-form-only; pre-authenticated session not yet supported)

---

## Constraints + guardrails

Inherited from iter-1 verbatim. No agent architecture changes. Apache 2.0 header on every new file. No `print()`, no `requests`, no bare `except:`. No hardcoded secrets. No `git` from leaves — `./auto-commit.sh` only. `git push --force` / `rm -rf` outside `/tmp` require explicit confirmation. Mycelium vocabulary precise. Multi-tenancy design-only.

**Iter-2-specific:**
- Real ATS submissions are real money to the candidate (real applications appear in real recruiters' inboxes). AutoApply blocks until human approval. No automated approval bypass exists, ever.
- Resend API key is a secret. AWS Secrets Manager only; never in `.env` committed; dev uses `.env.local` outside git.

---

## Open questions (iter-2 — resolved + remaining)

| Question | Iter-1 default | Iter-2 resolution |
|---|---|---|
| Production magic-link email provider | Leave TODO | **Resend** |
| Real ATS target for `auto_apply` | Dry-run | **All four public sources: Greenhouse, Lever, Ashby, Workday** |
| Crawler sources | Stub | **Greenhouse / Lever / Ashby JSON APIs + Workday Playwright crawl; slugs curated in `sources.yaml`** |
| Frontend JWT storage | localStorage | **localStorage (confirmed)** |
| AWS account ID + ECR push permissions | Block on first deploy | **Still open — bootstrap when SPY provides account; deploy step is leaf-level work and may sit in `PENDING_AWS` until then** |

The AWS account question is the only remaining unresolved input. Cultivation proceeds; the INFRA biome's `deploy-staging` deliverable can run `setup-aws.sh` in dry-run mode and emit a `HANDOFF.md` line documenting the gating credential.

---

## How to run

Single-call pipeline (this run):

```bash
cd /Users/spy/mfautomation/repos/creation-station/reverse-search
mycelium ddp \
  --brief ./brief.md \
  --stack nextjs-fastapi-supabase \
  --security startup \
  --concurrency 30 \
  --threshold 0.8
```

**Stack preset note.** `mycelium` v0.1.0 ships presets `nextjs-fastapi-supabase` and `expo-supabase`. There's no `fastapi-postgres` preset — falling back to `nextjs-fastapi-supabase` as the closest match (FastAPI half lines up; Supabase ≠ Postgres but the brief locks Postgres explicitly in §Stack, so leaves must read §Stack as canon, not the preset). To be documented in `HANDOFF.md` once cultivation writes one.

Pre-flight (run before the real `ddp`):

```bash
mycelium plant ./brief.md --stack nextjs-fastapi-supabase --security startup --dry-run
```

This prints the planner prompt without invoking the SDK — lets SPY (and me) verify the brief decomposes cleanly against the 10 existing HYPHAE before burning agent budget.

---

## References

- **Repo CLAUDE.md:** `/Users/spy/mfautomation/repos/creation-station/reverse-search/CLAUDE.md`
- **Global CLAUDE.md:** `/Users/spy/.claude/CLAUDE.md`
- **Iter-1 brief (superseded, kept in git):** commit `9e9aea0` — file `brief.md` at that commit
- **HYPHA contracts (10, frozen iter-1):** `./hyphae/HYPHA-*.md`
- **Mycelium framework:** `/Users/spy/mfautomation/repos/legendary-funicular/`
- **Mycelium orchestrator + 30/60/90:** `/Users/spy/mfautomation/mycelium-orchestrator/`
- **Resend docs:** https://resend.com/docs/api-reference/emails/send-email
- **Greenhouse public boards JSON:** https://developers.greenhouse.io/job-board.html
- **Lever public postings JSON:** https://github.com/lever/postings-api
- **Ashby posting API:** https://developers.ashbyhq.com/reference/posting-api-overview
- **Workday board structure (no public docs — Playwright-driven):** company-specific
- **Phase-1 build prompts:** `01-discovery-engine.md`, `02-application-engine.md`
- **Framework spec (deferred):** `03-vibespace-framework.md`
- **Digital Dash pipeline:** `./digital-dash-pipeline.yml`
