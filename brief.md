# Talent Agent — Cultivation Brief (Iteration 3)

> Input to `mycelium plant`. Canonical spec the cultivation seeds from. This brief **locks the current state of the project at HEAD `328420c`** (iter-3 freeze tree) and absorbs the new mycelium framework surface shipped in `legendary-funicular` PR #3 (dashboard + cache-network + theme.yaml + concurrency lessons).
>
> Read `CLAUDE.md` (project), `/Users/spy/.claude/CLAUDE.md` (global VibeSpace context), the existing `hyphae/HYPHA-*.md` contracts (11 files — 10 from iter-1, plus `HYPHA-DESIGN-CORE` frozen at `cccbef2`), and `legendary-funicular/HANDOFF.md` (the 2026-05-16 dashboard+cache entry) before acting on anything below.
>
> **Supersedes iter-2 brief at `a804ec1`.** iter-2's product scope did not ship — iter-3 carries it forward, folds in the new framework surface, and adds the DESIGN-CORE leaf.

---

## Stack-canon override (READ FIRST — supersedes preset)

This repo cultivates with `--stack nextjs-fastapi-supabase` because no `fastapi-postgres` preset exists yet in `legendary-funicular`. The preset's contract appendix (Section H, security rules) is **wrong for this stack** in three specific ways. When the preset and this brief conflict, **§Stack and this override block win — always.**

**Negated rules (do NOT enforce, do NOT generate code that satisfies them):**

- **H.1.3 (`NEXT_PUBLIC_` prefix enforcement) — NEGATED.** This repo's frontend is **React 19 + Vite 8**, not Next.js. Env vars use the **`VITE_*`** prefix per Vite's `import.meta.env` convention. Any leaf generating `NEXT_PUBLIC_*` references is wrong.
- **H.2.1 (httpOnly cookies, never localStorage) — NEGATED.** JWT storage is **localStorage** per iter-2's resolved open question. The `AuthContext` reads/writes `localStorage` directly and sets a `Bearer` header in `lib/api.js`. Do NOT migrate to httpOnly cookies. Do NOT add `Set-Cookie` headers to `backend/api/auth.py`.
- **H.3.1 (every Supabase table has `ENABLE ROW LEVEL SECURITY`) — NEGATED.** This repo uses **raw PostgreSQL 15 via SQLAlchemy 2.0 async + Alembic**. There is no Supabase, no `supabase-py`, no `@supabase/supabase-js`. Migrations are SQL files at `backend/migrations/000–003_*.sql`. RLS is a Supabase-specific construct that does not apply.

**Positive stack canon (this is the real stack — generate code for THIS):**

- **Frontend:** React 19 · Vite 8 · Tailwind 4 · lucide-react · react-router-dom 7. NOT Next.js. No App Router. No Server Components. No Server Actions. No Route Handlers. Pages live at `frontend/src/pages/*.jsx`, components at `frontend/src/components/*.jsx`.
- **Backend:** FastAPI · Python 3.12 · Pydantic v2 · SQLAlchemy 2.0 async · Alembic. NOT a Next.js API route runtime. Routes live at `backend/api/*.py` and mount under `/api/v1`.
- **Database:** PostgreSQL 15 raw, accessed via SQLAlchemy async engine in `backend/database.py`. NOT Supabase. No `supabase-py` import. No `from supabase import create_client`. No RLS policies.
- **Auth:** JWT `HS256`, 7d, stored in `localStorage`, sent as `Authorization: Bearer <token>`. Magic-link via Resend. NOT Supabase Auth. NOT NextAuth. NOT cookie-based sessions.
- **Storage:** Local FS during dev; S3 in prod (future). NOT Supabase Storage.
- **Env vars:** `VITE_*` for frontend (`import.meta.env.VITE_API_BASE_URL`), unprefixed for backend (loaded via `backend/config.py` Pydantic Settings from `.env`). NOT `NEXT_PUBLIC_*`. NOT `process.env` in client components.

