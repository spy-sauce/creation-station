# VIBESPACE PRODUCT FRAMEWORK
## Claude Code Prompt — Extract Framework from Digital Dash

---

## MISSION

You are analyzing **Digital Dash** — a production AI-native CI/CD platform built by VibeSpace LLC — and extracting its architectural patterns, conventions, and structure into a **reusable product framework template** called `vibespace-framework`.

This framework will be the foundation for every future VibeSpace product. When a new product is started, Claude Code agents will read this framework and scaffold the new product from it. The framework evolves over time — background agents will monitor engineering best practices, propose updates, and make commits that run through Digital Dash's own pipeline before merging.

This is a living document. Not a one-time scaffold. An evolving standard.

---

## PHASE 1 — EXTRACT

Analyze the Digital Dash codebase and extract the following into `/vibespace-framework/`:

### 1. Architecture Patterns · `patterns/`

Document every architectural decision as a pattern file:

**`patterns/api-structure.md`**
- How FastAPI apps are organized (routers, dependencies, middleware)
- Request/response model conventions
- Error handling patterns
- Auth patterns

**`patterns/agent-structure.md`**
- How agents are structured (BaseAgent interface)
- Lifecycle state machine
- Event bus integration
- Agent communication patterns

**`patterns/database-patterns.md`**
- SQLAlchemy async patterns
- Migration conventions (Alembic)
- Model base class conventions
- Query patterns (avoid N+1, prefer joins)

**`patterns/async-patterns.md`**
- Async best practices extracted from codebase
- Task queue patterns (Celery)
- Concurrency patterns (asyncio.gather, semaphores)
- Background task patterns

**`patterns/ai-integration.md`**
- Claude API call patterns
- Prompt construction conventions
- Response parsing patterns
- Retry + fallback patterns
- Caching strategy for LLM calls

**`patterns/testing-patterns.md`**
- Test structure and naming conventions
- Async test patterns (pytest-asyncio)
- Mocking strategies (external APIs, DB)
- Fixture conventions

---

### 2. Scaffold Templates · `templates/`

Reusable file templates that new products start from:

**`templates/backend/`**
- `main.py` — FastAPI app with standard middleware, CORS, health check, lifespan
- `config.py` — Pydantic Settings with standard env vars
- `database.py` — Async SQLAlchemy engine + session factory
- `base_model.py` — SQLAlchemy base with id/created_at/updated_at
- `base_agent.py` — BaseAgent with standard lifecycle
- `base_router.py` — FastAPI router with standard error handling
- `logging.py` — structlog configuration

**`templates/migrations/`**
- `000_init.sql` — Standard init migration (extensions, enums)

**`templates/docker/`**
- `Dockerfile` — Production-optimized multi-stage build
- `docker-compose.yml` — Local dev with postgres + redis + app
- `.dockerignore`

**`templates/ci/`**
- `digital-dash-pipeline.yml` — Pipeline config for Digital Dash integration
- `.env.example` — Standard env var template

**`templates/tests/`**
- `conftest.py` — Standard fixtures (async db session, test client, mocked Claude API)
- `test_health.py` — Boilerplate health check test

---

### 3. Conventions Doc · `CONVENTIONS.md`

A single reference document covering:
- File naming (snake_case for files, PascalCase for classes, etc.)
- Directory structure conventions
- Commit message format
- Branch naming
- PR conventions
- Versioning strategy
- Environment naming (local / staging / production)
- Secret management
- Logging conventions
- Error code conventions

---

### 4. New Product Checklist · `NEW_PRODUCT.md`

Step-by-step checklist for spinning up a new VibeSpace product:

```
□ Copy scaffold templates
□ Update product name in all files
□ Configure env vars
□ Run init migration
□ Wire product into Digital Dash pipeline
□ Register with Mycelium Event Bus
□ Create product CLAUDE.md
□ Create README.md
□ Run test suite (must be green before first commit)
```

---

### 5. Framework CLAUDE.md · `CLAUDE.md`

Instructions for the background agent that maintains this framework:

```markdown
# vibespace-framework CLAUDE.md

You are the framework maintenance agent for VibeSpace LLC.

Your job: Keep this framework current, correct, and useful.

## Triggers
- PR merged into a VibeSpace product → extract any new patterns not yet in framework
- Weekly scheduled run → research FastAPI/SQLAlchemy/Python best practices for updates
- Manual invocation → accept a specific pattern update proposal

## What you can do autonomously
- Update pattern documentation
- Improve template files (non-breaking changes)
- Add new pattern files
- Update CONVENTIONS.md

## What requires human review
- Any breaking change to existing templates
- Removing or significantly changing an existing pattern
- Changes to the scaffold templates that affect existing products

## Commit format
feat(framework): [short description]

Examples:
feat(framework): add async context manager pattern from digital-dash
feat(framework): update claude api retry pattern to use tenacity
feat(framework): add playwright test fixture template

## Pipeline
All commits run through Digital Dash before merging.
Green pipeline = auto-merge.
Red pipeline = flag for human review.
```

---

## PHASE 2 — TEMPLATIZE

Once extraction is complete:

1. Create a CLI tool `vibespace-init` that:
   - Takes a product name as input
   - Copies all templates to a new directory
   - Replaces placeholder strings (`{{PRODUCT_NAME}}`, `{{PRODUCT_DESCRIPTION}}`) with actual values
   - Runs `git init`, makes initial commit
   - Outputs checklist of next steps

```bash
vibespace-init talent-agent "The AI-powered personal talent agent"
# → creates /talent-agent/ with full scaffold
# → git init + initial commit
# → prints NEW_PRODUCT.md checklist
```

---

## PHASE 3 — BACKGROUND AGENT

Create the background maintenance agent that keeps the framework alive:

**`agents/framework_watcher.py`**

This agent:
- Runs weekly (Celery beat)
- Uses web search to find recent FastAPI, SQLAlchemy, Python async, and AI integration best practices
- Compares findings against current framework patterns
- Proposes updates as PRs (commits to a branch, opens PR)
- PR description includes: what changed, why, source of the best practice
- PR runs through Digital Dash pipeline
- Auto-merges if green, flags for human review if red

**`agents/pattern_extractor.py`**

This agent:
- Triggers on PR merge in any VibeSpace product repo
- Reads the diff
- Identifies patterns not yet captured in the framework
- Proposes additions to the relevant pattern file
- Same PR flow as the framework watcher

---

## OUTPUT

When complete:

```
vibespace-framework/
├── CLAUDE.md                    ← framework agent instructions
├── CONVENTIONS.md               ← canonical coding conventions
├── NEW_PRODUCT.md               ← new product checklist
├── patterns/
│   ├── api-structure.md
│   ├── agent-structure.md
│   ├── database-patterns.md
│   ├── async-patterns.md
│   ├── ai-integration.md
│   └── testing-patterns.md
├── templates/
│   ├── backend/
│   ├── migrations/
│   ├── docker/
│   ├── ci/
│   └── tests/
├── agents/
│   ├── framework_watcher.py
│   └── pattern_extractor.py
└── bin/
    └── vibespace-init
```

This framework is the DNA of every VibeSpace product. Build it with the same care you'd give a product that ships to customers — because every product that ships *starts here.*
