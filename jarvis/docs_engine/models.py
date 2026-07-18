"""Documentation Engine data models."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ModuleDoc:
    """Documentation for a single module."""

    name: str
    purpose: str
    architecture: str
    public_api: List[str]
    examples: List[str]
    dependencies: List[str]
    limitations: List[str]
    future_work: List[str]


@dataclass
class ProjectDocs:
    """Complete project documentation set."""

    modules: List[ModuleDoc]
    api_reference: str
    architecture_book: str
    handbook: str
    database_docs: str
    readme: str
