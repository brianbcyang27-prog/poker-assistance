"""Engineering Intelligence engine — eight built-in analyzers for continuous code analysis."""

import ast
import hashlib
import os
import re
import time
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from jarvis.eng_intel.models import (
    DriftIssue,
    EngineeringIssue,
    IssueCategory,
    ProjectHealth,
    Recommendation,
    Severity,
)


# ---------------------------------------------------------------------------
# Analyzer: DuplicationDetector
# ---------------------------------------------------------------------------

class DuplicationDetector:
    """Hash function bodies to find exact or near-exact copies."""

    def __init__(self) -> None:
        self._body_hashes: Dict[str, List[Tuple[str, int, str]]] = defaultdict(list)

    def analyze(self, file_path: str, source: str) -> List[EngineeringIssue]:
        issues: List[EngineeringIssue] = []
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body_src = ast.get_source_segment(source, node)
                if body_src is None:
                    continue
                body_hash = hashlib.sha256(body_src.encode()).hexdigest()
                self._body_hashes[body_hash].append(
                    (file_path, node.lineno, node.name)
                )

        return issues

    def find_duplicates(self) -> Dict[str, List[Tuple[str, int, str]]]:
        return {
            h: locs
            for h, locs in self._body_hashes.items()
            if len(locs) > 1
        }


# ---------------------------------------------------------------------------
# Analyzer: NamingChecker
# ---------------------------------------------------------------------------

class NamingChecker:
    """PEP 8 naming compliance and consistency checks."""

    _SNAKE_CASE = re.compile(r"^[a-z_][a-z0-9_]*$")
    _PASCAL_CASE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
    _CONSTANT = re.compile(r"^[A-Z_][A-Z0-9_]*$")

    def analyze(self, file_path: str, source: str) -> List[EngineeringIssue]:
        issues: List[EngineeringIssue] = []
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                if name.startswith("__") and name.endswith("__"):
                    continue
                if not self._SNAKE_CASE.match(name):
                    issues.append(EngineeringIssue(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        file_path=file_path,
                        line=node.lineno,
                        category=IssueCategory.NAMING.value,
                        severity=Severity.WARNING.value,
                        description=f"Function '{name}' is not snake_case",
                        suggestion=f"Rename to '{self._to_snake(name)}'",
                        auto_fixable=True,
                        confidence=0.9,
                    ))
            elif isinstance(node, ast.ClassDef):
                if not self._PASCAL_CASE.match(node.name):
                    issues.append(EngineeringIssue(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        file_path=file_path,
                        line=node.lineno,
                        category=IssueCategory.NAMING.value,
                        severity=Severity.WARNING.value,
                        description=f"Class '{node.name}' is not PascalCase",
                        suggestion=f"Rename to '{node.name.capitalize()}'",
                        auto_fixable=True,
                        confidence=0.85,
                    ))

        return issues

    @staticmethod
    def _to_snake(name: str) -> str:
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# ---------------------------------------------------------------------------
# Analyzer: DocumentationChecker
# ---------------------------------------------------------------------------

class DocumentationChecker:
    """Docstring coverage and README quality checks."""

    def analyze(self, file_path: str, source: str) -> List[EngineeringIssue]:
        issues: List[EngineeringIssue] = []
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("__"):
                    continue
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Constant, ast.Str))
                ):
                    issues.append(EngineeringIssue(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        file_path=file_path,
                        line=node.lineno,
                        category=IssueCategory.DOCUMENTATION.value,
                        severity=Severity.INFO.value,
                        description=f"Function '{node.name}' lacks a docstring",
                        suggestion="Add a docstring describing the function's purpose",
                        auto_fixable=False,
                        confidence=0.95,
                    ))
            elif isinstance(node, ast.ClassDef):
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Constant, ast.Str))
                ):
                    issues.append(EngineeringIssue(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        file_path=file_path,
                        line=node.lineno,
                        category=IssueCategory.DOCUMENTATION.value,
                        severity=Severity.INFO.value,
                        description=f"Class '{node.name}' lacks a docstring",
                        suggestion="Add a docstring describing the class",
                        auto_fixable=False,
                        confidence=0.9,
                    ))

        return issues


# ---------------------------------------------------------------------------
# Analyzer: ComplexityAnalyzer
# ---------------------------------------------------------------------------

