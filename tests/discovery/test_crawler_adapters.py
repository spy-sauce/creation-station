# Licensed under the Apache License, Version 2.0
"""
Unit tests for the real ATS adapters in crawler_agent.py.

These tests mock httpx via pytest-httpx so we never hit live boards in CI.
"""

import asyncio
import pytest
import httpx
from pytest_httpx import HTTPXMock

from backend.agents.discovery.crawler_agent import (
    AshbyAdapter,
    CrawlerAgent,
    GreenhouseAdapter,
    LeverAdapter,
    USER_AGENT,
    _RateLimitedClient,
    _strip_html,
    _title_matches,
)


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _client_factory() -> tuple[httpx.AsyncClient, _RateLimitedClient]:
    raw = httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=5.0)
    return raw, _RateLimitedClient(raw)


# ─── pure helpers ─────────────────────────────────────────────────────────────


def test_title_matches_substring_and_case_insensitive():
    assert _title_matches("Senior AI Engineer", ["ai engineer"])
    assert _title_matches("Senior AI Engineer", ["Engineer"])
    assert not _title_matches("Marketing Coordinator", ["ai engineer"])


def test_title_matches_empty_filter_passes_everything():
    assert _title_matches("Anything", [])


def test_strip_html_removes_tags_and_unescapes_entities():
    raw = "<p>Hello &amp; <strong>world</strong></p>"
    out = _strip_html(raw)
    assert "Hello" in out
    assert "world" in out
    assert "<" not in out
    assert "&amp;" not in out


def test_url_hash_is_deterministic_and_case_insensitive():
    a = CrawlerAgent.url_hash("https://Example.com/A")
    b = CrawlerAgent.url_hash("https://example.com/a")
    assert a == b
    assert len(a) == 64  # sha256 hex


# ─── adapter: Greenhouse ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_greenhouse_adapter_parses_real_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://boards.greenhouse.io/anthropic.json",
        json={
            "jobs": [
                {
                    "id": 4001,
                    "title": "Staff AI Engineer · Agent Systems",
                    "location": {"name": "Remote (US)"},
                    "absolute_url": "https://boards.greenhouse.io/anthropic/jobs/4001",
                    "updated_at": "2026-05-15T10:00:00Z",
                    "content": "<p>Build agent <strong>orchestration</strong> &amp; tooling.</p>",
                },
                {
                    "id": 4002,
                    "title": "Sales Manager",
                    "location": {"name": "NYC"},
                    "absolute_url": "https://boards.greenhouse.io/anthropic/jobs/4002",
                    "updated_at": "2026-05-15T10:00:00Z",
                    "content": "Sales role.",
                },
            ]
        },
    )

    raw, client = await _client_factory()
    try:
        rows = await GreenhouseAdapter().fetch(client, ["anthropic"], ["ai engineer"])
    finally:
        await raw.aclose()

    assert len(rows) == 1
    job = rows[0]
    assert job["source"] == "greenhouse"
    assert job["title"] == "Staff AI Engineer · Agent Systems"
    assert job["url"] == "https://boards.greenhouse.io/anthropic/jobs/4001"
    assert "orchestration" in job["description"]
    assert "<" not in job["description"]


@pytest.mark.asyncio
async def test_greenhouse_adapter_skips_failed_slug(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://boards.greenhouse.io/ok.json", json={"jobs": []})
    httpx_mock.add_response(url="https://boards.greenhouse.io/bad.json", status_code=500)

    raw, client = await _client_factory()
    try:
        rows = await GreenhouseAdapter().fetch(client, ["ok", "bad"], [])
    finally:
        await raw.aclose()

    assert rows == []  # neither slug yields rows but no exception bubbles up


# ─── adapter: Lever ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lever_adapter_parses_real_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lever.co/v0/postings/vercel?mode=json",
        json=[
            {
                "id": "abc-123",
                "text": "Principal Engineer · Platform",
                "categories": {"location": "Remote · Americas", "team": "Platform"},
                "descriptionPlain": "Edge compute engineering.",
                "hostedUrl": "https://jobs.lever.co/vercel/abc-123",
                "createdAt": 1715000000000,
            },
            {
                "id": "abc-124",
                "text": "Recruiter",
                "categories": {"location": "NYC"},
                "descriptionPlain": "Recruiting role.",
                "hostedUrl": "https://jobs.lever.co/vercel/abc-124",
                "createdAt": 1715000000000,
            },
        ],
    )

    raw, client = await _client_factory()
    try:
        rows = await LeverAdapter().fetch(client, ["vercel"], ["engineer"])
    finally:
        await raw.aclose()

    assert len(rows) == 1
    assert rows[0]["source"] == "lever"
    assert rows[0]["title"] == "Principal Engineer · Platform"
    assert rows[0]["url"] == "https://jobs.lever.co/vercel/abc-123"
    assert rows[0]["posted_at"] is not None  # ms timestamp converted


# ─── adapter: Ashby ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ashby_adapter_parses_real_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.ashbyhq.com/posting-api/job-board/clay",
        json={
            "jobs": [
                {
                    "id": "ash-77",
                    "title": "Senior Backend Engineer",
                    "location": "Remote",
                    "descriptionPlain": "Backend at Clay.",
                    "jobUrl": "https://jobs.ashbyhq.com/clay/ash-77",
                    "publishedDate": "2026-05-10T00:00:00Z",
                    "compensation": {
                        "compensationTierSummary": {"minValue": 180000, "maxValue": 240000},
                    },
                },
            ]
        },
    )

    raw, client = await _client_factory()
    try:
        rows = await AshbyAdapter().fetch(client, ["clay"], ["backend"])
    finally:
        await raw.aclose()

    assert len(rows) == 1
    job = rows[0]
    assert job["source"] == "ashby"
    assert job["salary_min"] == 180000
    assert job["salary_max"] == 240000


# ─── CrawlerAgent.run integration ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crawler_agent_run_dedupes_by_url(httpx_mock: HTTPXMock, monkeypatch, tmp_path):
    # Point SOURCES_YAML at a tiny test roster
    test_sources = tmp_path / "sources.yaml"
    test_sources.write_text(
        "greenhouse: [acme]\n"
        "lever: [acme]\n"
        "ashby: []\n"
    )
    from backend.agents.discovery import crawler_agent as ca
    monkeypatch.setattr(ca, "SOURCES_YAML", test_sources)

    # Two adapters return the SAME url → dedup down to 1
    dup_url = "https://example.com/jobs/777"
    httpx_mock.add_response(
        url="https://boards.greenhouse.io/acme.json",
        json={"jobs": [{
            "id": 777, "title": "Senior Engineer",
            "location": {"name": "Remote"},
            "absolute_url": dup_url,
            "updated_at": "2026-05-15T10:00:00Z",
            "content": "<p>Build.</p>",
        }]},
    )
    httpx_mock.add_response(
        url="https://api.lever.co/v0/postings/acme?mode=json",
        json=[{
            "id": "lev-777", "text": "Senior Engineer",
            "categories": {"location": "Remote"},
            "descriptionPlain": "Build.",
            "hostedUrl": dup_url,
            "createdAt": 1715000000000,
        }],
    )

    from backend.agents.discovery.schemas import SearchManifestSchema
    from uuid import uuid4

    manifest = SearchManifestSchema(
        target_titles=["engineer"],
        keywords=[],
        excluded_companies=[],
        excluded_industries=[],
    )
    agent = ca.CrawlerAgent(uuid4())
    rows = await agent.run(manifest)

    assert len(rows) == 1  # deduped
    assert str(rows[0].url) == dup_url
