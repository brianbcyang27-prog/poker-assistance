"""Main Repository Intelligence analyzer engine."""

import ast
import glob
import json
import os
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple

from .models import (
    ArchitectureReport,
    CodeStyleReport,
    DebtIssue,
    DebtReport,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    ImprovementItem,
    ImprovementReport,
    ProjectDNA,
)

# Framework detection patterns
FRAMEWORK_IMPORTS = {
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "starlette": ["starlette"],
    "uvicorn": ["uvicorn"],
    "pydantic": ["pydantic"],
    "sqlalchemy": ["sqlalchemy"],
    "celery": ["celery"],
    "pytest": ["pytest"],
    "unittest": ["unittest"],
    "react": ["react", "next"],
    "vue": ["vue", "nuxt"],
    "angular": ["angular"],
    "express": ["express"],
    "fastify": ["fastify"],
    "spring": ["spring"],
    "rails": ["rails"],
    "laravel": ["laravel"],
}

# Build system config files
BUILD_SYSTEM_FILES = {
    "pyproject.toml": "poetry/setuptools",
    "setup.py": "setuptools",
    "setup.cfg": "setuptools",
    "package.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "Cargo.toml": "cargo",
    "go.mod": "go",
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
    "build.gradle": "gradle",
    "pom.xml": "maven",
    "Gemfile": "bundler",
    "composer.json": "composer",
    "Dockerfile": "docker",
    "docker-compose.yml": "docker-compose",
    "docker-compose.yaml": "docker-compose",
    ".github/workflows": "github-actions",
    ".gitlab-ci.yml": "gitlab-ci",
    "Jenkinsfile": "jenkins",
    "Procfile": "heroku",
    "vercel.json": "vercel",
    "netlify.toml": "netlify",
}

# Package manager config files
PACKAGE_MANAGER_FILES = {
    "requirements.txt": "pip",
    "Pipfile": "pipenv",
    "poetry.lock": "poetry",
    "pyproject.toml": "pip",
    "package.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "Cargo.lock": "cargo",
    "go.sum": "go",
    "Gemfile.lock": "bundler",
    "composer.lock": "composer",
}

# Skip directories
SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".env", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".eggs", "*.egg-info", ".next", ".nuxt", "target", "vendor",
}

# Code patterns for architecture detection
PATTERN_INDICATORS = {
    "mvc": ["models", "views", "controllers", "templates"],
    "repository": ["repository", "repositories", "repo", "repos"],
    "factory": ["factory", "factories", "provider", "providers"],
    "singleton": ["_instance", "getInstance", "instance"],
    "observer": ["observer", "listener", "event", "subscriber", "emitter"],
    "decorator": ["decorator", "wraps"],
    "strategy": ["strategy", "strategies", "policy"],
    "command": ["command", "commands", "handler", "handlers"],
    "adapter": ["adapter", "adapters", "bridge"],
    "proxy": ["proxy", "proxies"],
    "middleware": ["middleware", "middlewares"],
    "plugin": ["plugin", "plugins", "extension", "extensions"],
}


