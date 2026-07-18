"""Main codebase indexing engine."""

from __future__ import annotations

import ast
import fnmatch
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import FileIndex, RepoIndex, Symbol
from .search import SearchEngine

IGNORE_DIRS = frozenset([
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".eggs", "*.egg-info", ".opencode",
])

PYTHON_EXTENSIONS = frozenset([".py"])
JS_EXTENSIONS = frozenset([".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"])
STYLE_EXTENSIONS = frozenset([".css", ".scss", ".less", ".styl"])
MARKUP_EXTENSIONS = frozenset([".html", ".htm", ".xml", ".svg", ".vue", ".svelte"])
CONFIG_EXTENSIONS = frozenset([".yaml", ".yml", ".toml", ".ini", ".cfg", ".json"])
DOC_EXTENSIONS = frozenset([".md", ".rst", ".txt"])

LANG_MAP = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mjs": "javascript",
    ".cjs": "javascript", ".css": "css", ".scss": "scss",
    ".less": "less", ".html": "html", ".htm": "html", ".xml": "xml",
    ".svg": "svg", ".vue": "vue", ".svelte": "svelte",
    ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".ini": "ini", ".cfg": "cfg", ".json": "json",
    ".md": "markdown", ".rst": "rst", ".txt": "text",
}

COMPLEXITY_NODES = (
    ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With,
    ast.Assert, ast.BoolOp, ast.ListComp, ast.SetComp,
    ast.DictComp, ast.GeneratorExp,
)


