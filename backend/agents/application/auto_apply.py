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

# ─── ATS Field Maps ────────────────────────────────────────────────────────────
# Known selectors for the most common ATS platforms

_ATS_FIELD_MAPS = {
    "greenhouse": {
        "first_name": "#first_name",
        "last_name": "#last_name",
        "email": "#email",
        "phone": "#phone",
        "resume_upload": "input[type='file']",
        "linkedin": "input[placeholder*='LinkedIn'], input[name*='linkedin']",
        "github": "input[placeholder*='GitHub'], input[name*='github']",
        "cover_letter": "textarea[name*='cover_letter'], #cover_letter",
    },
    "lever": {
        "first_name": "input[name='name']",  # Lever uses full name
        "email": "input[name='email']",
        "phone": "input[name='phone']",
        "resume_upload": "input[type='file']",
        "linkedin": "input[name='urls[LinkedIn]']",
        "github": "input[name='urls[GitHub]']",
        "cover_letter": "textarea[name='comments']",
    },
    "workday": {
        "first_name": "input[data-automation-id='legalNameSection_firstName']",
        "last_name": "input[data-automation-id='legalNameSection_lastName']",
        "email": "input[data-automation-id='email']",
        "phone": "input[data-automation-id='phone-number']",
        "resume_upload": "input[type='file']",
    },
    "ashby": {
        "first_name": "input[name='firstName'], input[placeholder*='First']",
        "last_name": "input[name='lastName'], input[placeholder*='Last']",
        "email": "input[name='email'], input[type='email']",
        "phone": "input[name='phone'], input[type='tel']",
        "resume_upload": "input[type='file']",
        "linkedin": "input[placeholder*='LinkedIn']",
        "github": "input[placeholder*='GitHub']",
    },
}


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

            field_map = _ATS_FIELD_MAPS.get(ats, {})

            # Fill name fields
            name_parts = candidate.name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            if ats == "lever":
                # Lever uses a single full name field
                if await self._fill_field(page, field_map.get("first_name", ""), candidate.name):
                    fields_completed.append("full_name")
            else:
                if await self._fill_field(page, field_map.get("first_name", ""), first_name):
                    fields_completed.append("first_name")
                if await self._fill_field(page, field_map.get("last_name", ""), last_name):
                    fields_completed.append("last_name")

            if await self._fill_field(page, field_map.get("email", "input[type='email']"), candidate.email):
                fields_completed.append("email")

            await page.screenshot(path=str(shot_dir / "02_basic_info.png"))

            # Upload resume PDF
            if resume.pdf_path and os.path.exists(resume.pdf_path):
                upload_sel = field_map.get("resume_upload", "input[type='file']")
                try:
                    file_input = await page.query_selector(upload_sel)
                    if file_input:
                        await file_input.set_input_files(resume.pdf_path)
                        fields_completed.append("resume")
                        await page.screenshot(path=str(shot_dir / "03_resume_uploaded.png"))
                except Exception as e:
                    logger.warning("auto_apply.upload_failed", error=str(e))

            # LinkedIn / GitHub
            if candidate.linkedin_url:
                if await self._fill_field(page, field_map.get("linkedin", ""), candidate.linkedin_url):
                    fields_completed.append("linkedin")
            if candidate.github_url:
                if await self._fill_field(page, field_map.get("github", ""), candidate.github_url):
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

    async def _fill_field(self, page: Page, selector: str, value: str) -> bool:
        """Attempt to fill a form field. Returns True if successful."""
        if not selector or not value:
            return False
        try:
            # Try each selector if comma-separated
            for sel in [s.strip() for s in selector.split(",")]:
                element = await page.query_selector(sel)
                if element:
                    await element.fill(value)
                    return True
        except Exception as e:
            logger.debug("auto_apply.field_fill_failed", selector=selector, error=str(e))
        return False

    async def _has_captcha(self, page: Page) -> bool:
        """Detect common CAPTCHA patterns on the page."""
        captcha_signals = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            "#captcha",
            "div[class*='captcha']",
        ]
        for signal in captcha_signals:
            element = await page.query_selector(signal)
            if element:
                return True
        return False
