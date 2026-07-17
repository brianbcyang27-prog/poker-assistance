"""Agent Review Pipeline — Quality gate after task completion.

From Devin/Hermes pattern: after a worker completes a task, a reviewer agent
checks the result for quality, correctness, and completeness before it's
returned to the user or the calling agent.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from loguru import logger


class ReviewVerdict(str, Enum):
    PASS = "pass"
    NEEDS_WORK = "needs_work"
    FAIL = "fail"


@dataclass
class ReviewResult:
    """Result of a quality review."""
    verdict: ReviewVerdict
    score: float  # 0-1
    feedback: str
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    reviewer: str = "review_pipeline"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "score": round(self.score, 3),
            "feedback": self.feedback,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
        }


class ReviewPipeline:
    """Quality gate that reviews task outputs before delivery."""

    # Quality checks (applied in order)
    CHECKS = [
        "completeness",   # Did the task address all parts?
        "correctness",    # Is the output logically correct?
        "safety",         # No dangerous commands or secrets?
        "clarity",        # Is the response clear?
    ]

    # Patterns that indicate potential issues
    DANGER_PATTERNS = [
        "rm -rf", "sudo rm", "DROP TABLE", "DELETE FROM",
        "password =", "api_key =", "secret =", "token =",
        "chmod 777", "> /dev/sda", "dd if=",
    ]

    def __init__(self):
        self._reviews: list[ReviewResult] = []
        self._max_reviews = 200

    async def review(
        self,
        task_type: str,
        task_description: str,
        result: str,
        confidence: float,
        issues: list[str] = None,
    ) -> ReviewResult:
        """Review a task result and return quality assessment."""
        issues = issues or []
        score = 1.0
        found_issues = list(issues)
        suggestions = []

        # Check 1: Completeness
        if len(result.strip()) < 10:
            score -= 0.3
            found_issues.append("Response too short — may be incomplete")

        # Check 2: Safety
        lower_result = result.lower()
        for pattern in self.DANGER_PATTERNS:
            if pattern.lower() in lower_result:
                score -= 0.4
                found_issues.append(f"Potentially dangerous pattern detected: {pattern}")

        # Check 3: Confidence
        if confidence < 0.3:
            score -= 0.2
            found_issues.append(f"Low confidence: {confidence:.2f}")
            suggestions.append("Consider retrying with a different approach")

        # Check 4: Error signals
        error_signals = ["error", "failed", "exception", "traceback", "not found"]
        for sig in error_signals:
            if sig in lower_result and "no error" not in lower_result:
                score -= 0.1
                found_issues.append(f"Contains error signal: '{sig}'")

        # Check 5: Tool use completeness
        if "[TOOL:" in result and "[TOOL_RESULT:" not in result:
            score -= 0.1
            found_issues.append("Tool call present but no result — may be incomplete")

        # Determine verdict
        score = max(0.0, min(1.0, score))
        if score >= 0.8:
            verdict = ReviewVerdict.PASS
        elif score >= 0.5:
            verdict = ReviewVerdict.NEEDS_WORK
        else:
            verdict = ReviewVerdict.FAIL

        # Generate feedback
        if verdict == ReviewVerdict.PASS:
            feedback = "Task output meets quality standards."
        elif verdict == ReviewVerdict.NEEDS_WORK:
            feedback = f"Task output has {len(found_issues)} issue(s) that should be addressed."
            suggestions.append("Review the flagged issues and consider a retry")
        else:
            feedback = f"Task output failed quality check ({len(found_issues)} issues)."
            suggestions.append("Retry the task with more context or a different approach")

        review = ReviewResult(
            verdict=verdict,
            score=score,
            feedback=feedback,
            issues=found_issues,
            suggestions=suggestions,
        )

        self._reviews.append(review)
        if len(self._reviews) > self._max_reviews:
            self._reviews = self._reviews[-self._max_reviews:]

        logger.info(f"Review: {verdict.value} (score={score:.2f}, issues={len(found_issues)})")
        return review

    def get_stats(self) -> dict:
        if not self._reviews:
            return {"total": 0, "pass_rate": 0, "avg_score": 0}

        pass_count = sum(1 for r in self._reviews if r.verdict == ReviewVerdict.PASS)
        avg_score = sum(r.score for r in self._reviews) / len(self._reviews)
        return {
            "total": len(self._reviews),
            "pass_rate": round(pass_count / len(self._reviews), 3),
            "avg_score": round(avg_score, 3),
            "verdicts": {
                "pass": pass_count,
                "needs_work": sum(1 for r in self._reviews if r.verdict == ReviewVerdict.NEEDS_WORK),
                "fail": sum(1 for r in self._reviews if r.verdict == ReviewVerdict.FAIL),
            },
        }


# Module-level singleton
review_pipeline = ReviewPipeline()