**Run protocol:** cultivation runs with `--skip-audit` so the preset's freeze gate (RLS check, localStorage check) doesn't kill the freeze step. The override above is the canonical contract; the audit's absence is intentional, not an emergency bypass.

**For every leaf:** before generating any frontend or auth code, re-read this block. If your output references Next.js, Supabase client, RLS, httpOnly cookies, or `NEXT_PUBLIC_*`, it is wrong for this stack regardless of what the preset's contract appendix says.

---

## What changed since iter-2

Two streams of change since the iter-2 brief was written:

**Repo-side (Talent Agent):**
- `HYPHA-DESIGN-CORE` drafted and frozen (commit `cccbef2`). Top Shelf editorial variant locked. The design-language is now an upstream NUTRIENT alongside `HYPHA-SCHEMA-CORE`; every frontend HYPHA reads tokens from it.
- `vibespace-framework/brief.md` committed (`328420c`) on the `[VSF]` stream — sister cultivation that crystallizes reusable DNA from this repo. Sits alongside `[TA]`, does not block it.
- No iter-2 product code shipped yet. Crawler still stub, AutoApply still scaffolded, AUTH still dev-mode, OBS still partial, INFRA still un-deployed.

**Framework-side (legendary-funicular PR #3, 40 commits, +11,304 / -930):**
- **`mycelium dashboard {init,serve,render}`** — new operator surface. Three.js Bloch-sphere agents on a fibonacci globe, cache-relay inner shell, Star Wars HUD, ≥1.5s pulse discipline. Per-cultivation `theme.yaml` molds palette + brand + biome→identity-color map. `serve` re-reads `state.json` + `theme.yaml` every request; SSE event stream at `/events/stream`.
- **`cli/src/lib/cache-network/`** — LRU `CacheStore` wraps SDK calls at `cultivate.ts:480`. Default ON. `--no-cache` for bypass. Emits `cache.hit` / `cache.miss` / `cache.evict` / `cache.pulse` (1.4s aggregation). `state.cache` additive block on `sporenet/state.json`.
- **Micro-agent fan-out** — deterministic 2-4 micros per leaf via xorshift seeded from sha256(leafId). 70/30 cheap/full split (50/50 if critical severity).
- **Concurrency lesson learned the hard way.** First framework-internal cultivation at `-c 30`: 0/43 leaves, all rate-limited, $17 burned, zero output. Second at `-c 4`: 43/43 FRUIT_READY in 17.6 min. **iter-3 prescribes `-c 4` as the default.** Reserved for the framework's own token-bucket warmup pattern; can scale back up when the upstream cache hit-rate is high.

iter-3 framing: **iter-2 product scope + DESIGN-CORE freeze + per-cultivation theme.yaml + observe via `mycelium dashboard serve`.** No architectural redesign.

---

## What we're building (iter-3 scope)

**Talent Agent**, end-to-end loop activated for one candidate, with the new operator surface live. The loop (unchanged from iter-2):

1. Discovery finds **real jobs** from Greenhouse / Lever / Ashby / Workday public boards for SPY's seeded identity.
2. Application engine, on approval, tailors a real resume, researches the real company, finds a real contact, composes a real outreach email, and **submits a real form** to the live ATS.
3. Magic-link auth sends real emails via **Resend**.
4. Digital Dash deploys backend + frontend to **AWS ECS Fargate staging** and reaches `/health` green.
5. Every agent transition is visible on the dashboard via Redis pub/sub.
6. **NEW iter-3:** SPY can run `mycelium dashboard serve` against this repo's `sporenet/state.json` and watch the Three.js console live while cultivation runs.

"Done" for iter-3 = the iter-2 acceptance criteria 1–8 PLUS a `theme.yaml` that paints the dashboard in Top Shelf editorial (gold-on-black), PLUS a green Digital Dash pipeline to staging.

---

## Why

iter-2's acceptance criteria didn't ship because the cultivation pre-conditions weren't right (untracked design contract, no theme.yaml, no operator visibility into a long-running cultivation). iter-3 fixes the pre-conditions and re-runs the loop. This is also the first **non-framework-internal cultivation** that exercises the new dashboard + cache-network surface against a real Python/FastAPI/Postgres workload.

---

## Team + governance

Unchanged from iter-2.

- **Operator:** SPY (Sean Young, Space Cowboy #9) — Founder & CEO, VibeSpace LLC. Build authority.
- **Stream tag:** `TA/` · **Branch:** `TA/<kebab-desc>` · **Commit subject:** `[TA] <imperative>` · **PR title:** `[TA] <what shipped>`
- **Sister stream:** `[VSF]` (VibeSpace Framework) — runs independently in `vibespace-framework/`, does not block `[TA]`.
- **HYPHA gate:** non-negotiable. iter-3 does not rewrite the 10 iter-1 HYPHA contracts — it amends them with delivery deltas and adds `HYPHA-DESIGN-CORE` (frozen `cccbef2`) as the 11th. A new `theme.yaml` companion ships at repo root.

---

## Stack (locked — unchanged)

Inherits iter-2 §Stack verbatim. Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 async · PostgreSQL 15 · Redis 7 · Anthropic SDK (`claude-sonnet-4-20250514`, `max_tokens=4096`) · Playwright async · httpx · BeautifulSoup · PyMuPDF · `resend` Python SDK · JWT `HS256` · React 19 · Vite 8 · Tailwind 4 · lucide-react · react-router-dom 7 · Docker · AWS ECS Fargate (us-east-1) · ECR · AWS Secrets Manager · Digital Dash pipeline · structlog · pytest + pytest-asyncio · Apache 2.0.

**Type stack (locked by HYPHA-DESIGN-CORE):** Playfair Display (serif) · DM Sans (sans) · DM Mono (mono). Icon system: lucide-react only.

---

## Architecture

Unchanged from iter-2. iter-3 adds **no new product components** — it activates iter-2's pending deltas and adds the dashboard observation surface (which is external to the app, runs via `mycelium dashboard serve` against `sporenet/state.json`).

---

## iter-3 deltas (per HYPHA)

Each delta is amended into the named HYPHA contract during freeze. No HYPHA is rewritten end-to-end.

### TA/AUTH — magic-link email send via Resend
*(unchanged from iter-2 — carry forward verbatim)*
- Replace dev-mode `magic_link` return-in-body with **Resend** API send when `DEBUG=false`.
- New env vars: `RESEND_API_KEY` (AWS Secrets Manager in prod), `MAGIC_LINK_FROM_EMAIL` (default `auth@vibespace.io`).
- Template lives in `backend/api/auth_emails.py` (single file, no jinja yet).
- When `DEBUG=true`, log AND attempt send (dev still has a fast path).
- On Resend API failure: log error, fall back to dev-mode return (don't 500).

### TA/DISCOVER — real crawler sources
*(unchanged from iter-2 — carry forward verbatim)*
- Replace `crawler_agent` stub with multi-source real crawler:
  - **Greenhouse**: `https://boards.greenhouse.io/{slug}.json`
  - **Lever**: `https://api.lever.co/v0/postings/{slug}?mode=json`
  - **Ashby**: `https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true`
  - **Workday**: Playwright crawl of `https://{tenant}.wd*.myworkdayjobs.com/{board}`
- Slug discovery: `backend/agents/discovery/sources.yaml`, seed ~50 slugs across four sources.
- Per-source `httpx` rate limit: 2 req/sec, 0.5–2.0s jitter, UA `VibeSpaceTalentAgent/1.0`, respect `robots.txt`.
- `DiscoveredJob.source` ∈ {`greenhouse`, `lever`, `ashby`, `workday`}.

### TA/APPLY — real auto_apply across four ATS hosts
*(unchanged from iter-2 — carry forward verbatim)*
- Production Playwright selectors for Greenhouse / Lever / Workday / Ashby.
- Real submission. No `--dry-run` in normal mode. Requires `application_pipeline.status = APPROVED` + human approval timestamp.
- CAPTCHA detection → `REQUIRES_MANUAL` + screenshot + dashboard notify. No solving.
- Screenshots at every major step (`backend/agents/application/auto_apply_screens/<pipeline_id>/step-NN.png`).
- Per-host fixture YAML (`backend/agents/application/ats_selectors.yaml`) keyed by source + form variant.

### TA/DASH — wire frontend ↔ backend end-to-end
*(unchanged from iter-2 — carry forward verbatim)*
- `AuthContext`: call `POST /auth/request-link`, handle `/auth/verify?token=…`, store JWT in **localStorage**, set Bearer in `lib/api.js`.
- Onboarding wizard: POST to `/onboarding/resume` (multipart) and `/onboarding/profile`.
- Overview / Pipeline / ReviewQueue: consume real `/api/v1/...` endpoints.
- ReviewQueue detail panel: four artifact panes (parsed JD, tailored resume diff, company intel, outreach draft) + contact card.
- Polling: 5s on ReviewQueue and Pipeline; manual elsewhere.

### TA/OBS — observability activation
*(unchanged from iter-2 — carry forward verbatim)*
- `backend/logging_config.py`: JSON in prod, pretty-printer in dev.
- PII redaction filter: redact `email`, `phone`, `legal_name` in Claude prompt/response logs before emission.
- Redis pub/sub publisher singleton: `backend/events/publisher.py`. Used by Discovery, Application, AgentManager.
- Subscriber skeleton for future SSE bridge; not consumed by frontend yet.
- `/health` returns `{status, version, git_sha, redis: ok|down, db: ok|down}`.

### TA/INFRA — deploy to AWS staging
*(unchanged from iter-2 — carry forward verbatim)*
- `deploy/setup-aws.sh` once against target account. Idempotent.
- `deploy/deploy.sh staging backend <sha>` succeeds; same for `frontend`.
- ECS health checks pass; ALB `/health` returns 200.
- Secrets in AWS Secrets Manager: `ANTHROPIC_API_KEY`, `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`, `RESEND_API_KEY`.
- Digital Dash pipeline green through lint → test → build → deploy-staging → health-check. Prod gate stays manual.

### TA/DESIGN — design-language token rollout (NEW, iter-3 only)
- `HYPHA-DESIGN-CORE` is frozen at `cccbef2`. iter-3 cultivation verifies conformance:
  - `frontend/src/index.css` declares all tokens (palette, type, status colors, transitions, scrollbar, selection).
  - Typography utility classes (`.t-serif`, `.t-serif-bold`, `.t-label`, `.t-label-gold`, `.t-body`) present.
  - `StatusBadge.jsx` is the canonical status→color map.
  - `StatCard.jsx` is the primitive card treatment.
  - No hex literals in JSX. No icon-library mixing (lucide-react only).
- `frontend/src/design/CHEATSHEET.md` exists with: variant intent, signature flourishes, forbidden patterns, motion language, icon system. Surface HYPHAs reading from it.
- **Companion `theme.yaml` ships at repo root** (see TA/CULTIVATION below).

### TA/CULTIVATION — per-cultivation theme.yaml (NEW, iter-3 only)
- New file at repo root: `./theme.yaml`. Schema per `legendary-funicular/NUTRIENTS.md#1-theme-schema-per-cultivation-themeyaml`.
- Encodes the same design tokens as `HYPHA-DESIGN-CORE` so `mycelium dashboard serve` paints the operator console in Top Shelf editorial.
- Required keys:
  - `brand`: `{ name: "Talent Agent", seal: "TA", tagline: "The Dot Connects." }`
  - `palette`: gold-on-black (mirrors `frontend/src/index.css` custom properties — single source of truth, design-core wins on conflict)
  - `pulse_rate_ms`: 1800 (≥1.5s discipline)
  - `biome_identity_color`: maps each of the 11 HYPHA biome IDs to the design-core status palette
- DESIGN-CORE owns the canonical token values. `theme.yaml` references them. If a value drifts, design-core is canon and theme.yaml is patched, never the reverse.

### TA/SCHEMA, TA/AGENTS, TA/API, TA/ONBOARD — no scope change
Schema locked. Agent code from iter-1 unchanged in shape. API surface unchanged in shape. Onboarding complete.

---

## Domain entities

Unchanged. Source of truth: `backend/migrations/000–003_*.sql` and `backend/models/`. Locked at HEAD `328420c`.

---

## Biome split

Inherits iter-2's 10 biomes plus **`TA/DESIGN`** as the 11th. New `blocked_by` edges:

- `TA/DASH` now depends on `TA/DESIGN` (frontend can't ship without design tokens).
- `TA/DESIGN` has no upstream — it's a NUTRIENT producer like `TA/SCHEMA`.

`TA/CULTIVATION` is **not a biome** — it's a leaf-level artifact (single file `theme.yaml`) owned jointly by `TA/DESIGN` (token source) and the cultivation runner.

---

## Frozen contract surfaces

Per iter-2 brief §0–§12. Locked verbatim. iter-3-specific amendments:

- **§NEW (DESIGN-CORE)** — added. Token vocabulary, primitive components, icon and font system. See `hyphae/HYPHA-DESIGN-CORE.md`.
- **§7 (Auth + JWT)** — unchanged from iter-2 (Resend integration).
- **§9 (Claude API)** — unchanged from iter-2 (structlog contextvars binding).
- **§10 (External scraping)** — unchanged from iter-2 (four crawler sources, per-source rate limits).
- **§12 (Pipeline result codes)** — staging deploy in scope; prod gate manual.

---

## API surface

Unchanged. All under `/api/v1`. iter-3 adds no new endpoints.

---

## Acceptance criteria (cultivation done)

The cultivation is "ready to harvest" when, on a clean checkout of HEAD post-cultivation, SPY can:

1. `make up` → backend healthy at `/health` (returns `{status, version, git_sha, redis, db}`), Postgres + Redis containers up.
2. Open the dashboard, request a magic link → **real email arrives via Resend**, click → land on Onboarding.
3. Upload SPY's resume PDF → see extracted text preview → fill profile → land on Overview.
4. Trigger Discovery for SPY's candidate → **real jobs from Greenhouse + Lever + Ashby + Workday** populate the digest, scored 6-dim.
5. Open ReviewQueue → pipeline at `AWAITING_REVIEW` with all four artifact panels populated and contact card present.
6. Approve → pipeline → `SUBMITTED` → **AutoApply submits the real form against a real public ATS posting** → status `SENT`. Screenshots saved.
7. `./deploy/deploy.sh staging backend <sha>` succeeds; ALB `/health` returns 200; Digital Dash pipeline green through deploy-staging.
8. Every agent transition visible on the dashboard via Redis pub/sub (polled at 5s).
9. **NEW iter-3:** `mycelium dashboard serve --dir .` opens the Three.js operator console painted in Top Shelf editorial (gold-on-black, Playfair brand seal, ≥1.5s pulse). Cache relay shell visible. Cultivation state ticks live.
10. **NEW iter-3:** `frontend/src/index.css` declares all DESIGN-CORE tokens; `grep -r '#[0-9a-fA-F]\{3,8\}' frontend/src --include='*.jsx'` returns zero hex-literal hits in JSX (tokens-only).

Code quality bar: `ruff check backend/` clean · `pytest tests/ -v` green (including application-engine smoke tests) · `npm run build` clean · `npm run lint` clean.

---

## Out of scope (iter-3)

Inherits iter-2's non-goals. Unchanged:

- Multi-candidate concurrent processing (single-candidate MVP)
- Agency dashboard / white-label / multi-tenant (design-only via `candidate_id` FK)
- CAPTCHA solving (Playwright detects → `REQUIRES_MANUAL`)
- Stripe / PESO billing
- Mycelium `BaseAgent` NODE wrappers
- Bloom identity-card integration
- `framework_watcher` / `pattern_extractor` agents (still empty scaffold)
- Push notifications (in-app banners only)
- Mobile app (web dashboard only)
- Production ECS deploy (staging in scope; prod manual)
- SSE/WebSocket realtime app dashboard streaming (polling stays — separate from `mycelium dashboard`'s SSE which is operator-facing only)
- A11y / i18n / mobile responsive beyond table breakpoints
- Automated crawler-source slug discovery (curated YAML)
- ATS auth/login automation (public-form-only)
- Cellar / back-of-house design variants (DESIGN-CORE locks Top Shelf only)

---

## Constraints + guardrails

Inherited from iter-2 verbatim. Apache 2.0 header on every new file. No `print()`, no `requests`, no bare `except:`. No hardcoded secrets. No `git` from leaves — `./auto-commit.sh` only. `git push --force` / `rm -rf` outside `/tmp` require explicit confirmation. Mycelium vocabulary precise. Multi-tenancy design-only.

**iter-3-specific:**
- Real ATS submissions are real money. AutoApply blocks until human approval. No automated-approval bypass exists.
- Resend API key is a secret. AWS Secrets Manager only; never in committed `.env`; dev uses `.env.local` outside git.
- **No hex literals in JSX.** Tokens via CSS custom properties only. Enforced as acceptance criterion #10.
- **Icon system is lucide-react only.** Mixing icon libraries fails design-core conformance.

---

## Open questions (iter-3 — resolved + remaining)

| Question | iter-2 resolution | iter-3 status |
|---|---|---|
| Production magic-link email provider | Resend | unchanged |
| Real ATS targets for auto_apply | Greenhouse / Lever / Ashby / Workday | unchanged |
| Crawler sources | Same four | unchanged |
| Frontend JWT storage | localStorage | unchanged |
| AWS account ID + ECR push permissions | Open | **Still open** — bootstrap when SPY provides account; INFRA deploy may sit in `PENDING_AWS`. |
| `theme.yaml` schema for dashboard | (not in iter-2) | **Resolved** — per `legendary-funicular/NUTRIENTS.md#1`. DESIGN-CORE is canon; theme.yaml mirrors. |
| Cultivation concurrency | `-c 30` | **Resolved** — `-c 4` per framework-internal cultivation evidence (`-c 30` rate-limited 0/43; `-c 4` shipped 43/43). |

The AWS account question remains the only unresolved input. Cultivation proceeds; INFRA biome's `deploy-staging` deliverable runs `setup-aws.sh` in dry-run mode and emits a `HANDOFF.md` line documenting the gating credential.

---

## Known framework gotchas (don't waste leaf cycles on these)

Inherited from `legendary-funicular/HANDOFF.md` (2026-05-16). iter-3 cultivation leaves should NOT debug these — they're framework bugs being tracked separately:

1. **`mycelium harvest` threshold mis-reports 0%.** Looks for `feat/<biome-id>` branches per `mycelium.yaml agents[].branch`, but cultivate emits `feat/<leaf-id>` branches. Threshold check reports 0% even when work is fully landed via CommitQueue. Workaround: trust `state.json` leaf statuses, not the harvest percentage.
2. **`mycelium contracts freeze` requires `--stack` flag.** Talent Agent has a stack (`nextjs-fastapi-supabase` fallback — see "How to run"), so this is fine. Just don't omit the flag.
3. **Artifact-path mismatches.** Some leaves emit files but declare different artifact paths; framework's `git add --all -- <declared-paths>` may not match. Files land; commit attribution may split. Worth a HANDOFF line if observed, not a blocker.
4. **Some leaves report "0 files committed" despite files on disk.** Possible sibling-overlap auto-commit. Verify by `git log -- <path>` rather than trusting the leaf status banner.

---

## How to run

**Pre-flight (always):**

```bash
cd /Users/spy/mfautomation/repos/creation-station/reverse-search
git status                                            # MUST be clean — iter-3 freeze captures the tree
mycelium plant ./brief.md \
  --stack nextjs-fastapi-supabase \
  --security startup \
  --dry-run
```

This prints the planner prompt without invoking the SDK — verifies the brief decomposes cleanly against the 11 existing HYPHAE.

**Stack preset note (unchanged from iter-2).** `mycelium` ships presets `nextjs-fastapi-supabase` and `expo-supabase`. There's no `fastapi-postgres` preset — falling back to `nextjs-fastapi-supabase` as closest match (FastAPI half lines up; Supabase ≠ Postgres but the brief locks Postgres explicitly in §Stack, so leaves must read §Stack as canon, not the preset).

**Single-call pipeline (this run):**

```bash
mycelium ddp \
  --brief ./brief.md \
  --stack nextjs-fastapi-supabase \
  --security startup \
  --concurrency 4 \
  --threshold 0.8 \
  --skip-audit
```

**`--skip-audit` is REQUIRED, not an emergency bypass.** The `nextjs-fastapi-supabase` preset's Section H rules conflict with this repo's real stack (raw Postgres + Vite + localStorage JWT). See the "Stack-canon override" block at the top of this brief for the negated rules and the positive canon. The override block IS the contract; the preset's audit appendix is wrong for this stack. Future iteration: land a `fastapi-postgres` preset in legendary-funicular, then drop `--skip-audit`.

**Concurrency = 4, NOT 30.** Per `legendary-funicular/HANDOFF.md` 2026-05-16: `-c 30` hit Anthropic rate-limits on every leaf, $17 burned, zero output. `-c 4` shipped 43/43 in 17.6 min by letting the token bucket recover between batches and warming the prompt cache. Cache-network (default ON) further reduces token spend on retries.

**Operator visibility (NEW, iter-3):**

In a second terminal, while `ddp` runs:

```bash
mycelium dashboard serve --dir . --port 3334
```

Opens the Three.js operator console painted from `./theme.yaml`. Watch leaves germinate → grow → flow → fruit live. Cache hits show as cyan-teal pulses on the inner relay shell. SSE event stream at `/events/stream` if you want to tail events from CLI.

**Emergency cache bypass** (use only if you suspect a stale cache contaminating output):

```bash
mycelium cultivate --no-cache ...
```

Default OFF (i.e. cache ON) is correct for nearly all runs.

---

## References

- **Repo CLAUDE.md:** `/Users/spy/mfautomation/repos/creation-station/reverse-search/CLAUDE.md`
- **Global CLAUDE.md:** `/Users/spy/.claude/CLAUDE.md`
- **iter-2 brief (superseded, kept in git):** commit `a804ec1` — file `brief.md` at that commit
- **HYPHA contracts (11 frozen):** `./hyphae/HYPHA-*.md` — 10 from iter-1 + `HYPHA-DESIGN-CORE` (`cccbef2`)
- **Mycelium framework:** `/Users/spy/mfautomation/repos/legendary-funicular/`
- **Framework PR #3 (dashboard + cache-net):** https://github.com/spy-sauce/legendary-funicular/pull/3
- **Framework HANDOFF:** `/Users/spy/mfautomation/repos/legendary-funicular/HANDOFF.md` — read the 2026-05-16 entry
- **Framework NUTRIENTS (theme.yaml schema):** `legendary-funicular/NUTRIENTS.md#1-theme-schema-per-cultivation-themeyaml`
- **VibeSpace Framework sister brief:** `./vibespace-framework/brief.md` — `[VSF]` stream, runs independently
- **Resend docs:** https://resend.com/docs/api-reference/emails/send-email
- **Greenhouse public boards JSON:** https://developers.greenhouse.io/job-board.html
- **Lever public postings JSON:** https://github.com/lever/postings-api
- **Ashby posting API:** https://developers.ashbyhq.com/reference/posting-api-overview
- **Workday board structure:** company-specific, Playwright-driven, no public docs
- **Phase-1 build prompts:** `01-discovery-engine.md`, `02-application-engine.md`
- **Framework spec (deferred):** `03-vibespace-framework.md`
- **Digital Dash pipeline:** `./digital-dash-pipeline.yml`
