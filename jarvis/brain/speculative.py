"""Speculative Planner — Predicts next steps and pre-delegates tasks.

From Hermes/Devin pattern: after a task completes, predict likely follow-ups
and pre-warm agents or queue micro-tasks to reduce perceived latency.
"""

import time
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class SpeculativeTask:
    """A predicted follow-up task."""
    task_type: str
    description: str
    confidence: float  # 0-1 how likely this follow-up is
    suggested_worker: str  # card_id of suggested worker
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending | pre_delegated | confirmed | expired


class SpeculativePlanner:
    """Predicts follow-up tasks and pre-delegates to reduce latency."""

    # Pattern: task_type -> likely follow-ups
    PREDICTION_PATTERNS = {
        "code_review": [
            {"type": "write_tests", "desc": "Write tests for the reviewed code", "confidence": 0.7, "worker": "♠3"},
            {"type": "refactor", "desc": "Refactor based on review feedback", "confidence": 0.4, "worker": "♠4"},
        ],
        "write_code": [
            {"type": "code_review", "desc": "Review the written code", "confidence": 0.8, "worker": "♠5"},
            {"type": "write_tests", "desc": "Write tests for the new code", "confidence": 0.6, "worker": "♠3"},
        ],
        "web_search": [
            {"type": "summarize", "desc": "Summarize search results", "confidence": 0.9, "worker": "♦2"},
            {"type": "fact_check", "desc": "Fact-check key claims", "confidence": 0.5, "worker": "♦4"},
        ],
        "screen_capture": [
            {"type": "analyze_image", "desc": "Analyze the screenshot content", "confidence": 0.7, "worker": "♣3"},
            {"type": "extract_text", "desc": "Extract text from screenshot", "confidence": 0.6, "worker": "♣4"},
        ],
        "browser_navigate": [
            {"type": "browser_interact", "desc": "Interact with the loaded page", "confidence": 0.8, "worker": "♣3"},
            {"type": "browser_screenshot", "desc": "Screenshot the page", "confidence": 0.5, "worker": "♣4"},
        ],
        "shell_execute": [
            {"type": "analyze_output", "desc": "Analyze command output", "confidence": 0.6, "worker": "♣5"},
        ],
        "resume_project": [
            {"type": "check_status", "desc": "Check project status and recent changes", "confidence": 0.9, "worker": "♣6"},
            {"type": "run_project", "desc": "Start the project server", "confidence": 0.7, "worker": "♣6"},
        ],
    }

    def __init__(self, max_predictions: int = 50):
        self._predictions: list[SpeculativeTask] = []
        self._max_predictions = max_predictions
        self._confirmed: list[str] = []  # task_types that were confirmed correct

    def predict(self, completed_task_type: str) -> list[SpeculativeTask]:
        """Generate predictions for follow-up tasks after a task completes."""
        patterns = self.PREDICTION_PATTERNS.get(completed_task_type, [])

        predictions = []
        for p in patterns:
            task = SpeculativeTask(
                task_type=p["type"],
                description=p["desc"],
                confidence=p["confidence"],
                suggested_worker=p["worker"],
            )
            predictions.append(task)
            self._predictions.append(task)

        # Trim old predictions
        if len(self._predictions) > self._max_predictions:
            self._predictions = self._predictions[-self._max_predictions:]

        if predictions:
            logger.info(f"Speculative: predicted {len(predictions)} follow-ups for '{completed_task_type}'")
        return predictions

    def confirm(self, task_type: str):
        """Mark a prediction as confirmed (user actually asked for it)."""
        self._confirmed.append(task_type)
        for p in self._predictions:
            if p.task_type == task_type and p.status == "pending":
                p.status = "confirmed"
                break

    def get_pending(self) -> list[SpeculativeTask]:
        """Get pending predictions that haven't been confirmed or expired."""
        now = time.time()
        pending = []
        for p in self._predictions:
            if p.status == "pending" and (now - p.created_at) < 300:  # 5min TTL
                pending.append(p)
            elif p.status == "pending" and (now - p.created_at) >= 300:
                p.status = "expired"
        return pending

    def get_accuracy(self) -> float:
        """Calculate prediction accuracy."""
        total = len(self._confirmed)
        if total == 0:
            return 0.0
        return total / max(1, len(self._predictions))

    def get_stats(self) -> dict:
        return {
            "total_predictions": len(self._predictions),
            "pending": len(self.get_pending()),
            "confirmed": len(self._confirmed),
            "accuracy": round(self.get_accuracy(), 3),
            "patterns": list(self.PREDICTION_PATTERNS.keys()),
        }


# Module-level singleton
speculative_planner = SpeculativePlanner()
