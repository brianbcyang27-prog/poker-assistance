"""Specialized code analyzers — health, tests, security, performance, complexity."""

import ast
import hashlib
import math
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from jarvis.dashboard.models import HealthIssue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iter_python_files(root: str) -> List[str]:
    """Recursively collect all .py files under root, skipping hidden dirs."""
    files = []  # type: List[str]
    for dirpath, _, filenames in os.walk(root):
        parts = dirpath.split(os.sep)
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue
        for fn in filenames:
            if fn.endswith(".py"):
                files.append(os.path.join(dirpath, fn))
    return files


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, IOError):
        return ""


def _relative(path: str, root: str) -> str:
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ===========================================================================
# CodeHealthAnalyzer
# ===========================================================================

class CodeHealthAnalyzer:
    """Analyzes code structure, naming, nesting, and type hints."""

    MAX_FUNC_LINES = 50
    MAX_NESTING = 4
    MIN_TYPE_HINT_COVERAGE = 0.5

    def analyze(self, root: str) -> Tuple[float, List[HealthIssue], Dict[str, Any]]:
        issues = []  # type: List[HealthIssue]
        total_funcs = 0
        hinted = 0
        long_funcs = 0
        deep_nesting = 0

        for path in _iter_python_files(root):
            source = _read(path)
            if not source:
                continue
            rel = _relative(path, root)
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue

            lines = source.splitlines()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total_funcs += 1
                    func_lines = (node.end_lineno or node.lineno) - node.lineno + 1
                    if func_lines > self.MAX_FUNC_LINES:
                        long_funcs += 1
                        issues.append(HealthIssue(
                            file=rel, line=node.lineno,
                            category="function_length",
                            severity="warning",
                            description=f"Function '{node.name}' is {func_lines} lines (max {self.MAX_FUNC_LINES})",
                            suggestion="Break into smaller functions",
                        ))
                    # type hint coverage
                    if node.returns is not None:
                        hinted += 1
                    for arg in node.args.args:
                        if arg.annotation is not None:
                            hinted += 1
                            break
                    # nesting depth
                    depth = self._max_nesting(node)
                    if depth > self.MAX_NESTING:
                        deep_nesting += 1
                        issues.append(HealthIssue(
                            file=rel, line=node.lineno,
                            category="nesting_depth",
                            severity="warning",
                            description=f"Function '{node.name}' nesting depth {depth} (max {self.MAX_NESTING})",
                            suggestion="Reduce nesting with early returns or extraction",
                        ))
                    # naming convention
                    if not node.name.startswith("_") and not node.name.isupper():
                        if not re.match(r"^[a-z_][a-z0-9_]*$", node.name):
                            issues.append(HealthIssue(
                                file=rel, line=node.lineno,
                                category="naming_convention",
                                severity="info",
                                description=f"Function '{node.name}' doesn't follow snake_case",
                                suggestion="Rename to snake_case convention",
                                auto_fixable=True,
                            ))

        hint_ratio = hinted / max(total_funcs * 2, 1)
        long_ratio = long_funcs / max(total_funcs, 1)
        nest_ratio = deep_nesting / max(total_funcs, 1)
        health = _clamp(
            100
            - long_ratio * 40       # up to -40 for 100% long functions
            - nest_ratio * 30       # up to -30 for 100% deep nesting
            - max(0, (0.5 - hint_ratio)) * 60  # up to -30 for 0% type hints
        )
        meta = {
            "total_functions": total_funcs,
            "long_functions": long_funcs,
            "deep_nesting": deep_nesting,
            "type_hint_ratio": round(hint_ratio, 3),
        }
        return health, issues, meta

    def _max_nesting(self, node: ast.AST, depth: int = 0) -> int:
        max_d = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)):
                max_d = max(max_d, self._max_nesting(child, depth + 1))
            else:
                max_d = max(max_d, self._max_nesting(child, depth))
        return max_d


# ===========================================================================
# TestAnalyzer
# ===========================================================================

