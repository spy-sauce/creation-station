# VibeSpace Framework — Cultivation Brief (iter-1)

> Input to `mycelium plant`. Canonical spec the cultivation seeds from. This brief **locks the current state of the project at HEAD `a804ec1`** for HYPHA contract-freeze on the framework cultivation.
>
> Read `CLAUDE.md` (project root), `/Users/spy/.claude/CLAUDE.md` (global VibeSpace context), `../03-vibespace-framework.md` (original framework prompt — source intent), and the existing `../hyphae/HYPHA-*.md` contracts (10 frozen TA contracts — pattern reference) before acting on anything below.
>
> **New stream.** Tag `[VSF]` (VibeSpace Framework). Sits alongside `[TA]` cultivation in this repo; does not block it.

---

## What we're building

The **VibeSpace Product Framework** — the reusable DNA every future VibeSpace product (BLM, VC, DD, BD, TSJ, CS, AN) scaffolds from. Lives at `./vibespace-framework/` in this repo (temporary home; will graduate to its own repo once stable).

The framework is **extracted from real built code in this repo** (Talent Agent at HEAD `a804ec1`) plus the Digital Dash pipeline spec (`./digital-dash-pipeline.yml`). Not designed from scratch — *crystallized from working production code*.

Three deliverables:

1. **`patterns/`** — six pattern docs codifying architectural decisions actually present in Talent Agent (FastAPI structure, agent lifecycle, async/SQLAlchemy, Claude API integration, testing). Each pattern cites file:line evidence from the TA codebase.
2. **`templates/`** — copy-pasteable scaffold files (`{{PRODUCT_NAME}}` placeholders) for `backend/`, `migrations/`, `docker/`, `ci/`, `tests/`. New products start from these.
3. **`bin/vibespace-init`** — CLI that takes `(product_name, description, stream_tag)`, copies templates with placeholder substitution, runs `git init`, prints the `NEW_PRODUCT.md` checklist.

Plus the connective tissue: `CLAUDE.md` (already stubbed — refine), `CONVENTIONS.md`, `NEW_PRODUCT.md`.

**Not in this iter:** `agents/framework_watcher.py` and `agents/pattern_extractor.py` — the autonomous maintenance agents. Those land in iter-2 once the manual framework is stable enough to have something worth watching.

---

## Why

Three products are queued (BLM next, then VC). Each one currently starts from a blank `mkdir` and recreates the FastAPI/SQLAlchemy/async/Claude wiring by hand. Talent Agent is the third time this scaffolding has been hand-built. **Third time = framework time.**

Secondary: the framework is the spec that `vibespace-init` reads, and `vibespace-init` is what a future Mycelium *fruiting body* invokes when SPY says "start a new product." No framework = no autonomous product instantiation.

Tertiary: this is a continued **dogfood pass for Mycelium on a docs+templates+CLI workload** — prior `ddp` runs targeted full-stack Python/TS apps. The framework cultivation surfaces gaps in how Mycelium handles non-application artifacts (markdown, jinja-templated scaffolds, shell tooling).

---

## Team + governance

