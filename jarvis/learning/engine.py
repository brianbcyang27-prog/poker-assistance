"""Continuous Learning Engine — learn from every mission."""

import hashlib
import json
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from .models import LearningRecord, SkillUpdate


class LearningEngine:
    """Analyses completed missions and distills actionable learnings."""

    def __init__(self) -> None:
        self._knowledge_base: List[LearningRecord] = []
        self._skill_registry: Dict[str, SkillUpdate] = {}

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------

    async def analyze_mission(self, mission_data: Dict[str, Any]) -> LearningRecord:
        """Analyse a completed mission and produce a LearningRecord."""
        mission_id = str(mission_data.get("mission_id", self._hash(mission_data)))
        libraries = self._extract_libraries(mission_data)
        patterns = self._extract_patterns_from_single(mission_data)
        mistakes = self._extract_mistakes(mission_data)
        speed = self._extract_speed_improvements(mission_data)
        suggestions = self._extract_skill_suggestions(mission_data)
        knowledge = self._extract_knowledge_updates(mission_data)

        record = LearningRecord(
            mission_id=mission_id,
            libraries_discovered=libraries,
            patterns_learned=patterns,
            mistakes=mistakes,
            speed_improvements=speed,
            skill_suggestions=suggestions,
            knowledge_updates=knowledge,
        )
        await self.update_knowledge_base(record)
        return record

    async def extract_patterns(self, missions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find recurring patterns across multiple missions."""
        pattern_counter: Counter = Counter()
        pattern_details: Dict[str, List[str]] = defaultdict(list)

        for mission in missions:
            patterns = self._extract_patterns_from_single(mission)
            mission_id = str(mission.get("mission_id", "unknown"))
            for p in patterns:
                pattern_counter[p] += 1
                pattern_details[p].append(mission_id)

        results: List[Dict[str, Any]] = []
        for pattern, count in pattern_counter.most_common():
            if count >= 2:
                results.append({
                    "pattern": pattern,
                    "occurrence_count": count,
                    "mission_ids": pattern_details[pattern],
                })
        return results

    async def suggest_skill(
        self, mission_data: Dict[str, Any]
    ) -> Optional[SkillUpdate]:
        """Suggest a brand-new skill based on a mission's data."""
        suggestions = self._extract_skill_suggestions(mission_data)
        if not suggestions:
            return None

        best = suggestions[0]
        return SkillUpdate(
            skill_name=best,
            description=f"Auto-suggested from mission {mission_data.get('mission_id', 'unknown')}",
            before=None,
            after=best,
            reason="Recurring pattern detected across missions",
            confidence=0.5,
        )

    async def improve_skill(
        self, skill_name: str, mission_data: Dict[str, Any]
    ) -> SkillUpdate:
        """Produce a SkillUpdate that improves an existing skill."""
        existing = self._skill_registry.get(skill_name)
        before_desc = existing.after if existing else None

        improvements = self._extract_speed_improvements(mission_data)
        new_approach = improvements[0] if improvements else f"Refined {skill_name}"

        update = SkillUpdate(
            skill_name=skill_name,
            description=f"Improved after mission {mission_data.get('mission_id', 'unknown')}",
            before=before_desc,
            after=new_approach,
            reason="Mission outcomes indicate room for improvement",
            confidence=0.6,
        )
        self._skill_registry[skill_name] = update
        return update

    async def update_knowledge_base(self, record: LearningRecord) -> None:
        """Persist a learning record in the in-memory knowledge base."""
        if not any(
            r.mission_id == record.mission_id for r in self._knowledge_base
        ):
            self._knowledge_base.append(record)

    async def get_recommendations(self, task: str) -> List[Dict[str, Any]]:
        """Return recommendations for a new task based on past learnings."""
        task_lower = task.lower()
        recommendations: List[Dict[str, Any]] = []

        for record in self._knowledge_base:
            for pattern in record.patterns_learned:
                if self._text_overlap(task_lower, pattern.lower()):
                    recommendations.append({
                        "type": "pattern",
                        "content": pattern,
                        "source_mission": record.mission_id,
                    })
            for lib in record.libraries_discovered:
                if self._text_overlap(task_lower, lib.lower()):
                    recommendations.append({
                        "type": "library",
                        "content": lib,
                        "source_mission": record.mission_id,
                    })
            for mistake in record.mistakes:
                if self._text_overlap(task_lower, mistake.lower()):
                    recommendations.append({
                        "type": "warning",
                        "content": mistake,
                        "source_mission": record.mission_id,
                    })

        recommendations.sort(key=lambda r: r.get("type", ""), reverse=True)
        return recommendations

    # ------------------------------------------------------------------
    # Internal extraction helpers
    # ------------------------------------------------------------------

    def _extract_libraries(self, mission_data: Dict[str, Any]) -> List[str]:
        return list(mission_data.get("libraries_used", []))

    def _extract_patterns_from_single(self, mission_data: Dict[str, Any]) -> List[str]:
        patterns: List[str] = []
        for action in mission_data.get("actions", []):
            action_type = action.get("type", "")
            tool = action.get("tool", "")
            if action_type and tool:
                patterns.append(f"{action_type}:{tool}")
        for step in mission_data.get("plan", []):
            if isinstance(step, str) and step:
                patterns.append(step)
        return list(dict.fromkeys(patterns))

    def _extract_mistakes(self, mission_data: Dict[str, Any]) -> List[str]:
        mistakes: List[str] = []
        for action in mission_data.get("actions", []):
            if action.get("failed") or action.get("error"):
                desc = action.get("error", action.get("description", "unknown error"))
                mistakes.append(str(desc))
        for retry in mission_data.get("retries", []):
            mistakes.append(str(retry.get("reason", "retry")))
        return mistakes

    def _extract_speed_improvements(self, mission_data: Dict[str, Any]) -> List[str]:
        improvements: List[str] = []
        for action in mission_data.get("actions", []):
            if action.get("optimization"):
                improvements.append(str(action["optimization"]))
        return improvements

    def _extract_skill_suggestions(self, mission_data: Dict[str, Any]) -> List[str]:
        suggestions: List[str] = []
        for action in mission_data.get("actions", []):
            if action.get("reusable"):
                skill_name = action.get("skill_name", "")
                if skill_name:
                    suggestions.append(skill_name)
        for s in mission_data.get("suggested_skills", []):
            suggestions.append(str(s))
        return list(dict.fromkeys(suggestions))

    def _extract_knowledge_updates(self, mission_data: Dict[str, Any]) -> List[str]:
        updates: List[str] = []
        for finding in mission_data.get("findings", []):
            updates.append(str(finding))
        return updates

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(data: Dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @staticmethod
    def _text_overlap(a: str, b: str) -> bool:
        """Simple token-overlap check between two strings."""
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return False
        overlap = tokens_a & tokens_b
        return len(overlap) / min(len(tokens_a), len(tokens_b)) >= 0.4
