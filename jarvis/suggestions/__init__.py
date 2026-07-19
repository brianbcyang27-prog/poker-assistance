"""JARVIS Smart Suggestions Engine — confidence-scored, non-intrusive suggestions.

Generates suggestions based on context analysis and built-in rules.
Suggestions are scored by confidence and categorized for targeted advice.

Usage:
    engine = SuggestionEngine()
    suggestions = await engine.analyze(context, timeline)
"""

import logging
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import Suggestion, SuggestionCategory, SuggestionPriority, SuggestionStats

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Generates confidence-scored suggestions without interrupting workflow."""

    def __init__(self) -> None:
        self._suggestions: List[Suggestion] = []
        self._dismissed_ids: set = set()
        self._acknowledged_ids: set = set()
        self._stats = SuggestionStats()

    async def analyze(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> List[Suggestion]:
        """Analyze context and timeline to generate suggestions.

        Args:
            context: Current working context (files, project info, etc.)
            timeline: Recent activity timeline for pattern detection.

        Returns:
            List of generated suggestions sorted by confidence.
        """
        new_suggestions: List[Suggestion] = []

        rules = [
            self._rule_no_recent_commits,
            self._rule_large_files,
            self._rule_no_tests,
            self._rule_stale_todos,
            self._rule_build_failures,
            self._rule_unused_imports,
            self._rule_long_functions,
            self._rule_missing_docs,
            self._rule_circular_imports,
            self._rule_dead_code,
        ]

        for rule in rules:
            try:
                result = await rule(context, timeline)
                if result is not None:
                    new_suggestions.append(result)
            except Exception as exc:
                logger.warning("Rule %s failed: %s", rule.__name__, exc)

        new_suggestions.sort(key=lambda s: s.confidence, reverse=True)
        self._suggestions.extend(new_suggestions)
        self._stats.total_generated += len(new_suggestions)

        for s in new_suggestions:
            cat = s.category.value
            self._stats.by_category[cat] = self._stats.by_category.get(cat, 0) + 1

        return new_suggestions

    async def should_notify(self, suggestion: Suggestion) -> bool:
        """Check if a suggestion warrants notification.

        A suggestion warrants notification if its confidence exceeds
        the auto-dismiss threshold and it has not been dismissed.
        """
        if suggestion.dismissed:
            return False
        if suggestion.confidence < suggestion.auto_dismiss_threshold:
            return False
        return True

    async def get_suggestions(self, limit: int = 10) -> List[Suggestion]:
        """Get recent active suggestions, newest first.

        Args:
            limit: Maximum number of suggestions to return.

        Returns:
            List of non-dismissed suggestions.
        """
        active = [s for s in self._suggestions if not s.dismissed]
        active.sort(key=lambda s: s.timestamp, reverse=True)
        return active[:limit]

    async def dismiss(self, suggestion_id: str) -> None:
        """Dismiss a suggestion by its ID."""
        for s in self._suggestions:
            if s.id == suggestion_id:
                s.dismissed = True
                self._dismissed_ids.add(suggestion_id)
                self._stats.total_dismissed += 1
                self._update_acceptance_rate()
                return

    async def acknowledge(self, suggestion_id: str) -> None:
        """Acknowledge a suggestion by its ID."""
        for s in self._suggestions:
            if s.id == suggestion_id:
                s.acknowledged = True
                self._acknowledged_ids.add(suggestion_id)
                self._update_acceptance_rate()
                return

    async def get_stats(self) -> Dict[str, Any]:
        """Get suggestion statistics."""
        self._update_acceptance_rate()
        return self._stats.to_dict()

    def _update_acceptance_rate(self) -> None:
        total = self._stats.total_generated
        if total == 0:
            self._stats.acceptance_rate = 0.0
            return
        acknowledged = len(self._acknowledged_ids)
        self._stats.acceptance_rate = round(acknowledged / total, 4)

    def _new_suggestion(
        self,
        title: str,
        description: str,
        confidence: float,
        category: SuggestionCategory,
        priority: SuggestionPriority,
    ) -> Suggestion:
        """Create a new Suggestion with a unique ID and current timestamp."""
        return Suggestion(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            title=title,
            description=description,
            confidence=max(0.0, min(1.0, confidence)),
            category=category,
            priority=priority,
        )

    # ------------------------------------------------------------------
    # Built-in rules
    # ------------------------------------------------------------------

    async def _rule_no_recent_commits(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 1: No commits in 3+ hours."""
        last_commit_time = context.get("last_commit_time")
        if last_commit_time is None:
            return None

        if isinstance(last_commit_time, str):
            try:
                last_commit_time = datetime.fromisoformat(last_commit_time)
            except ValueError:
                return None

        elapsed = datetime.now() - last_commit_time
        if elapsed < timedelta(hours=3):
            return None

        hours = int(elapsed.total_seconds() // 3600)
        return self._new_suggestion(
            title="You haven't committed in a while",
            description=f"No commits detected in the last {hours} hours. Consider saving your progress.",
            confidence=min(0.9, 0.5 + hours * 0.05),
            category=SuggestionCategory.COMMIT,
            priority=SuggestionPriority.MEDIUM,
        )

    async def _rule_large_files(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 2: Large files (>500 lines)."""
        large_files = context.get("large_files", [])
        if not large_files:
            return None

        names = [f.get("name", "unknown") for f in large_files[:3]]
        max_lines = max((f.get("lines", 0) for f in large_files), default=0)
        confidence = min(0.85, 0.4 + len(large_files) * 0.1)

        return self._new_suggestion(
            title="This file is getting large",
            description=f"{len(large_files)} file(s) exceed 500 lines: {', '.join(names)}. Longest is {max_lines} lines.",
            confidence=confidence,
            category=SuggestionCategory.REFACTOR,
            priority=SuggestionPriority.MEDIUM if len(large_files) <= 3 else SuggestionPriority.HIGH,
        )

    async def _rule_no_tests(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 3: No tests found in project."""
        has_tests = context.get("has_tests", True)
        if has_tests:
            return None

        return self._new_suggestion(
            title="This project has no tests",
            description="No test files detected. Adding tests improves reliability and enables safe refactoring.",
            confidence=0.75,
            category=SuggestionCategory.TEST,
            priority=SuggestionPriority.HIGH,
        )

    async def _rule_stale_todos(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 4: Stale TODO comments."""
        todo_count = context.get("todo_count", 0)
        if todo_count < 1:
            return None

        confidence = min(0.8, 0.3 + todo_count * 0.05)
        return self._new_suggestion(
            title=f"There are {todo_count} TODO comments",
            description=f"Found {todo_count} TODO comment(s) across the codebase. Consider addressing or triaging them.",
            confidence=confidence,
            category=SuggestionCategory.REMINDER,
            priority=SuggestionPriority.LOW if todo_count <= 5 else SuggestionPriority.MEDIUM,
        )

    async def _rule_build_failures(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 5: Build failures detected."""
        build_failed = context.get("build_failed", False)
        if not build_failed:
            return None

        error_msg = context.get("build_error", "Unknown error")
        return self._new_suggestion(
            title="Build failed",
            description=f"Last build failed: {error_msg[:200]}",
            confidence=0.95,
            category=SuggestionCategory.BUG,
            priority=SuggestionPriority.HIGH,
        )

    async def _rule_unused_imports(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 6: Unused imports detected."""
        unused_imports = context.get("unused_imports", [])
        if not unused_imports:
            return None

        count = len(unused_imports)
        confidence = min(0.8, 0.4 + count * 0.05)
        return self._new_suggestion(
            title=f"Found {count} unused import(s)",
            description=f"Unused imports: {', '.join(unused_imports[:5])}. Remove them to clean up the code.",
            confidence=confidence,
            category=SuggestionCategory.REFACTOR,
            priority=SuggestionPriority.LOW,
        )

    async def _rule_long_functions(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 7: Long functions (>50 lines)."""
        long_functions = context.get("long_functions", [])
        if not long_functions:
            return None

        worst = max(long_functions, key=lambda f: f.get("lines", 0))
        count = len(long_functions)
        confidence = min(0.85, 0.4 + count * 0.1)
        return self._new_suggestion(
            title=f"Function {worst.get('name', 'X')} is {worst.get('lines', 0)} lines",
            description=f"{count} function(s) exceed 50 lines. Consider refactoring for readability.",
            confidence=confidence,
            category=SuggestionCategory.REFACTOR,
            priority=SuggestionPriority.MEDIUM,
        )

    async def _rule_missing_docs(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 8: Modules without docstrings."""
        missing_docs = context.get("missing_docstrings", [])
        if not missing_docs:
            return None

        count = len(missing_docs)
        confidence = min(0.7, 0.3 + count * 0.04)
        return self._new_suggestion(
            title=f"Module X has no docstring",
            description=f"{count} module(s) lack docstrings: {', '.join(missing_docs[:3])}.",
            confidence=confidence,
            category=SuggestionCategory.DOCUMENTATION,
            priority=SuggestionPriority.LOW,
        )

    async def _rule_circular_imports(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 9: Circular dependency detected."""
        circular = context.get("circular_imports", [])
        if not circular:
            return None

        pair = circular[0] if circular else ("", "")
        return self._new_suggestion(
            title="Circular dependency detected",
            description=f"Circular import chain: {' -> '.join(pair) if isinstance(pair, (list, tuple)) else pair}",
            confidence=0.85,
            category=SuggestionCategory.BUG,
            priority=SuggestionPriority.HIGH,
        )

    async def _rule_dead_code(
        self, context: Dict[str, Any], timeline: List[Dict]
    ) -> Optional[Suggestion]:
        """Rule 10: Unused functions detected."""
        dead_code = context.get("dead_code", [])
        if not dead_code:
            return None

        count = len(dead_code)
        confidence = min(0.75, 0.35 + count * 0.05)
        return self._new_suggestion(
            title=f"Found {count} unused function(s)",
            description=f"Unused: {', '.join(dead_code[:5])}. Consider removing dead code.",
            confidence=confidence,
            category=SuggestionCategory.REFACTOR,
            priority=SuggestionPriority.LOW,
        )