class RepoIntelligence:
    """Repository Intelligence engine for analyzing Git repositories."""

    def __init__(self):
        self._file_cache: Dict[str, str] = {}
        self._ast_cache: Dict[str, ast.Module] = {}

    async def analyze(self, repo_path: str) -> ProjectDNA:
        """Perform full repository analysis and return ProjectDNA."""
        return await self.generate_dna(repo_path)

    async def detect_languages(self, repo_path: str) -> Dict[str, float]:
        """Detect programming languages and their proportion."""
        extension_counts: Counter = Counter()
        total_files = 0

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files:
                if file.startswith(".") or file.endswith((".lock", ".sum")):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    extension_counts[ext] += 1
                    total_files += 1

        if total_files == 0:
            return {}

        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
            ".kt": "kotlin", ".scala": "scala", ".go": "go",
            ".rs": "rust", ".c": "c", ".cpp": "cpp", ".h": "c",
            ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby", ".php": "php",
            ".swift": "swift", ".m": "objective-c", ".r": "r",
            ".R": "r", ".jl": "julia", ".lua": "lua", ".pl": "perl",
            ".sh": "shell", ".bash": "shell", ".zsh": "shell",
            ".sql": "sql", ".html": "html", ".htm": "html",
            ".css": "css", ".scss": "scss", ".less": "less",
            ".json": "json", ".yaml": "yaml", ".yml": "yaml",
            ".toml": "toml", ".xml": "xml", ".md": "markdown",
            ".dart": "dart", ".ex": "elixir", ".exs": "elixir",
            ".erl": "erlang", ".hs": "haskell", ".clj": "clojure",
            ".vue": "vue", ".svelte": "svelte",
        }

        lang_counts: Counter = Counter()
        for ext, count in extension_counts.items():
            lang = lang_map.get(ext, ext.lstrip("."))
            lang_counts[lang] += count

        return {
            lang: round(count / total_files * 100, 2)
            for lang, count in lang_counts.most_common()
        }

    async def detect_frameworks(self, repo_path: str) -> List[str]:
        """Detect frameworks and libraries used."""
        frameworks: Set[str] = set()

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(50000)
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                mod = alias.name.split(".")[0].lower()
                                for fw, keywords in FRAMEWORK_IMPORTS.items():
                                    if mod in keywords:
                                        frameworks.add(fw)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                mod = node.module.split(".")[0].lower()
                                for fw, keywords in FRAMEWORK_IMPORTS.items():
                                    if mod in keywords:
                                        frameworks.add(fw)
                except (SyntaxError, UnicodeDecodeError):
                    pass

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files:
                if file == "package.json":
                    try:
                        filepath = os.path.join(root, file)
                        with open(filepath, "r", encoding="utf-8") as f:
                            pkg = json.load(f)
                        all_deps = {}
                        all_deps.update(pkg.get("dependencies", {}))
                        all_deps.update(pkg.get("devDependencies", {}))
                        for dep in all_deps:
                            dep_lower = dep.lower().replace("@", "").replace("/", "-")
                            for fw, keywords in FRAMEWORK_IMPORTS.items():
                                for kw in keywords:
                                    if kw in dep_lower:
                                        frameworks.add(fw)
                    except (json.JSONDecodeError, OSError):
                        pass

        return sorted(frameworks)

    async def detect_build_system(self, repo_path: str) -> Dict[str, str]:
        """Detect build systems and tools."""
        build_systems: Dict[str, str] = {}

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files:
                if file in BUILD_SYSTEM_FILES:
                    key = file if not file.startswith(".") else file
                    build_systems[key] = BUILD_SYSTEM_FILES[file]
            if os.path.isdir(os.path.join(root, ".github", " workflows")):
                build_systems[".github/workflows"] = "github-actions"

        if os.path.isfile(os.path.join(repo_path, "pyproject.toml")):
            try:
                with open(os.path.join(repo_path, "pyproject.toml"), "r") as f:
                    content = f.read()
                if "[tool.poetry]" in content:
                    build_systems["pyproject.toml"] = "poetry"
                elif "[build-system]" in content:
                    build_systems["pyproject.toml"] = "setuptools"
            except OSError:
                pass

        return build_systems

    async def analyze_dependencies(self, repo_path: str) -> DependencyGraph:
        """Analyze project dependencies and build a dependency graph."""
        graph = DependencyGraph()

        req_files = [
            ("requirements.txt", "pip"),
            ("Pipfile", "pipenv"),
            ("setup.py", "setuptools"),
        ]

        for filename, ecosystem in req_files:
            filepath = os.path.join(repo_path, filename)
            if os.path.isfile(filepath):
                deps = self._parse_requirements(filepath)
                for name, version in deps:
                    graph.nodes.append(DependencyNode(
                        name=name, version=version, type="direct", ecosystem=ecosystem
                    ))

        pkg_path = os.path.join(repo_path, "package.json")
        if os.path.isfile(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                for name, ver in pkg.get("dependencies", {}).items():
                    graph.nodes.append(DependencyNode(
                        name=name, version=ver, type="direct", ecosystem="npm"
                    ))
                for name, ver in pkg.get("devDependencies", {}).items():
                    graph.nodes.append(DependencyNode(
                        name=name, version=ver, type="dev", ecosystem="npm"
                    ))
                for name, ver in pkg.get("peerDependencies", {}).items():
                    graph.nodes.append(DependencyNode(
                        name=name, version=ver, type="optional", ecosystem="npm"
                    ))
            except (json.JSONDecodeError, OSError):
                pass

        pyproject_path = os.path.join(repo_path, "pyproject.toml")
        if os.path.isfile(pyproject_path):
            try:
                deps = self._parse_pyproject_deps(pyproject_path)
                for name, version in deps:
                    graph.nodes.append(DependencyNode(
                        name=name, version=version, type="direct", ecosystem="pypi"
                    ))
            except OSError:
                pass

        return graph

    async def analyze_architecture(self, repo_path: str) -> ArchitectureReport:
        """Analyze repository architecture."""
        report = ArchitectureReport(style="unknown")
        top_dirs = []
        all_dirs = set()
        entry_points = []
        config_files = []

        for item in os.listdir(repo_path):
            if item.startswith(".") or item in SKIP_DIRS:
                continue
            path = os.path.join(repo_path, item)
            if os.path.isdir(path):
                top_dirs.append(item)
                all_dirs.add(item.lower())

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            rel_root = os.path.relpath(root, repo_path)
            for file in files:
                if file.startswith(".") or file.startswith("__"):
                    continue
                rel_path = os.path.join(rel_root, file) if rel_root != "." else file
                if file in ("main.py", "app.py", "index.py", "server.py", "manage.py"):
                    entry_points.append(rel_path)
                if file in ("settings.py", "config.py", "config.json", "config.yaml",
                            "config.yml", ".env", ".env.example", "pyproject.toml",
                            "package.json", "tsconfig.json"):
                    config_files.append(rel_path)

        detected_patterns = []
        all_dirs_lower = {d.lower() for d in top_dirs}
        for pattern, indicators in PATTERN_INDICATORS.items():
            if any(ind in all_dirs_lower for ind in indicators):
                detected_patterns.append(pattern)

        layers = []
        if "src" in all_dirs_lower or "lib" in all_dirs_lower:
            layers.append("source")
        if "tests" in all_dirs_lower or "test" in all_dirs_lower:
            layers.append("tests")
        if "docs" in all_dirs_lower or "doc" in all_dirs_lower:
            layers.append("docs")
        if "config" in all_dirs_lower or "conf" in all_dirs_lower:
            layers.append("config")

        style = self._detect_arch_style(top_dirs, detected_patterns)
        report.style = style
        report.modules = top_dirs
        report.layers = layers
        report.patterns = detected_patterns
        report.entry_points = entry_points
        report.config_files = config_files

        return report

    async def analyze_code_style(self, repo_path: str) -> CodeStyleReport:
        """Analyze coding style metrics."""
        report = CodeStyleReport()
        line_lengths = []
        function_lengths = []
        total_functions = 0
        functions_with_docstrings = 0
        total_params = 0
        params_with_hints = 0

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    for line in lines:
                        stripped = line.rstrip("\n")
                        if stripped:
                            line_lengths.append(len(stripped))

                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            total_functions += 1
                            end_line = getattr(node, "end_lineno", node.lineno)
                            func_len = end_line - node.lineno + 1
                            function_lengths.append(func_len)

                            if (node.body and isinstance(node.body[0], ast.Expr) and
                                    isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                                functions_with_docstrings += 1

                            for arg in node.args.args:
                                if arg.arg != "self" and arg.arg != "cls":
                                    total_params += 1
                                    if arg.annotation is not None:
                                        params_with_hints += 1

                            for arg in node.args.posonlyargs:
                                total_params += 1
                                if arg.annotation is not None:
                                    params_with_hints += 1

                            for arg in node.args.kwonlyargs:
                                total_params += 1
                                if arg.annotation is not None:
                                    params_with_hints += 1

                except (SyntaxError, UnicodeDecodeError):
                    pass

        if line_lengths:
            report.avg_line_length = round(sum(line_lengths) / len(line_lengths), 1)
        if function_lengths:
            report.max_function_length = max(function_lengths)
            report.avg_function_length = round(sum(function_lengths) / len(function_lengths), 1)
        if total_functions > 0:
            report.docstring_coverage = round(
                functions_with_docstrings / total_functions * 100, 1
            )
        if total_params > 0:
            report.type_hint_coverage = round(
                params_with_hints / total_params * 100, 1
            )

        report.naming_convention = self._detect_naming_convention(repo_path)
        return report

    async def analyze_debt(self, repo_path: str) -> DebtReport:
        """Analyze technical debt in the repository."""
        issues: List[DebtIssue] = []
        total_score = 0.0

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, repo_path)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    content = "".join(lines)

                    debt_issues = self._analyze_file_debt(rel_path, lines, content)
                    issues.extend(debt_issues)
                except (SyntaxError, UnicodeDecodeError):
                    pass

        for issue in issues:
            severity_scores = {"low": 1, "medium": 3, "high": 7, "critical": 10}
            total_score += severity_scores.get(issue.severity, 1)

        max_possible = len(issues) * 10 if issues else 1
        normalized_score = min(100, (total_score / max_possible) * 100) if max_possible > 0 else 0

        severity_counts = Counter(i.severity for i in issues)
        category_counts = Counter(i.category for i in issues)

        summary_parts = []
        if severity_counts.get("critical", 0) > 0:
            summary_parts.append(f"{severity_counts['critical']} critical issues")
        if severity_counts.get("high", 0) > 0:
            summary_parts.append(f"{severity_counts['high']} high-severity issues")
        summary_parts.append(f"{len(issues)} total issues found")
        summary = "; ".join(summary_parts) if summary_parts else "No significant debt detected"

        return DebtReport(score=round(normalized_score, 1), issues=issues, summary=summary)

    async def generate_dna(self, repo_path: str) -> ProjectDNA:
        """Generate complete ProjectDNA for the repository."""
        repo_name = os.path.basename(os.path.abspath(repo_path))

        languages = await self.detect_languages(repo_path)
        frameworks = await self.detect_frameworks(repo_path)
        build_system = await self.detect_build_system(repo_path)
        dependencies = await self.analyze_dependencies(repo_path)
        architecture = await self.analyze_architecture(repo_path)
        code_style = await self.analyze_code_style(repo_path)
        debt = await self.analyze_debt(repo_path)

        package_managers = []
        for key, value in build_system.items():
            if value in ("npm", "yarn", "pnpm", "pip", "pipenv", "poetry",
                         "cargo", "bundler", "composer"):
                package_managers.append(value)
        package_managers = list(set(package_managers))

        folder_structure = self._get_folder_structure(repo_path)
        purpose = self._infer_purpose(repo_path, frameworks, languages)
        testing_framework = self._detect_testing_framework(repo_path)
        deployment_method = self._detect_deployment(repo_path)
        ci_cd = self._detect_ci_cd(repo_path)
        documentation_quality = await self._assess_documentation(repo_path)
        patterns = architecture.patterns

        health_score = self._calculate_health_score(
            code_style, debt, documentation_quality, len(languages)
        )
        risk_score = self._calculate_risk_score(debt, health_score)

        return ProjectDNA(
            name=repo_name,
            purpose=purpose,
            languages=languages,
            frameworks=frameworks,
            build_system=build_system,
            package_managers=package_managers,
            architecture_style=architecture.style,
            folder_structure=folder_structure,
            coding_style=code_style,
            patterns=patterns,
            testing_framework=testing_framework,
            deployment_method=deployment_method,
            ci_cd=ci_cd,
            documentation_quality=documentation_quality,
            debt_score=debt.score,
            health_score=health_score,
            risk_score=risk_score,
        )

    def _parse_requirements(self, filepath: str) -> List[Tuple[str, str]]:
        """Parse requirements.txt style files."""
        deps = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    match = re.match(r"^([a-zA-Z0-9_.-]+)\s*([><=!~]+.*)?$", line)
                    if match:
                        name = match.group(1)
                        version = (match.group(2) or "any").strip()
                        deps.append((name, version))
        except OSError:
            pass
        return deps

    def _parse_pyproject_deps(self, filepath: str) -> List[Tuple[str, str]]:
        """Parse dependencies from pyproject.toml without toml library."""
        deps = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            in_deps = False
            in_dev_deps = False
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped == "[project.optional-dependencies]":
                    in_deps = True
                    in_dev_deps = False
                elif stripped.startswith("[") or stripped == "[project]":
                    if in_deps and stripped.startswith("[project."):
                        continue
                    in_deps = False
                    in_dev_deps = False

                if in_deps and "=" in stripped:
                    match = re.match(r'^"?([a-zA-Z0-9_.-]+)"?\s*=\s*"(.+)"', stripped)
                    if match:
                        deps.append((match.group(1), match.group(2)))
        except OSError:
            pass
        return deps

    def _detect_arch_style(self, top_dirs: List[str], patterns: List[str]) -> str:
        """Detect architecture style from directory structure."""
        dirs_lower = [d.lower() for d in top_dirs]

        if "src" in dirs_lower and len(top_dirs) <= 3:
            return "flat"
        if any(d in dirs_lower for d in ["services", "microservices", "apps"]):
            return "microservices"
        if any(p in patterns for p in ["mvc", "repository", "factory"]):
            return "layered"
        if len(top_dirs) > 5:
            return "modular"
        if any(d in dirs_lower for d in ["lib", "pkg", "internal"]):
            return "monorepo"
        return "monolith"

    def _detect_naming_convention(self, repo_path: str) -> str:
        """Detect dominant naming convention in Python files."""
        snake_count = 0
        camel_count = 0

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(30000)
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            name = node.name
                            if "_" in name and not name.startswith("_"):
                                snake_count += 1
                            elif name[0].isupper() or any(c.isupper() for c in name[1:]):
                                camel_count += 1
                        elif isinstance(node, ast.ClassDef):
                            camel_count += 1
                except (SyntaxError, UnicodeDecodeError):
                    pass

        if snake_count > camel_count * 2:
            return "snake_case"
        elif camel_count > snake_count * 2:
            return "camelCase"
        return "mixed"

    def _analyze_file_debt(self, rel_path: str, lines: List[str], content: str) -> List[DebtIssue]:
        """Analyze a single file for technical debt."""
        issues: List[DebtIssue] = []
        max_line_len = 120
        max_func_len = 50
        max_nesting = 4

        try:
            tree = ast.parse(content)
        except SyntaxError:
            issues.append(DebtIssue(
                file=rel_path, line=1, category="complexity",
                description="File has syntax errors",
                severity="critical", suggestion="Fix syntax errors before analysis"
            ))
            return issues

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = getattr(node, "end_lineno", node.lineno)
                func_len = end_line - node.lineno + 1

                if func_len > max_func_len:
                    issues.append(DebtIssue(
                        file=rel_path, line=node.lineno, category="complexity",
                        description=f"Function '{node.name}' is {func_len} lines (max {max_func_len})",
                        severity="high" if func_len > 100 else "medium",
                        suggestion=f"Refactor '{node.name}' into smaller functions"
                    ))

                nesting = self._get_max_nesting(node)
                if nesting > max_nesting:
                    issues.append(DebtIssue(
                        file=rel_path, line=node.lineno, category="complexity",
                        description=f"Function '{node.name}' has nesting depth {nesting}",
                        severity="medium",
                        suggestion="Reduce nesting with early returns or extraction"
                    ))

                has_docstring = (node.body and isinstance(node.body[0], ast.Expr) and
                                 isinstance(node.body[0].value, (ast.Constant, ast.Str)))
                if not has_docstring and not node.name.startswith("_"):
                    issues.append(DebtIssue(
                        file=rel_path, line=node.lineno, category="documentation",
                        description=f"Function '{node.name}' missing docstring",
                        severity="low", suggestion="Add docstring to document function purpose"
                    ))

        import_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    import_names.add(alias.asname or alias.name)

        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        for imp in import_names:
            if imp not in used_names and imp != "*":
                issues.append(DebtIssue(
                    file=rel_path, line=1, category="import",
                    description=f"Unused import: '{imp}'",
                    severity="low", suggestion=f"Remove unused import '{imp}'"
                ))

        long_lines = []
        for i, line in enumerate(lines, 1):
            if len(line.rstrip()) > max_line_len:
                long_lines.append(i)

        if long_lines:
            sample = long_lines[:3]
            issues.append(DebtIssue(
                file=rel_path, line=sample[0], category="style",
                description=f"{len(long_lines)} lines exceed {max_line_len} characters",
                severity="low", suggestion="Break long lines for readability"
            ))

        return issues

    def _get_max_nesting(self, node: ast.AST) -> int:
        """Get maximum nesting depth in a function."""
        max_depth = 0
        nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try,
                         ast.ExceptHandler, ast.AsyncFor, ast.AsyncWith)

        def walk_depth(current: ast.AST, depth: int) -> None:
            nonlocal max_depth
            if isinstance(current, nesting_nodes):
                depth += 1
                max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(current):
                walk_depth(child, depth)

        walk_depth(node, 0)
        return max_depth

    def _get_folder_structure(self, repo_path: str) -> Dict[str, int]:
        """Get folder structure with file counts."""
        structure: Dict[str, int] = {}
        for item in os.listdir(repo_path):
            if item.startswith(".") or item in SKIP_DIRS:
                continue
            path = os.path.join(repo_path, item)
            if os.path.isdir(path):
                count = sum(
                    len(files)
                    for _, _, files in os.walk(path)
                    if not any(d in SKIP_DIRS for d in _)
                )
                structure[item] = count
            else:
                structure[item] = 1
        return structure

    def _infer_purpose(self, repo_path: str, frameworks: List[str], languages: Dict[str, float]) -> str:
        """Infer project purpose from structure and frameworks."""
        readme_path = os.path.join(repo_path, "README.md")
        if os.path.isfile(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[:20]
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("!"):
                        return line[:200]
            except OSError:
                pass

        if any(fw in frameworks for fw in ["fastapi", "django", "flask", "express"]):
            return "Web API/Backend service"
        if any(fw in frameworks for fw in ["react", "vue", "angular", "svelte"]):
            return "Web frontend application"
        if "pytest" in frameworks or "unittest" in frameworks:
            return "Python library with tests"
        if any(lang in (languages or {}) for lang in ["go", "rust"]):
            return "Systems/CLI tool"
        return "Software project"

    def _detect_testing_framework(self, repo_path: str) -> str:
        """Detect testing framework used."""
        test_configs = [
            ("pytest.ini", "pytest"),
            ("setup.cfg", "pytest"),
            ("tox.ini", "tox"),
            ("phpunit.xml", "phpunit"),
            ("jest.config.js", "jest"),
            ("jest.config.ts", "jest"),
            ("vitest.config.ts", "vitest"),
            (".mocharc.yml", "mocha"),
        ]

        for filename, framework in test_configs:
            if os.path.isfile(os.path.join(repo_path, filename)):
                return framework

        test_dirs = ["tests", "test", "__tests__", "spec"]
        for d in test_dirs:
            if os.path.isdir(os.path.join(repo_path, d)):
                return "pytest" if any(
                    f.endswith(".py") for f in os.listdir(os.path.join(repo_path, d))
                ) else "unknown"

        return "unknown"

    def _detect_deployment(self, repo_path: str) -> str:
        """Detect deployment method."""
        deploy_indicators = {
            "Dockerfile": "docker",
            "docker-compose.yml": "docker-compose",
            "docker-compose.yaml": "docker-compose",
            "Procfile": "heroku",
            "vercel.json": "vercel",
            "netlify.toml": "netlify",
            "app.yaml": "app-engine",
            "serverless.yml": "serverless",
            "serverless.yaml": "serverless",
            "terraform": "terraform",
            "kubernetes": "kubernetes",
            "k8s": "kubernetes",
            "helm": "helm",
            "cdk.json": "aws-cdk",
            "SAM": "aws-sam",
        }

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files:
                if file in deploy_indicators:
                    return deploy_indicators[file]
            rel = os.path.relpath(root, repo_path)
            for key, method in deploy_indicators.items():
                if key.lower() in rel.lower():
                    return method

        return "unknown"

    def _detect_ci_cd(self, repo_path: str) -> List[str]:
        """Detect CI/CD configurations."""
        ci_cd = []
        ci_files = {
            ".github/workflows": "github-actions",
            ".gitlab-ci.yml": "gitlab-ci",
            "Jenkinsfile": "jenkins",
            ".circleci/config.yml": "circleci",
            ".travis.yml": "travis",
            "azure-pipelines.yml": "azure-pipelines",
            "bitbucket-pipelines.yml": "bitbucket",
            "cloudbuild.yaml": "cloud-build",
            "buildkite.yml": "buildkite",
        }

        for path, name in ci_files.items():
            full_path = os.path.join(repo_path, path)
            if os.path.isfile(full_path) or os.path.isdir(full_path):
                ci_cd.append(name)

        return ci_cd

    async def _assess_documentation(self, repo_path: str) -> float:
        """Assess documentation quality (0-100)."""
        score = 0.0
        factors = 0

        if os.path.isfile(os.path.join(repo_path, "README.md")):
            try:
                with open(os.path.join(repo_path, "README.md"), "r", encoding="utf-8") as f:
                    content = f.read()
                length = len(content)
                if length > 1000:
                    score += 30
                elif length > 200:
                    score += 15
                elif length > 0:
                    score += 5
                if "##" in content or "**" in content:
                    score += 10
            except OSError:
                pass
            factors += 1

        docs_dir = os.path.join(repo_path, "docs")
        if os.path.isdir(docs_dir):
            doc_files = glob.glob(os.path.join(docs_dir, "**/*.md"), recursive=True)
            doc_files += glob.glob(os.path.join(docs_dir, "**/*.rst"), recursive=True)
            if len(doc_files) > 5:
                score += 30
            elif len(doc_files) > 0:
                score += 15
            factors += 1

        if os.path.isfile(os.path.join(repo_path, "CONTRIBUTING.md")):
            score += 10
        if os.path.isfile(os.path.join(repo_path, "CHANGELOG.md")):
            score += 10
        if os.path.isfile(os.path.join(repo_path, "LICENSE")):
            score += 5

        docstrings_found = 0
        total_functions = 0
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file in files[:50]:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            total_functions += 1
                            if (node.body and isinstance(node.body[0], ast.Expr) and
                                    isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                                docstrings_found += 1
                except (SyntaxError, UnicodeDecodeError):
                    pass

        if total_functions > 0:
            docstring_ratio = docstrings_found / total_functions
            score += min(15, docstring_ratio * 15)

        return min(100, round(score, 1))

    def _calculate_health_score(self, code_style: CodeStyleReport, debt: DebtReport,
                                doc_quality: float, num_languages: int) -> float:
        """Calculate overall health score (0-100, higher is better)."""
        score = 100.0

        score -= min(20, debt.score * 0.2)
        score -= min(15, max(0, 60 - doc_quality) * 0.25)
        if code_style.type_hint_coverage < 30:
            score -= 10
        elif code_style.type_hint_coverage < 60:
            score -= 5
        if code_style.docstring_coverage < 30:
            score -= 10
        elif code_style.docstring_coverage < 60:
            score -= 5
        if num_languages > 5:
            score -= 5

        return max(0, min(100, round(score, 1)))

    def _calculate_risk_score(self, debt: DebtReport, health: float) -> float:
        """Calculate risk score (0-100, higher is riskier)."""
        risk = debt.score * 0.4
        risk += max(0, (100 - health)) * 0.3
        critical_count = sum(1 for i in debt.issues if i.severity == "critical")
        high_count = sum(1 for i in debt.issues if i.severity == "high")
        risk += min(20, critical_count * 5 + high_count * 2)
        return max(0, min(100, round(risk, 1)))
