# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Auto-Apply Agent — navigates career pages and submits application forms via Playwright.

NEVER submits without explicit Review Dashboard approval.
Handles known ATS systems (Greenhouse, Lever, Workday, Ashby) with field maps.
Unknown ATSs: AI-guided DOM inspection.

CAPTCHA detection → marks as REQUIRES_MANUAL and surfaces to dashboard.
Screenshots every major step for audit trail.
"""

import asyncio
import os
import re
from pathlib import Path
from uuid import UUID

import structlog
from playwright.async_api import async_playwright, Page, Browser

from backend.agents.application.schemas import (
    ApplicationResultSchema,
    TailoredResumeSchema,
)
from backend.agents.discovery.schemas import CandidateSchema

logger = structlog.get_logger(__name__)

# ─── ATS Selectors — loaded from ats_selectors.yaml ────────────────────────────

_SELECTORS_YAML = Path(__file__).parent / "ats_selectors.yaml"


def _load_selectors() -> dict:
    """Load ats_selectors.yaml. Returns empty dict if missing (engine falls back to query-by-attribute)."""
    try:
        import yaml
        with open(_SELECTORS_YAML) as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception as exc:
        logger.warning("auto_apply.selectors_load_failed", error=str(exc))
        return {}


def _selectors_for(field_map: dict, field: str) -> list[str]:
    """Return list of selectors for a field. Accepts either str (legacy) or list[str]."""
    raw = field_map.get(field)
    if raw is None:
        return []
    if isinstance(raw, str):
        return [s.strip() for s in raw.split(",") if s.strip()]
    if isinstance(raw, list):
        return [str(s) for s in raw]
    return []


def _detect_ats(url: str) -> str:
    """Detect ATS type from URL pattern."""
    url_lower = url.lower()
    if "greenhouse.io" in url_lower or "boards.greenhouse.io" in url_lower:
        return "greenhouse"
    if "lever.co" in url_lower or "jobs.lever.co" in url_lower:
        return "lever"
    if "myworkdayjobs.com" in url_lower or "workday.com" in url_lower:
        return "workday"
    if "jobs.ashby.io" in url_lower or "ashbyhq.com" in url_lower:
        return "ashby"
    return "unknown"


class AutoApplyAgent:
    """
    Submits application forms via Playwright.

    CRITICAL: Only call submit() after receiving explicit APPROVED status from the pipeline.
    This agent runs headless in production.
    """

    def __init__(self, screenshot_dir: str = "./screenshots"):
        self._screenshot_dir = Path(screenshot_dir)
        self._selectors = _load_selectors()

    async def submit(
        self,
        job_url: str,
        job_id: UUID,
        pipeline_id: UUID,
        candidate: CandidateSchema,
        resume: TailoredResumeSchema,
    ) -> ApplicationResultSchema:
        """
        Submit an application form. Only called after Review Dashboard approval.

        Args:
            job_url: The job posting URL
            job_id: Job ID for tracking
            pipeline_id: Pipeline ID for tracking
            candidate: Candidate profile with contact details
            resume: Tailored resume with PDF path

        Returns:
            ApplicationResultSchema with outcome
        """
        log = logger.bind(job_id=str(job_id), url=job_url)
        shot_dir = self._screenshot_dir / str(job_id)
        shot_dir.mkdir(parents=True, exist_ok=True)

        ats = _detect_ats(job_url)
        log.info("auto_apply.starting", ats=ats)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                result = await self._navigate_and_fill(
                    browser, job_url, job_id, pipeline_id,
                    candidate, resume, ats, shot_dir
                )
                return result
            except Exception as e:
                log.error("auto_apply.failed", error=str(e))
                return ApplicationResultSchema(
                    pipeline_id=pipeline_id,
                    job_id=job_id,
                    status="FAILED",
                    error=str(e),
                    fallback_url=job_url,
                )
            finally:
                await browser.close()

    async def _navigate_and_fill(
        self,
        browser: Browser,
        url: str,
        job_id: UUID,
        pipeline_id: UUID,
        candidate: CandidateSchema,
        resume: TailoredResumeSchema,
        ats: str,
        shot_dir: Path,
    ) -> ApplicationResultSchema:
        """Navigate to the application form and fill it out."""
        page = await browser.new_page()
        fields_completed: list[str] = []

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.screenshot(path=str(shot_dir / "01_loaded.png"))

            # CAPTCHA detection
            if await self._has_captcha(page):
                logger.warning("auto_apply.captcha_detected", url=url)
                await page.screenshot(path=str(shot_dir / "captcha.png"))
                return ApplicationResultSchema(
                    pipeline_id=pipeline_id,
                    job_id=job_id,
                    status="REQUIRES_MANUAL",
                    screenshot_path=str(shot_dir / "captcha.png"),
                    error="CAPTCHA detected — requires manual submission",
                    fallback_url=url,
                )

            field_map = self._selectors.get(ats, {})

            # Fill name fields
            name_parts = candidate.name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            if ats in ("lever", "ashby"):
                # Lever/Ashby use a single 'name' field
                name_sels = _selectors_for(field_map, "name") or _selectors_for(field_map, "first_name")
                if await self._fill_field(page, name_sels, candidate.name):
                    fields_completed.append("full_name")
            else:
                if await self._fill_field(page, _selectors_for(field_map, "first_name"), first_name):
                    fields_completed.append("first_name")
                if await self._fill_field(page, _selectors_for(field_map, "last_name"), last_name):
                    fields_completed.append("last_name")

            email_sels = _selectors_for(field_map, "email") or ["input[type='email']"]
            if await self._fill_field(page, email_sels, candidate.email):
                fields_completed.append("email")

            await page.screenshot(path=str(shot_dir / "02_basic_info.png"))

            # Upload resume PDF
            if resume.pdf_path and os.path.exists(resume.pdf_path):
                upload_sels = (
                    _selectors_for(field_map, "resume_file")
                    or _selectors_for(field_map, "resume_upload")
                    or ["input[type='file']"]
                )
                for upload_sel in upload_sels:
                    try:
                        file_input = await page.query_selector(upload_sel)
                        if file_input:
                            await file_input.set_input_files(resume.pdf_path)
                            fields_completed.append("resume")
                            await page.screenshot(path=str(shot_dir / "03_resume_uploaded.png"))
                            break
                    except Exception as e:
                        logger.debug("auto_apply.upload_attempt_failed", selector=upload_sel, error=str(e))

            # LinkedIn / GitHub
            if candidate.linkedin_url:
                if await self._fill_field(page, _selectors_for(field_map, "linkedin"), candidate.linkedin_url):
                    fields_completed.append("linkedin")
            if candidate.github_url:
                if await self._fill_field(page, _selectors_for(field_map, "github"), candidate.github_url):
                    fields_completed.append("github")

            await page.screenshot(path=str(shot_dir / "04_filled.png"))

            logger.info(
                "auto_apply.form_filled",
                fields=fields_completed,
                ats=ats,
            )

            # NOTE: We do NOT submit here — the form is filled and staged.
            # The Review Dashboard confirms fields were filled correctly.
            # Actual submission happens only after a second explicit human approval.
            return ApplicationResultSchema(
                pipeline_id=pipeline_id,
                job_id=job_id,
                status="REQUIRES_MANUAL",  # Human clicks submit after reviewing filled form
                screenshot_path=str(shot_dir / "04_filled.png"),
                fields_completed=fields_completed,
                fallback_url=url,
            )

        finally:
            await page.close()

    async def _fill_field(self, page: Page, selectors, value: str) -> bool:
        """
        Attempt to fill a form field. `selectors` is a list of CSS selectors
        tried in order; first match wins. Accepts a single string for
        backwards compatibility (will be split on comma).
        """
        if not value:
            return False
        if isinstance(selectors, str):
            selectors = [s.strip() for s in selectors.split(",") if s.strip()]
        if not selectors:
            return False
        for sel in selectors:
            try:
                element = await page.query_selector(sel)
                if element:
                    await element.fill(value)
                    return True
            except Exception as e:
                logger.debug("auto_apply.field_fill_failed", selector=sel, error=str(e))
        return False

    async def _has_captcha(self, page: Page) -> bool:
        """Detect CAPTCHA via patterns from ats_selectors.yaml."""
        indicators = self._selectors.get("captcha_indicators") or [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            "#captcha",
            "div[class*='captcha']",
        ]
        for signal in indicators:
            try:
                element = await page.query_selector(signal)
                if element:
                    return True
            except Exception:
                continue
        return False