- **Operator:** SPY (Sean Young, Space Cowboy #9) — Founder & CEO, VibeSpace LLC. Build authority.
- **Stream tag:** `VSF/` · **Branch:** `VSF/<kebab-desc>` · **Commit subject:** `[VSF] <imperative>` · **PR title:** `[VSF] <what shipped>`
- **HYPHA gate:** non-negotiable. No code/template/doc written against an unfrozen HYPHA spec. This brief + the new `hyphae/HYPHA-FRAMEWORK-*.md` files (six, see Biome split) freeze together before any leaf-level work begins.
- **Source-of-truth for extraction:** the TA codebase at HEAD `a804ec1` is the canonical reference. If a pattern claim and the TA code disagree, **the code wins**; patch the pattern doc, do not retrofit the code.

---

## Stack (locked)

The framework itself ships no runtime — it's docs, templates, and a Python CLI. Stack constraints apply to what the framework *prescribes* for downstream products:

- Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 async · PostgreSQL 15 · Redis 7
- Anthropic SDK (`claude-sonnet-4-20250514`, `max_tokens=4096`)
- Playwright async (where web automation applies) · httpx · BeautifulSoup
- Alembic migrations · structlog · pytest + pytest-asyncio
- Docker · Docker Compose (local) · AWS ECS Fargate (prod) · Digital Dash pipeline
- Apache 2.0 license header on every prescribed file

**Framework tooling stack:**
- `bin/vibespace-init` written in **Python 3.12** (no Node dep; `click` for CLI, `jinja2` for templating, `pathspec` for file copy filters)
- Pattern docs in **GitHub-flavored Markdown** with file:line citations into TA
- Templates use **`{{MUSTACHE_PLACEHOLDERS}}`** (jinja2-compatible, human-readable in raw form)

---

## Architecture

```
vibespace-framework/
├── CLAUDE.md                    ← maintenance-agent prompt (exists, refine)
├── CONVENTIONS.md               ← canonical conventions (NEW)
├── NEW_PRODUCT.md               ← spinup checklist (NEW)
├── brief.md                     ← THIS FILE
├── patterns/                    ← six pattern docs (NEW)
│   ├── api-structure.md
│   ├── agent-structure.md
│   ├── database-patterns.md
│   ├── async-patterns.md
│   ├── ai-integration.md
│   └── testing-patterns.md
├── templates/                   ← copy-pasteable scaffolds (NEW)
│   ├── backend/
│   │   ├── main.py.j2
│   │   ├── config.py.j2
│   │   ├── database.py.j2
│   │   ├── base_model.py.j2
│   │   ├── base_agent.py.j2
│   │   ├── base_router.py.j2
│   │   └── logging_config.py.j2
│   ├── migrations/
│   │   └── 000_init.sql.j2
│   ├── docker/
│   │   ├── Dockerfile.j2
│   │   ├── docker-compose.yml.j2
│   │   └── .dockerignore
│   ├── ci/
│   │   ├── digital-dash-pipeline.yml.j2
│   │   └── .env.example.j2
│   └── tests/
│       ├── conftest.py.j2
│       └── test_health.py.j2
└── bin/
    └── vibespace-init           ← Python CLI entry-point (NEW)
```

Pattern doc anatomy (each `patterns/*.md`):

1. **Pattern name** + one-line intent
2. **Why** (the problem it solves)
3. **Reference implementation** (citations: `backend/api/auth.py:42-89`)
4. **The pattern** (the abstracted shape, with code snippets)
5. **When to use / when not to**
6. **Anti-patterns** (what the framework explicitly rejects)
7. **Open questions** (places the pattern hasn't converged)

---

## Biome split

Six biomes. `blocked_by` edges shown.

| Biome | HYPHA file | Owns | `blocked_by` |
|---|---|---|---|
| `VSF/PATTERNS` | `HYPHA-FRAMEWORK-PATTERNS.md` | All six `patterns/*.md` docs | — |
| `VSF/TEMPLATES` | `HYPHA-FRAMEWORK-TEMPLATES.md` | All `templates/**/*.j2` files | `VSF/PATTERNS` (patterns define what templates emit) |
| `VSF/CLI` | `HYPHA-FRAMEWORK-CLI.md` | `bin/vibespace-init` + tests | `VSF/TEMPLATES` (CLI consumes templates) |
| `VSF/CONVENTIONS` | `HYPHA-FRAMEWORK-CONVENTIONS.md` | `CONVENTIONS.md` + `NEW_PRODUCT.md` | — |
| `VSF/AGENT-PROMPT` | `HYPHA-FRAMEWORK-AGENT-PROMPT.md` | `vibespace-framework/CLAUDE.md` refinement | `VSF/PATTERNS`, `VSF/CONVENTIONS` |
| `VSF/ACCEPTANCE` | `HYPHA-FRAMEWORK-ACCEPTANCE.md` | End-to-end smoke test: scaffold a throwaway product, build it, run its test suite | `VSF/CLI`, `VSF/TEMPLATES` |

The acceptance biome is the integration test — it proves the framework actually works by *using* it.

---

## Frozen contract surfaces

### §1 — Pattern doc contract

Every `patterns/*.md` MUST contain the seven sections listed in §Architecture. Citations MUST point at a real file:line in the TA codebase at HEAD `a804ec1` (or this brief's HEAD if cultivation produces later commits — pin to the cultivation start SHA in each doc's footer).

### §2 — Template placeholder contract

Templates use jinja2 syntax. Reserved placeholders:

| Placeholder | Meaning | Example |
|---|---|---|
| `{{ product_name }}` | snake_case product slug | `talent_agent` |
| `{{ product_name_kebab }}` | kebab-case slug | `talent-agent` |
| `{{ product_name_pascal }}` | PascalCase class prefix | `TalentAgent` |
| `{{ product_description }}` | one-line description | `"The AI-powered personal talent agent"` |
| `{{ stream_tag }}` | global stream taxonomy tag | `TA` |
| `{{ year }}` | current year (for license header) | `2026` |

Any other placeholder is a leaf-level error — cultivation must catch it before commit.

### §3 — CLI contract

```
vibespace-init <product_name> "<description>" --tag <STREAM_TAG> [--dir <output_dir>]
```

- Exit 0: scaffold complete, `git init` ran, initial commit `[<STREAM_TAG>] scaffold from vibespace-framework@<sha>` made.
- Exit 1: placeholder unresolved, template missing, or output dir already non-empty.
- Exit 2: `--tag` not in the global stream taxonomy (`/Users/spy/.claude/CLAUDE.md` §Stream taxonomy).
- `--dry-run`: prints the file list it would write, makes no changes.
- `--force`: overrides non-empty dir check (requires confirm prompt unless `--yes`).

### §4 — License header contract

Every scaffolded `.py` / `.ts` / `.tsx` / `.sql` file starts with the Apache 2.0 header, year templated. Templates ship with the header pre-filled; the framework rejects any template that omits it.

### §5 — Mycelium-aware contract

Every template emits files compatible with the **HYPHA gate** workflow:
- No file is generated outside a `hyphae/` contract surface unless flagged `# scaffold-only` (init layer)
- The scaffolded project's `CLAUDE.md` includes the "HYPHA before execution" guardrail verbatim
- The scaffolded `Makefile` exposes `make plant` and `make ddp` targets that pre-flight `mycelium` against the new project's brief

### §6 — Scaffold smoke test contract

The acceptance biome MUST scaffold a throwaway product called `proof-of-life` in `/tmp/`, run its full test suite green (`make test` → 0 failures), and tear down. CI runs this on every framework PR.

---

## Acceptance criteria (cultivation done)

On a clean checkout of HEAD post-cultivation, SPY can:

1. `cat vibespace-framework/patterns/*.md` → six pattern docs, each with the seven-section anatomy, citing real TA file:lines, all citations resolve.
2. `ls vibespace-framework/templates/**/*.j2` → every template listed in §Architecture exists, every one renders cleanly with the canonical placeholder set, every rendered output passes `ruff check` (Python) / `prettier --check` (yaml/json) / `shellcheck` (shell).
3. `vibespace-init proof-of-life "throwaway smoke test" --tag MYC --dir /tmp/proof-of-life` → scaffolds, `git init`s, makes initial commit, prints checklist. Exit 0.
4. `cd /tmp/proof-of-life && make up && make test` → all health checks pass, test suite green.
5. `cat vibespace-framework/CONVENTIONS.md` → covers file naming, dir structure, commit format, branch naming, PR conventions, versioning, env naming, secret mgmt, logging, error codes. No `TODO` lines.
6. `cat vibespace-framework/NEW_PRODUCT.md` → step-by-step checklist, every step actionable, references `vibespace-init` correctly.
7. `cat vibespace-framework/CLAUDE.md` → refined from current stub: includes the autonomy boundaries, the trigger conditions, the commit format, and a section on **how the agent reads the patterns/ docs before proposing updates**.
8. Digital Dash pipeline runs lint → test → build → scaffold-smoke (the §6 contract) green on every PR.

Code quality bar: `ruff check vibespace-framework/bin/` clean, `pytest vibespace-framework/tests/` green, every template renders without warnings.

---

## Out of scope (iter-1)

- `agents/framework_watcher.py` (autonomous weekly pattern updates) — iter-2
- `agents/pattern_extractor.py` (PR-merge-triggered pattern proposal) — iter-2
- Multi-version framework registry (the framework has a version but no upgrade path for existing products yet) — iter-3
- Pattern extraction from Digital Dash, BLM, VC, etc. — only TA at HEAD `a804ec1` is the extraction source for iter-1
- Frontend scaffolding templates (React/Vite/Tailwind) — TA frontend is too project-specific to generalize yet; iter-2
- Mycelium `BaseAgent` NODE wrappers in templates — still aspirational
- Graduation to its own repo (`vibespace/vibespace-framework`) — iter-1 lives inside `reverse-search`; graduation gated on framework stabilizing
- Publishing `vibespace-init` to PyPI — iter-1 ships it as a local script
- Iterational quantum computing primitives in Mycelium (parked — see Open questions)

---

## Constraints + guardrails

Inherited from global + project guardrails:

- Apache 2.0 header on every new file
- No `print()`, no `requests`, no bare `except:` — in templates and in `vibespace-init`
- No hardcoded secrets in templates — every secret in `.env.example.j2` with placeholder value
- No `git` from leaves — `./auto-commit.sh` only
- `git push --force` / `rm -rf` outside `/tmp` require explicit confirmation
- Mycelium vocabulary precise — HYPHA / BIOME BUS / FRUITING BODY / SPORULATION usage must match the global glossary
- Multi-tenancy design-only (framework templates include `tenant_id` as nullable FK, no enforcement)
- **AMMSS is proprietary IP** — no template, doc, or pattern in the framework may reference AMMSS internals. Framework templates may expose a *configuration hook* for AMMSS integration without describing what AMMSS does.

**Framework-specific:**
- Patterns extracted MUST be present in the TA reference implementation. No aspirational patterns. If a pattern is "what we *should* do" instead of "what we *do*", it goes in `patterns/<name>.md` under an explicit `## Open questions` section, not as a prescribed pattern.
- Templates MUST render byte-identical output for identical placeholder inputs across runs. No timestamps, no random IDs, no environment-dependent paths in template bodies.
- The `vibespace-init` CLI MUST be idempotent on `--dry-run` and reject non-idempotent runs by default.

---

## Open questions

| Question | Default | Note |
|---|---|---|
| Where does the framework graduate to its own repo? | Stay in `reverse-search` for iter-1 | Graduate at iter-2 once `framework_watcher` lands |
| How do existing products (TA) consume framework updates? | Manual cherry-pick of pattern changes for iter-1 | iter-3 introduces a `framework-sync` upgrade tool |
| Do we ship a frontend template (React 19 + Vite 8 + Tailwind 4)? | Defer to iter-2 | TA frontend is still too project-specific to abstract |
| How does Mycelium plant against a non-runtime artifact like docs+templates+CLI? | Reuse `nextjs-fastapi-supabase` preset, treat docs as no-op for build/test stages | Documented in HANDOFF.md after first `ddp` run |
| "Iterational quantum computing" framing for Mycelium iteration model | Parked — separate brief once iter-1 ships | SPY raised the term 2026-05-16; the framework iter-1 should ship in classical-Mycelium mode first to give the QC framing a real substrate to layer onto |

---

## How to run

Single-call pipeline:

```bash
cd /Users/spy/mfautomation/repos/creation-station/reverse-search
mycelium ddp \
  --brief ./vibespace-framework/brief.md \
  --stack nextjs-fastapi-supabase \
  --security startup \
  --concurrency 12 \
  --threshold 0.85
```

**Stack preset note.** No preset matches "Python CLI + Markdown + Jinja2 templates." Falling back to `nextjs-fastapi-supabase` and relying on leaves to read the brief's §Stack section as canonical. Document in `HANDOFF.md` after first run.

Pre-flight:

```bash
mycelium plant ./vibespace-framework/brief.md --stack nextjs-fastapi-supabase --security startup --dry-run
```

Verifies the brief decomposes cleanly into the six VSF/* HYPHAE before burning agent budget.

---

## References

- **This brief sits under:** `./vibespace-framework/brief.md`
- **Original framework prompt (source of intent):** `./03-vibespace-framework.md`
- **Reference implementation (extraction source):** TA at HEAD `a804ec1` — `./backend/**` and `./frontend/**`
- **HYPHA format reference:** `./hyphae/HYPHA-AUTH.md` (any of the 10 frozen TA contracts)
- **Repo CLAUDE.md:** `./CLAUDE.md`
- **Global VibeSpace CLAUDE.md:** `/Users/spy/.claude/CLAUDE.md`
- **Mycelium framework source:** `/Users/spy/mfautomation/repos/legendary-funicular/`
- **Mycelium orchestrator + 30/60/90:** `/Users/spy/mfautomation/mycelium-orchestrator/`
- **Digital Dash pipeline (CI integration target):** `./digital-dash-pipeline.yml`
- **TA iter-2 brief (parallel cultivation, does not block this one):** `./brief.md`

---

*The framework is the DNA. The DNA crystallizes from working code. The DNA does not invent — it remembers.*
