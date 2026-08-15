"""GitHub repo research and install service.

Research: paste a GitHub URL → fetch metadata + README → produce a structured
report (summary, benefits, cons, install method) using heuristic extraction,
enriched by the LLM when one is reachable.
Install: clone into ~/.jarvis/installed and run a whitelisted install command.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

INSTALL_DIR = Path.home() / ".jarvis" / "installed"
STATE_FILE = Path.home() / ".jarvis" / "research_state.json"

REPO_URL_RE = re.compile(r"^https?://(?:www\.)?github\.com/([^/\s]+)/([^/#?\s]+)", re.IGNORECASE)

_LANG_MANIFESTS = {
    "python": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"],
    "node": ["package.json"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "ruby": ["Gemfile"],
    "php": ["composer.json"],
    "docker": ["Dockerfile", "docker-compose.yml"],
}

_DOMAIN_KEYWORDS = {
    "voice": ["voice", "tts", "stt", "speech", "whisper", "audio", "mic"],
    "calendar": ["calendar", "schedule", "event", "reminder"],
    "email": ["email", "gmail", "mail", "outbox"],
    "memory": ["memory", "embedding", "vector", "recall", "knowledge", "rag"],
    "research": ["research", "search", "crawl", "scrape", "retrieval", "llm"],
    "ui": ["ui", "widget", "terminal", "dashboard", "desktop", "app"],
    "agents": ["agent", "autonomous", "orchestrat", "workflow", "tool", "mcp"],
    "system": ["monitor", "automation", "shortcut", "keyboard", "clipboard", "file"],
}

_POSITIVE_HINTS = re.compile(
    r"feature|support|integrat|fast|lightweight|easy|simple|private|local|offline|"
    r"open.?source|free|api|cli|gui|cross.?platform|secure|extensible|plugin",
    re.IGNORECASE,
)

_NEGATIVE_HINTS = re.compile(
    r"heavy|gpu|large.?download|requires|api.?key|beta|experimental|deprecated|"
    r"not.?maintained|commercial|proprietary|paid|subscription",
    re.IGNORECASE,
)

_GITHUB_API = "https://api.github.com/repos"
_RAW_BASE = "https://raw.githubusercontent.com"


def parse_repo_url(url: str) -> tuple[str, str] | None:
    """Return (owner, repo) for a GitHub URL, or None if not a GitHub repo."""
    match = REPO_URL_RE.match(url.strip())
    if not match:
        return None
    return match.group(1), match.group(2).removesuffix(".git")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (ValueError, OSError):
            pass
    return {"repos": {}}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def history() -> list[dict]:
    state = _load_state()
    repos = []
    for key, info in state["repos"].items():
        entry = dict(info)
        entry["key"] = key
        repos.append(entry)
    return sorted(repos, key=lambda r: r.get("added", 0), reverse=True)


def _fetch_repo_info(owner: str, repo: str) -> dict | None:
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        try:
            meta = client.get(f"{_GITHUB_API}/{owner}/{repo}").json()
        except httpx.HTTPError:
            return None
        if "full_name" not in meta:
            return None

        default_branch = meta.get("default_branch", "main")
        readme_text = ""
        for candidate in ("README.md", "readme.md", "README.rst", "Readme.md"):
            try:
                resp = client.get(f"{_RAW_BASE}/{owner}/{repo}/{default_branch}/{candidate}")
                if resp.status_code == 200 and len(resp.text) > 40:
                    readme_text = resp.text
                    break
            except httpx.HTTPError:
                continue

        files = _fetch_file_list(client, owner, repo, default_branch)

    return {
        "full_name": meta.get("full_name"),
        "description": meta.get("description") or "",
        "language": meta.get("language"),
        "stars": meta.get("stargazers_count", 0),
        "forks": meta.get("forks_count", 0),
        "open_issues": meta.get("open_issues_count", 0),
        "license": (meta.get("license") or {}).get("spdx_id"),
        "updated_at": meta.get("updated_at"),
        "pushed_at": meta.get("pushed_at"),
        "topics": meta.get("topics", []),
        "homepage": meta.get("homepage"),
        "default_branch": default_branch,
        "readme": readme_text,
        "files": files,
    }


def _fetch_file_list(client: httpx.Client, owner: str, repo: str, branch: str) -> list[str]:
    try:
        tree = client.get(
            f"{_GITHUB_API}/git/trees/{owner}/{repo}/{branch}?recursive=0"
        ).json()
    except httpx.HTTPError:
        return []
    return [item["path"] for item in tree.get("tree", []) if item.get("type") == "blob"]


_LANGUAGE_ALIASES = {
    "javascript": "node",
    "typescript": "node",
    "js": "node",
    "ts": "node",
}


def _detect_language(files: list[str], language: str | None) -> str:
    if files:
        for lang, manifests in _LANG_MANIFESTS.items():
            for manifest in manifests:
                if manifest in files or any(f.endswith("/" + manifest) for f in files):
                    return lang
    if language:
        language = language.lower()
        if language in _LANGUAGE_ALIASES:
            return _LANGUAGE_ALIASES[language]
        for lang, manifests in _LANG_MANIFESTS.items():
            if lang in language:
                return lang
    return "unknown"


def _flatten_line(line: str) -> str:
    line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
    return re.sub(r"<[^>]+>", " ", line).strip()


def _readme_summary(readme: str, limit: int = 3) -> str:
    import html

    text = re.sub(r"```.*?```", " ", readme, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[#>*`\[\]()!-]", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    picked = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 25:
            continue
        if re.search(r"(install|clone|pip install|npm install|license|contribute)", sentence, re.I):
            continue
        picked.append(sentence)
        if len(picked) >= limit:
            break
    return " ".join(picked)[:600]


def _match_domains(text: str) -> list[str]:
    hits = []
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(keyword in text.lower() for keyword in keywords):
            hits.append(domain)
    return hits


def _extract_benefits(text: str, language: str) -> list[str]:
    benefits = []
    for match in re.finditer(r"(?:^|\n)\s*[-*•]\s+(.+)", text):
        line = _flatten_line(match.group(1))
        if (
            15 < len(line) < 180
            and _POSITIVE_HINTS.search(line)
            and not _NEGATIVE_HINTS.search(line)
        ):
            benefits.append(line.rstrip())
        if len(benefits) >= 8:
            break
    if not benefits:
        first_para = _readme_summary(text, limit=1)
        if first_para:
            benefits.append(first_para)
    if language == "python":
        benefits.append("Python package — installs into JARVIS's own environment")
    return benefits[:8]


def _extract_cons(text: str, language: str, stars: int, license_id: str | None) -> list[str]:
    cons = []
    if language == "docker":
        cons.append(
            "Runs in Docker — requires a container runtime, not installed into JARVIS directly"
        )
    for match in re.finditer(r"(?:^|\n)\s*[-*•]\s+(.+)", text):
        line = _flatten_line(match.group(1))
        if 15 < len(line) < 180 and _NEGATIVE_HINTS.search(line):
            cons.append(line.rstrip())
        if len(cons) >= 5:
            break
    if stars < 50:
        cons.append("Low traction — fewer than 50 stars; expect rough edges")
    if license_id in ("AGPL-3.0", "AGPL-3.0-only", "SSPL-1.0"):
        cons.append("Copyleft license (AGPL/SSPL) — may impose obligations if redistributed")
    if not cons:
        cons.append("Heuristic scan found no obvious drawbacks — verify before relying on it")
    return cons[:6]


def _install_method(language: str, files: list[str]) -> dict:
    if language == "python":
        return {
            "method": "pip",
            "command_hint": "clone + pip install -e .",
            "requirements": ["git"],
        }
    if language == "node":
        return {
            "method": "npm",
            "command_hint": "clone + npm install",
            "requirements": ["git", "node"],
        }
    if language == "docker":
        return {"method": "docker", "command_hint": "docker compose up", "requirements": ["docker"]}
    if language in ("go", "rust", "ruby", "php"):
        return {
            "method": "clone",
            "command_hint": f"clone only — build with {language} toolchain",
            "requirements": ["git", language],
        }
    return {
        "method": "clone",
        "command_hint": "clone only — no recognized build manifest",
        "requirements": ["git"],
    }


def _risk_verdict(
    license_id: str | None,
    pushed_at: str | None,
    stars: int,
    cons: list[str],
    install_method: str,
) -> dict:
    """Estimate install risk from licensing, maintenance, traction and cons."""
    factors = []
    if license_id in ("AGPL-3.0", "AGPL-3.0-only", "SSPL-1.0"):
        factors.append("copyleft license (AGPL/SSPL)")
    try:
        if pushed_at:
            pushed = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            days = (datetime.now(UTC) - pushed).days
            if days > 180:
                factors.append(f"no commits in {days} days")
    except ValueError:
        factors.append("last activity unknown")
    if stars < 50:
        factors.append("low traction (<50 stars)")
    con_text = " ".join(cons).lower()
    if "gpu" in con_text or "subscription" in con_text or "api key" in con_text:
        factors.append("heavy or paid dependency")
    if install_method == "pip":
        pass
    elif install_method == "clone":
        factors.append("not auto-installable — clone only")
    else:
        factors.append(f"installs via {install_method}, not into JARVIS directly")

    level = "low" if not factors else ("moderate" if len(factors) < 3 else "high")
    return {"level": level, "factors": factors}


def _analyze_with_llm(repo: dict) -> dict | None:
    try:
        import jarvis.web.main as web_main

        llm = getattr(web_main.jarvis, "_llm", None)
        if llm is None or not llm.is_available():
            return None
        messages = [
            {
                "role": "user",
                "content": (
                    f"Analyze this GitHub repo for a personal desktop assistant. "
                    f"Name: {repo['full_name']}. Description: {repo['description']}. "
                    f"Language: {repo.get('language')}. Stars: {repo['stars']}. "
                    f"README excerpt: {repo['readme'][:2000]}. "
                    "Return JSON only: {\"summary\": str, \"benefits\": [str], \"cons\": [str]} — "
                    "benefits = what this tool could add to a JARVIS assistant, "
                    "cons = drawbacks, integration effort, licensing, maintenance risk."
                ),
            }
        ]
        data = llm.chat_json(messages)
        if isinstance(data, dict) and ("benefits" in data or "summary" in data):
            return data
    except Exception:
        return None
    return None


def research(url: str) -> dict:
    """Investigate a GitHub URL and return a structured report."""
    parsed = parse_repo_url(url)
    if parsed is None:
        return {"ok": False, "error": "Not a valid GitHub repository URL"}
    owner, repo_name = parsed

    info = _fetch_repo_info(owner, repo_name)
    if info is None:
        return {"ok": False, "error": f"Could not fetch {owner}/{repo_name} — check the URL"}

    files = info["files"]
    language = _detect_language(files, info["language"])
    info["detected_language"] = language

    llm_report = _analyze_with_llm(info)
    if llm_report:
        summary = llm_report.get("summary", "")
        benefits = llm_report.get("benefits", [])
        cons = llm_report.get("cons", [])
        source = "llm"
    else:
        all_text = f"{info['readme']} {info['description']}"
        summary = _readme_summary(info["readme"])
        benefits = _extract_benefits(all_text, language)
        cons = _extract_cons(all_text, language, info["stars"], info["license"])
        source = "heuristic"

    report = {
        "ok": True,
        "source": source,
        "repo": {
            "full_name": info["full_name"],
            "description": info["description"],
            "language": info["detected_language"],
            "stars": info["stars"],
            "license": info["license"],
            "pushed_at": info["pushed_at"],
            "topics": info["topics"],
            "url": url.rstrip("/"),
        },
        "summary": summary,
        "benefits": benefits,
        "cons": cons,
        "applies_to": _match_domains(f"{info['readme']} {info['description']}"),
        "install": _install_method(language, files),
    }
    report["verdict"] = _risk_verdict(
        report["repo"]["license"],
        report["repo"]["pushed_at"],
        report["repo"]["stars"],
        cons,
        report["install"]["method"],
    )

    state = _load_state()
    key = f"{owner}__{repo_name}"
    state["repos"][key] = {
        "url": report["repo"]["url"],
        "full_name": info["full_name"],
        "added": time.time(),
        "status": "researched",
        "install": report["install"],
        "verdict": report["verdict"],
        "summary": summary,
        "benefits": benefits,
        "cons": cons,
    }
    _save_state(state)
    return report


def install(url: str) -> dict:
    """Install a previously researched repo by cloning it into INSTALL_DIR."""
    parsed = parse_repo_url(url)
    if parsed is None:
        return {"ok": False, "error": "Not a valid GitHub repository URL"}
    owner, repo_name = parsed
    key = f"{owner}__{repo_name}"

    state = _load_state()
    entry = state["repos"].get(key)
    if entry is None:
        return {"ok": False, "error": "Research this repo first — no install plan exists"}
    if entry.get("status") == "installed":
        return {"ok": False, "error": "Already installed", "target": entry.get("target")}

    method = entry["install"].get("method", "clone")
    target = INSTALL_DIR / key

    try:
        clone = subprocess.run(
            ["git", "clone", "--depth", "1", entry["url"], str(target)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if clone.returncode != 0:
            return {"ok": False, "error": f"git clone failed: {clone.stderr.strip()[-300:]}"}

        if method == "pip":
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(target)],
                capture_output=True,
                text=True,
                timeout=420,
            )
            log = (result.stdout or "")[-600:] + (result.stderr or "")[-600:]
            if result.returncode != 0:
                return {
                    "ok": False,
                    "error": f"pip install failed: {log[-400:]}",
                    "target": str(target),
                }
            status, detail = "installed", "pip editable install complete"
        elif method == "npm":
            npm = subprocess.run(
                ["npm", "install"], cwd=target, capture_output=True, text=True, timeout=420
            )
            log = (npm.stdout or "")[-600:] + (npm.stderr or "")[-600:]
            if npm.returncode != 0:
                return {
                    "ok": False,
                    "error": f"npm install failed: {log[-400:]}",
                    "target": str(target),
                }
            status, detail = "installed", "npm install complete"
        else:
            status, detail = "cloned", f"cloned to {target} — no auto-build for {method}"

        entry["status"] = status
        entry["target"] = str(target)
        entry["detail"] = detail
        entry["installed_at"] = time.time()
        _save_state(state)
        return {"ok": True, "status": status, "detail": detail, "target": str(target)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Install timed out"}
    except OSError as exc:
        return {"ok": False, "error": f"Install failed: {exc}"}


def _editable_dist_name(target: str) -> str | None:
    try:
        import importlib.metadata as md
        from urllib.parse import urlparse

        resolved = str(Path(target).resolve())
        for dist in md.distributions():
            direct_url = dist.read_text("direct_url.json")
            if not direct_url:
                continue
            try:
                parsed = urlparse(json.loads(direct_url).get("url", ""))
            except ValueError:
                continue
            if parsed.scheme == "file" and Path(parsed.path).resolve().as_posix() == Path(
                resolved
            ).as_posix():
                return dist.metadata["Name"]
    except Exception:
        return None
    return None


def uninstall(url: str) -> dict:
    """Remove an installed repo: pip uninstall when pip-installed, else drop the clone."""
    parsed = parse_repo_url(url)
    if parsed is None:
        return {"ok": False, "error": "Not a valid GitHub repository URL"}
    owner, repo_name = parsed
    key = f"{owner}__{repo_name}"

    state = _load_state()
    entry = state["repos"].get(key)
    if entry is None:
        return {"ok": False, "error": "No record of this repo"}
    status = entry.get("status")
    target = entry.get("target")
    if status == "researched":
        state["repos"].pop(key, None)
        _save_state(state)
        return {"ok": True, "status": "removed", "detail": "Research record removed"}

    if status == "installed" and entry.get("install", {}).get("method") == "pip" and target:
        dist_name = _editable_dist_name(target)
        if dist_name:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", dist_name],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                return {
                    "ok": False,
                    "error": f"pip uninstall failed: {result.stderr.strip()[-300:]}",
                }
        import shutil

        shutil.rmtree(target, ignore_errors=True)
        entry["status"] = "researched"
        entry.pop("target", None)
        entry.pop("installed_at", None)
        _save_state(state)
        return {"ok": True, "status": "researched", "detail": "Uninstalled — repo removed"}

    if target:
        import shutil

        shutil.rmtree(target, ignore_errors=True)
    state["repos"].pop(key, None)
    _save_state(state)
    return {"ok": True, "status": "removed", "detail": "Clone removed"}
