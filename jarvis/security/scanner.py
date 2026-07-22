"""Repository secret scanner.

Detects hardcoded secrets in source code and generates security_report.md.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_SECRET_PATTERNS = [
    ("NVIDIA API Key", r"nvapi-[A-Za-z0-9\-_]{20,}", "critical"),
    ("OpenAI API Key", r"sk-[A-Za-z0-9]{20,}", "critical"),
    ("Anthropic API Key", r"sk-ant-[A-Za-z0-9\-_]{20,}", "critical"),
    ("GitHub Token", r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9\-_]{20,}", "critical"),
    ("AWS Access Key", r"AKIA[0-9A-Z]{16}", "critical"),
    ("AWS Secret Key", r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}", "critical"),
    ("Google API Key", r"AIza[0-9A-Za-z\-_]{35}", "high"),
    ("Azure Connection String", r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{44}", "critical"),
    ("JWT Token", r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_.+/=]+", "high"),
    ("Bearer Token", r"(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}", "high"),
    ("Private Key", r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "critical"),
    ("Password in Code", r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "high"),
    ("Connection String", r"(?i)(mysql|postgres|mongodb|redis)://[^\s\"']{20,}", "high"),
    ("Slack Token", r"xox[baprs]-[A-Za-z0-9\-]{10,}", "high"),
    ("Google OAuth", r"[0-9]+-[A-Za-z0-9_]{32}\.apps\.googleusercontent\.com", "medium"),
]

_IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "env", ".env", "dist", "build", ".tox", ".mypy_cache",
    "graphify-out", "test-output",
}

_IGNORE_FILES = {
    ".env.example", "test_secret_manager.py", "test_vault.py",
    "security_report.md", ".secrets.meta.json",
}


class SecretScanner:
    """Scan repository for hardcoded secrets."""

    def __init__(self, repo_dir: Optional[str] = None):
        self._dir = Path(repo_dir) if repo_dir else Path.cwd()
        self._findings: List[Dict] = []

    def scan(self, include_tests: bool = False) -> List[Dict]:
        """Scan the entire repository for secrets."""
        self._findings = []
        extensions = {".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml",
                      ".cfg", ".ini", ".sh", ".bash", ".zsh", ".env", ".txt",
                      ".md", ".html", ".css", ".jsx", ".tsx", ".vue", ".svelte",
                      ".pem", ".key", ".crt", ".j2", ".conf"}

        for root, dirs, files in os.walk(self._dir):
            dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]

            for fname in files:
                if fname in _IGNORE_FILES:
                    continue
                if not any(fname.endswith(ext) for ext in extensions):
                    continue
                if not include_tests and ("test_" in fname or "_test.py" in fname):
                    continue

                fpath = Path(root) / fname
                try:
                    self._scan_file(fpath)
                except (OSError, UnicodeDecodeError):
                    continue

        return self._findings

    def _scan_file(self, path: Path) -> None:
        """Scan a single file for secrets."""
        try:
            content = path.read_text(errors="replace")
        except OSError:
            return

        rel_path = str(path.relative_to(self._dir))
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            for pattern_name, pattern, severity in _SECRET_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    matched_text = match.group(0)
                    context_start = max(0, match.start() - 20)
                    context_end = min(len(line), match.end() + 20)
                    context = line[context_start:context_end].strip()

                    self._findings.append({
                        "file": rel_path,
                        "line": line_num,
                        "type": pattern_name,
                        "severity": severity,
                        "context": context,
                        "matched_length": len(matched_text),
                    })

    def generate_report(self, findings: Optional[List[Dict]] = None) -> str:
        """Generate security_report.md from findings."""
        if findings is None:
            findings = self._findings

        critical = [f for f in findings if f["severity"] == "critical"]
        high = [f for f in findings if f["severity"] == "high"]
        medium = [f for f in findings if f["severity"] == "medium"]

        report = [
            "# Security Scan Report",
            "",
            f"**Scanned:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Repository:** {self._dir}",
            "",
            "## Summary",
            "",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| Critical | {len(critical)} |",
            f"| High | {len(high)} |",
            f"| Medium | {len(medium)} |",
            f"| **Total** | **{len(findings)}** |",
            "",
        ]

        health_score = max(0, 100 - len(critical) * 20 - len(high) * 10 - len(medium) * 5)
        report.append(f"**Security Health Score:** {health_score}/100\n")

        if findings:
            report.append("## Findings\n")
            report.append("| # | Severity | Type | File | Line | Context |")
            report.append("|---|----------|------|------|------|---------|")
            for i, f in enumerate(findings, 1):
                ctx = f["context"].replace("|", "\\|")[:60]
                report.append(f"| {i} | {f['severity'].upper()} | {f['type']} | `{f['file']}` | {f['line']} | `{ctx}` |")

            report.append("\n## Recommendations\n")
            if critical:
                report.append("1. **IMMEDIATE:** Remove all critical secrets from source code")
                report.append("2. Rotate any exposed credentials immediately")
                report.append("3. Use `jarvis.security.SecretManager` instead of hardcoded values")
            if high:
                report.append("4. Review high-severity findings and move to vault")
            report.append("5. Enable git pre-commit hook: `python -m jarvis.security.git_hook install`")
        else:
            report.append("## Status: CLEAN\n")
            report.append("No secrets found in the repository.\n")

        return "\n".join(report)

    def scan_and_save(self, output_path: Optional[str] = None) -> str:
        """Scan and save report to file."""
        findings = self.scan()
        report = self.generate_report(findings)

        out = Path(output_path) if output_path else self._dir / "security_report.md"
        out.write_text(report)

        json_out = out.with_suffix(".json")
        json_out.write_text(json.dumps(findings, indent=2))

        return str(out)
