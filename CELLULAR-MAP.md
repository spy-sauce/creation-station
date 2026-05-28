# Talent Agent Cellular Execution Map

> **Gating model:** Max-concurrency tree. Gating = **contract freeze** (not fruit completion). Every leaf is its own Claude Agent SDK session on its own branch. Specialists consume frozen contract stubs, not upstream code; integration happens at merge time via deterministic merge order, not execution time.

---

## Concurrency Math

| Depth | Count | Description |
|---|---|---|
| Biomes (1) | 14 | 10 existing + 4 new (scheduler, api-streaming, api-client, tests) |
| Specialists (2) | ~32 | After iter-4 decomposition |
| Leaf specialists (3) | ~62 | Including infra leaves and test leaves |
| **Total concurrent sessions at peak** | **4** | Current (rate-limit discipline) |
| **Target peak (full depth-3)** | **8-12** | After cache warmup + token bucket optimization |

**Iter-4 deltas:**
- +4 new biomes: scheduler-agent, api-streaming-agent, api-client-agent, tests-agent
- +11 new specialists across new biomes
- infra-agent decomposed into 6 explicit leaves

---

## Gating Semantics

**Old wave-gating (deprecated):** Biome A must reach FRUIT_READY before Biome B can GERMINATE. This serializes execution, wasting concurrency budget on blocking waits.

**New contract-freeze gating:** All contracts freeze upfront. Specialists read frozen stubs from NUTRIENTS.md, not live code from upstream biomes. Biome A and Biome B can germinate, grow, and fruit concurrently. Integration happens at merge time: the deterministic `merge_order` in mycelium.yaml ensures A lands before B when B depends on A's exports.

**Implication:** The tree below shows logical dependencies, not execution order. Every agent can run concurrently from GERMINATE through FRUIT once its `blocked_by` contracts are frozen—which happens before cultivation starts.

---

## Execution Tree