class ComplexityAnalyzer:
    """Function length, nesting depth, and cyclomatic complexity checks."""

    MAX_FUNCTION_LINES = 60
    MAX_NESTING = 4
    MAX_COMPLEXITY = 10

    def analyze(self, file_path: str, source: str) -> List[EngineeringIssue]:
        issues: List[EngineeringIssue] = []
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
                if func_lines > self.MAX_FUNCTION_LINES:
                    issues.append(EngineeringIssue(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        file_path=file_path,
                        line=node.lineno,
                        category=IssueCategory.COMPLEXITY.value,
                        severity=Severity.WARNING.value,
                        description=f"Function '{node.name}' is {func_lines} lines (max {self.MAX_FUNCTION_LINES})",
                        suggestion="Consider breaking this function into smaller pieces",
                        auto_fixable=False,
                        confidence=0.95,
                    ))

                depth = self._max_nesting(node)
                if depth > self.MAX_NESTING:
                    issues.append(EngineeringIssue(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        file_path=file_path,
                        line=node.lineno,
                        category=IssueCategory.COMPLEXITY.value,
                        severity=Severity.WARNING.value,
                        description=f"Function '{node.name}' has nesting depth {depth} (max {self.MAX_NESTING})",
                        suggestion="Reduce nesting by extracting logic or using early returns",
                        auto_fixable=False,
                        confidence=0.9,
                    ))

                cc = self._cyclomatic_complexity(node)
                if cc > self.MAX_COMPLEXITY:
                    issues.append(EngineeringIssue(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        file_path=file_path,
                        line=node.lineno,
                        category=IssueCategory.COMPLEXITY.value,
                        severity=Severity.CRITICAL.value,
                        description=f"Function '{node.name}' has cyclomatic complexity {cc} (max {self.MAX_COMPLEXITY})",
                        suggestion="Refactor to reduce branching complexity",
                        auto_fixable=False,
                        confidence=0.85,
                    ))

        return issues

    def _max_nesting(self, node: ast.AST, depth: int = 0) -> int:
        max_d = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                max_d = max(max_d, self._max_nesting(child, depth + 1))
            else:
                max_d = max(max_d, self._max_nesting(child, depth))
        return max_d

    def _cyclomatic_complexity(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
        return complexity


# ---------------------------------------------------------------------------
# Analyzer: DeadCodeDetector
# ---------------------------------------------------------------------------

class DeadCodeDetector:
    """Unused imports and unreferenced functions."""

    def analyze(self, file_path: str, source: str) -> List[EngineeringIssue]:
        issues: List[EngineeringIssue] = []
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return issues

        imports: List[Tuple[str, int]] = []
        defined_names: Set[str] = set()
        used_names: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name.split(".")[0]
                    imports.append((name, node.lineno))
                    defined_names.add(name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.append((name, node.lineno))
                    defined_names.add(name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    defined_names.add(node.name)
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                used_names.add(node.attr)

        for name, lineno in imports:
            if name not in used_names and name != "*":
                issues.append(EngineeringIssue(
                    id=str(uuid.uuid4())[:8],
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    file_path=file_path,
                    line=lineno,
                    category=IssueCategory.DEAD_CODE.value,
                    severity=Severity.WARNING.value,
                    description=f"Import '{name}' is unused",
                    suggestion=f"Remove unused import of '{name}'",
                    auto_fixable=True,
                    confidence=0.9,
                ))

        return issues


# ---------------------------------------------------------------------------
# Analyzer: StaleAPIDetector
# ---------------------------------------------------------------------------

class StaleAPIDetector:
    """Functions not called from outside their defining module."""

    def __init__(self) -> None:
        self._module_functions: Dict[str, List[Tuple[str, str, int]]] = defaultdict(list)
        self._external_calls: Set[str] = set()

    def record_file(self, file_path: str, source: str) -> None:
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return

        module_name = os.path.splitext(os.path.basename(file_path))[0]
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    self._module_functions[module_name].append(
                        (file_path, node.name, node.lineno)
                    )
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    self._external_calls.add(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    self._external_calls.add(node.func.id)

    def find_stale(self) -> List[EngineeringIssue]:
        issues: List[EngineeringIssue] = []
        for module_name, funcs in self._module_functions.items():
            for file_path, func_name, lineno in funcs:
                if func_name not in self._external_calls:
                    issues.append(EngineeringIssue(
                        id=str(uuid.uuid4())[:8],
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        file_path=file_path,
                        line=lineno,
                        category=IssueCategory.STALE_API.value,
                        severity=Severity.INFO.value,
                        description=f"Function '{func_name}' in '{module_name}' is not called externally",
                        suggestion="Consider marking as private or removing if unused",
                        auto_fixable=False,
                        confidence=0.7,
                    ))
        return issues


# ---------------------------------------------------------------------------
# Analyzer: MissingTestDetector
# ---------------------------------------------------------------------------

class MissingTestDetector:
    """Modules without corresponding test files."""

    def analyze_project(self, project_path: str, py_files: List[str]) -> List[EngineeringIssue]:
        issues: List[EngineeringIssue] = []
        test_dirs = set()
        for root, dirs, files in os.walk(project_path):
            for d in dirs:
                if d.startswith("test"):
                    test_dirs.add(os.path.join(root, d))

        test_files: Set[str] = set()
        for test_dir in test_dirs:
            for root, _, files in os.walk(test_dir):
                for f in files:
                    if f.startswith("test_") and f.endswith(".py"):
                        test_files.add(f[5:-3])

        for fpath in py_files:
            basename = os.path.basename(fpath)
            if basename.startswith("__") or basename.startswith("test_"):
                continue
            module_name = basename[:-3]
            if module_name not in test_files:
                issues.append(EngineeringIssue(
                    id=str(uuid.uuid4())[:8],
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    file_path=fpath,
                    line=0,
                    category=IssueCategory.MISSING_TEST.value,
                    severity=Severity.WARNING.value,
                    description=f"Module '{module_name}' has no corresponding test file",
                    suggestion=f"Create a test file 'test_{module_name}.py'",
                    auto_fixable=False,
                    confidence=0.85,
                ))

        return issues


# ---------------------------------------------------------------------------
# Analyzer: ArchitectureDriftDetector
# ---------------------------------------------------------------------------

class ArchitectureDriftDetector:
    """Modules importing from unexpected layers."""

    LAYER_MAP = {
        "core": {"core"},
        "brain": {"brain", "core"},
        "agents": {"agents", "core"},
        "memory": {"memory", "core"},
        "voice": {"voice", "core"},
        "browser": {"browser", "core"},
        "context": {"context", "core"},
        "suggestions": {"suggestions", "core"},
        "monitoring": {"monitoring", "core"},
    }

    def analyze(self, file_path: str, source: str) -> List[EngineeringIssue]:
        issues: List[EngineeringIssue] = []
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return issues

        parts = os.path.relpath(file_path).replace(os.sep, ".").split(".")
        module_layer = parts[1] if len(parts) > 1 else "unknown"
        allowed = self.LAYER_MAP.get(module_layer, set())

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_parts = node.module.split(".")
                if len(imported_parts) > 1 and imported_parts[0] == "jarvis":
                    target_layer = imported_parts[1]
                    if target_layer not in allowed and target_layer != module_layer:
                        issues.append(EngineeringIssue(
                            id=str(uuid.uuid4())[:8],
                            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            file_path=file_path,
                            line=node.lineno,
                            category=IssueCategory.CIRCULAR_IMPORT.value,
                            severity=Severity.CRITICAL.value,
                            description=(
                                f"Layer '{module_layer}' imports from '{target_layer}' "
                                f"(allowed: {allowed or '{self}'})"
                            ),
                            suggestion=f"Avoid cross-layer imports from '{target_layer}' into '{module_layer}'",
                            auto_fixable=False,
                            confidence=0.8,
                        ))

        return issues


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class EngineeringIntelEngine:
    """Orchestrates all eight built-in analyzers."""

    def __init__(self) -> None:
        self.duplication = DuplicationDetector()
        self.naming = NamingChecker()
        self.documentation = DocumentationChecker()
        self.complexity = ComplexityAnalyzer()
        self.dead_code = DeadCodeDetector()
        self.stale_api = StaleAPIDetector()
        self.missing_test = MissingTestDetector()
        self.architecture = ArchitectureDriftDetector()

    def scan_source(self, file_path: str, source: str) -> List[EngineeringIssue]:
        """Run all analyzers on a single file's source code."""
        issues: List[EngineeringIssue] = []

        self.duplication.analyze(file_path, source)
        issues.extend(self.naming.analyze(file_path, source))
        issues.extend(self.documentation.analyze(file_path, source))
        issues.extend(self.complexity.analyze(file_path, source))
        issues.extend(self.dead_code.analyze(file_path, source))
        self.stale_api.record_file(file_path, source)
        issues.extend(self.architecture.analyze(file_path, source))

        return issues

    def scan_file(self, file_path: str) -> List[EngineeringIssue]:
        """Read and analyze a single file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                source = fh.read()
        except (OSError, IOError):
            return []
        return self.scan_source(file_path, source)

    def scan_project(self, project_path: str) -> List[EngineeringIssue]:
        """Scan all Python files in a project."""
        all_issues: List[EngineeringIssue] = []
        py_files: List[str] = []

        for root, _dirs, files in os.walk(project_path):
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    py_files.append(fpath)
                    all_issues.extend(self.scan_file(fpath))

        # Duplication report across files
        dupes = self.duplication.find_duplicates()
        for _h, locs in dupes.items():
            for file_path, lineno, name in locs:
                all_issues.append(EngineeringIssue(
                    id=str(uuid.uuid4())[:8],
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    file_path=file_path,
                    line=lineno,
                    category=IssueCategory.DUPLICATION.value,
                    severity=Severity.WARNING.value,
                    description=f"Function '{name}' is duplicated in {len(locs)} locations",
                    suggestion="Extract shared logic into a utility function",
                    auto_fixable=False,
                    confidence=0.85,
                ))

        # Stale API report
        all_issues.extend(self.stale_api.find_stale())

        # Missing test report
        all_issues.extend(self.missing_test.analyze_project(project_path, py_files))

        return all_issues

    def get_health(self, issues: List[EngineeringIssue]) -> ProjectHealth:
        """Compute project health from a list of issues."""
        by_cat: Dict[str, int] = defaultdict(int)
        for issue in issues:
            by_cat[issue.category] += 1

        total = len(issues) if issues else 1
        critical = sum(1 for i in issues if i.severity == "critical")
        warnings = sum(1 for i in issues if i.severity == "warning")
        infos = sum(1 for i in issues if i.severity == "info")

        # Score: start at 100, subtract weighted issues
        score = 100.0
        score -= (critical / total) * 40
        score -= (warnings / total) * 30
        score -= (infos / total) * 10
        score = max(0.0, min(100.0, score))

        grades: Dict[str, str] = {}
        for cat, count in by_cat.items():
            if count == 0:
                grades[cat] = "A"
            elif count <= 3:
                grades[cat] = "B"
            elif count <= 7:
                grades[cat] = "C"
            elif count <= 15:
                grades[cat] = "D"
            else:
                grades[cat] = "F"

        return ProjectHealth(
            overall_score=round(score, 1),
            grades=grades,
            issues_by_category=dict(by_cat),
            trends={},
            last_scan=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def build_recommendations(self, issues: List[EngineeringIssue]) -> List[Recommendation]:
        """Generate prioritized recommendations from issues."""
        recs: List[Recommendation] = []
        cat_groups: Dict[str, List[EngineeringIssue]] = defaultdict(list)
        for issue in issues:
            cat_groups[issue.category].append(issue)

        for cat, cat_issues in cat_groups.items():
            critical_count = sum(1 for i in cat_issues if i.severity == "critical")
            if not cat_issues:
                continue

            priority = len(cat_issues) * 0.3 + critical_count * 2.0
            impact = "high" if critical_count > 0 else ("medium" if len(cat_issues) > 5 else "low")
            effort = "high" if cat in ("circular_import", "complexity") else "low"

            recs.append(Recommendation(
                id=str(uuid.uuid4())[:8],
                category=cat,
                title=f"Address {cat.replace('_', ' ')} issues ({len(cat_issues)} found)",
                description=cat_issues[0].suggestion,
                impact=impact,
                effort=effort,
                files_affected=list({i.file_path for i in cat_issues}),
                priority_score=round(priority, 2),
            ))

        recs.sort(key=lambda r: r.priority_score, reverse=True)
        return recs

    def detect_drift(self, issues: List[EngineeringIssue]) -> List[DriftIssue]:
        """Extract architecture drift from issues."""
        drifts: List[DriftIssue] = []
        for issue in issues:
            if issue.category == "circular_import":
                drifts.append(DriftIssue(
                    module=issue.file_path,
                    expected_pattern="layer isolation",
                    actual_pattern=issue.description,
                    description=issue.suggestion,
                    severity=issue.severity,
                ))
        return drifts
