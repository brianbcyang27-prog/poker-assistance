"""Git protection — .gitignore management and pre-commit hooks."""

import os
import stat
from pathlib import Path
from typing import Optional

_GITIGNORE_ENTRIES = [
    "# JARVIS Security",
    ".env",
    ".env.*",
    ".secrets.enc",
    ".secrets.meta.json",
    ".security_audit.jsonl",
    "*.pem",
    "*.key",
    "*.crt",
    "*.p12",
    "credentials.json",
    "service-account.json",
]

_PRE_COMMIT_HOOK = """#!/usr/bin/env bash
# JARVIS Secret Scanner — pre-commit hook
# Prevents committing secrets to the repository

set -e

echo "[JARVIS] Scanning staged changes for secrets..."

# Get staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Secret patterns
PATTERNS=(
    "nvapi-[A-Za-z0-9\\-_]\\{20,\\}"
    "sk-[A-Za-z0-9]\\{20,\\}"
    "sk-ant-[A-Za-z0-9\\-_]\\{20,\\}"
    "ghp_[A-Za-z0-9]\\{36\\}"
    "github_pat_[A-Za-z0-9\\-_]\\{20,\\}"
    "AKIA[0-9A-Z]\\{16\\}"
    "AIza[0-9A-Za-z\\-_]\\{35\\}"
    "-----BEGIN.*PRIVATE KEY-----"
)

FOUND=0

for FILE in $STAGED_FILES; do
    # Skip binary and deleted files
    [ -f "$FILE" ] || continue

    for PATTERN in "${PATTERNS[@]}"; do
        if grep -qnE "$PATTERN" "$FILE" 2>/dev/null; then
            echo "[JARVIS] SECRET DETECTED in $FILE"
            echo "         Pattern: $PATTERN"
            grep -nE "$PATTERN" "$FILE" | head -3
            FOUND=1
        fi
    done
done

if [ "$FOUND" -eq 1 ]; then
    echo ""
    echo "[JARVIS] COMMIT REJECTED — secrets detected!"
    echo "         Use SecretManager.get() instead of hardcoded values."
    echo "         Run: python -m jarvis.security.scanner to scan the repo."
    exit 1
fi

echo "[JARVIS] No secrets detected."
exit 0
"""


class GitProtection:
    """Manage .gitignore entries and pre-commit hooks."""

    def __init__(self, repo_dir: Optional[str] = None):
        self._dir = Path(repo_dir) if repo_dir else Path.cwd()
        self._git_dir = self._dir / ".git"
        self._hooks_dir = self._git_dir / "hooks"

    @property
    def is_git_repo(self) -> bool:
        return self._git_dir.exists()

    def setup_gitignore(self) -> bool:
        """Add security entries to .gitignore."""
        gitignore_path = self._dir / ".gitignore"
        existing = gitignore_path.read_text() if gitignore_path.exists() else ""

        entries_to_add = []
        for entry in _GITIGNORE_ENTRIES:
            if entry.startswith("#"):
                if entry not in existing:
                    entries_to_add.append(entry)
            elif entry not in existing:
                entries_to_add.append(entry)

        if entries_to_add:
            with open(gitignore_path, "a") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("\n".join(entries_to_add) + "\n")

        return True

    def install_pre_commit_hook(self) -> bool:
        """Install the secret scanner pre-commit hook."""
        if not self.is_git_repo:
            return False

        self._hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = self._hooks_dir / "pre-commit"

        hook_path.write_text(_PRE_COMMIT_HOOK)
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        return True

    def uninstall_pre_commit_hook(self) -> bool:
        """Remove the pre-commit hook."""
        hook_path = self._hooks_dir / "pre-commit"
        if hook_path.exists():
            content = hook_path.read_text()
            if "JARVIS Secret Scanner" in content:
                hook_path.unlink()
                return True
        return False

    def is_hook_installed(self) -> bool:
        """Check if the JARVIS pre-commit hook is installed."""
        hook_path = self._hooks_dir / "pre-commit"
        if hook_path.exists():
            return "JARVIS Secret Scanner" in hook_path.read_text()
        return False

    def get_status(self) -> dict:
        """Get git protection status."""
        return {
            "is_git_repo": self.is_git_repo,
            "hook_installed": self.is_hook_installed(),
            "gitignore_entries": len(_GITIGNORE_ENTRIES),
        }
