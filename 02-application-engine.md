# TALENT AGENT — APPLICATION ENGINE
## Claude Code Prompt · Phase 2

---

## CONTEXT

You are building the **Application Engine** for **VibeSpace Talent Agent** — an autonomous AI talent system built by **Sean Young (Space Cowboy #9)** at **VibeSpace LLC ("The Dot Connector")**, Miami, FL.

This is Phase 2. The Discovery Engine (Phase 1) already exists and delivers a `DailyDigest` of scored, ranked job opportunities. The Application Engine picks up where the digest leaves off — it takes an approved job and autonomously handles the entire application process: parsing the JD, tailoring the resume, researching the company, finding the right contact, composing outreach, and submitting the application.

**Human stays in the loop.** Every deliverable (tailored resume, outreach email, form submission) lands in the Review Dashboard for approval before anything sends. The agent prepares. The human decides.

---

## PHILOSOPHY

Generic applications get ignored. This engine produces applications that feel hand-crafted — because the AI does the hand-crafting work at scale.

The goal for every application:
- The resume reads like it was written specifically for this role
- The outreach email references something specific and real about the company
- The hiring manager gets the impression that this candidate actually knows who they are
- The career page form is filled out completely and accurately

No templates. No keyword stuffing. No copy-paste. Every application is a fresh artifact built from the candidate's real story, matched to the company's real context.

---

## WHAT YOU ARE BUILDING

### Directory: `backend/agents/application/`

---

### 1. JD Parser · `jd_parser.py`

**Purpose:** Deep parse of the job description to extract every signal that matters for tailoring the application.

**Input:** `ScoredJob` (from Discovery Engine)

**Output:** `ParsedJD`
- `required_skills`: Hard requirements (must-haves)
- `preferred_skills`: Nice-to-haves
- `seniority_level`: Inferred level from language and requirements
- `team_context`: What team this person joins, who they report to
- `key_responsibilities`: Top 5 responsibilities ranked by emphasis
- `culture_signals`: Language patterns indicating culture (move fast, collaborative, ownership, etc.)
- `tech_stack`: Technologies mentioned explicitly + implied
- `pain_points`: What problem is this hire solving for the company?
- `tone`: Formal / startup-casual / technical / mission-driven
- `comp_mentioned`: Compensation if disclosed
- `red_flags`: Signals worth noting (unrealistic requirements, culture mismatch indicators)
- `application_instructions`: Any specific instructions for applying (cover letter required, portfolio, etc.)

**Implementation:**
- Use Claude API with a structured output prompt — parse JD text into `ParsedJD` JSON
- Cross-reference against candidate's `IdentityProfile` to flag gaps and strengths
- Log parsed JD to PostgreSQL — reuse if job is re-processed

---

### 2. Resume Tailor · `resume_tailor.py`

**Purpose:** Rewrites the candidate's resume to align with the specific role — without fabricating experience or keyword stuffing.

**Input:** `ParsedJD` + `Candidate` + `IdentityProfile`

**Output:** `TailoredResume`
- `summary`: Rewritten profile/summary section targeting this specific role and company
- `bullets`: Rewritten bullet points for each experience entry — mirror JD language where truthful
- `skills_section`: Reordered/reprioritised based on JD requirements
- `highlighted_projects`: Projects most relevant to this role surfaced first
- `full_text`: Complete resume text ready for PDF generation
- `change_log`: What changed from base resume and why (shown in Review Dashboard)

**Rules:**
- Never fabricate experience, titles, dates, or metrics
- Mirror JD language naturally — not robotically (don't repeat phrases verbatim)
- Prioritise relevance over comprehensiveness — cut bullets that don't serve this application
- Preserve the candidate's voice and authenticity
- If a required skill is missing from the candidate's profile, do not invent it — flag it in `change_log` as a gap

**Implementation:**
- Use Claude API with the base resume, identity profile, and parsed JD as context
- Prompt: "Rewrite this resume to position this candidate for this specific role. Be honest. Be compelling. Sound like a human wrote it."
- Generate PDF using `reportlab` or `weasyprint` from the tailored text
- Version control: every tailored resume stored with job_id foreign key

---

### 3. Company Intel Agent · `company_intel.py`

**Purpose:** Researches the company to give the outreach composer real, specific context to work with.

**Input:** Company name + URL from `ScoredJob`

**Output:** `CompanyIntel`
- `about`: 2–3 sentence summary of what the company does
- `recent_news`: Last 30 days of significant news (funding, launches, partnerships, hires)
- `tech_stack`: Technologies confirmed from job postings, StackShare, GitHub, engineering blog
- `engineering_culture`: Signals from engineering blog, tech talks, open source contributions
- `glassdoor_signals`: Rating, common praise/complaints (if available)
- `growth_stage`: Seed / Series A / B / C / Public / Enterprise
- `team_size`: Engineering team size estimate
- `notable_facts`: Anything specific and interesting — a hook for the outreach email
- `cache_age`: When this intel was gathered (TTL: 7 days)

**Sources to scrape:**
1. Company website (`/about`, `/team`, `/engineering`, `/blog`)
2. Engineering blog (if exists)
3. GitHub org (public repos, activity, tech signals)
4. StackShare company profile
5. Crunchbase (funding stage, investors)
6. Google News (last 30 days, company name)
7. Glassdoor (rating + top reviews — handle carefully, scrape only what's visible)

**Implementation:**
- Cache all intel in Redis (TTL: 7 days) — don't re-scrape the same company within a week
- Persist to PostgreSQL `company_intel` table
- Use Claude API to synthesise raw scraped data into structured `CompanyIntel` object
- Flag if company has <6 months of data available (startup with no public footprint)

---

### 4. Contact Finder · `contact_finder.py`

**Purpose:** Finds the right person to send the cold outreach email to — typically the engineering manager or hiring manager.

**Input:** `CompanyIntel` + `ParsedJD`

**Output:** `Contact`
- `name`: Full name
- `title`: Current title
- `email`: Best available email
- `linkedin_url`: Profile URL
- `confidence`: HIGH / MEDIUM / LOW (how confident we are this is the right person)
- `source`: Where the contact was found
- `fallback_email`: Generic recruiter/HR email if direct contact unavailable

**Strategy (in order):**
1. Check JD for hiring manager name mentioned explicitly
2. Search LinkedIn for `{company} engineering manager {team}`
3. Search LinkedIn for `{company} head of engineering`
4. Use Hunter.io API to find verified email patterns for the domain
5. Construct likely email from name + domain pattern (e.g. `first.last@company.com`)
6. Fall back to `jobs@`, `recruiting@`, `engineering@` generic addresses

**Implementation:**
- Hunter.io API for email verification and pattern discovery
- LinkedIn scraping with Playwright — be respectful, use delays
- Never use email addresses found in data broker sites
- Store contacts in PostgreSQL — reuse if same company applied to again
- Mark contact as `UNVERIFIED` until an email bounces or opens confirm delivery

---

### 5. Outreach Composer · `outreach_composer.py`

**Purpose:** Writes a cold email that doesn't read like a cold email. Specific, personal, compelling — grounded in real company context.

**Input:** `ParsedJD` + `CompanyIntel` + `Contact` + `TailoredResume` + `IdentityProfile`

**Output:** `OutreachEmail`
- `to`: Recipient email
- `subject`: Subject line (tested for open rate patterns)
- `body`: Email body
- `tone_used`: The tone chosen based on company culture signals
- `hook_used`: The specific company fact used as the opening hook
- `attachments`: Tailored resume PDF

**Email structure:**
1. **Hook** (1 sentence) — reference something specific and real: recent funding, a product launch, an engineering blog post, a shared connection, something in the JD that signals the team's current challenge
2. **Bridge** (1–2 sentences) — connect that hook to why the candidate is reaching out
3. **Value** (2–3 sentences) — the candidate's most relevant proof of impact for this specific role — not a generic summary
4. **Ask** (1 sentence) — clear, low-friction CTA. Not "I'd love to chat" — something specific like "Would a 20-minute call this week make sense?"
5. **Signature** — name, title, links (GitHub, portfolio, Bloom card if applicable)

**Rules:**
- Total length: 150–200 words max. Busy engineers don't read walls of text.
- Never start with "I hope this email finds you well"
- Never use "I'm reaching out because..."
- Never list every skill — pick the one or two that matter most for this role
- Sound like a human being wrote this at 9pm after doing research, not like an AI blasted it at 6am

**Implementation:**
- Use Claude API with a detailed prompt including all context
- Generate 3 subject line variants — show all 3 in Review Dashboard
- Log email drafts to PostgreSQL with job_id foreign key
- Mark as `DRAFT` until approved in Review Dashboard

---

### 6. Auto-Apply Agent · `auto_apply.py`

**Purpose:** Navigates the company's career page and submits the application form.

**Input:** Job URL + `TailoredResume` + `Candidate` + `ParsedJD`

**Output:** `ApplicationResult`
- `status`: SUCCESS / FAILED / REQUIRES_MANUAL
- `confirmation_number`: Application confirmation if provided
- `screenshot`: Screenshot of confirmation page
- `fields_completed`: List of form fields that were filled
- `error`: Error message if failed
- `fallback_url`: Direct link for manual submission if auto-apply fails

**Implementation:**
- Use `Playwright` async for form navigation
- Detect ATS type from URL patterns (Greenhouse, Lever, Workday, Ashby) and use known field maps
- For unknown ATSs: use AI-guided form detection — read the DOM, infer field purposes
- Upload tailored resume PDF to file upload fields
- Fill standard fields: name, email, phone, location, LinkedIn, GitHub, cover letter (optional)
- **Never submit without explicit approval from Review Dashboard**
- Take screenshot after every major step — saved to `/screenshots/{job_id}/`
- If CAPTCHA detected: mark as `REQUIRES_MANUAL` and surface to dashboard

**ATS Field Maps:**
Build known field maps for Greenhouse, Lever, Workday, Ashby so form detection is fast and accurate for the most common systems.

---

### 7. Application Orchestrator · `orchestrator.py`

**Purpose:** Coordinates the full application pipeline for a single approved job.

**Flow:**
```
receive_approved_job(job_id)
  → jd_parser.parse(job)
  → resume_tailor.tailor(parsed_jd, candidate)
  → company_intel.research(company)          ← async, parallel with resume
  → contact_finder.find(company_intel)
  → outreach_composer.compose(all_context)
  → [PAUSE — await Review Dashboard approval]
  → auto_apply.submit(job, resume)           ← only if approved
  → outreach_sender.send(email)              ← only if approved
  → log_to_crm(result)
```

**Parallel execution:** `resume_tailor` and `company_intel` run concurrently — both need the parsed JD but don't depend on each other.

**Pipeline status tracking:**
```
QUEUED → PARSING → TAILORING → RESEARCHING → COMPOSING → AWAITING_REVIEW → APPROVED/REJECTED → SUBMITTED → SENT → TRACKED
```

Every status transition logged to PostgreSQL with timestamp.

---

### 8. Review Dashboard API · `api/review.py`

**Purpose:** Exposes all draft artifacts for human review before anything is sent.

```
GET    /review/queue                        → list all awaiting review
GET    /review/application/{job_id}         → full application package
PATCH  /review/application/{job_id}/approve → approve and trigger send
PATCH  /review/application/{job_id}/reject  → skip this application
PATCH  /review/resume/{job_id}              → update tailored resume
PATCH  /review/email/{job_id}               → update outreach email
GET    /review/preview/{job_id}/resume      → render resume PDF preview
GET    /review/preview/{job_id}/email       → preview email in browser
```

---

### 9. CRM · `crm.py`

**Purpose:** Tracks every application and its outcome over time.

**Tracks:**
- Date applied
- Company + role
- Contact reached
- Email open (webhook/pixel if possible)
- Response received
- Interview scheduled
- Offer received
- Placement

Simple PostgreSQL table + API endpoints. No third-party CRM dependency in MVP.

---

## MODELS · `models/application.py`

```python
class ParsedJD(BaseModel): ...
class TailoredResume(BaseModel): ...
class CompanyIntel(BaseModel): ...
class Contact(BaseModel): ...
class OutreachEmail(BaseModel): ...
class ApplicationResult(BaseModel): ...
class ApplicationPipeline(BaseModel): ...  # full pipeline state
```

---

## DATABASE SCHEMA · `migrations/002_application.sql`

Tables:
- `parsed_jds` — cached JD parse results
- `tailored_resumes` — versioned per job_id
- `company_intel` — cached company research (7-day TTL)
- `contacts` — discovered contacts per company
- `outreach_emails` — drafts + sent emails
- `application_pipelines` — full pipeline state machine per job
- `application_results` — outcome of form submissions
- `crm_events` — timeline of events per application

---

## ENVIRONMENT VARIABLES

```env
ANTHROPIC_API_KEY=
HUNTER_API_KEY=
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SCREENSHOT_DIR=./screenshots
MAX_PARALLEL_APPLICATIONS=3
AUTO_APPLY_ENABLED=true
OUTREACH_ENABLED=true
```

---

## CONSTRAINTS & STANDARDS

Same as Discovery Engine — FastAPI, Pydantic v2, async SQLAlchemy, pytest, Apache 2.0.

Additional:
- Playwright always runs headless in production
- All form submissions gated behind `AWAITING_REVIEW` status — never auto-send
- Screenshot every form interaction for audit trail
- Rate limit outreach: max 10 cold emails per day per candidate
- Respect robots.txt on all scraped sites

---

## OUTPUT

When complete, confirm:
- [ ] All 9 modules created and wired
- [ ] Pydantic models defined
- [ ] Database migration written
- [ ] Review Dashboard API endpoints registered
- [ ] CRM module functional
- [ ] ATS field maps for Greenhouse, Lever, Workday, Ashby
- [ ] `tests/application/` with smoke tests for orchestrator + composer
- [ ] `.env.example` updated

Start with `models/application.py`, then `jd_parser.py`, then `orchestrator.py`. The orchestrator defines the pipeline — build everything else to serve it.
