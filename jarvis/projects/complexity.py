"""Complexity estimation for the task-flow router (v9.0.0 M2)."""

import re

_SMALL_SCORE = 25
_MISSION_SCORE = 55
_PROJECT_SCORE = 80

_MULTI_GOAL_MARKERS = re.compile(r"\b(and|then|also|plus|after that|additionally)\b", re.IGNORECASE)
_IMPERATIVE_MARKERS = re.compile(
    r"\b(build|create|implement|write|develop|design|refactor|fix|add|make|set up|"
    r"configure|migrate|deploy|analyze|research)\b",
    re.IGNORECASE,
)
_DOMAIN_KEYWORDS = re.compile(
    r"\b(website|app|api|database|backend|frontend|pipeline|script|module|"
    r"dashboard|service|integration|test|algorithm)\b",
    re.IGNORECASE,
)
_ARTIFACT_MARKERS = re.compile(
    r"\b(report|document|design doc|spec|architecture|diagram|proposal|"
    r"code review|plan)\b",
    re.IGNORECASE,
)


def _score_request(request: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    length = len(request.strip())
    if length > 300:
        score += 35
        reasons.append("long request")
    elif length > 120:
        score += 20
        reasons.append("detailed request")
    elif length > 40:
        score += 5
        reasons.append("moderate length")

    if _MULTI_GOAL_MARKERS.search(request):
        score += 20
        reasons.append("multiple goals")
    if _IMPERATIVE_MARKERS.search(request):
        score += 15
        reasons.append("imperative build verb")
    if _DOMAIN_KEYWORDS.search(request):
        score += 15
        reasons.append("technical domain keywords")
    if _ARTIFACT_MARKERS.search(request):
        score += 15
        reasons.append("artifact delivery expected")

    return min(100, score), reasons


def suggest_action(level: str) -> str:
    return {
        "tiny": "direct",
        "small": "mission",
        "mission": "mission",
        "project": "create_project",
    }.get(level, "direct")


def estimate_complexity(request: str) -> dict:
    """Estimate complexity of a user request.

    Returns {level, score, reasons, suggested_action}. `tiny` → direct
    answer; `small` → single mission; `mission` → mission under an existing
    project or a "create project?" prompt; `project` → auto-create project
    and start its first mission.
    """
    score, reasons = _score_request(request)

    if score >= _PROJECT_SCORE:
        level = "project"
    elif score >= _MISSION_SCORE:
        level = "mission"
    elif score >= _SMALL_SCORE:
        level = "small"
    else:
        level = "tiny"

    return {
        "level": level,
        "score": score,
        "reasons": reasons,
        "suggested_action": suggest_action(level),
    }