class TestAnalyzer:
    """Analyzes test suite metrics."""

    def analyze(self, root: str) -> Tuple[float, Dict[str, Any]]:
        test_files = []  # type: List[str]
        test_count = 0
        fixture_count = 0
        assertion_count = 0

        for path in _iter_python_files(root):
            bn = os.path.basename(path)
            if bn.startswith("test_") or bn.endswith("_test.py"):
                test_files.append(path)
                source = _read(path)
                if not source:
                    continue
                try:
                    tree = ast.parse(source, filename=path)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("test_"):
                            test_count += 1
                    if isinstance(node, ast.FunctionDef) and any(
                        isinstance(d, ast.Name) and d.id == "fixture"
                        for d in node.decorator_list
                    ):
                        fixture_count += 1
                    # count assert statements
                    if isinstance(node, (ast.Assert, ast.Call)):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Attribute) and node.func.attr in ("assertEqual", "assertTrue", "assertFalse", "assertIn", "assertRaises"):
                                assertion_count += 1
                        else:
                            assertion_count += 1

        # compute total LOC for ratio
        code_loc = 0
        for path in _iter_python_files(root):
            bn = os.path.basename(path)
            if not (bn.startswith("test_") or bn.endswith("_test.py")):
                code_loc += len(_read(path).splitlines())

        test_loc = sum(len(_read(f).splitlines()) for f in test_files)
        ratio = test_loc / max(code_loc, 1)
        assertion_density = assertion_count / max(test_count, 1)

        # score: ratio ~0.3 is ideal, assertion_density ~3 is ideal
        ratio_score = _clamp(ratio / 0.3 * 100)
        density_score = _clamp(assertion_density / 3 * 0.5 * 100 + 50)
        presence_score = _clamp(100 if test_count > 0 else 20)

        score = (ratio_score * 0.3 + density_score * 0.4 + presence_score * 0.3)

        meta = {
            "test_files": len(test_files),
            "test_count": test_count,
            "fixture_count": fixture_count,
            "assertion_count": assertion_count,
            "test_to_code_ratio": round(ratio, 4),
            "assertion_density": round(assertion_density, 2),
        }
        return _clamp(score), meta


# ===========================================================================
# SecurityAnalyzer
# ===========================================================================

