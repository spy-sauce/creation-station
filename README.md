# VibeSpace Talent Agent
### The AI-Powered Personal Talent Agent · Built by Space Cowboy #9

> *"Stop searching for jobs. Let the right ones find you — then let the agent handle everything else."*

---

## What This Is

Most job search tools help you search faster. This isn't that.

This is a **24/7 autonomous talent agent** that reverse-engineers the web to find roles that match the whole person — not just the resume. It then tailors your application, finds the right contact, writes the outreach, fills the form, and sends it. You sit in the review seat and approve or skip.

Built on the **Mycelium Agent Network** — bio-inspired multi-agent orchestration infrastructure from VibeSpace LLC.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        IDENTITY CORE                            │
│         Engineer · Founder · DJ · Visionary · Builder           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │      DISCOVERY ENGINE          │  ← runs daily (cron)
          │                                │
          │  Web Crawler → Reverse Eng.    │
          │  → Relevance Scorer → Digest   │
          └───────────────┬────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │     APPLICATION ENGINE         │  ← triggered per role
          │                                │
          │  JD Parser → Resume Tailor     │
          │  → Company Intel → Contact     │
          │  → Outreach Composer           │
          │  → Auto-Apply Agent            │
          └───────────────┬────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │      REVIEW DASHBOARD          │  ← human in the loop
          │   Approve · Tweak · Skip       │
          └───────────────┬────────────────┘
                          │
          ┌───────────────▼────────────────┐
          │        SENT + TRACKED          │
          │  Email sent · Form submitted   │
          │  · CRM logged · Status tracked │
          └────────────────────────────────┘
```

---

## Discovery Engine

The core innovation. Instead of searching job boards, the Discovery Engine:

1. **Builds a multi-dimensional identity profile** from the candidate's full context — not just title and skills, but their projects, philosophy, creative work, and ambitions
2. **Reverse-engineers the web** — crawls job boards (Greenhouse, Lever, Workday, LinkedIn, company careers pages) for roles that match the *whole person*
3. **Scores relevance across dimensions** — technical match, culture fit, growth trajectory, industry alignment, compensation band
4. **Delivers a ranked daily digest** — top 10 roles, scored and contextualized, ready for the Application Engine

**Key insight:** A candidate who is "Senior Java Engineer + AI Founder + DJ" should surface roles like *Head of AI Products*, *Technical Co-Founder*, *AI Creative Director*, *VP Engineering at a music-tech startup* — not just "Senior Software Engineer L5." The reverse-engineer agent finds opportunities the candidate would never have searched for.

---

## Application Engine

Once a role is approved from the digest, the Application Engine runs autonomously:

| Agent | What it does |
|---|---|
| **JD Parser** | Extracts keywords, required skills, tone, team culture signals, and hidden requirements |
| **Resume Tailor** | Rewrites bullet points to mirror JD language without keyword stuffing — reads natural |
| **Company Intel** | Scrapes recent news, engineering blog, tech stack (StackShare, GitHub), Glassdoor culture signals |
| **Contact Finder** | Locates engineering manager / hiring manager email via LinkedIn, Hunter.io, company website |
| **Outreach Composer** | Writes a personalised cold email grounded in company intel — not a template |
| **Auto-Apply Agent** | Navigates career page, fills form, uploads tailored resume, submits |

**Nothing sends without human approval.** Every draft lands in the Review Dashboard first.

---

## B2B Opportunity

This system is designed to operate at scale for **recruiting agencies**:

- One agency manages 50–500 candidates simultaneously
- Each candidate runs through their own isolated agent pipeline
- Agency gets a white-label dashboard with placement tracking and ROI metrics
- Revenue model: SaaS per seat + per-placement success fee

**Target customer:** Mid-size recruiting firms (10–50 staff) spending hours manually tailoring and submitting applications. This replaces that entirely.

---

## Tech Stack

| Layer | Stack |
|---|---|
| **Backend** | FastAPI · Python · Celery |
| **Agent Orchestration** | Mycelium Agent Network · NATS · Redis Streams |
| **AI** | Claude API · Web search tool |
| **Web Scraping** | Playwright · BeautifulSoup · Scrapy |
| **Database** | PostgreSQL · Redis |
| **Frontend** | React 18 · Vite · Tailwind CSS |
| **Infrastructure** | Docker · AWS ECS Fargate · EventBridge |

---

## Project Structure

```
talent-agent/
├── README.md                    ← you are here
├── CLAUDE.md                    ← agent instructions
├── prompts/
│   ├── 01-discovery-engine.md   ← Claude Code prompt
│   └── 02-application-engine.md ← Claude Code prompt
├── backend/
│   ├── main.py
│   ├── agents/
│   │   ├── discovery/
│   │   └── application/
│   ├── models/
│   └── api/
├── frontend/
│   └── src/
├── docker-compose.yml
└── .env.example
```

---

## Roadmap

- [ ] **Phase 1 — MVP** · Single candidate · Discovery + Application Engine · Manual review dashboard
- [ ] **Phase 2 — Agency Pilot** · Multi-candidate support · White-label dashboard · Design partner (1 agency)
- [ ] **Phase 3 — Scale** · Bloom identity integration · CentralStatic creative profile layer · Full Mycelium network orchestration
- [ ] **Phase 4 — Network** · Candidates refer candidates · Agency marketplace · AI placement predictions

---

## Built By

**VibeSpace LLC — The Dot Connector**  
Sean Young (Space Cowboy #9) · spy@seanyoung.biz  
Miami, FL · github.com/tyzeeington

*Part of The Digital Renaissance ecosystem.*
