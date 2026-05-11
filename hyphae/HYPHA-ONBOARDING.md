# HYPHA-ONBOARDING

> HYPHA tag: `TA/ONBOARD`

## Goal

Own the authenticated-user onboarding flow: resume PDF upload + text extraction, candidate profile + preferences capture, and the onboarding-status read endpoint. This is what gets a freshly-verified user from "just signed up" to "ready for Discovery."

## Scope

### In Scope
- `POST /onboarding/resume` — multipart PDF upload, PyMuPDF text extraction, candidate-record create-or-update
- `POST /onboarding/profile` — profile + preferences write to `candidates`, sets `users.is_onboarded=true`
- `GET /onboarding/status` — onboarding completeness check
- Linking `users.candidate_id` on first resume upload
- File-size guard (≤10 MB), MIME-type guard (`application/pdf` only)

### Out of Scope
- LinkedIn/GitHub OAuth-pull (URLs are typed manually for now)
- Skill/experience extraction from the resume (identity_profiler does that downstream)
- Multi-resume support (one resume per candidate; re-upload replaces)
- Avatar/photo uploads
- Email change / account recovery

## Inputs

- auth: `get_current_user` dependency, `User` model
- schema-core: `Candidate` ORM model
- `backend/database.py`: `get_db`
- `backend/config.py`: settings (none specific yet, but PII redaction policy)
- Library: `PyMuPDF` (imported as `fitz`)

## Outputs (Deliverables)

Existing files locked at HEAD:
- `backend/api/onboarding.py`

Contracts:
- `POST /api/v1/onboarding/resume` (multipart `file`) → `{ message, candidate_id, text_length, preview }`
- `POST /api/v1/onboarding/profile { name, linkedin_url?, github_url?, personal_context?, target_locations?, remote_preference="flexible", min_compensation?, excluded_companies?, excluded_industries? }` → `{ message, candidate_id, is_onboarded }`
- `GET /api/v1/onboarding/status` → `{ is_onboarded, has_resume, has_profile, candidate_id? }`

## Acceptance Criteria

- [ ] Uploading a valid PDF returns `200` and creates a `candidates` row with extracted `resume_text`
- [ ] Uploading a PDF for an existing candidate updates `resume_text` in place (no duplicate rows)
- [ ] `users.candidate_id` is set on first successful upload and persists
- [ ] Non-PDF MIME types return `422 "Only PDF files are accepted…"`
- [ ] Files over 10 MB return `422 "File too large. Max 10MB."`
- [ ] PDFs that yield empty extracted text return `422 "Could not extract any text from the PDF"`
- [ ] PyMuPDF exceptions other than `ValueError` produce a structured `500` and an `onboarding.pdf_extraction_failed` log line
- [ ] Resume preview is exactly first 500 characters (no smart truncation)
- [ ] `POST /profile` before any resume upload returns `400 "Please upload your resume first…"`
- [ ] `POST /profile` persists all optional fields (None-safe), sets `users.is_onboarded=true`, copies `payload.name` into `users.name`
- [ ] `GET /status` returns `has_resume=true` iff the candidate row has non-empty `resume_text`
- [ ] `GET /status` returns `has_profile = users.is_onboarded`
- [ ] All endpoints require Bearer JWT — unauthenticated requests get `401`
- [ ] Logged events: `onboarding.resume_uploaded`, `onboarding.profile_saved`, `onboarding.pdf_extraction_failed`
- [ ] PII (resume text contents, candidate email) is not echoed into structlog payloads at INFO level
- [ ] `ruff check backend/api/onboarding.py` clean

## Notes

- PyMuPDF is imported inside the extraction function (lazy) so the module loads even if `fitz` is unavailable at static-import time. Keep this pattern.
- The 10 MB ceiling matches typical resume max sizes; raising it requires a config setting and a justified leaf.
- The candidate's `name` is seeded from the user's email local-part if `User.name` is null at upload time — explicit `profile.name` overwrites it.
- `target_locations` and the exclusion arrays are Postgres `TEXT[]` — Pydantic must serialize lists, not comma-strings.
- Re-running `POST /profile` is idempotent on the candidate row but always re-sets `is_onboarded=true` (acceptable — there's no "un-onboard" flow).
- Frontend onboarding flow consumes these three endpoints in order: resume → profile → status check on every refresh.
