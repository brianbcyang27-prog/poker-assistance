"""Intelligent Documentation Engine — auto-generate project docs from source."""

import ast
import os
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

from .models import ModuleDoc, ProjectDocs


class DocsEngine:
    """Generates comprehensive documentation from a Python repository."""

    IGNORE_DIRS = {
        "__pycache__", ".git", ".venv", "venv", "node_modules",
        ".mypy_cache", ".pytest_cache", "dist", "build", ".eggs",
    }

    async def generate_module_docs(self, repo_path: str) -> List[ModuleDoc]:
        """Produce a ModuleDoc for every Python module in the repo."""
        modules: List[ModuleDoc] = []
        for module_path in self._find_modules(repo_path):
            doc = self._document_module(module_path, repo_path)
            if doc is not None:
                modules.append(doc)
        return modules

    async def generate_api_reference(self, repo_path: str) -> str:
        """Generate a Markdown API reference for all public symbols."""
        modules = await self.generate_module_docs(repo_path)
        lines: List[str] = ["# API Reference\n"]
        for mod in modules:
            lines.append(f"## `{mod.name}`\n")
            lines.append(f"{mod.purpose}\n")
            if mod.public_api:
                lines.append("### Public API\n")
                for symbol in mod.public_api:
                    lines.append(f"- `{symbol}`")
                lines.append("")
            if mod.dependencies:
                lines.append("**Dependencies:** " + ", ".join(mod.dependencies) + "\n")
        return "\n".join(lines)

    async def generate_architecture_book(self, repo_path: str) -> str:
        """Generate an architecture overview document."""
        modules = await self.generate_module_docs(repo_path)
        lines: List[str] = ["# Architecture Overview\n"]
        lines.append("## Module Map\n")
        for mod in modules:
            lines.append(f"- **{mod.name}** — {mod.purpose}")
        lines.append("")
        lines.append("## Dependency Graph\n")
        dep_map = {mod.name: mod.dependencies for mod in modules}
        for name, deps in dep_map.items():
            if deps:
                for dep in deps:
                    lines.append(f"- `{name}` → `{dep}`")
        lines.append("")
        lines.append("## Design Decisions\n")
        lines.append(
            "Each module is designed to be independently testable and composable. "
            "Modules communicate through well-defined async interfaces.\n"
        )
        return "\n".join(lines)

    async def generate_developer_handbook(self, repo_path: str) -> str:
        """Generate a developer onboarding guide."""
        project_name = Path(repo_path).name
        lines: List[str] = [
            f"# Developer Handbook — {project_name}\n",
            "## Getting Started\n",
            "1. Clone the repository",
            "2. Create a virtual environment: `python3 -m venv .venv`",
            "3. Activate it: `source .venv/bin/activate`",
            "4. Install dependencies if any\n",
            "## Project Structure\n",
        ]
        modules = await self.generate_module_docs(repo_path)
        for mod in modules:
            lines.append(f"- `{mod.name}`: {mod.purpose}")
        lines.append("")
        lines.append("## Coding Conventions\n")
        lines.append("- All code must be compatible with Python 3.9+")
        lines.append("- Use `Optional[X]` instead of `X | None`")
        lines.append("- Prefer dataclasses for data models")
        lines.append("- All public functions must be `async`")
        lines.append("- Type hints are required on all public APIs\n")
        lines.append("## Testing\n")
        lines.append("Run the test suite with your preferred framework.\n")
        return "\n".join(lines)

    async def generate_database_docs(self, repo_path: str) -> str:
        """Generate database schema documentation."""
        lines: List[str] = ["# Database Schema Documentation\n"]
        schema_files = self._find_schema_files(repo_path)
        if not schema_files:
            lines.append(
                "_No database schema files found in the repository._\n"
            )
            return "\n".join(lines)
        for sf in schema_files:
            lines.append(f"## `{sf}`\n")
            try:
                content = Path(sf).read_text(encoding="utf-8")
                lines.append("```sql")
                lines.append(content)
                lines.append("```\n")
            except Exception:
                lines.append("_Could not read file._\n")
        return "\n".join(lines)

    async def generate_readme(self, repo_path: str) -> str:
        """Auto-generate a README.md for the project."""
        project_name = Path(repo_path).name
        modules = await self.generate_module_docs(repo_path)
        lines: List[str] = [
            f"# {project_name}\n",
            "## Overview\n",
        ]
        if modules:
            lines.append(
                f"This project contains {len(modules)} module(s).\n"
            )
        else:
            lines.append("A Python project.\n")
        lines.append("## Modules\n")
        for mod in modules:
            lines.append(f"### {mod.name}")
            lines.append(f"{mod.purpose}\n")
        lines.append("## Installation\n")
        lines.append("```bash")
        lines.append(f"git clone <repo-url>")
        lines.append(f"cd {project_name}")
        lines.append("python3 -m venv .venv")
        lines.append("source .venv/bin/activate")
        lines.append("```\n")
        lines.append("## License\n")
        lines.append("See LICENSE file for details.\n")
        return "\n".join(lines)

    async def generate_full_docs(self, repo_path: str) -> ProjectDocs:
        """Generate the complete documentation set."""
        modules = await self.generate_module_docs(repo_path)
        api_ref = await self.generate_api_reference(repo_path)
        arch = await self.generate_architecture_book(repo_path)
        handbook = await self.generate_developer_handbook(repo_path)
        db_docs = await self.generate_database_docs(repo_path)
        readme = await self.generate_readme(repo_path)
        return ProjectDocs(
            modules=modules,
            api_reference=api_ref,
            architecture_book=arch,
            handbook=handbook,
            database_docs=db_docs,
            readme=readme,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_modules(self, repo_path: str) -> List[str]:
        """Walk the repo and return paths to Python files."""
        py_files: List[str] = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [
                d for d in dirs
                if d not in self.IGNORE_DIRS and not d.startswith(".")
            ]
            for fname in files:
                if fname.endswith(".py") and not fname.startswith("."):
                    py_files.append(os.path.join(root, fname))
        py_files.sort()
        return py_files

    def _document_module(self, file_path: str, repo_path: str) -> Optional[ModuleDoc]:
        """Parse a single Python file and extract documentation."""
        try:
            source = Path(file_path).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=file_path)
        except Exception:
            return None

        rel = os.path.relpath(file_path, repo_path)
        module_name = rel.replace(os.sep, ".").replace(".py", "")
        if module_name.endswith(".__init__"):
            module_name = module_name[: -len(".__init__")]

        docstring = ast.get_docstring(tree) or ""
        purpose = docstring.split("\n")[0].strip() if docstring else f"Module {module_name}"

        public_api: List[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    public_api.append(f"{module_name}.{node.name}()")
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    public_api.append(f"{module_name}.{node.name}")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_"):
                        public_api.append(f"{module_name}.{target.id}")

        imports: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        examples = self._extract_examples(source)
        limitations = self._extract_by_marker(source, "Limitation")
        future_work = self._extract_by_marker(source, "Future")

        return ModuleDoc(
            name=module_name,
            purpose=purpose,
            architecture=self._infer_architecture(tree),
            public_api=public_api,
            examples=examples,
            dependencies=sorted(set(imports)),
            limitations=limitations,
            future_work=future_work,
        )

    def _infer_architecture(self, tree: ast.Module) -> str:
        """Return a short architectural description."""
        class_count = sum(1 for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef))
        func_count = sum(
            1 for n in ast.iter_child_nodes(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        parts: List[str] = []
        if class_count:
            parts.append(f"{class_count} class(es)")
        if func_count:
            parts.append(f"{func_count} function(s)")
        return ", ".join(parts) if parts else "Module-level code"

    def _extract_examples(self, source: str) -> List[str]:
        """Extract lines marked as examples in docstrings."""
        examples: List[str] = []
        try:
            tree = ast.parse(source)
        except Exception:
            return examples
        for node in self._docstring_nodes(tree):
            docstring = ast.get_docstring(node)
            if docstring:
                in_example = False
                for line in docstring.split("\n"):
                    stripped = line.strip().lower()
                    if "example" in stripped:
                        in_example = True
                        continue
                    if in_example and stripped:
                        examples.append(line.strip())
                    elif in_example and not stripped:
                        in_example = False
        return examples

    def _extract_by_marker(self, source: str, marker: str) -> List[str]:
        """Extract bullet points following a marker keyword in docstrings."""
        results: List[str] = []
        try:
            tree = ast.parse(source)
        except Exception:
            return results
        for node in self._docstring_nodes(tree):
            docstring = ast.get_docstring(node)
            if docstring:
                in_section = False
                for line in docstring.split("\n"):
                    stripped = line.strip().lower()
                    if marker.lower() in stripped:
                        in_section = True
                        continue
                    if in_section and stripped.startswith(("-", "*")):
                        results.append(stripped.lstrip("-* ").strip())
                    elif in_section and not stripped:
                        in_section = False
        return results

    @staticmethod
    def _docstring_nodes(tree: ast.Module) -> List[ast.AST]:
        """Yield only AST nodes that support docstrings."""
        _DOCVISIBLE = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        return [n for n in ast.walk(tree) if isinstance(n, _DOCVISIBLE)]

    def _find_schema_files(self, repo_path: str) -> List[str]:
        """Find SQL schema files."""
        schema_files: List[str] = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            for fname in files:
                if fname.endswith((".sql",)) and any(
                    kw in fname.lower()
                    for kw in ("schema", "migration", "create")
                ):
                    schema_files.append(os.path.join(root, fname))
        schema_files.sort()
        return schema_files
