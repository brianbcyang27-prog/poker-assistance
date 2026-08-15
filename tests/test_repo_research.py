"""Tests for the GitHub repo research/install service (pure functions only)."""

from jarvis.web.services.repo_research import (
    _detect_language,
    _extract_benefits,
    _extract_cons,
    _install_method,
    _match_domains,
    _readme_summary,
    _risk_verdict,
    parse_repo_url,
)

SAMPLE_README = """
# FastNotes

A super fast, lightweight note-taking CLI with full-text search and offline sync.

## Features
- Lightning-fast fuzzy search over thousands of notes
- Private by design — everything stays local on your machine
- Cross-platform: macOS, Linux, Windows
- Easy plugin system for extending commands
- Optional cloud sync via a free API

## Requirements
- Python 3.10+
- Requires an API key for cloud sync
- Experimental sync feature is not yet stable

## Installation
pip install fastnotes
"""


def test_parse_repo_url_valid():
    assert parse_repo_url("https://github.com/owner/repo") == ("owner", "repo")
    assert parse_repo_url("https://github.com/owner/repo/") == ("owner", "repo")
    assert parse_repo_url("https://github.com/owner/repo.git") == ("owner", "repo")
    assert parse_repo_url("https://github.com/owner/repo/tree/main") == ("owner", "repo")


def test_parse_repo_url_invalid():
    assert parse_repo_url("https://gitlab.com/owner/repo") is None
    assert parse_repo_url("https://example.com/not-github") is None
    assert parse_repo_url("") is None


def test_detect_language_by_manifest():
    assert _detect_language(["pyproject.toml", "src/main.py"], None) == "python"
    assert _detect_language(["package.json", "index.js"], None) == "node"
    assert _detect_language(["go.mod", "main.go"], None) == "go"
    assert _detect_language(["Cargo.toml"], None) == "rust"
    assert _detect_language(["Dockerfile"], None) == "docker"


def test_detect_language_falls_back_to_meta():
    assert _detect_language([], "Python") == "python"
    assert _detect_language([], "JavaScript") == "node"
    assert _detect_language([], None) == "unknown"


def test_readme_summary_skips_install_and_short_lines():
    summary = _readme_summary(SAMPLE_README)
    assert summary
    assert "FastNotes" in summary
    assert "install" not in summary.lower()


def test_extract_benefits_picks_feature_bullets():
    benefits = _extract_benefits(SAMPLE_README, "python")
    assert any("fuzzy search" in b.lower() for b in benefits)
    assert any("local" in b.lower() for b in benefits)
    assert not any("API key" in b for b in benefits)


def test_extract_benefits_empty_readme_appends_fallback():
    benefits = _extract_benefits("just some words with no bullets", "python")
    assert any("Python package" in b for b in benefits)


def test_extract_cons_flags_requirements_and_experimental():
    cons = _extract_cons(SAMPLE_README, "python", stars=500, license_id="MIT")
    assert any("API key" in c for c in cons)
    assert any("experimental" in c.lower() for c in cons)


def test_extract_cons_flags_low_traction():
    cons = _extract_cons(SAMPLE_README, "python", stars=5, license_id="MIT")
    assert any("stars" in c for c in cons)


def test_extract_cons_flags_copyleft_license():
    cons = _extract_cons(SAMPLE_README, "python", stars=500, license_id="AGPL-3.0")
    assert any("copyleft" in c.lower() for c in cons)


def test_match_domains():
    domains = _match_domains("voice assistant with memory and research tools")
    assert "voice" in domains
    assert "memory" in domains
    assert "research" in domains


def test_install_method_by_language():
    assert _install_method("python", [])["method"] == "pip"
    assert _install_method("node", [])["method"] == "npm"
    assert _install_method("docker", [])["method"] == "docker"
    assert _install_method("go", [])["method"] == "clone"
    assert _install_method("unknown", [])["method"] == "clone"


def test_risk_verdict_low_for_healthy_repo():
    verdict = _risk_verdict("MIT", "2026-07-01T00:00:00Z", 500, [], "pip")
    assert verdict["level"] == "low"


def test_risk_verdict_moderate_for_stale_repo():
    verdict = _risk_verdict("MIT", "2020-01-01T00:00:00Z", 500, [], "pip")
    assert verdict["level"] == "moderate"
    assert any("no commits" in f for f in verdict["factors"])


def test_risk_verdict_high_for_copyleft_low_traction_clone():
    verdict = _risk_verdict(
        "AGPL-3.0", "2020-01-01T00:00:00Z", 10, ["Requires an API key"], "clone"
    )
    assert verdict["level"] == "high"
    assert any("copyleft" in f for f in verdict["factors"])
    assert any("low traction" in f for f in verdict["factors"])
