"""Dashboard collector — orchestrates all analyzers into ProjectMetrics."""

import ast
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from jarvis.dashboard.analyzers import (
    CodeHealthAnalyzer,
    ComplexityAnalyzer,
    DeadCodeAnalyzer,
    DependencyAnalyzer,
    DocumentationAnalyzer,
    DuplicateAnalyzer,
    PerformanceAnalyzer,
    SecurityAnalyzer,
    TestAnalyzer,
    _iter_python_files,
    _read,
    _relative,
    _grade,
    _clamp,
)
from jarvis.dashboard.models import HealthIssue, HealthReport, ProjectMetrics


# File extension -> language name
_LANG_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".r": "R",
    ".R": "R",
    ".sh": "Shell",
    ".bash": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".json": "JSON",
    ".xml": "XML",
    ".sql": "SQL",
    ".md": "Markdown",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
}

# Framework detection signatures
_FRAMEWORK_SIGNATURES = {
    "Django": ["django", "manage.py", "settings.py"],
    "Flask": ["flask", "Flask"],
    "FastAPI": ["fastapi", "FastAPI"],
    "pytest": ["pytest", "conftest.py"],
    "SQLAlchemy": ["sqlalchemy", "SQLAlchemy"],
    "Celery": ["celery", "Celery"],
    "TensorFlow": ["tensorflow", "tf."],
    "PyTorch": ["torch", "nn.Module"],
    "NumPy": ["numpy", "np."],
    "Pandas": ["pandas", "pd."],
    "Requests": ["requests.get", "requests.post"],
    "aiohttp": ["aiohttp"],
    "asyncio": ["asyncio"],
}


