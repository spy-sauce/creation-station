# Talent Agent — Cultivation Brief (Iteration 3.5 — Targeted)

> Input to `mycelium cultivate --only-biome`. Targeted re-cultivation of two biomes that shipped stubs in iter-3. **Do not re-cultivate other biomes.**
>
> Read `CLAUDE.md` (project), `NUTRIENTS.md` (frozen contracts), and `hyphae/HYPHA-*.md` before acting.

---

## Scope

Two biomes only:

1. **discover-agent** — ship a real multi-source crawler. The stub-shell file at `backend/agents/discovery/crawler_agent.py` now raises `NotImplementedError` in every method. Replace those raises with real working code.
2. **apply-agent** — ship `backend/agents/application/ats_selectors.yaml` and update `backend/agents/application/auto_apply.py` to load and use it.

**No other biome is in scope.** Do not touch frontend, design, auth, data, obs, api, infra, agents files.

---

## Stack canon

Same as iter-3. The repo uses `--stack nextjs-fastapi-supabase` as a label only — the real stack is:

- Backend: FastAPI · Python 3.12 · Pydantic v2 · SQLAlchemy 2.0 async · Alembic · httpx · Playwright async
- DB: raw PostgreSQL 15 (NOT Supabase)
- No Next.js, no Supabase, no httpOnly cookies, no RLS, no NEXT_PUBLIC_ env vars

---

## TA/DISCOVER — real crawler delta

The file `backend/agents/discovery/crawler_agent.py` currently declares five classes that raise `NotImplementedError`: `GreenhouseAdapter`, `LeverAdapter`, `AshbyAdapter`, `WorkdayAdapter`, and `CrawlerAgent.run`. **Implement all five.**

### Hard requirements

