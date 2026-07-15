"""Research Workers - ♦ Suit."""

from .base import BaseWorker
from ...core.models import Suit, Rank


class WebResearchWorker(BaseWorker):
    """♦ Queen - Web Researcher."""
    
    def __init__(self):
        super().__init__(suit=Suit.DIAMONDS, rank=Rank.QUEEN)
    
    @property
    def name(self) -> str:
        return "Web Research"
    
    @property
    def title(self) -> str:
        return "Web Researcher"
    
    def get_system_prompt(self) -> str:
        return """You are the Web Researcher (♦Q).
Specialize in: web searches, information gathering, data collection.
Focus on: accuracy, source credibility, comprehensive coverage.
Find reliable information efficiently."""


class DocumentationWorker(BaseWorker):
    """♦ Jack - Documentation Researcher."""
    
    def __init__(self):
        super().__init__(suit=Suit.DIAMONDS, rank=Rank.JACK)
    
    @property
    def name(self) -> str:
        return "Doc Research"
    
    @property
    def title(self) -> str:
        return "Documentation Researcher"
    
    def get_system_prompt(self) -> str:
        return """You are the Documentation Researcher (♦J).
Specialize in: technical documentation, API references, library docs.
Focus on: official sources, version accuracy, practical examples.
Find the right documentation for any technology."""


class FactCheckWorker(BaseWorker):
    """♦ 10 - Fact Checker."""
    
    def __init__(self):
        super().__init__(suit=Suit.DIAMONDS, rank=Rank.TEN)
    
    @property
    def name(self) -> str:
        return "Fact Check"
    
    @property
    def title(self) -> str:
        return "Fact Checker"
    
    def get_system_prompt(self) -> str:
        return """You are the Fact Checker (♦10).
Specialize in: verification, cross-referencing, source validation.
Focus on: accuracy, evidence, multiple sources.
Verify claims and ensure correctness."""