class Dashboard:
    """Main metrics collection engine for JARVIS v5.2.0."""

    def __init__(self) -> None:
        self.health_analyzer = CodeHealthAnalyzer()
        self.test_analyzer = TestAnalyzer()
        self.security_analyzer = SecurityAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.dead_code_analyzer = DeadCodeAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()
        self.documentation_analyzer = DocumentationAnalyzer()
        self.duplicate_analyzer = DuplicateAnalyzer()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def collect(self, repo_path: str) -> ProjectMetrics:
        """Collect all metrics for a repository."""
        repo_path = os.path.abspath(repo_path)
        metrics = ProjectMetrics()

        # Basic stats
        loc, files, classes, functions, langs = self._basic_stats(repo_path)
        metrics.total_loc = loc
        metrics.total_files = files
        metrics.total_classes = classes
        metrics.total_functions = functions
        metrics.languages = langs

        # Frameworks
        metrics.frameworks = self._detect_frameworks(repo_path)

        # Test count
        _, test_meta = self.test_analyzer.analyze(repo_path)
        metrics.total_tests = test_meta.get("test_count", 0)

        # Run all analyzers
        health_score, health_issues, health_meta = self.health_analyzer.analyze(repo_path)
        test_score, test_meta = self.test_analyzer.analyze(repo_path)
        sec_score, sec_issues, sec_meta = self.security_analyzer.analyze(repo_path)
        perf_score, perf_issues, perf_meta = self.performance_analyzer.analyze(repo_path)
        cplx_score, cplx_meta = self.complexity_analyzer.analyze(repo_path)
        dead_count, dead_meta = self.dead_code_analyzer.analyze(repo_path)
        dep_score, dep_issues, dep_meta = self.dependency_analyzer.analyze(repo_path)
        doc_score, doc_meta = self.documentation_analyzer.analyze(repo_path)
        dup_score, dup_meta = self.duplicate_analyzer.analyze(repo_path)

        # Populate metrics
        metrics.health_score = _clamp(health_score)
        metrics.test_coverage = _clamp(test_score)
        metrics.security_score = _clamp(sec_score)
        metrics.performance_score = _clamp(perf_score)
        metrics.complexity_score = _clamp(cplx_score)
        metrics.duplication_score = _clamp(dup_score)
        metrics.documentation_score = _clamp(doc_score)

        # Architecture score: weighted combo
        capped_dead = min(dead_count, 50)
        metrics.architecture_score = _clamp(
            health_score * 0.3
            + (100 - min(cplx_meta.get("average_complexity", 0), 20) * 3) * 0.2
            + doc_score * 0.2
            + dup_score * 0.15
            + (100 - capped_dead * 0.5) * 0.15
        )

        # Debt score: how much work is needed (0 = no debt, 100 = maximum)
        capped_sec = min(sec_meta.get("total_issues", 0), 20)
        capped_unpinned = min(dep_meta.get("unpinned", 0), 10)
        metrics.debt_score = _clamp(
            (100 - health_score) * 0.25
            + capped_sec * 2
            + capped_dead * 0.4
            + capped_unpinned * 2
            + (100 - dup_score) * 0.2
        )

        metrics.dead_code_count = dead_count
        metrics.unused_files = dead_meta.get("unused_functions", 0)
        metrics.unused_apis = dead_meta.get("unused_imports", 0) + dead_meta.get("unused_variables", 0)
        metrics.dependency_issues = len(dep_issues)

        return metrics

    async def code_health(self, repo_path: str) -> HealthReport:
        """Full code health analysis with issues and recommendations."""
        repo_path = os.path.abspath(repo_path)
        score, issues, meta = self.health_analyzer.analyze(repo_path)
        _, test_meta = self.test_analyzer.analyze(repo_path)
        sec_score, sec_issues, sec_meta = self.security_analyzer.analyze(repo_path)
        cplx_score, cplx_meta = self.complexity_analyzer.analyze(repo_path)
        doc_score, _ = self.documentation_analyzer.analyze(repo_path)
        dup_score, _ = self.duplicate_analyzer.analyze(repo_path)

        all_issues = issues + sec_issues
        all_issues.sort(key=lambda i: {"critical": 0, "warning": 1, "info": 2}.get(i.severity, 3))

        grades = {
            "code_quality": _grade(score),
            "security": _grade(sec_score),
            "complexity": _grade(cplx_score),
            "documentation": _grade(doc_score),
            "duplication": _grade(dup_score),
            "testing": _grade(test_meta.get("test_count", 0) * 10),
        }

        overall = (score + sec_score + cplx_score + doc_score + dup_score) / 5

        recommendations = []  # type: List[str]
        if sec_meta.get("hardcoded_secrets", 0) > 0:
            recommendations.append("Remove hardcoded secrets and use environment variables")
        if sec_meta.get("eval_exec_usage", 0) > 0:
            recommendations.append("Replace eval()/exec() with safer alternatives")
        if meta.get("long_functions", 0) > 0:
            recommendations.append(f"Refactor {meta['long_functions']} overly long functions")
        if meta.get("type_hint_ratio", 0) < 0.5:
            recommendations.append("Add type hints to improve code clarity")
        if test_meta.get("test_count", 0) == 0:
            recommendations.append("Add tests — no test files detected")
        if cplx_meta.get("complex_functions", 0) > 0:
            recommendations.append(f"Simplify {cplx_meta['complex_functions']} high-complexity functions")
        if doc_score < 50:
            recommendations.append("Improve documentation coverage with docstrings and README")
        if dup_score < 70:
            recommendations.append("Extract duplicate code into shared utilities")

        return HealthReport(
            overall_score=_clamp(overall),
            grades=grades,
            issues=all_issues,
            recommendations=recommendations,
        )

    async def test_coverage(self, repo_path: str) -> Dict[str, Any]:
        """Detailed test coverage analysis."""
        score, meta = self.test_analyzer.analyze(os.path.abspath(repo_path))
        meta["score"] = score
        meta["grade"] = _grade(score)
        return meta

    async def security_score(self, repo_path: str) -> Dict[str, Any]:
        """Security vulnerability scan."""
        score, issues, meta = self.security_analyzer.analyze(os.path.abspath(repo_path))
        meta["score"] = score
        meta["grade"] = _grade(score)
        meta["issues"] = [
            {
                "file": i.file,
                "line": i.line,
                "category": i.category,
                "severity": i.severity,
                "description": i.description,
                "suggestion": i.suggestion,
                "auto_fixable": i.auto_fixable,
            }
            for i in issues
        ]
        return meta

    async def performance_score(self, repo_path: str) -> Dict[str, Any]:
        """Performance indicator analysis."""
        score, issues, meta = self.performance_analyzer.analyze(os.path.abspath(repo_path))
        meta["score"] = score
        meta["grade"] = _grade(score)
        meta["issues"] = [
            {
                "file": i.file,
                "line": i.line,
                "category": i.category,
                "severity": i.severity,
                "description": i.description,
                "suggestion": i.suggestion,
            }
            for i in issues
        ]
        return meta

    async def complexity_report(self, repo_path: str) -> Dict[str, Any]:
        """Code complexity analysis."""
        score, meta = self.complexity_analyzer.analyze(os.path.abspath(repo_path))
        meta["score"] = score
        meta["grade"] = _grade(score)
        return meta

    async def dead_code_analysis(self, repo_path: str) -> Dict[str, Any]:
        """Unused code detection."""
        count, meta = self.dead_code_analyzer.analyze(os.path.abspath(repo_path))
        meta["score"] = _clamp(100 - count * 3)
        meta["grade"] = _grade(meta["score"])
        return meta

    async def dependency_health(self, repo_path: str) -> Dict[str, Any]:
        """Dependency analysis."""
        score, issues, meta = self.dependency_analyzer.analyze(os.path.abspath(repo_path))
        meta["score"] = score
        meta["grade"] = _grade(score)
        meta["issues"] = [
            {
                "file": i.file,
                "category": i.category,
                "severity": i.severity,
                "description": i.description,
                "suggestion": i.suggestion,
            }
            for i in issues
        ]
        return meta

    async def documentation_score(self, repo_path: str) -> Dict[str, Any]:
        """Documentation coverage analysis."""
        score, meta = self.documentation_analyzer.analyze(os.path.abspath(repo_path))
        meta["score"] = score
        meta["grade"] = _grade(score)
        return meta

    async def duplicate_code(self, repo_path: str) -> Dict[str, Any]:
        """Code duplication detection."""
        score, meta = self.duplicate_analyzer.analyze(os.path.abspath(repo_path))
        meta["score"] = score
        meta["grade"] = _grade(score)
        return meta

    async def to_dict(self, metrics: ProjectMetrics) -> Dict[str, Any]:
        """Serialize ProjectMetrics to a dictionary for dashboard consumption."""
        return metrics.to_dict()

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _basic_stats(self, root: str) -> Tuple[int, int, int, int, Dict[str, int]]:
        """Compute LOC, file count, class/function counts, and language breakdown."""
        total_loc = 0
        total_files = 0
        total_classes = 0
        total_functions = 0
        langs = defaultdict(int)  # type: Dict[str, int]

        for dirpath, _, filenames in os.walk(root):
            # skip hidden dirs and __pycache__
            parts = dirpath.split(os.sep)
            if any(p.startswith(".") or p == "__pycache__" for p in parts):
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1]
                if ext not in _LANG_MAP:
                    continue
                full = os.path.join(dirpath, fn)
                total_files += 1
                lang = _LANG_MAP[ext]
                langs[lang] += 1

                if ext == ".py":
                    source = _read(full)
                    loc = len(source.splitlines())
                    total_loc += loc
                    try:
                        tree = ast.parse(source, filename=full)
                    except SyntaxError:
                        continue
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            total_classes += 1
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            total_functions += 1
                else:
                    # non-Python: just count lines
                    total_loc += len(_read(full).splitlines())

        return total_loc, total_files, total_classes, total_functions, dict(langs)

    def _detect_frameworks(self, root: str) -> List[str]:
        """Detect frameworks/libraries from imports and config files."""
        detected = set()  # type: Set[str]

        # Check config files
        for name in ("requirements.txt", "setup.py", "pyproject.toml", "package.json"):
            p = os.path.join(root, name)
            if os.path.isfile(p):
                content = _read(p).lower()
                for fw, sigs in _FRAMEWORK_SIGNATURES.items():
                    for sig in sigs:
                        if sig.lower() in content:
                            detected.add(fw)

        # Check Python imports
        for path in _iter_python_files(root):
            source = _read(path)
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for fw, sigs in _FRAMEWORK_SIGNATURES.items():
                            for sig in sigs:
                                if sig.lower() in alias.name.lower():
                                    detected.add(fw)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for fw, sigs in _FRAMEWORK_SIGNATURES.items():
                            for sig in sigs:
                                if sig.lower() in node.module.lower():
                                    detected.add(fw)

        return sorted(detected)
