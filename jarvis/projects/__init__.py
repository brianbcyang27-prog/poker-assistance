"""JARVIS Project Awareness — living project objects with continuous scanning.

Maintains a registry of known projects, discovers new ones, and tracks
project state including git info, dependencies, build status, and activity.

Usage:
    manager = ProjectManager()
    projects = await manager.scan_projects("/path/to/root")
    active = await manager.get_active_project()
"""

import hashlib
import json
import logging
import os
import re
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import BuildStatus, Project, ProjectActivity

logger = logging.getLogger(__name__)

# File extensions to scan for language detection
LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".sh": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
}

# Framework detection file patterns
FRAMEWORK_PATTERNS = {
    "Django": ["manage.py", "settings.py"],
    "Flask": ["app.py", "wsgi.py"],
    "FastAPI": ["main.py"],
    "React": ["package.json"],
    "Next.js": ["next.config.js", "next.config.mjs"],
    "Vue": ["vue.config.js", "nuxt.config.js"],
    "Express": ["server.js", "app.js"],
    "Rust-Cargo": ["Cargo.toml"],
    "Go-Modules": ["go.mod"],
}

# Directories to skip during scanning
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".env", ".tox", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".next", ".nuxt", "target",
}


class ProjectManager:
    """Maintains living project objects with continuous state tracking."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._projects: Dict[str, Project] = {}
        self._activities: Dict[str, List[ProjectActivity]] = {}
        self._active_project_id: Optional[str] = None
        self._storage_path = storage_path or os.path.join(
            os.path.expanduser("~"), ".jarvis", "projects.json"
        )

    async def scan_projects(self, root_path: str) -> List[Project]:
        """Discover projects under root_path.

        Scans for directories containing project indicators (package.json,
        Cargo.toml, go.mod, pyproject.toml, etc.) and creates/updates
        Project objects for each.

        Args:
            root_path: Root directory to scan for projects.

        Returns:
            List of discovered projects.
        """
        discovered: List[Project] = []

        if not os.path.isdir(root_path):
            logger.warning("Root path does not exist: %s", root_path)
            return discovered

        for entry in os.scandir(root_path):
            if not entry.is_dir():
                continue
            if entry.name in SKIP_DIRS:
                continue

            project = await self._analyze_directory(entry.path)
            if project is not None:
                self._projects[project.id] = project
                discovered.append(project)

        return discovered

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        return self._projects.get(project_id)

    async def update_project(self, project_id: str) -> None:
        """Refresh a project's state from disk."""
        project = self._projects.get(project_id)
        if project is None:
            return

        updated = await self._analyze_directory(project.path)
        if updated is not None:
            updated.context_snapshot = project.context_snapshot
            updated.last_accessed = project.last_accessed
            self._projects[project_id] = updated

    async def get_active_project(self) -> Optional[Project]:
        """Get the currently active project."""
        if self._active_project_id is None:
            return None
        return self._projects.get(self._active_project_id)

    async def set_active_project(self, project_id: str) -> None:
        """Set the active project."""
        if project_id in self._projects:
            self._active_project_id = project_id
            self._projects[project_id].last_accessed = datetime.now()

    async def get_project_history(self, project_id: str) -> List[Dict]:
        """Get recent activity for a project."""
        activities = self._activities.get(project_id, [])
        return [a.to_dict() for a in activities[-50:]]

    async def restore_context(self, project_id: str) -> Dict[str, Any]:
        """Restore saved context for a project."""
        project = self._projects.get(project_id)
        if project is None:
            return {}
        return dict(project.context_snapshot)

    async def save_context(self, project_id: str, context: Dict[str, Any]) -> None:
        """Save context snapshot for a project."""
        project = self._projects.get(project_id)
        if project is not None:
            project.context_snapshot = context

    async def log_activity(
        self,
        project_id: str,
        action: str,
        detail: str,
        files_affected: Optional[List[str]] = None,
    ) -> None:
        """Log an activity event for a project."""
        activity = ProjectActivity(
            timestamp=datetime.now(),
            action=action,
            detail=detail,
            files_affected=files_affected or [],
        )
        if project_id not in self._activities:
            self._activities[project_id] = []
        self._activities[project_id].append(activity)

        # Keep last 200 activities per project
        if len(self._activities[project_id]) > 200:
            self._activities[project_id] = self._activities[project_id][-200:]

    async def save(self) -> None:
        """Persist projects to disk."""
        data = {
            "active_project_id": self._active_project_id,
            "projects": {pid: p.to_dict() for pid, p in self._projects.items()},
            "activities": {
                pid: [a.to_dict() for a in acts]
                for pid, acts in self._activities.items()
            },
        }

        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved %d projects to %s", len(self._projects), self._storage_path)

    async def load(self) -> None:
        """Load projects from disk."""
        if not os.path.exists(self._storage_path):
            logger.info("No projects file at %s", self._storage_path)
            return

        with open(self._storage_path, "r") as f:
            data = json.load(f)

        self._active_project_id = data.get("active_project_id")
        self._projects = {
            pid: Project.from_dict(pdata)
            for pid, pdata in data.get("projects", {}).items()
        }
        self._activities = {
            pid: [ProjectActivity.from_dict(a) for a in acts]
            for pid, acts in data.get("activities", {}).items()
        }
        logger.info("Loaded %d projects from %s", len(self._projects), self._storage_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _project_id(self, path: str) -> str:
        """Generate a deterministic project ID from path."""
        return hashlib.sha256(path.encode()).hexdigest()[:12]

    async def _analyze_directory(self, dir_path: str) -> Optional[Project]:
        """Analyze a directory and return a Project if it looks like a project."""
        indicators = self._find_project_indicators(dir_path)
        if not indicators:
            return None

        name = os.path.basename(dir_path)
        project_id = self._project_id(dir_path)
        languages = self._detect_languages(dir_path)
        frameworks = self._detect_frameworks(dir_path)
        git_remote, git_branch = self._git_info(dir_path)
        dependencies = self._detect_dependencies(dir_path, indicators)
        build_status = self._detect_build_status(dir_path)
        recent_commits = self._recent_commits(dir_path, limit=10)
        todos = self._count_todos(dir_path)
        doc_score = self._documentation_score(dir_path)

        purpose = self._infer_purpose(name, frameworks, languages)

        existing = self._projects.get(project_id)
        last_accessed = existing.last_accessed if existing else None

        return Project(
            id=project_id,
            name=name,
            purpose=purpose,
            path=dir_path,
            languages=languages,
            frameworks=frameworks,
            git_remote=git_remote,
            git_branch=git_branch,
            dependencies=dependencies,
            build_status=build_status,
            recent_commits=recent_commits,
            todos=todos,
            documentation_score=doc_score,
            last_accessed=last_accessed,
            metadata={"indicators": indicators},
        )

    def _find_project_indicators(self, dir_path: str) -> List[str]:
        """Find files that indicate a project root."""
        indicators = []
        check_files = [
            "package.json", "Cargo.toml", "go.mod", "pyproject.toml",
            "setup.py", "setup.cfg", "Makefile", "CMakeLists.txt",
            "pom.xml", "build.gradle", "Gemfile", "composer.json",
            ".git",
        ]
        for fname in check_files:
            if os.path.exists(os.path.join(dir_path, fname)):
                indicators.append(fname)
        return indicators

    def _detect_languages(self, dir_path: str) -> List[str]:
        """Detect programming languages from file extensions."""
        lang_counts: Dict[str, int] = {}
        try:
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    lang = LANGUAGE_MAP.get(ext)
                    if lang:
                        lang_counts[lang] = lang_counts.get(lang, 0) + 1
                # Limit walk depth
                depth = root.replace(dir_path, "").count(os.sep)
                if depth >= 3:
                    dirs.clear()
        except PermissionError:
            pass

        sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, _ in sorted_langs[:10]]

    def _detect_frameworks(self, dir_path: str) -> List[str]:
        """Detect frameworks from project files."""
        frameworks: List[str] = []

        # Check for framework-specific files
        for framework, patterns in FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if os.path.exists(os.path.join(dir_path, pattern)):
                    frameworks.append(framework)
                    break

        # Check package.json for JS frameworks
        pkg_path = os.path.join(dir_path, "package.json")
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, "r") as f:
                    pkg = json.load(f)
                deps = {}
                deps.update(pkg.get("dependencies", {}))
                deps.update(pkg.get("devDependencies", {}))
                if "react" in deps:
                    frameworks.append("React")
                if "vue" in deps or "nuxt" in deps:
                    frameworks.append("Vue")
                if "next" in deps:
                    frameworks.append("Next.js")
                if "express" in deps:
                    frameworks.append("Express")
                if "fastapi" in deps:
                    frameworks.append("FastAPI")
                if "django" in deps:
                    frameworks.append("Django")
                if "flask" in deps:
                    frameworks.append("Flask")
            except (json.JSONDecodeError, OSError):
                pass

        return list(set(frameworks))

    def _git_info(self, dir_path: str) -> tuple:
        """Get git remote URL and current branch."""
        remote = None
        branch = None
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=dir_path, capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                remote = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=dir_path, capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return remote, branch

    def _detect_dependencies(self, dir_path: str, indicators: List[str]) -> List[str]:
        """Detect project dependencies."""
        deps: List[str] = []

        if "package.json" in indicators:
            try:
                with open(os.path.join(dir_path, "package.json"), "r") as f:
                    pkg = json.load(f)
                deps.extend(pkg.get("dependencies", {}).keys())
            except (json.JSONDecodeError, OSError):
                pass

        if "requirements.txt" in indicators:
            try:
                with open(os.path.join(dir_path, "requirements.txt"), "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                            deps.append(name)
            except OSError:
                pass

        if "Cargo.toml" in indicators:
            try:
                with open(os.path.join(dir_path, "Cargo.toml"), "r") as f:
                    content = f.read()
                for match in re.finditer(r'(\w[\w-]*)\s*=\s*"[^"]*"', content):
                    deps.append(match.group(1))
            except OSError:
                pass

        return deps[:50]

    def _detect_build_status(self, dir_path: str) -> BuildStatus:
        """Attempt to detect build status."""
        if os.path.exists(os.path.join(dir_path, "package.json")):
            lock = os.path.exists(os.path.join(dir_path, "node_modules"))
            return BuildStatus.PASSING if lock else BuildStatus.UNKNOWN
        if os.path.exists(os.path.join(dir_path, "Cargo.toml")):
            target = os.path.join(dir_path, "target")
            return BuildStatus.PASSING if os.path.isdir(target) else BuildStatus.UNKNOWN
        return BuildStatus.UNKNOWN

    def _recent_commits(self, dir_path: str, limit: int = 10) -> List[str]:
        """Get recent commit messages."""
        try:
            result = subprocess.run(
                ["git", "log", f"--oneline", f"-{limit}"],
                cwd=dir_path, capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def _count_todos(self, dir_path: str) -> List[str]:
        """Count TODO comments in the project."""
        todos: List[str] = []
        try:
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fname in files:
                    if not fname.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go")):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                stripped = line.strip()
                                if stripped.startswith("#") or stripped.startswith("//"):
                                    if "TODO" in stripped:
                                        rel = os.path.relpath(fpath, dir_path)
                                        todos.append(f"{rel}:{i}")
                                if len(todos) >= 50:
                                    return todos
                    except OSError:
                        continue
                depth = root.replace(dir_path, "").count(os.sep)
                if depth >= 4:
                    dirs.clear()
        except PermissionError:
            pass
        return todos

    def _documentation_score(self, dir_path: str) -> float:
        """Score documentation coverage (0.0 - 1.0)."""
        total_modules = 0
        documented = 0

        try:
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    total_modules += 1
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", errors="ignore") as f:
                            content = f.read(2000)
                        if '"""' in content or "'''" in content:
                            documented += 1
                    except OSError:
                        continue
                depth = root.replace(dir_path, "").count(os.sep)
                if depth >= 3:
                    dirs.clear()
        except PermissionError:
            pass

        if total_modules == 0:
            return 0.0
        return round(documented / total_modules, 2)

    def _infer_purpose(self, name: str, frameworks: List[str], languages: List[str]) -> str:
        """Infer project purpose from name and tech stack."""
        parts = []
        if frameworks:
            parts.append(", ".join(frameworks[:3]))
        if languages:
            parts.append(f"{languages[0]} project")
        if not parts:
            return f"Project: {name}"
        return f"{name} — {', '.join(parts)}"
