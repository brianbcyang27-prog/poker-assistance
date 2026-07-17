"""Skill learning system - save and reuse successful task workflows."""
import asyncio
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

SKILLS_DIR = Path("memory_store")
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_FILE = SKILLS_DIR / "skills.json"


@dataclass
class Skill:
    name: str
    description: str
    steps: List[Dict[str, str]]
    success_count: int = 0
    failure_count: int = 0
    created_at: float = 0.0
    last_used: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["success_rate"] = self.success_rate
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        return cls(
            name=data["name"],
            description=data["description"],
            steps=data.get("steps", []),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            created_at=data.get("created_at", 0.0),
            last_used=data.get("last_used", 0.0),
        )

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class SkillManager:
    """Manages reusable skill definitions learned from experience."""

    def __init__(self, skills_path: Optional[Path] = None):
        self._path = skills_path or SKILLS_FILE
        self._skills: Dict[str, Skill] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                self._skills = {k: Skill.from_dict(v) for k, v in data.items()}
            except (json.JSONDecodeError, KeyError):
                self._skills = {}

    def _save(self):
        data = {k: v.to_dict() for k, v in self._skills.items()}
        self._path.write_text(json.dumps(data, indent=2))

    async def record_skill(
        self, name: str, description: str, steps: List[Dict[str, str]]
    ) -> dict:
        """Save a new skill from a completed task."""
        if name in self._skills:
            return {"ok": False, "error": f"Skill '{name}' already exists. Use update or delete first."}

        skill = Skill(
            name=name,
            description=description,
            steps=steps,
            created_at=time.time(),
            last_used=time.time(),
        )
        self._skills[name] = skill
        self._save()
        return {"ok": True, "skill": skill.to_dict()}

    async def find_similar(self, description: str) -> dict:
        """Find skills matching a description via keyword overlap."""
        keywords = set(re.findall(r'\w+', description.lower()))
        scored = []
        for skill in self._skills.values():
            skill_words = set(re.findall(r'\w+', skill.description.lower()))
            overlap = len(keywords & skill_words)
            if overlap > 0:
                scored.append((overlap, skill))
        scored.sort(key=lambda x: (-x[0], -x[1].success_rate))
        return {
            "ok": True,
            "query": description,
            "matches": [
                {"name": s.name, "description": s.description, "score": score,
                 "success_rate": s.success_rate}
                for score, s in scored
            ],
        }

    async def get_skill(self, name: str) -> dict:
        """Get a specific skill by name."""
        skill = self._skills.get(name)
        if not skill:
            return {"ok": False, "error": f"Skill '{name}' not found"}
        return {"ok": True, "skill": skill.to_dict()}

    async def update_outcome(self, name: str, success: bool) -> dict:
        """Record whether a skill usage succeeded or failed."""
        skill = self._skills.get(name)
        if not skill:
            return {"ok": False, "error": f"Skill '{name}' not found"}
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1
        skill.last_used = time.time()
        self._save()
        return {"ok": True, "skill": skill.to_dict()}

    async def get_all_skills(self) -> dict:
        """List all recorded skills."""
        return {
            "ok": True,
            "count": len(self._skills),
            "skills": [s.to_dict() for s in self._skills.values()],
        }

    async def get_top_skills(self, n: int = 5) -> dict:
        """Get the most successful skills ranked by success rate."""
        ranked = sorted(
            self._skills.values(),
            key=lambda s: (-s.success_rate, -s.success_count),
        )[:n]
        return {
            "ok": True,
            "skills": [s.to_dict() for s in ranked],
        }

    async def delete_skill(self, name: str) -> dict:
        """Remove a skill by name."""
        if name not in self._skills:
            return {"ok": False, "error": f"Skill '{name}' not found"}
        del self._skills[name]
        self._save()
        return {"ok": True}


skill_manager = SkillManager()
