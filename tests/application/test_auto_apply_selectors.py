# Licensed under the Apache License, Version 2.0
"""
Unit tests for ats_selectors.yaml loading + the list-based selector handling
in auto_apply.py. No Playwright is launched here.
"""

from pathlib import Path

import pytest
import yaml

from backend.agents.application.auto_apply import (
    AutoApplyAgent,
    _load_selectors,
    _selectors_for,
)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SELECTORS_YAML = REPO_ROOT / "backend" / "agents" / "application" / "ats_selectors.yaml"


def test_yaml_file_exists():
    assert SELECTORS_YAML.exists(), f"missing {SELECTORS_YAML}"


def test_yaml_is_well_formed():
    with open(SELECTORS_YAML) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    # All four host keys present
    for host in ("greenhouse", "lever", "ashby", "workday"):
        assert host in data, f"missing host '{host}'"
        assert isinstance(data[host], dict)
    # Captcha indicators present and a list of strings
    assert "captcha_indicators" in data
    assert isinstance(data["captcha_indicators"], list)
    assert all(isinstance(s, str) for s in data["captcha_indicators"])


def test_every_field_value_is_list_of_strings():
    with open(SELECTORS_YAML) as f:
        data = yaml.safe_load(f)
    for host in ("greenhouse", "lever", "ashby", "workday"):
        for field, sels in data[host].items():
            assert isinstance(sels, list), f"{host}.{field} must be list, got {type(sels).__name__}"
            assert all(isinstance(s, str) for s in sels), f"{host}.{field} must be list[str]"
            assert sels, f"{host}.{field} must not be empty"


def test_load_selectors_returns_dict():
    sel = _load_selectors()
    assert isinstance(sel, dict)
    assert "greenhouse" in sel
    assert "captcha_indicators" in sel


def test_selectors_for_handles_list_format():
    field_map = {"email": ["input#email", "input[type='email']"]}
    assert _selectors_for(field_map, "email") == ["input#email", "input[type='email']"]


def test_selectors_for_handles_legacy_string_format():
    field_map = {"email": "input#email, input[type='email']"}
    assert _selectors_for(field_map, "email") == ["input#email", "input[type='email']"]


def test_selectors_for_missing_field_returns_empty():
    assert _selectors_for({}, "nonexistent") == []


def test_auto_apply_agent_initializes_with_selectors():
    """The engine must load the yaml at construction time."""
    agent = AutoApplyAgent(screenshot_dir="/tmp/test-shots")
    assert agent._selectors
    assert "greenhouse" in agent._selectors
    # Each host's selector list-of-lists must be queryable
    assert _selectors_for(agent._selectors["greenhouse"], "email")
    assert _selectors_for(agent._selectors["greenhouse"], "resume_file")


def test_known_greenhouse_selectors_match_brief():
    """Spot-check that the iter-3.5 brief's required selectors are present."""
    with open(SELECTORS_YAML) as f:
        data = yaml.safe_load(f)
    gh = data["greenhouse"]
    assert any("first_name" in s for s in gh["first_name"])
    assert any("job_application[email]" in s for s in gh["email"])
    assert any("submit" in s.lower() for s in gh["submit"])
