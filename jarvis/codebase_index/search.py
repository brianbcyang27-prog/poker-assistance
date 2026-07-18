"""Search engine for the codebase index."""

from __future__ import annotations

import difflib
import os
import re
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from .models import FileIndex, RepoIndex, SearchResult, Symbol


class SearchEngine:
    """Fuzzy and exact search over the codebase index."""

    def __init__(self, repo_index: RepoIndex) -> None:
        self.index = repo_index

    def fuzzy_name_match(self, query: str, name: str) -> float:
        """Score how closely `name` matches `query` (0.0 - 1.0)."""
        query_lower = query.lower()
        name_lower = name.lower()

        if query_lower == name_lower:
            return 1.0

        if query_lower in name_lower:
            return 0.8 + 0.2 * (len(query_lower) / len(name_lower))

        if name_lower in query_lower:
            return 0.6

        ratio = difflib.SequenceMatcher(None, query_lower, name_lower).ratio()
        if ratio > 0.6:
            return ratio * 0.7

        query_parts = re.split(r"[_.\-]", query_lower)
        name_parts = re.split(r"[_.\-]", name_lower)
        matched_parts = sum(1 for p in query_parts if p in name_parts)
        if matched_parts > 0:
            return 0.3 + 0.4 * (matched_parts / len(query_parts))

        return 0.0

    def search_name(self, query: str, limit: int = 50) -> List[SearchResult]:
        """Fuzzy search by symbol name."""
        results: List[Tuple[float, Symbol]] = []
        for name, sym_list in self.index.symbols.items():
            score = self.fuzzy_name_match(query, name)
            if score > 0.2:
                for sym in sym_list:
                    results.append((score, sym))
        results.sort(key=lambda x: x[0], reverse=True)
        return [
            SearchResult(symbol=sym, score=score, match_type="name")
            for score, sym in results[:limit]
        ]

    def search_exact(self, name: str) -> List[Symbol]:
        """Exact lookup by symbol name."""
        return list(self.index.symbols.get(name, []))

    def search_docstring(self, query: str, limit: int = 50) -> List[SearchResult]:
        """Search symbol docstrings for a query."""
        results: List[SearchResult] = []
        query_lower = query.lower()
        for sym_list in self.index.symbols.values():
            for sym in sym_list:
                if sym.docstring and query_lower in sym.docstring.lower():
                    score = 0.5 + 0.5 * (
                        sym.docstring.lower().count(query_lower)
                        / max(len(sym.docstring), 1)
                    )
                    results.append(
                        SearchResult(symbol=sym, score=min(score, 1.0), match_type="docstring")
                    )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def search_signature(self, query: str, limit: int = 50) -> List[SearchResult]:
        """Search function/method signatures."""
        results: List[SearchResult] = []
        query_lower = query.lower()
        for sym_list in self.index.symbols.values():
            for sym in sym_list:
                if sym.signature and query_lower in sym.signature.lower():
                    results.append(
                        SearchResult(symbol=sym, score=0.7, match_type="signature")
                    )
        return results[:limit]

    def search_usage(self, name: str, limit: int = 50) -> List[SearchResult]:
        """Find symbols that call or reference the given name."""
        results: List[SearchResult] = []
        for sym_list in self.index.symbols.values():
            for sym in sym_list:
                if name in sym.calls:
                    results.append(
                        SearchResult(symbol=sym, score=0.6, match_type="usage")
                    )
                elif name in sym.imports:
                    results.append(
                        SearchResult(symbol=sym, score=0.5, match_type="usage")
                    )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def references(self, name: str) -> List[Symbol]:
        """Find all symbols that reference the given name."""
        seen: Set[str] = set()
        results: List[Symbol] = []
        for sym_list in self.index.symbols.values():
            for sym in sym_list:
                key = f"{sym.file_path}:{sym.name}:{sym.line_start}"
                if key in seen:
                    continue
                if (
                    name in sym.calls
                    or name in sym.imports
                    or name == sym.parent_class
                    or name in sym.children
                    or (sym.docstring and name in sym.docstring)
                ):
                    seen.add(key)
                    results.append(sym)
        return results

    def import_chain(self, module_name: str, max_depth: int = 10) -> Dict[str, List[str]]:
        """Traverse import dependencies from a module."""
        visited: Set[str] = set()
        result: Dict[str, List[str]] = {}
        queue: deque = deque([(module_name, 0)])
        while queue:
            current, depth = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            deps = self.index.import_graph.get(current, [])
            result[current] = deps
            for dep in deps:
                if dep not in visited:
                    queue.append((dep, depth + 1))
        return result

    def call_chain(self, symbol_name: str, max_depth: int = 10) -> Dict[str, List[str]]:
        """Traverse call graph from a symbol."""
        visited: Set[str] = set()
        result: Dict[str, List[str]] = {}
        queue: deque = deque([(symbol_name, 0)])
        while queue:
            current, depth = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            callees = self.index.call_graph.get(current, [])
            result[current] = callees
            for callee in callees:
                if callee not in visited:
                    queue.append((callee, depth + 1))
        return result

    def callers_of(self, symbol_name: str) -> List[str]:
        """Find all symbols that call the given symbol (reverse call graph)."""
        callers: List[str] = []
        for caller, callees in self.index.call_graph.items():
            if symbol_name in callees:
                callers.append(caller)
        return callers

    def importers_of(self, module_name: str) -> List[str]:
        """Find all modules that import the given module."""
        importers: List[str] = []
        for importer, imports in self.index.import_graph.items():
            if module_name in imports:
                importers.append(importer)
        return importers

    def inheritance_chain(self, class_name: str, max_depth: int = 10) -> Dict[str, List[str]]:
        """Traverse class hierarchy."""
        visited: Set[str] = set()
        result: Dict[str, List[str]] = {}
        queue: deque = deque([(class_name, 0)])
        while queue:
            current, depth = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            parents = self.index.inheritance_graph.get(current, [])
            result[current] = parents
            for parent in parents:
                if parent not in visited:
                    queue.append((parent, depth + 1))
        return result

    def children_of(self, class_name: str) -> List[str]:
        """Find all classes that inherit from the given class."""
        children: List[str] = []
        for child, parents in self.index.inheritance_graph.items():
            if class_name in parents:
                children.append(child)
        return children

    def semantic_search(self, query: str, limit: int = 50) -> List[SearchResult]:
        """Combined search across name, docstring, signature, and usage."""
        seen: Dict[str, SearchResult] = {}
        for result in self.search_name(query, limit=limit):
            key = f"{result.symbol.file_path}:{result.symbol.name}"
            if key not in seen or result.score > seen[key].score:
                seen[key] = result
        for result in self.search_docstring(query, limit=limit):
            key = f"{result.symbol.file_path}:{result.symbol.name}"
            if key not in seen or result.score > seen[key].score:
                seen[key] = result
        for result in self.search_signature(query, limit=limit):
            key = f"{result.symbol.file_path}:{result.symbol.name}"
            if key not in seen or result.score > seen[key].score:
                seen[key] = result
        combined = list(seen.values())
        combined.sort(key=lambda r: r.score, reverse=True)
        return combined[:limit]

    def find_context_lines(self, file_path: str, line_number: int, context: int = 3) -> List[str]:
        """Read surrounding lines from a file for context."""
        full = self._resolve_path(file_path)
        if not full or not os.path.isfile(full):
            return []
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (OSError, IOError):
            return []
        start = max(0, line_number - 1 - context)
        end = min(len(lines), line_number + context)
        return [f"{i + 1}: {lines[i].rstrip()}" for i in range(start, end)]

    def _resolve_path(self, file_path: str) -> Optional[str]:
        if os.path.isabs(file_path):
            return file_path
        if self.index.stats.get("repo_path"):
            return os.path.join(self.index.stats["repo_path"], file_path)
        return file_path