class CodebaseIndex:
    """Indexes every symbol in a repository for fast search."""

    def __init__(self) -> None:
        self.repo_index = RepoIndex()
        self.engine = SearchEngine(self.repo_index)
        self._repo_path = ""

    async def index(self, repo_path: str) -> None:
        """Index entire repository."""
        self._repo_path = os.path.abspath(repo_path)
        self.repo_index.stats["repo_path"] = self._repo_path
        self.repo_index.stats["indexed_at"] = time.time()

        all_symbols: Dict[str, List[Symbol]] = {}
        files: Dict[str, FileIndex] = {}
        modules: Dict[str, List[str]] = {}
        call_graph: Dict[str, List[str]] = {}
        import_graph: Dict[str, List[str]] = {}
        inheritance_graph: Dict[str, List[str]] = {}

        for root, dirnames, filenames in os.walk(self._repo_path):
            dirnames[:] = [
                d for d in dirnames
                if not any(fnmatch.fnmatch(d, pat) for pat in IGNORE_DIRS)
            ]
            for filename in filenames:
                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                if ext not in LANG_MAP:
                    continue
                rel = os.path.relpath(filepath, self._repo_path)
                try:
                    fi = self._index_file(filepath, rel, ext)
                except Exception:
                    continue
                if fi is None:
                    continue
                files[rel] = fi
                import_graph[rel] = list(fi.imports)
                for sym in fi.symbols:
                    all_symbols.setdefault(sym.name, []).append(sym)
                    for call in sym.calls:
                        call_graph.setdefault(sym.full_name, [])
                        if call not in call_graph[sym.full_name]:
                            call_graph[sym.full_name].append(call)
                    if sym.kind == "class" and sym.parent_class:
                        inheritance_graph.setdefault(sym.name, [])
                        if sym.parent_class not in inheritance_graph[sym.name]:
                            inheritance_graph[sym.name].append(sym.parent_class)
                    if fi.language == "python":
                        mod = self._module_path(rel)
                        modules.setdefault(mod, [])
                        if rel not in modules[mod]:
                            modules[mod].append(rel)

        total_loc = sum(f.loc for f in files.values())
        total_symbols = sum(len(f.symbols) for f in files.values())
        total_complexity = sum(f.complexity for f in files.values())

        lang_counts: Dict[str, int] = {}
        for f in files.values():
            lang_counts[f.language] = lang_counts.get(f.language, 0) + 1

        self.repo_index.files = files
        self.repo_index.symbols = all_symbols
        self.repo_index.modules = modules
        self.repo_index.call_graph = call_graph
        self.repo_index.import_graph = import_graph
        self.repo_index.inheritance_graph = inheritance_graph
        self.repo_index.stats.update({
            "repo_path": self._repo_path,
            "total_files": len(files),
            "total_symbols": total_symbols,
            "total_loc": total_loc,
            "total_complexity": total_complexity,
            "languages": lang_counts,
        })
        self.engine = SearchEngine(self.repo_index)

    async def reindex_file(self, rel_path: str) -> None:
        """Re-index a single file (incremental update)."""
        ext = os.path.splitext(rel_path)[1].lower()
        full = os.path.join(self._repo_path, rel_path)
        if not os.path.isfile(full):
            self._remove_file_from_index(rel_path)
            return
        old = self.repo_index.files.get(rel_path)
        if old:
            self._remove_file_from_index(rel_path)
        try:
            fi = self._index_file(full, rel_path, ext)
        except Exception:
            return
        if fi is None:
            return
        self.repo_index.files[rel_path] = fi
        self.repo_index.import_graph[rel_path] = list(fi.imports)
        for sym in fi.symbols:
            self.repo_index.symbols.setdefault(sym.name, []).append(sym)
            for call in sym.calls:
                cg = self.repo_index.call_graph.setdefault(sym.full_name, [])
                if call not in cg:
                    cg.append(call)
            if sym.kind == "class" and sym.parent_class:
                ig2 = self.repo_index.inheritance_graph.setdefault(sym.name, [])
                if sym.parent_class not in ig2:
                    ig2.append(sym.parent_class)
            if fi.language == "python":
                mod = self._module_path(rel_path)
                ml = self.repo_index.modules.setdefault(mod, [])
                if rel_path not in ml:
                    ml.append(rel_path)
        self.engine = SearchEngine(self.repo_index)

    async def search(self, query: str, search_type: str = "semantic") -> List:
        """Search symbols."""
        if search_type == "name":
            return self.engine.search_name(query)
        elif search_type == "docstring":
            return self.engine.search_docstring(query)
        elif search_type == "signature":
            return self.engine.search_signature(query)
        elif search_type == "usage":
            return self.engine.search_usage(query)
        else:
            return self.engine.semantic_search(query)

    async def search_symbol(self, name: str) -> List[Symbol]:
        """Find symbol by exact name."""
        return self.engine.search_exact(name)

    async def search_references(self, name: str) -> List[Symbol]:
        """Find all references to a symbol."""
        return self.engine.references(name)

    async def get_call_graph(self, symbol_name: str) -> Dict[str, List[str]]:
        """Who calls what, starting from symbol_name."""
        forward = self.engine.call_chain(symbol_name)
        reverse: Dict[str, List[str]] = {}
        for caller, callees in self.repo_index.call_graph.items():
            if symbol_name in callees:
                reverse.setdefault(symbol_name, []).append(caller)
        result = dict(forward)
        if reverse:
            existing = result.get(symbol_name, [])
            for r in reverse[symbol_name]:
                if r not in existing:
                    existing.append(r)
            result[f"{symbol_name} (callers)"] = reverse[symbol_name]
        return result

    async def get_import_graph(self, symbol_name: str) -> Dict[str, List[str]]:
        """Import dependencies for a module."""
        return self.engine.import_chain(symbol_name)

    async def get_inheritance_graph(self, class_name: str) -> Dict[str, List[str]]:
        """Class hierarchy."""
        return self.engine.inheritance_chain(class_name)

    async def get_module_graph(self) -> Dict[str, List[str]]:
        """Module-level dependencies."""
        return dict(self.repo_index.import_graph)

    async def get_file_stats(self, file_path: str) -> Dict[str, Any]:
        """Statistics for a single file."""
        fi = self.repo_index.files.get(file_path)
        if not fi:
            return {"error": f"File not indexed: {file_path}"}
        return {
            "path": fi.path,
            "language": fi.language,
            "loc": fi.loc,
            "complexity": fi.complexity,
            "symbol_count": len(fi.symbols),
            "symbols": [
                {"name": s.name, "kind": s.kind, "line": s.line_start}
                for s in fi.symbols
            ],
            "imports": fi.imports,
            "exports": fi.exports,
        }

    async def get_repo_stats(self) -> Dict[str, Any]:
        """Overall repository statistics."""
        return dict(self.repo_index.stats)

    def save_index(self, path: str) -> None:
        """Persist index to JSON."""
        self.repo_index.save(path)

    def load_index(self, path: str) -> None:
        """Load index from JSON."""
        self.repo_index = RepoIndex.load(path)
        self.engine = SearchEngine(self.repo_index)

    # ── Private: file parsing ───────────────────────────────────────

    def _remove_file_from_index(self, rel_path: str) -> None:
        fi = self.repo_index.files.pop(rel_path, None)
        if not fi:
            return
        for sym in fi.symbols:
            syms = self.repo_index.symbols.get(sym.name, [])
            self.repo_index.symbols[sym.name] = [
                s for s in syms
                if not (s.file_path == rel_path and s.line_start == sym.line_start)
            ]
            if not self.repo_index.symbols[sym.name]:
                del self.repo_index.symbols[sym.name]
        self.repo_index.call_graph = {
            k: v for k, v in self.repo_index.call_graph.items()
            if not k.startswith(rel_path)
        }
        self.repo_index.import_graph.pop(rel_path, None)
        self.repo_index.modules = {
            k: [p for p in v if p != rel_path]
            for k, v in self.repo_index.modules.items()
        }
        self.repo_index.modules = {
            k: v for k, v in self.repo_index.modules.items() if v
        }

    def _index_file(
        self, full_path: str, rel_path: str, ext: str
    ) -> Optional[FileIndex]:
        try:
            stat = os.stat(full_path)
        except OSError:
            return None
        mtime = stat.st_mtime
        cached = self.repo_index.files.get(rel_path)
        if cached and abs(cached.last_modified - mtime) < 0.001:
            return cached

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, IOError):
            return None

        lines = content.split("\n")
        loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

        language = LANG_MAP.get(ext, "unknown")
        symbols: List[Symbol] = []
        imports: List[str] = []
        exports: List[str] = []
        complexity = 0

        if ext in PYTHON_EXTENSIONS:
            symbols, imports, exports, complexity = self._parse_python(
                content, rel_path
            )
        elif ext in JS_EXTENSIONS:
            symbols, imports, exports, complexity = self._parse_js(
                content, rel_path
            )
        elif ext in CONFIG_EXTENSIONS:
            symbols, imports, exports, complexity = self._parse_config(
                content, rel_path
            )
        elif ext in DOC_EXTENSIONS:
            symbols, imports, exports, complexity = self._parse_docs(
                content, rel_path
            )

        return FileIndex(
            path=rel_path,
            language=language,
            symbols=symbols,
            imports=imports,
            exports=exports,
            loc=loc,
            complexity=complexity,
            last_modified=mtime,
        )

    def _parse_python(
        self, content: str, file_path: str
    ) -> Tuple[List[Symbol], List[str], List[str], int]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return [], [], [], 0

        symbols: List[Symbol] = []
        imports: List[str] = []
        exports: List[str] = []
        total_complexity = 0

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imp = self._extract_import(node)
                if imp:
                    imports.append(imp)
                continue

            sym, cplx = self._parse_python_node(node, file_path)
            if sym:
                symbols.append(sym)
                total_complexity += cplx

        for node in ast.walk(tree):
            if isinstance(node, COMPLEXITY_NODES):
                total_complexity += 1

        for sym in symbols:
            if not sym.name.startswith("_"):
                exports.append(sym.name)

        return symbols, imports, exports, total_complexity

    def _parse_python_node(
        self, node: ast.AST, file_path: str
    ) -> Tuple[Optional[Symbol], int]:
        if isinstance(node, ast.ClassDef):
            return self._parse_class(node, file_path)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return self._parse_function(node, file_path, None)
        elif isinstance(node, ast.Assign):
            return self._parse_assignment(node, file_path)
        return None, 0

    def _parse_class(
        self, node: ast.ClassDef, file_path: str
    ) -> Tuple[Symbol, int]:
        docstring = ast.get_docstring(node)
        decorators = [self._unparse_name(d) for d in node.decorator_list]
        parent = None
        if node.bases:
            parent = self._unparse_name(node.bases[0])

        end_line = self._get_end_line(node)
        children: List[str] = []
        body_complexity = 0
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_sym, mc = self._parse_function(item, file_path, node.name)
                if method_sym:
                    children.append(method_sym.name)
                    body_complexity += mc

        sig_parts = []
        for base in node.bases:
            sig_parts.append(self._unparse_name(base))
        for kw in node.keywords:
            sig_parts.append(f"{kw.arg}={self._unparse_name(kw.value)}")
        signature = f"class {node.name}({', '.join(sig_parts)})" if sig_parts else f"class {node.name}"

        sym = Symbol(
            name=node.name,
            kind="class",
            file_path=file_path,
            line_start=node.lineno,
            line_end=end_line,
            docstring=docstring,
            signature=signature,
            decorators=decorators,
            parent_class=parent,
            children=children,
            complexity=body_complexity,
            loc=end_line - node.lineno + 1,
        )
        return sym, body_complexity

    def _parse_function(
        self,
        node: ast.FunctionDef,
        file_path: str,
        parent_class: Optional[str],
    ) -> Tuple[Symbol, int]:
        docstring = ast.get_docstring(node)
        decorators = [self._unparse_name(d) for d in node.decorator_list]
        end_line = self._get_end_line(node)

        args = self._format_args(node.args)
        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        signature = f"{prefix}def {node.name}({args})"

        calls = self._extract_calls(node)
        imports: List[str] = []
        kind = "method" if parent_class else "function"

        complexity = 1
        for n in ast.walk(node):
            if isinstance(n, COMPLEXITY_NODES):
                complexity += 1

        sym = Symbol(
            name=node.name,
            kind=kind,
            file_path=file_path,
            line_start=node.lineno,
            line_end=end_line,
            docstring=docstring,
            signature=signature,
            decorators=decorators,
            calls=calls,
            parent_class=parent_class,
            complexity=complexity,
            loc=end_line - node.lineno + 1,
        )
        return sym, complexity

    def _parse_assignment(
        self, node: ast.Assign, file_path: str
    ) -> Tuple[Optional[Symbol], int]:
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if name.startswith("_") and name != "__all__":
                    continue
                sym = Symbol(
                    name=name,
                    kind="variable",
                    file_path=file_path,
                    line_start=node.lineno,
                    line_end=node.lineno,
                )
                return sym, 0
        return None, 0

    def _extract_import(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Import):
            parts = []
            for alias in node.names:
                parts.append(alias.name)
            return ", ".join(parts)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [a.name for a in node.names]
            return f"from {module} import {', '.join(names)}"
        return None

    def _extract_calls(self, node: ast.AST) -> List[str]:
        calls: List[str] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = self._unparse_name(child.func)
                if name:
                    calls.append(name)
        return calls

    def _unparse_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parent = self._unparse_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        elif isinstance(node, ast.Subscript):
            base = self._unparse_name(node.value)
            return base
        elif isinstance(node, ast.Index):
            return self._unparse_name(node.value)
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return ""

    def _format_args(self, args: ast.arguments) -> str:
        parts: List[str] = []
        defaults_offset = len(args.args) - len(args.defaults)
        for i, arg in enumerate(args.args):
            if arg.arg == "self" or arg.arg == "cls":
                continue
            annotation = ""
            if i >= defaults_offset and args.defaults:
                dflt = self._unparse_name(args.defaults[i - defaults_offset])
                annotation = f"={dflt}" if dflt else "=..."
            parts.append(f"{arg.arg}{annotation}")

        for arg in args.kwonlyargs:
            annotation = ""
            if args.kw_defaults:
                idx = args.kwonlyargs.index(arg)
                if idx < len(args.kw_defaults) and args.kw_defaults[idx] is not None:
                    dflt = self._unparse_name(args.kw_defaults[idx])
                    annotation = f"={dflt}" if dflt else "=..."
            parts.append(f"{arg.arg}{annotation}")

        if args.vararg:
            parts.append(f"*{args.vararg.arg}")
        if args.kwarg:
            parts.append(f"**{args.kwarg.arg}")

        return ", ".join(parts)

    def _get_end_line(self, node: ast.AST) -> int:
        if hasattr(node, "end_lineno") and node.end_lineno:
            return node.end_lineno
        max_line = getattr(node, "lineno", 0)
        for child in ast.iter_child_nodes(node):
            child_end = self._get_end_line(child)
            if child_end > max_line:
                max_line = child_end
        return max_line

    # ── Private: non-Python parsing ─────────────────────────────────

    def _parse_js(
        self, content: str, file_path: str
    ) -> Tuple[List[Symbol], List[str], List[str], int]:
        symbols: List[Symbol] = []
        imports: List[str] = []
        exports: List[str] = []
        complexity = 0

        for m in re.finditer(
            r"""(?:^|\n)\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)""",
            content,
        ):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            symbols.append(Symbol(
                name=name, kind="class", file_path=file_path,
                line_start=line, line_end=line,
            ))
            if "export" in content[m.start():m.end() + 20]:
                exports.append(name)

        for m in re.finditer(
            r"""(?:^|\n)\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s+(\w+)\s*\(([^)]*)\)""",
            content,
        ):
            name = m.group(1)
            args = m.group(2)
            line = content[: m.start()].count("\n") + 1
            symbols.append(Symbol(
                name=name, kind="function", file_path=file_path,
                line_start=line, line_end=line,
                signature=f"function {name}({args})",
            ))
            if "export" in content[m.start():m.end() + 20]:
                exports.append(name)

        for m in re.finditer(
            r"""(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)\s*=>|function)""",
            content,
        ):
            name = m.group(1)
            line = content[: m.start()].count("\n") + 1
            symbols.append(Symbol(
                name=name, kind="function", file_path=file_path,
                line_start=line, line_end=line,
            ))

        for m in re.finditer(
            r"""(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+(\w+)""",
            content,
        ):
            name = m.group(1)
            if any(s.name == name for s in symbols):
                continue
            line = content[: m.start()].count("\n") + 1
            symbols.append(Symbol(
                name=name, kind="variable", file_path=file_path,
                line_start=line, line_end=line,
            ))

        for m in re.finditer(
            r"""(?:^|\n)\s*import\s+.*?\s+from\s+['"]([^'"]+)['"]""",
            content,
        ):
            imports.append(m.group(1))

        for m in re.finditer(
            r"""(?:^|\n)\s*import\s+['"]([^'"]+)['"]""",
            content,
        ):
            imports.append(m.group(1))

        for m in re.finditer(
            r"""(?:^|\n)\s*require\s*\(\s*['"]([^'"]+)['"]\s*\)""",
            content,
        ):
            imports.append(m.group(1))

        complexity = (
            len(re.findall(r"\bif\s*\(", content))
            + len(re.findall(r"\bfor\s*\(", content))
            + len(re.findall(r"\bwhile\s*\(", content))
            + len(re.findall(r"\bcatch\s*\(", content))
            + len(re.findall(r"\?\s*", content))
        )

        return symbols, imports, exports, complexity

    def _parse_config(
        self, content: str, file_path: str
    ) -> Tuple[List[Symbol], List[str], List[str], int]:
        symbols: List[Symbol] = []
        imports: List[str] = []
        exports: List[str] = []
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".json":
            try:
                import json
                data = json.loads(content)
                if isinstance(data, dict):
                    for key in data.keys():
                        symbols.append(Symbol(
                            name=key, kind="config", file_path=file_path,
                            line_start=1, line_end=1,
                        ))
            except (ValueError, RecursionError):
                pass

        elif ext in (".yaml", ".yml"):
            for m in re.finditer(r"^(\w[\w.-]*)\s*:", content, re.MULTILINE):
                symbols.append(Symbol(
                    name=m.group(1), kind="config", file_path=file_path,
                    line_start=content[: m.start()].count("\n") + 1,
                    line_end=content[: m.start()].count("\n") + 1,
                ))

        elif ext == ".toml":
            for m in re.finditer(r"^(\w[\w.-]*)\s*=", content, re.MULTILINE):
                symbols.append(Symbol(
                    name=m.group(1), kind="config", file_path=file_path,
                    line_start=content[: m.start()].count("\n") + 1,
                    line_end=content[: m.start()].count("\n") + 1,
                ))

        elif ext == ".ini" or ext == ".cfg":
            for m in re.finditer(r"^\[([\w.-]+)\]", content, re.MULTILINE):
                symbols.append(Symbol(
                    name=m.group(1), kind="config", file_path=file_path,
                    line_start=content[: m.start()].count("\n") + 1,
                    line_end=content[: m.start()].count("\n") + 1,
                ))

        return symbols, imports, exports, 0

    def _parse_docs(
        self, content: str, file_path: str
    ) -> Tuple[List[Symbol], List[str], List[str], int]:
        symbols: List[Symbol] = []
        exports: List[str] = []

        for m in re.finditer(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE):
            level = len(m.group(1))
            title = m.group(2).strip()
            line = content[: m.start()].count("\n") + 1
            symbols.append(Symbol(
                name=title, kind="module", file_path=file_path,
                line_start=line, line_end=line,
                metadata={"heading_level": level},
            ))

        return symbols, [], exports, 0

    def _module_path(self, rel_path: str) -> str:
        path = rel_path.replace(os.sep, "/")
        if path.endswith(".py"):
            path = path[:-3]
            if path.endswith("/__init__"):
                path = path[:-9]
        return path