class SecurityAnalyzer:
    """Detects common security issues in Python code."""

    SECRET_PATTERNS = [
        (re.compile(r"""(?:password|passwd|secret|api_key|apikey|token)\s*=\s*['"][^'"]+['"]""", re.I), "hardcoded_secret"),
        (re.compile(r"""(?:AWS_SECRET_ACCESS_KEY|AWS_ACCESS_KEY_ID)\s*=\s*['"][^'"]+['"]"""), "aws_secret"),
        (re.compile(r"""-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"""), "private_key"),
    ]
    UNSAFE_BUILTINS = {"eval", "exec", "compile", "__import__"}
    SQL_INJECTION = re.compile(
        r"""(?:execute|cursor\.execute)\s*\(\s*(?:f['"]|['"].*%s|['"].*\+\s*\w)""", re.I
    )

    def analyze(self, root: str) -> Tuple[float, List[HealthIssue], Dict[str, Any]]:
        issues = []  # type: List[HealthIssue]
        secrets = 0
        unsafe_imports = 0
        eval_exec = 0
        sql_inject = 0

        for path in _iter_python_files(root):
            source = _read(path)
            if not source:
                continue
            rel = _relative(path, root)
            lines = source.splitlines()

            for i, line in enumerate(lines, 1):
                for pattern, cat in self.SECRET_PATTERNS:
                    if pattern.search(line):
                        secrets += 1
                        issues.append(HealthIssue(
                            file=rel, line=i, category=cat,
                            severity="critical",
                            description=f"Possible hardcoded secret detected: {cat}",
                            suggestion="Move to environment variable or secret manager",
                        ))

            # SQL injection
            for m in self.SQL_INJECTION.finditer(source):
                line_no = source[:m.start()].count("\n") + 1
                sql_inject += 1
                issues.append(HealthIssue(
                    file=rel, line=line_no, category="sql_injection",
                    severity="critical",
                    description="Potential SQL injection via string interpolation",
                    suggestion="Use parameterized queries",
                    auto_fixable=False,
                ))

            # AST-based checks
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("pickle", "shelve", "marshal"):
                            unsafe_imports += 1
                            issues.append(HealthIssue(
                                file=rel, line=node.lineno, category="unsafe_import",
                                severity="warning",
                                description=f"Unsafe deserialization module '{alias.name}' imported",
                                suggestion="Avoid unpickling untrusted data",
                            ))
                if isinstance(node, ast.ImportFrom):
                    if node.module and ("subprocess" in node.module or "os" in node.module):
                        for alias in node.names:
                            if alias.name in ("system", "popen", "exec*"):
                                pass  # tracked separately
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id in self.UNSAFE_BUILTINS:
                        eval_exec += 1
                        issues.append(HealthIssue(
                            file=rel, line=node.lineno, category="eval_exec",
                            severity="critical",
                            description=f"Use of '{func.id}()' — potential code injection",
                            suggestion="Replace with safe alternatives (ast.literal_eval, importlib)",
                        ))

        total_issues = secrets + unsafe_imports + eval_exec + sql_inject
        score = _clamp(
            100
            - min(secrets, 3) * 20       # max -60 from secrets
            - min(eval_exec, 3) * 15     # max -45 from eval/exec
            - min(sql_inject, 2) * 15    # max -30 from SQL injection
            - min(unsafe_imports, 3) * 5  # max -15 from unsafe imports
        )
        meta = {
            "hardcoded_secrets": secrets,
            "unsafe_imports": unsafe_imports,
            "eval_exec_usage": eval_exec,
            "sql_injection_patterns": sql_inject,
            "total_issues": total_issues,
        }
        return score, issues, meta


# ===========================================================================
# PerformanceAnalyzer
# ===========================================================================