```
organism: talent-agent (iter-4)
│
├── data-agent (4 specialists) — FROZEN
│   ├── data-agent.migrations
│   │   ├── data-agent.migrations.init
│   │   ├── data-agent.migrations.discovery
│   │   ├── data-agent.migrations.application
│   │   └── data-agent.migrations.auth
│   ├── data-agent.models
│   │   ├── data-agent.models.base
│   │   ├── data-agent.models.discovery
│   │   ├── data-agent.models.application
│   │   └── data-agent.models.auth
│   ├── data-agent.schemas-discovery
│   │   └── data-agent.schemas-discovery.all
│   └── data-agent.schemas-application
│       └── data-agent.schemas-application.all
│
├── design-agent (3 specialists) — FROZEN
│   ├── design-agent.tokens
│   │   ├── design-agent.tokens.palette
│   │   ├── design-agent.tokens.typography
│   │   └── design-agent.tokens.spacing
│   ├── design-agent.primitives
│   │   ├── design-agent.primitives.status-badge
│   │   └── design-agent.primitives.stat-card
│   └── design-agent.docs
│       ├── design-agent.docs.cheatsheet
│       └── design-agent.docs.reference
│
├── auth-agent (2 specialists) — FROZEN
│   ├── auth-agent.magic-link
│   │   ├── auth-agent.magic-link.request
│   │   ├── auth-agent.magic-link.verify
│   │   └── auth-agent.magic-link.resend
│   └── auth-agent.jwt
│       ├── auth-agent.jwt.issue
│       ├── auth-agent.jwt.validate
│       └── auth-agent.jwt.current-user
│
├── obs-agent (2 specialists) — FROZEN
│   ├── obs-agent.logging
│   │   ├── obs-agent.logging.config
│   │   └── obs-agent.logging.pii-redact
│   └── obs-agent.pubsub
│       ├── obs-agent.pubsub.taxonomy
│       └── obs-agent.pubsub.publisher
│
├── discover-agent (6 specialists) — ITER-4 MODIFIED
│   ├── discover-agent.identity
│   │   └── discover-agent.identity.profiler
│   ├── discover-agent.archetype
│   │   └── discover-agent.archetype.generator
│   ├── discover-agent.crawler
│   │   ├── discover-agent.crawler.greenhouse
│   │   ├── discover-agent.crawler.lever
│   │   ├── discover-agent.crawler.ashby
│   │   └── discover-agent.crawler.workday
│   ├── discover-agent.scorer
│   │   └── discover-agent.scorer.relevance
│   ├── discover-agent.digest
│   │   └── discover-agent.digest.builder
│   ├── discover-agent.orchestrator
│   │   └── discover-agent.orchestrator.main
│   └── discover-agent.pubsub  ← NEW: _publish_status helper
│       └── discover-agent.pubsub.status-events
│
├── apply-agent (7 specialists) — FROZEN
│   ├── apply-agent.jd-parser
│   │   └── apply-agent.jd-parser.main
│   ├── apply-agent.resume-tailor
│   │   └── apply-agent.resume-tailor.main
│   ├── apply-agent.company-intel
│   │   └── apply-agent.company-intel.main
│   ├── apply-agent.contact-finder
│   │   └── apply-agent.contact-finder.main
│   ├── apply-agent.outreach
│   │   └── apply-agent.outreach.composer
│   ├── apply-agent.auto-apply
│   │   ├── apply-agent.auto-apply.greenhouse
│   │   ├── apply-agent.auto-apply.lever
│   │   ├── apply-agent.auto-apply.ashby
│   │   └── apply-agent.auto-apply.workday
│   └── apply-agent.orchestrator
│       └── apply-agent.orchestrator.main
│
├── agents-agent (3 specialists) — FROZEN
│   ├── agents-agent.registry
│   │   └── agents-agent.registry.defaults
│   ├── agents-agent.runner
│   │   ├── agents-agent.runner.execute
│   │   └── agents-agent.runner.retry
│   └── agents-agent.dispatcher
│       └── agents-agent.dispatcher.pipeline
│
├── api-agent (4 specialists) — FROZEN
│   ├── api-agent.core
│   │   ├── api-agent.core.main
│   │   ├── api-agent.core.config
│   │   └── api-agent.core.database
│   ├── api-agent.routers
│   │   ├── api-agent.routers.discovery
│   │   ├── api-agent.routers.application
│   │   └── api-agent.routers.review
│   ├── api-agent.onboarding
│   │   └── api-agent.onboarding.resume-profile
│   └── api-agent.health
│       └── api-agent.health.endpoint
│
├── scheduler-agent (4 specialists) ← NEW BIOME
│   ├── scheduler-agent.app
│   │   └── scheduler-agent.app.celery-factory
│   ├── scheduler-agent.tasks
│   │   └── scheduler-agent.tasks.daily-discovery
│   ├── scheduler-agent.beat
│   │   └── scheduler-agent.beat.schedule
│   └── scheduler-agent.retry
│       └── scheduler-agent.retry.exponential-backoff
│
├── api-streaming-agent (4 specialists) ← NEW BIOME
│   ├── api-streaming-agent.events
│   │   └── api-streaming-agent.events.endpoint
│   ├── api-streaming-agent.subscriber
│   │   └── api-streaming-agent.subscriber.redis-pubsub
│   ├── api-streaming-agent.heartbeat
│   │   └── api-streaming-agent.heartbeat.ping
│   └── api-streaming-agent.backpressure
│       └── api-streaming-agent.backpressure.slow-client
│
├── frontend-agent (6 specialists) — FROZEN
│   ├── frontend-agent.primitives
│   │   ├── frontend-agent.primitives.button
│   │   ├── frontend-agent.primitives.input
│   │   ├── frontend-agent.primitives.card
│   │   └── frontend-agent.primitives.dialog
│   ├── frontend-agent.layout
│   │   ├── frontend-agent.layout.sidebar
│   │   └── frontend-agent.layout.dashboard
│   ├── frontend-agent.auth-flow
│   │   ├── frontend-agent.auth-flow.login
│   │   ├── frontend-agent.auth-flow.verify
│   │   └── frontend-agent.auth-flow.context
│   ├── frontend-agent.onboarding
│   │   └── frontend-agent.onboarding.wizard
│   ├── frontend-agent.dashboard
│   │   ├── frontend-agent.dashboard.overview
│   │   ├── frontend-agent.dashboard.pipeline
│   │   └── frontend-agent.dashboard.analytics
│   └── frontend-agent.review-queue
│       ├── frontend-agent.review-queue.list
│       └── frontend-agent.review-queue.detail
│
├── api-client-agent (7 specialists) ← NEW BIOME
│   ├── api-client-agent.client
│   │   └── api-client-agent.client.fetch-wrapper
│   ├── api-client-agent.auth
│   │   └── api-client-agent.auth.magic-link
│   ├── api-client-agent.discovery
│   │   └── api-client-agent.discovery.digest-api
│   ├── api-client-agent.applications
│   │   └── api-client-agent.applications.review-api
│   ├── api-client-agent.events
│   │   └── api-client-agent.events.sse-subscription
│   ├── api-client-agent.error-handling
│   │   └── api-client-agent.error-handling.401-logout
│   └── api-client-agent.page-wiring
│       └── api-client-agent.page-wiring.data-integration
│
├── infra-agent (6 specialists) — ITER-4 LEAF DECOMPOSED
│   ├── infra-agent.docker.backend
│   │   └── infra-agent.docker.backend.dockerfile
│   ├── infra-agent.docker.frontend
│   │   └── infra-agent.docker.frontend.dockerfile-nginx
│   ├── infra-agent.docker.compose
│   │   └── infra-agent.docker.compose.six-services
│   ├── infra-agent.ecs.task-defs
│   │   ├── infra-agent.ecs.task-defs.backend
│   │   ├── infra-agent.ecs.task-defs.frontend
│   │   ├── infra-agent.ecs.task-defs.celery-worker
│   │   └── infra-agent.ecs.task-defs.celery-beat
│   ├── infra-agent.ecs.bootstrap
│   │   └── infra-agent.ecs.bootstrap.setup-aws
│   └── infra-agent.pipeline.digital-dash
│       └── infra-agent.pipeline.digital-dash.deploy-celery
│
└── tests-agent (5 specialists) ← NEW BIOME
    ├── tests-agent.discovery.pubsub
    │   └── tests-agent.discovery.pubsub.event-sequence
    ├── tests-agent.scheduler.daily
    │   └── tests-agent.scheduler.daily.task-creation
    ├── tests-agent.api.events
    │   └── tests-agent.api.events.sse-frames
    ├── tests-agent.api.review
    │   └── tests-agent.api.review.approve-flow
    └── tests-agent.frontend.client
        └── tests-agent.frontend.client.auth-injection
```