**Create `backend/agents/discovery/sources.yaml`** — a curated roster. Seed with ~12 slugs per source (don't need 50 to satisfy iter-3.5):

```yaml
greenhouse:
  - anthropic
  - openai
  - figma
  - vercel
  - replit
  - cursor
  - linear
  - notion
  - airbnb
  - stripe
  - databricks
  - retool

lever:
  - netflix
  - palantir
  - ramp
  - mercury
  - brex
  - rippling
  - retool
  - flexport
  - scale
  - convoy
  - benchling
  - openai

ashby:
  - browserbase
  - posthog
  - clay
  - hex
  - vanta
  - cohere
  - perplexity
  - elevenlabs
  - mistralai
  - together
  - groq
  - modal

workday:
  - tenant: nvidia
    board: NVIDIAExternalCareerSite
  - tenant: microsoft
    board: External
  - tenant: salesforce
    board: External_Career_Site
  - tenant: workday
    board: Workday
```

### Implementation rules

- **Use `httpx.AsyncClient`** for Greenhouse / Lever / Ashby. NEVER `requests`. Set `timeout=15.0`. Concurrent fan-out across slugs via `asyncio.gather` with a semaphore of 4.
- **Rate-limit per host**: 2 req/sec max per domain. Add 0.5-2.0s jitter via `asyncio.sleep(random.uniform(0.5, 2.0))` between calls to the same host.
- **User-Agent**: `"TalentAgent/1.0 (+https://github.com/example/talent-agent)"`. Set on every request.
- **Greenhouse URL**: `https://boards.greenhouse.io/{slug}.json`. Response shape: `{jobs: [{id, title, location: {name}, absolute_url, updated_at, content}]}`. The HTML `content` field needs `html.unescape` then `BeautifulSoup(content, "html.parser").get_text()` to extract `raw_description`.
- **Lever URL**: `https://api.lever.co/v0/postings/{slug}?mode=json`. Response is a list of postings: `[{id, text, categories: {location, team}, descriptionPlain, hostedUrl, createdAt}]`.
- **Ashby URL**: `POST https://api.ashbyhq.com/posting-api/job-board/{slug}` with body `{"includeCompensation": true}` and `Content-Type: application/json`. Response: `{jobs: [{id, title, location, employmentType, jobUrl, publishedDate, descriptionPlain}]}`.
- **Workday adapter**: use Playwright async (already in `requirements.txt`). Launch chromium headless, navigate to `https://{tenant}.wd1.myworkdayjobs.com/{board}` (try `wd1`, then `wd5`, then `wd103`), scrape `[data-automation-id='jobTitle']` and `[data-automation-id='jobPostingHeader']` links. Set timeout=30s. Close browser in finally.
- **Title filter**: case-insensitive substring match of manifest `target_titles` against the posting title. If any keyword appears, include the row.
- **Output shape**: every adapter returns `list[dict]` with these exact keys: `title`, `company`, `source` (one of `greenhouse|lever|ashby|workday`), `url`, `location`, `posted_at` (ISO string or None), `raw_description`, `raw_payload` (the full upstream JSON for debugging).
- **`CrawlerAgent.run`**: load `sources.yaml` via `yaml.safe_load`, fan out to all four adapters in parallel via `asyncio.gather`, merge results, dedupe by `url_hash`, convert each dict to `DiscoveredJobSchema`, return the list. Log structured events: `crawler.adapter_start`, `crawler.adapter_complete` with counts, `crawler.dedup` with before/after counts.
- **Error handling**: if one adapter raises, log it and continue with the others — never let one source's failure kill the whole crawl. Use `return_exceptions=True` on `asyncio.gather`.

### Tests

Add `tests/discovery/test_crawler_adapters.py`:

- One test per adapter using `respx` (already in test deps if needed — add to `requirements.txt` test extras) to mock the HTTP response and assert the adapter returns parsed dicts of the right shape.
- One test for `CrawlerAgent.run` that mocks all four adapters and asserts dedup works correctly.
- One test for `url_hash` determinism + case-insensitivity.

### What MUST NOT happen

- Do NOT add comments containing "STUB", "Phase 1B", "TODO: implement", or "placeholder" anywhere in this file.
- Do NOT leave any `raise NotImplementedError` in the shipped file.
- Do NOT preserve the existing stub class bodies — replace them entirely.
- Do NOT skip the `sources.yaml` file. The crawler MUST load it from disk.
- Do NOT change the `CrawlerAgent.url_hash` method — it's already correct.

---

## TA/APPLY — ats_selectors.yaml delta

Ship `backend/agents/application/ats_selectors.yaml`. Each ATS host has known form field patterns. The yaml maps source name → form field → CSS selector(s).

```yaml
greenhouse:
  first_name: ["input#first_name", "input[name='job_application[first_name]']"]
  last_name: ["input#last_name", "input[name='job_application[last_name]']"]
  email: ["input#email", "input[name='job_application[email]']"]
  phone: ["input#phone", "input[name='job_application[phone]']"]
  resume_file: ["input[type='file']#resume", "input[name='job_application[resume]']"]
  cover_letter_file: ["input[type='file']#cover_letter"]
  linkedin: ["input[name='job_application[answers_attributes][0][text_value]']"]
  submit: ["input[type='submit']#submit_app", "button[type='submit']"]

lever:
  first_name: ["input[name='name']"]  # Lever uses single 'name' field; split in adapter
  email: ["input[name='email']"]
  phone: ["input[name='phone']"]
  resume_file: ["input[type='file'][name='resume']"]
  linkedin: ["input[name='urls[LinkedIn]']"]
  submit: ["button[type='submit'].posting-btn-submit"]

ashby:
  first_name: ["input[name='_systemfield_name']"]  # combined name
  email: ["input[name='_systemfield_email']"]
  phone: ["input[name='_systemfield_phone']"]
  resume_file: ["input[type='file'][data-testid='resume-upload']"]
  linkedin: ["input[name*='LinkedIn']", "input[name*='linkedin']"]
  submit: ["button[data-testid='submit-button']", "button[type='submit']"]

workday:
  # Workday is multi-step; selectors per step
  step1_continue: ["button[data-automation-id='continueButton']"]
  email: ["input[data-automation-id='email']"]
  password: ["input[data-automation-id='password']"]
  resume_upload: ["input[data-automation-id='file-upload-input-ref']"]
  first_name: ["input[data-automation-id='legalNameSection_firstName']"]
  last_name: ["input[data-automation-id='legalNameSection_lastName']"]
  phone: ["input[data-automation-id='phone-number']"]
  submit: ["button[data-automation-id='bottom-navigation-next-button']"]

# Captcha indicators — any of these visible → mark REQUIRES_MANUAL
captcha_indicators:
  - "iframe[src*='recaptcha']"
  - "iframe[src*='hcaptcha']"
  - "div.cf-challenge"
  - "div[data-sitekey]"
  - "iframe[title*='challenge']"
```

### Implementation rules for auto_apply.py

- Load `ats_selectors.yaml` at `AutoApplyAgent.__init__` time. Cache it as `self._selectors`.
- The existing `_navigate_and_fill` method already references `host` (greenhouse/lever/workday/ashby). Use `self._selectors[host]` to drive field discovery. For each field, try each selector in the list in order; first match wins.
- The existing `_has_captcha` method: replace its current logic with iterating `self._selectors['captcha_indicators']` and checking `page.locator(sel).count() > 0` for each.
- **Do NOT change the public surface** — `AutoApplyAgent.submit(...)` keeps the same signature. Only internals change.
- Add a unit test `tests/application/test_auto_apply_selectors.py` that loads the yaml and asserts every value is a list of strings, all four hosts are present, and `captcha_indicators` exists.

### What MUST NOT happen

- Do NOT add a new method to `AutoApplyAgent` beyond what already exists.
- Do NOT touch the `submit()` signature.
- Do NOT remove the screenshots-per-step logic.
- Do NOT introduce a new dependency. `yaml` is already in `requirements.txt`.

---

## Acceptance

- `python -c "from backend.agents.discovery.crawler_agent import CrawlerAgent; print('ok')"` → ok (no import errors)
- `python -c "import yaml; yaml.safe_load(open('backend/agents/discovery/sources.yaml'))"` → no exception, returns dict with keys `greenhouse, lever, ashby, workday`
- `python -c "import yaml; yaml.safe_load(open('backend/agents/application/ats_selectors.yaml'))"` → no exception, returns dict with keys `greenhouse, lever, ashby, workday, captcha_indicators`
- `grep -c 'NotImplementedError' backend/agents/discovery/crawler_agent.py` → 0
- `grep -ci 'stub\|phase 1b' backend/agents/discovery/crawler_agent.py` → 0
- `pytest tests/discovery/test_crawler_adapters.py tests/application/test_auto_apply_selectors.py -v` → all green
- `ruff check backend/` → clean

---

## How to run

```bash
cd /Users/spy/mfautomation/repos/creation-station/reverse-search

# Targeted re-cultivation. Already-shipped biomes are skipped.
mycelium cultivate \
  --only-biome discover-agent \
  --max-concurrency 2

mycelium cultivate \
  --only-biome apply-agent \
  --max-concurrency 2
```

Run them sequentially (not in parallel) since each does heavy file work in adjacent directories — fewer race conditions on the auto-commit step.
