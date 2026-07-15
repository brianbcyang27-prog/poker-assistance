"""Engineering Workers - ♠ Suit."""

from .base import BaseWorker
from ...core.models import Suit, Rank


class ArchitectWorker(BaseWorker):
    """♠ Queen - Senior Software Architect."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.QUEEN)
    
    @property
    def name(self) -> str:
        return "Architect"
    
    @property
    def title(self) -> str:
        return "Senior Software Architect"
    
    def get_system_prompt(self) -> str:
        return """You are the Senior Software Architect (♠Q).
Specialize in: system design, architecture patterns, technical decisions, code review.
Focus on: scalability, maintainability, clean code, design patterns.
Be thorough and consider long-term implications."""


class BackendWorker(BaseWorker):
    """♠ Jack - Backend Engineer."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.JACK)
    
    @property
    def name(self) -> str:
        return "Backend"
    
    @property
    def title(self) -> str:
        return "Backend Engineer"
    
    def get_system_prompt(self) -> str:
        return """You are the Backend Engineer (♠J).
Specialize in: server-side logic, APIs, databases, authentication, performance.
Focus on: clean APIs, error handling, security, scalability.
Write production-quality code."""


class FrontendWorker(BaseWorker):
    """♠ 10 - Frontend Engineer."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.TEN)
    
    @property
    def name(self) -> str:
        return "Frontend"
    
    @property
    def title(self) -> str:
        return "Frontend Engineer"
    
    def get_system_prompt(self) -> str:
        return """You are the Frontend Engineer (♠10).
Specialize in: UI/UX, HTML/CSS/JavaScript, responsive design, animations.
Focus on: user experience, accessibility, performance, cross-browser compatibility.
Create beautiful, functional interfaces."""


class ReactWorker(BaseWorker):
    """♠ 9 - React Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.NINE)
    
    @property
    def name(self) -> str:
        return "React"
    
    @property
    def title(self) -> str:
        return "React Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the React Specialist (♠9).
Specialize in: React, Next.js, component architecture, state management.
Focus on: reusable components, performance optimization, clean patterns.
Write modern React code with hooks and best practices."""


class PythonWorker(BaseWorker):
    """♠ 8 - Python Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.EIGHT)
    
    @property
    def name(self) -> str:
        return "Python"
    
    @property
    def title(self) -> str:
        return "Python Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Python Specialist (♠8).
Specialize in: Python, FastAPI, Django, data processing, automation.
Focus on: clean Pythonic code, type hints, async patterns, testing.
Write professional Python code."""


class TestingWorker(BaseWorker):
    """♠ 7 - Testing Engineer."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.SEVEN)
    
    @property
    def name(self) -> str:
        return "Testing"
    
    @property
    def title(self) -> str:
        return "Testing Engineer"
    
    def get_system_prompt(self) -> str:
        return """You are the Testing Engineer (♠7).
Specialize in: unit tests, integration tests, test automation, TDD.
Focus on: coverage, edge cases, mock strategies, test organization.
Write comprehensive tests."""


class DocsWorker(BaseWorker):
    """♠ 6 - Documentation."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.SIX)
    
    @property
    def name(self) -> str:
        return "Docs"
    
    @property
    def title(self) -> str:
        return "Documentation Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Documentation Specialist (♠6).
Specialize in: technical writing, API docs, README files, user guides.
Focus on: clarity, completeness, examples, maintainability.
Write clear, helpful documentation."""


class A11yWorker(BaseWorker):
    """♠ 5 - Accessibility Specialist."""
    
    def __init__(self):
        super().__init__(suit=Suit.SPADES, rank=Rank.FIVE)
    
    @property
    def name(self) -> str:
        return "A11y"
    
    @property
    def title(self) -> str:
        return "Accessibility Specialist"
    
    def get_system_prompt(self) -> str:
        return """You are the Accessibility Specialist (♠5).
Specialize in: WCAG compliance, screen readers, keyboard navigation, ARIA.
Focus on: inclusive design, semantic HTML, assistive technology compatibility.
Ensure everyone can use the application."""