class PerformanceAnalyzer:
    """Detects common performance anti-patterns."""

    LARGE_IMPORT_THRESHOLD = 50  # imports in a single file
    RECURSION_LIMIT = 10

    def analyze(self, root: str) -> Tuple[float, List[HealthIssue], Dict[str, Any]]:
        issues = []  # type: List[HealthIssue]
        n_plus_one = 0
        large_imports = 0
        deep_recursion = 0

        for path in _iter_python_files(root):
            source = _read(path)
            if not source:
                continue
            rel = _relative(path, root)

            # N+1 pattern: loop containing attribute access + function call
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue

            import_count = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_count += 1

                # Detect N+1: for loop with .query / .filter / .get inside
                if isinstance(node, (ast.For, ast.While)):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Attribute):
                                if child.func.attr in ("query", "filter", "get", "fetch", "find", "select"):
                                    n_plus_one += 1
                                    issues.append(HealthIssue(
                                        file=rel, line=node.lineno,
                                        category="n_plus_one",
                                        severity="warning",
                                        description="Possible N+1 query pattern inside loop",
                                        suggestion="Batch queries or use eager loading",
                                    ))
                                    break

                # Detect excessive recursion (functions that call themselves)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._check_recursion(node, rel, issues)

            if import_count > self.LARGE_IMPORT_THRESHOLD:
                large_imports += 1
                issues.append(HealthIssue(
                    file=rel, line=1, category="large_file_imports",
                    severity="info",
                    description=f"File has {import_count} imports (threshold {self.LARGE_IMPORT_THRESHOLD})",
                    suggestion="Consider splitting into smaller modules",
                ))

        score = _clamp(
            100
            - min(n_plus_one, 5) * 6     # max -30
            - min(large_imports, 4) * 5  # max -20
            - min(deep_recursion, 3) * 8 # max -24
        )
        meta = {
            "n_plus_one_patterns": n_plus_one,
            "large_import_files": large_imports,
            "deep_recursion_functions": deep_recursion,
        }
        return score, issues, meta

    def _check_recursion(self, node: ast.FunctionDef, rel: str, issues: List[HealthIssue]) -> None:
        """Check if a function directly calls itself (simple recursion detection)."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == node.name:
                    issues.append(HealthIssue(
                        file=rel, line=node.lineno,
                        category="recursion",
                        severity="info",
                        description=f"Function '{node.name}' calls itself recursively",
                        suggestion="Ensure base case exists or use iterative approach",
                    ))
                    return


# ===========================================================================
# ComplexityAnalyzer
# ===========================================================================

class ComplexityAnalyzer:
    """Estimates cyclomatic and cognitive complexity."""

    BRANCH_NODES = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)
    BOOL_OPS = {"and", "or"}

    def analyze(self, root: str) -> Tuple[float, Dict[str, Any]]:
        func_complexities = []  # type: List[Tuple[str, int, int]]  # (file, line, cc)
        total_cc = 0
        max_cc = 0

        for path in _iter_python_files(root):
            source = _read(path)
            if not source:
                continue
            rel = _relative(path, root)
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cc = self._cyclomatic(node)
                    cog = self._cognitive(node, depth=0)
                    combined = cc + cog
                    total_cc += combined
                    if combined > max_cc:
                        max_cc = combined
                    if combined > 10:
                        func_complexities.append((rel, node.lineno, combined))

        func_count = max(len(func_complexities), 1)
        avg = total_cc / func_count if func_complexities else 0

        # avg < 5 is excellent, > 20 is terrible; cap impact
        score = _clamp(
            100
            - min(avg, 20) * 3           # max -60 from average
            - min(max(0, max_cc - 20), 20) * 1  # max -20 from peak
        )
        meta = {
            "average_complexity": round(avg, 2),
            "max_complexity": max_cc,
            "complex_functions": len(func_complexities),
            "total_combined_complexity": total_cc,
        }
        return score, meta

    def _cyclomatic(self, node: ast.AST) -> int:
        cc = 1
        for child in ast.walk(node):
            if isinstance(child, self.BRANCH_NODES):
                cc += 1
            if isinstance(child, ast.BoolOp):
                cc += len(child.values) - 1
        return cc

    def _cognitive(self, node: ast.AST, depth: int) -> int:
        cog = 0
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While)):
                cog += 1 + depth
                cog += self._cognitive(child, depth + 1)
            elif isinstance(child, ast.Try):
                cog += depth
                cog += self._cognitive(child, depth + 1)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cog += 1 + depth
            else:
                cog += self._cognitive(child, depth)
        return cog


# ===========================================================================
# DeadCodeAnalyzer
# ===========================================================================

class DeadCodeAnalyzer:
    """Finds unused imports, unreferenced functions, and unused variables."""

    def analyze(self, root: str) -> Tuple[int, Dict[str, Any]]:
        total_dead = 0
        unused_imports = 0
        unused_functions = 0
        unused_vars = 0

        all_files = _iter_python_files(root)
        for path in all_files:
            source = _read(path)
            if not source:
                continue
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue

            # Collect all defined names
            defined_names = set()  # type: Set[str]
            imported_names = set()  # type: Set[str]
            used_names = set()  # type: Set[str]

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined_names.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    defined_names.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined_names.add(target.id)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imported_names.add(name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imported_names.add(name)
                elif isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    used_names.add(node.attr)

            # Unused imports
            for name in imported_names:
                if name not in used_names and name != "*":
                    unused_imports += 1
                    total_dead += 1

            # Unused local functions (not exported, not referenced elsewhere)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_"):
                        # Check if used outside definition
                        body_source = ast.get_source_segment(source, node)
                        if body_source:
                            rest = source.replace(body_source, "", 1)
                            if node.name not in rest:
                                unused_functions += 1
                                total_dead += 1

            # Unused variables (simple: assigned but never read)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id in defined_names:
                            # rough heuristic: check if name appears elsewhere
                            count = source.count(target.id)
                            if count == 1:
                                unused_vars += 1
                                total_dead += 1

        meta = {
            "unused_imports": unused_imports,
            "unused_functions": unused_functions,
            "unused_variables": unused_vars,
            "total_dead_code": total_dead,
        }
        return total_dead, meta


# ===========================================================================
# DependencyAnalyzer
# ===========================================================================

class DependencyAnalyzer:
    """Analyzes project dependencies from requirements.txt / setup.py / pyproject.toml."""

    def analyze(self, root: str) -> Tuple[float, List[HealthIssue], Dict[str, Any]]:
        issues = []  # type: List[HealthIssue]
        deps = []  # type: List[str]
        dep_files_found = []  # type: List[str]

        # Discover dependency files
        req_path = os.path.join(root, "requirements.txt")
        if os.path.isfile(req_path):
            deps.extend(self._parse_requirements(req_path))
            dep_files_found.append("requirements.txt")

        setup_path = os.path.join(root, "setup.py")
        if os.path.isfile(setup_path):
            deps.extend(self._parse_setup_py(setup_path))
            dep_files_found.append("setup.py")

        pyproject_path = os.path.join(root, "pyproject.toml")
        if os.path.isfile(pyproject_path):
            deps.extend(self._parse_pyproject(pyproject_path))
            dep_files_found.append("pyproject.toml")

        # Check for outdated indicators (version pins with ==)
        pinned = [d for d in deps if "==" in d]
        unpinned = [d for d in deps if "==" not in d and d]

        # Check if deps are actually imported
        imported_modules = set()  # type: Set[str]
        for path in _iter_python_files(root):
            source = _read(path)
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.add(node.module.split(".")[0])

        unused_deps = []  # type: List[str]
        for dep in deps:
            name = re.split(r"[><=!~]", dep)[0].strip().lower().replace("-", "_")
            # Normalize common package names
            name_map = {"pillow": "PIL", "scikit_learn": "sklearn", "pyyaml": "yaml"}
            check_name = name_map.get(name, name)
            if check_name not in imported_modules and name not in imported_modules:
                unused_deps.append(dep)

        for dep in unused_deps:
            issues.append(HealthIssue(
                file="dependencies", line=0,
                category="unused_dependency",
                severity="info",
                description=f"Dependency '{dep}' appears unused",
                suggestion="Remove if not needed at runtime",
            ))

        score = _clamp(100 - min(len(unpinned), 10) * 3 - min(len(unused_deps), 5) * 5)
        meta = {
            "total_dependencies": len(deps),
            "pinned": len(pinned),
            "unpinned": len(unpinned),
            "unused_dependencies": unused_deps,
            "dependency_files": dep_files_found,
            "imported_modules": sorted(imported_modules),
        }
        return score, issues, meta

    def _parse_requirements(self, path: str) -> List[str]:
        deps = []  # type: List[str]
        for line in _read(path).splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                deps.append(line)
        return deps

    def _parse_setup_py(self, path: str) -> List[str]:
        source = _read(path)
        deps = []  # type: List[str]
        match = re.search(r"install_requires\s*=\s*\[(.*?)\]", source, re.S)
        if match:
            for item in re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)):
                deps.append(item)
        return deps

    def _parse_pyproject(self, path: str) -> List[str]:
        source = _read(path)
        deps = []  # type: List[str]
        # Simple regex for [project] dependencies = [...]
        match = re.search(r"dependencies\s*=\s*\[(.*?)\]", source, re.S)
        if match:
            for item in re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)):
                deps.append(item)
        return deps


# ===========================================================================
# DocumentationAnalyzer
# ===========================================================================

class DocumentationAnalyzer:
    """Measures documentation coverage and quality."""

    def analyze(self, root: str) -> Tuple[float, Dict[str, Any]]:
        total_funcs = 0
        documented_funcs = 0
        total_classes = 0
        documented_classes = 0
        has_readme = False
        readme_length = 0
        modules_with_docs = 0
        total_modules = 0

        for path in _iter_python_files(root):
            source = _read(path)
            if not source:
                continue
            total_modules += 1
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue

            # Module docstring
            if ast.get_docstring(tree):
                modules_with_docs += 1

            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total_funcs += 1
                    if ast.get_docstring(node):
                        documented_funcs += 1
                elif isinstance(node, ast.ClassDef):
                    total_classes += 1
                    if ast.get_docstring(node):
                        documented_classes += 1

        # README check
        for name in ("README.md", "README.rst", "README.txt", "README"):
            p = os.path.join(root, name)
            if os.path.isfile(p):
                has_readme = True
                readme_length = len(_read(p).splitlines())
                break

        func_ratio = documented_funcs / max(total_funcs, 1)
        class_ratio = documented_classes / max(total_classes, 1)
        module_ratio = modules_with_docs / max(total_modules, 1)

        readme_score = 0.0
        if has_readme:
            readme_score = min(100, readme_length * 2)

        score = _clamp(
            func_ratio * 40 + class_ratio * 20 + module_ratio * 20 + readme_score * 0.2
        )
        meta = {
            "total_functions": total_funcs,
            "documented_functions": documented_funcs,
            "total_classes": total_classes,
            "documented_classes": documented_classes,
            "total_modules": total_modules,
            "documented_modules": modules_with_docs,
            "has_readme": has_readme,
            "readme_lines": readme_length,
            "function_docstring_ratio": round(func_ratio, 3),
            "class_docstring_ratio": round(class_ratio, 3),
        }
        return score, meta


# ===========================================================================
# DuplicateAnalyzer
# ===========================================================================

class DuplicateAnalyzer:
    """Detects duplicate code via function body hashing."""

    MIN_FUNC_LINES = 5

    def analyze(self, root: str) -> Tuple[float, Dict[str, Any]]:
        body_hashes = defaultdict(list)  # type: Dict[str, List[Tuple[str, int, str]]]
        total_funcs = 0

        for path in _iter_python_files(root):
            source = _read(path)
            if not source:
                continue
            rel = _relative(path, root)
            try:
                tree = ast.parse(source, filename=path)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total_funcs += 1
                    lines = (node.end_lineno or node.lineno) - node.lineno + 1
                    if lines < self.MIN_FUNC_LINES:
                        continue
                    # Hash the function body (excluding decorators and signature)
                    body_start = node.lineno
                    body_end = node.end_lineno or node.lineno
                    body_lines = source.splitlines()[body_start - 1:body_end]
                    # Normalize: strip whitespace, skip blank lines
                    normalized = "\n".join(
                        l.strip() for l in body_lines if l.strip()
                    )
                    if not normalized:
                        continue
                    h = hashlib.md5(normalized.encode()).hexdigest()
                    body_hashes[h].append((rel, node.lineno, node.name))

        # Find duplicates
        duplicate_groups = 0
        duplicate_lines = 0
        duplicates = []  # type: List[Dict[str, Any]]

        for h, locations in body_hashes.items():
            if len(locations) > 1:
                duplicate_groups += 1
                group = []
                for f, line, name in locations:
                    group.append({"file": f, "line": line, "function": name})
                    duplicate_lines += (line + self.MIN_FUNC_LINES) - line
                duplicates.append({"hash": h, "locations": group})

        dup_ratio = duplicate_lines / max(total_funcs * self.MIN_FUNC_LINES, 1)
        score = _clamp(100 - min(dup_ratio * 200, 50) - min(duplicate_groups, 5) * 10)
        meta = {
            "total_functions": total_funcs,
            "duplicate_groups": duplicate_groups,
            "duplicate_functions": sum(len(g["locations"]) for g in duplicates),
            "estimated_duplicate_lines": duplicate_lines,
            "duplicate_details": duplicates[:20],  # cap output
        }
        return score, meta