---

## Dependency Graph (Mermaid)

```mermaid
graph TD
    subgraph "Tier 0 (Foundation)"
        DATA[data-agent]
        DESIGN[design-agent]
    end

    subgraph "Tier 1 (Core Services)"
        AUTH[auth-agent]
        OBS[obs-agent]
    end

    subgraph "Tier 2 (Engines)"
        DISCOVER[discover-agent]
        APPLY[apply-agent]
    end

    subgraph "Tier 2b (New - Scheduler + Streaming)"
        SCHEDULER[scheduler-agent]
        STREAMING[api-streaming-agent]
    end

    subgraph "Tier 3 (Wrappers)"
        AGENTS[agents-agent]
    end

    subgraph "Tier 4 (Surfaces)"
        API[api-agent]
        FRONTEND[frontend-agent]
    end

    subgraph "Tier 4b (New - API Client)"
        APICLIENT[api-client-agent]
    end

    subgraph "Tier 5 (Deploy)"
        INFRA[infra-agent]
    end

    subgraph "Tier 6 (Validation)"
        TESTS[tests-agent]
    end

    DATA --> AUTH
    DATA --> OBS
    DATA --> DISCOVER
    DATA --> APPLY
    DATA --> API
    DATA --> SCHEDULER

    DESIGN --> FRONTEND

    AUTH --> API
    AUTH --> FRONTEND
    AUTH --> STREAMING

    OBS --> API
    OBS --> DISCOVER
    OBS --> APPLY
    OBS --> STREAMING

    DISCOVER --> APPLY
    DISCOVER --> SCHEDULER
    DISCOVER --> STREAMING

    APPLY --> AGENTS

    API --> FRONTEND
    API --> STREAMING
    API --> APICLIENT

    STREAMING --> APICLIENT

    FRONTEND --> APICLIENT
    FRONTEND --> INFRA

    SCHEDULER --> INFRA

    APICLIENT --> TESTS

    DISCOVER --> TESTS
    SCHEDULER --> TESTS
    STREAMING --> TESTS
```

---

## What's Next

1. **Cache hit-rate observability** (+0 sessions, iter-5 work)
   - Add metrics to track prompt cache utilization
   - Tune concurrency based on cache performance

2. **Decompose api-client-agent.page-wiring deeper** (+5 sessions)
   - Each page (Overview, Pipeline, Analytics, ReviewQueue, ReviewDetail) could be a leaf
   - Currently bundled for simplicity

3. **Add error recovery specialists** (+3 sessions)
   - Circuit breaker leaves for external API failures
   - Graceful degradation paths

4. **Parallel merge verification** (+1 background session)
   - Run merge-order checks while specialists are fruiting
   - Catch integration issues earlier

---

## Parked for Later

- **Rate-limit tuning:** Currently locked at `-c 4` per framework evidence. Re-evaluate once cache hit-rate is consistently >80%.
- **Circuit breakers:** Add backpressure mechanisms if any specialist consistently fails.
- **Cost tracking:** Token usage per leaf for budget forecasting.
- **Incremental freeze:** Allow mid-cultivation contract amendments without full re-freeze.
- **Event sourcing:** Full event replay for SSE connections (iter-5).
- **Multi-tenant isolation:** Agency-level candidate partitioning (post-MVP).
