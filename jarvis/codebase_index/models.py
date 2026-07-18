"""Data models for the codebase indexing engine."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set


SYMBOL_KINDS = frozenset([
    "class", "function", "method", "variable",
    "route", "config", "table", "component", "module",
])

MATCH_TYPES = frozenset(["name", "docstring", "signature", "usage"])


@dataclass
class Symbol:
    """A named symbol in the codebase."""
    name: str
    kind: str  # class/function/method/variable/route/config/table/component/module
    file_path: str
    line_start: int
    line_end: int = 0
    docstring: Optional[str] = None
    signature: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    parent_class: Optional[str] = None
    children: List[str] = field(default_factory=list)
    complexity: int = 1
    loc: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.line_end == 0:
            self.line_end = self.line_start

    @property
    def full_name(self) -> str:
        if self.parent_class:
            return f"{self.parent_class}.{self.name}"
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "docstring": self.docstring,
            "signature": self.signature,
            "decorators": self.decorators,
            "imports": self.imports,
            "calls": self.calls,
            "parent_class": self.parent_class,
            "children": self.children,
            "complexity": self.complexity,
            "loc": self.loc,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Symbol:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SearchResult:
    """A search result with relevance scoring."""
    symbol: Symbol
    score: float
    match_type: str  # name/docstring/signature/usage
    context_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol.to_dict(),
            "score": self.score,
            "match_type": self.match_type,
            "context_lines": self.context_lines,
        }


@dataclass
class FileIndex:
    """Index of a single file."""
    path: str
    language: str
    symbols: List[Symbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    loc: int = 0
    complexity: int = 0
    last_modified: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": self.imports,
            "exports": self.exports,
            "loc": self.loc,
            "complexity": self.complexity,
            "last_modified": self.last_modified,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FileIndex:
        symbols = [Symbol.from_dict(s) for s in data.get("symbols", [])]
        return cls(
            path=data["path"],
            language=data["language"],
            symbols=symbols,
            imports=data.get("imports", []),
            exports=data.get("exports", []),
            loc=data.get("loc", 0),
            complexity=data.get("complexity", 0),
            last_modified=data.get("last_modified", 0.0),
        )


@dataclass
class RepoIndex:
    """Full index of a repository."""
    files: Dict[str, FileIndex] = field(default_factory=dict)
    symbols: Dict[str, List[Symbol]] = field(default_factory=dict)
    modules: Dict[str, List[str]] = field(default_factory=dict)
    call_graph: Dict[str, List[str]] = field(default_factory=dict)
    import_graph: Dict[str, List[str]] = field(default_factory=dict)
    inheritance_graph: Dict[str, List[str]] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files": {k: v.to_dict() for k, v in self.files.items()},
            "symbols": {k: [s.to_dict() for s in v] for k, v in self.symbols.items()},
            "modules": self.modules,
            "call_graph": self.call_graph,
            "import_graph": self.import_graph,
            "inheritance_graph": self.inheritance_graph,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepoIndex:
        files = {k: FileIndex.from_dict(v) for k, v in data.get("files", {}).items()}
        symbols = {
            k: [Symbol.from_dict(s) for s in v]
            for k, v in data.get("symbols", {}).items()
        }
        return cls(
            files=files,
            symbols=symbols,
            modules=data.get("modules", {}),
            call_graph=data.get("call_graph", {}),
            import_graph=data.get("import_graph", {}),
            inheritance_graph=data.get("inheritance_graph", {}),
            stats=data.get("stats", {}),
        )

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load(cls, path: str) -> RepoIndex:
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
