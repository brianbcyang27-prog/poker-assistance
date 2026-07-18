"""Main RefactoringEngine class for JARVIS v5.2.0."""

import ast
import hashlib
import os
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from .models import IssueCategory, RefactorIssue, RefactorProposal, RiskLevel, Severity


class RefactoringEngine:
    """Autonomous Refactoring Engine that scans codebases and generates proposals."""

    def __init__(self) -> None:
        self._file_cache: Dict[str, str] = {}
        self._ast_cache: Dict[str, ast.Module] = {}

    def _read_file(self, filepath: str) -> Optional[str]:
        """Read file contents with caching."""
        if filepath in self._file_cache:
            return self._file_cache[filepath]
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self._file_cache[filepath] = content
            return content
        except (IOError, OSError):
            return None

    def _parse_ast(self, filepath: str) -> Optional[ast.Module]:
        """Parse Python file to AST with caching."""
        if filepath in self._ast_cache:
            return self._ast_cache[filepath]
        content = self._read_file(filepath)
        if content is None:
            return None
        try:
            tree = ast.parse(content, filename=filepath)
            self._ast_cache[filepath] = tree
            return tree
        except SyntaxError:
            return None

    def _get_python_files(self, repo_path: str) -> List[str]:
        """Recursively find all Python files in repo."""
        python_files = []
        for root, _dirs, files in os.walk(repo_path):
            if "__pycache__" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    python_files.append(os.path.join(root, f))
        return python_files

    def _get_code_snippet(self, filepath: str, line: int, context: int = 3) -> str:
        """Extract code snippet around a line."""
        content = self._read_file(filepath)
        if content is None:
            return ""
        lines = content.splitlines()
        start = max(0, line - context - 1)
        end = min(len(lines), line + context)
        return "\n".join(lines[start:end])

    async def scan(self, repo_path: str) -> List[RefactorIssue]:
        """Scan for all issues across the codebase."""
        all_issues: List[RefactorIssue] = []
        all_issues.extend(await self.scan_duplicates(repo_path))
        all_issues.extend(await self.scan_large_functions(repo_path))
        all_issues.extend(await self.scan_naming(repo_path))
        all_issues.extend(await self.scan_unused(repo_path))
        all_issues.extend(await self.scan_circular_imports(repo_path))
        all_issues.extend(await self.scan_code_smells(repo_path))
        all_issues.extend(await self.scan_long_files(repo_path))
        all_issues.extend(await self.scan_missing_docs(repo_path))
        all_issues.extend(await self.scan_high_complexity(repo_path))
        return all_issues

    async def scan_duplicates(self, repo_path: str) -> List[RefactorIssue]:
        """Detect duplicate code blocks using content hashing."""
        issues: List[RefactorIssue] = []
        file_blocks: Dict[str, List[Tuple[str, int, int]]] = {}

        python_files = self._get_python_files(repo_path)
        for filepath in python_files:
            content = self._read_file(filepath)
            if content is None:
                continue
            lines = content.splitlines()
            blocks = []
            i = 0
            while i < len(lines) - 14:
                block = "\n".join(lines[i:i + 15])
                if len(block.strip()) > 100:
                    block_hash = hashlib.md5(block.encode()).hexdigest()
                    blocks.append((block_hash, i + 1, i + 15))
                i += 5
            if blocks:
                file_blocks[filepath] = blocks

        seen_hashes: Dict[str, List[Tuple[str, int]]] = {}
        for filepath, blocks in file_blocks.items():
            for block_hash, start_line, end_line in blocks:
                if block_hash not in seen_hashes:
                    seen_hashes[block_hash] = []
                seen_hashes[block_hash].append((filepath, start_line))

        for block_hash, locations in seen_hashes.items():
            if len(locations) > 1:
                files = list(set(loc for loc, _ in locations))
                for filepath, line in locations:
                    snippet = self._get_code_snippet(filepath, line)
                    issues.append(RefactorIssue(
                        file=filepath,
                        line=line,
                        category=IssueCategory.DUPLICATION,
                        description=f"Duplicate code block found in {len(files)} locations",
                        severity=Severity.MEDIUM if len(files) == 2 else Severity.HIGH,
                        code_snippet=snippet,
                        suggestion=f"Extract common code into a shared function or module",
                    ))
        return issues

    async def scan_large_functions(
        self, repo_path: str, max_lines: int = 50
    ) -> List[RefactorIssue]:
        """Find functions exceeding max_lines."""
        issues: List[RefactorIssue] = []
        python_files = self._get_python_files(repo_path)

        for filepath in python_files:
            tree = self._parse_ast(filepath)
            if tree is None:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if hasattr(node, "end_lineno") and node.end_lineno is not None:
                        func_lines = node.end_lineno - node.lineno + 1
                        if func_lines > max_lines:
                            snippet = self._get_code_snippet(filepath, node.lineno)
                            issues.append(RefactorIssue(
                                file=filepath,
                                line=node.lineno,
                                category=IssueCategory.CODE_SMELL,
                                description=f"Function '{node.name}' is {func_lines} lines (max {max_lines})",
                                severity=Severity.HIGH if func_lines > max_lines * 2 else Severity.MEDIUM,
                                code_snippet=snippet,
                                suggestion=f"Break '{node.name}' into smaller, focused functions",
                            ))
        return issues

    async def scan_naming(self, repo_path: str) -> List[RefactorIssue]:
        """Check naming conventions (PEP 8)."""
        issues: List[RefactorIssue] = []
        python_files = self._get_python_files(repo_path)
        bad_name_pattern = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
        const_pattern = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")

        for filepath in python_files:
            tree = self._parse_ast(filepath)
            if tree is None:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not bad_name_pattern.match(node.name) and not node.name.startswith("_"):
                        snippet = self._get_code_snippet(filepath, node.lineno)
                        issues.append(RefactorIssue(
                            file=filepath,
                            line=node.lineno,
                            category=IssueCategory.NAMING,
                            description=f"Function '{node.name}' doesn't follow snake_case",
                            severity=Severity.LOW,
                            code_snippet=snippet,
                            suggestion=f"Rename to snake_case convention",
                        ))
                elif isinstance(node, ast.ClassDef):
                    if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                        snippet = self._get_code_snippet(filepath, node.lineno)
                        issues.append(RefactorIssue(
                            file=filepath,
                            line=node.lineno,
                            category=IssueCategory.NAMING,
                            description=f"Class '{node.name}' doesn't follow PascalCase",
                            severity=Severity.LOW,
                            code_snippet=snippet,
                            suggestion=f"Rename to PascalCase convention",
                        ))
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if not const_pattern.match(target.id) and target.id.isupper():
                                snippet = self._get_code_snippet(filepath, node.lineno)
                                issues.append(RefactorIssue(
                                    file=filepath,
                                    line=node.lineno,
                                    category=IssueCategory.NAMING,
                                    description=f"Variable '{target.id}' looks like a constant but naming is inconsistent",
                                    severity=Severity.LOW,
                                    code_snippet=snippet,
                                    suggestion="Use UPPER_SNAKE_CASE for constants or lowercase for variables",
                                ))
        return issues

    async def scan_unused(self, repo_path: str) -> List[RefactorIssue]:
        """Find unused imports and variables."""
        issues: List[RefactorIssue] = []
        python_files = self._get_python_files(repo_path)

        for filepath in python_files:
            content = self._read_file(filepath)
            tree = self._parse_ast(filepath)
            if content is None or tree is None:
                continue

            imports: List[Tuple[str, int]] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name.split(".")[0]
                        imports.append((name, node.lineno))
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imports.append((name, node.lineno))

            lines = content.splitlines()
            for name, lineno in imports:
                used = False
                for i, line in enumerate(lines):
                    if i + 1 == lineno:
                        continue
                    if re.search(r"\b" + re.escape(name) + r"\b", line):
                        used = True
                        break
                if not used:
                    snippet = self._get_code_snippet(filepath, lineno)
                    issues.append(RefactorIssue(
                        file=filepath,
                        line=lineno,
                        category=IssueCategory.UNUSED,
                        description=f"Unused import or alias '{name}'",
                        severity=Severity.LOW,
                        code_snippet=snippet,
                        suggestion=f"Remove unused import '{name}'",
                    ))
        return issues

    async def scan_circular_imports(self, repo_path: str) -> List[RefactorIssue]:
        """Detect circular import dependencies."""
        issues: List[RefactorIssue] = []
        python_files = self._get_python_files(repo_path)
        module_imports: Dict[str, Set[str]] = defaultdict(set)

        for filepath in python_files:
            tree = self._parse_ast(filepath)
            if tree is None:
                continue

            module_name = filepath.replace(repo_path, "").replace("/", ".").replace("\\", ".")
            if module_name.startswith("."):
                module_name = module_name[1:]
            if module_name.endswith(".py"):
                module_name = module_name[:-3]

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.level == 0:
                        module_imports[module_name].add(node.module)

        for module, imports in module_imports.items():
            for imp in imports:
                if imp in module_imports and module in module_imports[imp]:
                    filepath = module.replace(".", "/") + ".py"
                    issues.append(RefactorIssue(
                        file=os.path.join(repo_path, filepath) if not os.path.isabs(filepath) else filepath,
                        line=1,
                        category=IssueCategory.CIRCULAR_IMPORT,
                        description=f"Circular import between '{module}' and '{imp}'",
                        severity=Severity.HIGH,
                        code_snippet=f"import {imp}  # in {module}",
                        suggestion="Use lazy imports, protocols, or restructure to break the cycle",
                    ))
        return issues

    async def scan_code_smells(self, repo_path: str) -> List[RefactorIssue]:
        """Detect code smells: long parameters, deep nesting, god classes."""
        issues: List[RefactorIssue] = []
        python_files = self._get_python_files(repo_path)

        for filepath in python_files:
            tree = self._parse_ast(filepath)
            if tree is None:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    all_args = node.args.args + node.args.posonlyargs + node.args.kwonlyargs
                    if len(all_args) > 5:
                        snippet = self._get_code_snippet(filepath, node.lineno)
                        issues.append(RefactorIssue(
                            file=filepath,
                            line=node.lineno,
                            category=IssueCategory.CODE_SMELL,
                            description=f"Function '{node.name}' has {len(all_args)} parameters (max 5)",
                            severity=Severity.MEDIUM,
                            code_snippet=snippet,
                            suggestion="Use a dataclass or dict to group related parameters",
                        ))

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    max_depth = self._get_nesting_depth(node)
                    if max_depth > 4:
                        snippet = self._get_code_snippet(filepath, node.lineno)
                        issues.append(RefactorIssue(
                            file=filepath,
                            line=node.lineno,
                            category=IssueCategory.CODE_SMELL,
                            description=f"Function '{node.name}' has nesting depth of {max_depth} (max 4)",
                            severity=Severity.MEDIUM,
                            code_snippet=snippet,
                            suggestion="Extract nested logic into helper functions or use early returns",
                        ))

                if isinstance(node, ast.ClassDef):
                    methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    if len(methods) > 15:
                        snippet = self._get_code_snippet(filepath, node.lineno)
                        issues.append(RefactorIssue(
                            file=filepath,
                            line=node.lineno,
                            category=IssueCategory.CODE_SMELL,
                            description=f"Class '{node.name}' has {len(methods)} methods (god class, max 15)",
                            severity=Severity.HIGH,
                            code_snippet=snippet,
                            suggestion="Split into smaller, single-responsibility classes",
                        ))
        return issues

    def _get_nesting_depth(self, node: ast.AST) -> int:
        """Calculate maximum nesting depth of a function."""
        max_depth = 0

        def _walk(node: ast.AST, depth: int) -> None:
            nonlocal max_depth
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)):
                    _walk(child, depth + 1)
                else:
                    _walk(child, depth)
            if depth > max_depth:
                max_depth = depth

        _walk(node, 0)
        return max_depth

    async def scan_long_files(
        self, repo_path: str, max_lines: int = 500
    ) -> List[RefactorIssue]:
        """Find files exceeding max_lines."""
        issues: List[RefactorIssue] = []
        python_files = self._get_python_files(repo_path)

        for filepath in python_files:
            content = self._read_file(filepath)
            if content is None:
                continue
            line_count = len(content.splitlines())
            if line_count > max_lines:
                issues.append(RefactorIssue(
                    file=filepath,
                    line=1,
                    category=IssueCategory.LONG_FILE,
                    description=f"File has {line_count} lines (max {max_lines})",
                    severity=Severity.MEDIUM if line_count < max_lines * 2 else Severity.HIGH,
                    code_snippet=f"# File: {os.path.basename(filepath)} ({line_count} lines)",
                    suggestion="Split into smaller modules with clear responsibilities",
                ))
        return issues

    async def scan_missing_docs(self, repo_path: str) -> List[RefactorIssue]:
        """Find public functions/classes missing docstrings."""
        issues: List[RefactorIssue] = []
        python_files = self._get_python_files(repo_path)

        for filepath in python_files:
            tree = self._parse_ast(filepath)
            if tree is None:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_"):
                        continue
                    if not (node.body and isinstance(node.body[0], ast.Expr)
                            and isinstance(getattr(node.body[0], "value", None), ast.Constant)
                            and isinstance(node.body[0].value.value, str)):
                        snippet = self._get_code_snippet(filepath, node.lineno)
                        issues.append(RefactorIssue(
                            file=filepath,
                            line=node.lineno,
                            category=IssueCategory.MISSING_DOC,
                            description=f"Public function '{node.name}' missing docstring",
                            severity=Severity.LOW,
                            code_snippet=snippet,
                            suggestion=f"Add docstring describing purpose, args, and return value",
                        ))
                elif isinstance(node, ast.ClassDef):
                    if node.name.startswith("_"):
                        continue
                    if not (node.body and isinstance(node.body[0], ast.Expr)
                            and isinstance(getattr(node.body[0], "value", None), ast.Constant)
                            and isinstance(node.body[0].value.value, str)):
                        snippet = self._get_code_snippet(filepath, node.lineno)
                        issues.append(RefactorIssue(
                            file=filepath,
                            line=node.lineno,
                            category=IssueCategory.MISSING_DOC,
                            description=f"Public class '{node.name}' missing docstring",
                            severity=Severity.LOW,
                            code_snippet=snippet,
                            suggestion="Add class docstring describing purpose and usage",
                        ))
        return issues

    async def scan_high_complexity(
        self, repo_path: str, max_complexity: int = 10
    ) -> List[RefactorIssue]:
        """Calculate cyclomatic complexity and flag high-complexity functions."""
        issues: List[RefactorIssue] = []
        python_files = self._get_python_files(repo_path)

        for filepath in python_files:
            tree = self._parse_ast(filepath)
            if tree is None:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = self._calc_complexity(node)
                    if complexity > max_complexity:
                        snippet = self._get_code_snippet(filepath, node.lineno)
                        issues.append(RefactorIssue(
                            file=filepath,
                            line=node.lineno,
                            category=IssueCategory.HIGH_COMPLEXITY,
                            description=f"Function '{node.name}' has complexity {complexity} (max {max_complexity})",
                            severity=Severity.HIGH if complexity > max_complexity * 2 else Severity.MEDIUM,
                            code_snippet=snippet,
                            suggestion="Simplify logic, extract branches, or use polymorphism",
                        ))
        return issues

    def _calc_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function node."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                complexity += 1
        return complexity

    async def generate_proposals(
        self, issues: List[RefactorIssue]
    ) -> List[RefactorProposal]:
        """Generate PR-style refactoring proposals from issues."""
        proposals: List[RefactorProposal] = []
        grouped = self._group_issues(issues)

        for group_key, group_issues in grouped.items():
            category = group_issues[0].category
            title = self._generate_title(category, group_issues)
            description = self._generate_description(category, group_issues)
            benefits = self._generate_benefits(category, group_issues)
            risk = self._assess_risk(category, group_issues)
            impact = self._estimate_impact(category, group_issues)
            files = list(set(i.file for i in group_issues))

            before_code = self._extract_before_code(group_issues)
            after_code = self._generate_after_code(category, group_issues)

            proposal = RefactorProposal(
                title=title,
                description=description,
                issues=group_issues,
                before_code=before_code,
                after_code=after_code,
                benefits=benefits,
                risk=risk,
                estimated_impact=impact,
                files_affected=files,
                auto_applicable=risk == RiskLevel.LOW and len(group_issues) <= 3,
            )
            proposals.append(proposal)

        return proposals

    def _group_issues(self, issues: List[RefactorIssue]) -> Dict[str, List[RefactorIssue]]:
        """Group issues by category and file proximity."""
        groups: Dict[str, List[RefactorIssue]] = defaultdict(list)
        for issue in issues:
            key = f"{issue.category.value}:{issue.file}"
            groups[key].append(issue)
        return groups

    def _generate_title(
        self, category: IssueCategory, issues: List[RefactorIssue]
    ) -> str:
        """Generate a descriptive title for the proposal."""
        titles = {
            IssueCategory.DUPLICATION: "Remove duplicate code blocks",
            IssueCategory.COMPLEXITY: "Reduce function complexity",
            IssueCategory.NAMING: "Fix naming conventions",
            IssueCategory.UNUSED: "Remove unused imports/variables",
            IssueCategory.CIRCULAR_IMPORT: "Resolve circular imports",
            IssueCategory.CODE_SMELL: "Address code smells",
            IssueCategory.LONG_FILE: "Split large files",
            IssueCategory.MISSING_DOC: "Add missing documentation",
            IssueCategory.HIGH_COMPLEXITY: "Reduce cyclomatic complexity",
        }
        base = titles.get(category, "Refactor code")
        if len(issues) > 1:
            return f"{base} ({len(issues)} issues in {len(set(i.file for i in issues))} files)"
        return f"{base} in {os.path.basename(issues[0].file)}"

    def _generate_description(
        self, category: IssueCategory, issues: List[RefactorIssue]
    ) -> str:
        """Generate a detailed description for the proposal."""
        desc_parts = [f"## Refactoring Proposal\n"]
        desc_parts.append(f"**Category:** {category.value}\n")
        desc_parts.append(f"**Issues found:** {len(issues)}\n")
        desc_parts.append(f"**Files affected:** {len(set(i.file for i in issues))}\n\n")
        desc_parts.append("### Issues\n")
        for i, issue in enumerate(issues[:10], 1):
            desc_parts.append(f"{i}. **{issue.description}** ({issue.severity.value})")
            desc_parts.append(f"   - File: `{issue.file}:{issue.line}`")
            desc_parts.append(f"   - Suggestion: {issue.suggestion}\n")
        if len(issues) > 10:
            desc_parts.append(f"... and {len(issues) - 10} more issues\n")
        return "".join(desc_parts)

    def _generate_benefits(
        self, category: IssueCategory, issues: List[RefactorIssue]
    ) -> List[str]:
        """Generate list of benefits for the proposal."""
        benefit_map = {
            IssueCategory.DUPLICATION: [
                "Reduced code maintenance burden",
                "Single source of truth for repeated logic",
                "Smaller codebase footprint",
            ],
            IssueCategory.COMPLEXITY: [
                "Improved readability and maintainability",
                "Easier to test individual functions",
                "Lower cognitive load for developers",
            ],
            IssueCategory.NAMING: [
                "Consistent, predictable code style",
                "Better IDE autocompletion",
                "Easier onboarding for new contributors",
            ],
            IssueCategory.UNUSED: [
                "Cleaner import statements",
                "Reduced namespace pollution",
                "Faster module loading",
            ],
            IssueCategory.CIRCULAR_IMPORT: [
                "Eliminated import-time errors",
                "Clearer dependency graph",
                "Safer lazy-loading patterns",
            ],
            IssueCategory.CODE_SMELL: [
                "More maintainable code structure",
                "Easier to extend and modify",
                "Reduced technical debt",
            ],
            IssueCategory.LONG_FILE: [
                "Better separation of concerns",
                "Faster navigation and comprehension",
                "More targeted test coverage",
            ],
            IssueCategory.MISSING_DOC: [
                "Improved API discoverability",
                "Better developer experience",
                "Self-documenting codebase",
            ],
            IssueCategory.HIGH_COMPLEXITY: [
                "Reduced bug risk in complex paths",
                "Easier to reason about control flow",
                "Simplified unit testing",
            ],
        }
        return benefit_map.get(category, ["Improved code quality"])

    def _assess_risk(
        self, category: IssueCategory, issues: List[RefactorIssue]
    ) -> RiskLevel:
        """Assess the risk level of applying the refactoring."""
        risk_map = {
            IssueCategory.DUPLICATION: RiskLevel.MEDIUM,
            IssueCategory.COMPLEXITY: RiskLevel.HIGH,
            IssueCategory.NAMING: RiskLevel.LOW,
            IssueCategory.UNUSED: RiskLevel.LOW,
            IssueCategory.CIRCULAR_IMPORT: RiskLevel.HIGH,
            IssueCategory.CODE_SMELL: RiskLevel.MEDIUM,
            IssueCategory.LONG_FILE: RiskLevel.HIGH,
            IssueCategory.MISSING_DOC: RiskLevel.LOW,
            IssueCategory.HIGH_COMPLEXITY: RiskLevel.HIGH,
        }
        base_risk = risk_map.get(category, RiskLevel.MEDIUM)
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        if critical_count > 0:
            return RiskLevel.HIGH
        return base_risk

    def _estimate_impact(
        self, category: IssueCategory, issues: List[RefactorIssue]
    ) -> str:
        """Estimate the impact of the refactoring."""
        impact_map = {
            IssueCategory.DUPLICATION: f"~{len(issues) * 0.5:.1f}h maintenance saved per cycle",
            IssueCategory.COMPLEXITY: f"Improved testability for {len(issues)} functions",
            IssueCategory.NAMING: f"Consistent naming across {len(issues)} symbols",
            IssueCategory.UNUSED: f"Cleaned {len(issues)} unused references",
            IssueCategory.CIRCULAR_IMPORT: f"Resolved {len(issues)} circular dependencies",
            IssueCategory.CODE_SMELL: f"Improved structure in {len(set(i.file for i in issues))} files",
            IssueCategory.LONG_FILE: f"Split {len(issues)} oversized files",
            IssueCategory.MISSING_DOC: f"Documented {len(issues)} public APIs",
            IssueCategory.HIGH_COMPLEXITY: f"Simplified {len(issues)} complex functions",
        }
        return impact_map.get(category, f"Addressed {len(issues)} issues")

    def _extract_before_code(self, issues: List[RefactorIssue]) -> str:
        """Extract the 'before' code from issues."""
        snippets = []
        for issue in issues[:5]:
            snippets.append(f"# {issue.file}:{issue.line}")
            snippets.append(issue.code_snippet)
            snippets.append("")
        return "\n".join(snippets)

    def _generate_after_code(
        self, category: IssueCategory, issues: List[RefactorIssue]
    ) -> str:
        """Generate suggested 'after' code based on category."""
        if category == IssueCategory.NAMING:
            return "# Apply PEP 8 naming conventions:\n# Functions: snake_case\n# Classes: PascalCase\n# Constants: UPPER_SNAKE_CASE"
        elif category == IssueCategory.UNUSED:
            return "# Remove unused imports:\n# import os  # remove if unused\n# from typing import List  # remove if unused"
        elif category == IssueCategory.MISSING_DOC:
            return 'def function_name(args):\n    """Brief description.\n    \n    Args:\n        arg1: Description\n    \n    Returns:\n        Description of return value\n    """'
        elif category == IssueCategory.DUPLICATION:
            return "# Extract common logic into a shared function:\ndef shared_function(args):\n    # Common implementation\n    pass"
        elif category == IssueCategory.HIGH_COMPLEXITY:
            return "# Simplify by:\n# 1. Extracting conditional branches\n# 2. Using early returns\n# 3. Applying polymorphism for complex switches"
        else:
            return "# Apply refactoring based on specific issue suggestions"
