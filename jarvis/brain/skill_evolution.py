"""Skill Evolution — Learn from outcomes, refine strategies, compose skills.

Extends the basic SkillManager with:
- Strategy variants (A/B test different approaches)
- Auto-pruning of low-performing skills
- Skill composition (chain skills together)
- Outcome-driven refinement
"""

import time
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from loguru import logger


SKILLS_DIR = Path("memory_store")
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
EVOLUTION_FILE = SKILLS_DIR / "skill_evolution.json"


@dataclass
class StrategyVariant:
    """An alternative strategy for a skill."""
    name: str
    steps: list[dict]
    success_count: int = 0
    failure_count: int = 0
    created_at: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    def to_dict(self) -> dict:
        d = asdict(self)
        d["success_rate"] = round(self.success_rate, 3)
        return d


@dataclass
class SkillEvolution:
    """Evolution state for a skill."""
    skill_name: str
    variants: list[StrategyVariant] = field(default_factory=list)
    current_variant: str = "default"
    generations: int = 0
    best_score: float = 0.0
    total_attempts: int = 0
    composed_from: list[str] = field(default_factory=list)  # parent skills

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "variants": [v.to_dict() for v in self.variants],
            "current_variant": self.current_variant,
            "generations": self.generations,
            "best_score": round(self.best_score, 3),
            "total_attempts": self.total_attempts,
            "composed_from": self.composed_from,
        }


class SkillEvolver:
    """Evolves skills through variant testing and outcome-driven refinement."""

    # Thresholds
    MIN_ATTEMPTS_TO_PRUNE = 5
    PRUNE_THRESHOLD = 0.2  # success rate below this → prune
    IMPROVEMENT_THRESHOLD = 0.1  # variant must beat current by this much

    def __init__(self):
        self._evolutions: dict[str, SkillEvolution] = {}
        self._load()

    def _load(self):
        if EVOLUTION_FILE.exists():
            try:
                data = json.loads(EVOLUTION_FILE.read_text())
                for name, evo_data in data.items():
                    evo = SkillEvolution(
                        skill_name=name,
                        generations=evo_data.get("generations", 0),
                        best_score=evo_data.get("best_score", 0),
                        total_attempts=evo_data.get("total_attempts", 0),
                        composed_from=evo_data.get("composed_from", []),
                        current_variant=evo_data.get("current_variant", "default"),
                    )
                    for v in evo_data.get("variants", []):
                        evo.variants.append(StrategyVariant(
                            name=v["name"],
                            steps=v.get("steps", []),
                            success_count=v.get("success_count", 0),
                            failure_count=v.get("failure_count", 0),
                            created_at=v.get("created_at", 0),
                        ))
                    self._evolutions[name] = evo
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        data = {name: evo.to_dict() for name, evo in self._evolutions.items()}
        EVOLUTION_FILE.write_text(json.dumps(data, indent=2))

    async def record_outcome(self, skill_name: str, variant_name: str, success: bool):
        """Record an outcome for a specific variant."""
        evo = self._evolutions.get(skill_name)
        if not evo:
            evo = SkillEvolution(skill_name=skill_name)
            self._evolutions[skill_name] = evo

        evo.total_attempts += 1

        # Find or create variant
        variant = None
        for v in evo.variants:
            if v.name == variant_name:
                variant = v
                break
        if variant is None:
            variant = StrategyVariant(
                name=variant_name,
                steps=[],
                created_at=time.time(),
            )
            evo.variants.append(variant)

        if success:
            variant.success_count += 1
        else:
            variant.failure_count += 1

        # Update best score
        if evo.total_attempts > 0:
            evo.best_score = max(v.success_rate for v in evo.variants) if evo.variants else 0

        self._save()

    async def add_variant(self, skill_name: str, variant_name: str, steps: list[dict]) -> dict:
        """Add a new strategy variant for A/B testing."""
        evo = self._evolutions.get(skill_name)
        if not evo:
            evo = SkillEvolution(skill_name=skill_name)
            self._evolutions[skill_name] = evo

        # Check if variant already exists
        for v in evo.variants:
            if v.name == variant_name:
                return {"ok": False, "error": f"Variant '{variant_name}' already exists"}

        variant = StrategyVariant(
            name=variant_name,
            steps=steps,
            created_at=time.time(),
        )
        evo.variants.append(variant)
        self._save()
        return {"ok": True, "variant": variant.to_dict()}

    async def select_best_variant(self, skill_name: str) -> Optional[StrategyVariant]:
        """Select the best-performing variant."""
        evo = self._evolutions.get(skill_name)
        if not evo or not evo.variants:
            return None

        # Thompson sampling: balance exploration vs exploitation
        import random
        sampled = []
        for v in evo.variants:
            # Beta distribution approximation
            alpha = v.success_count + 1
            beta = v.failure_count + 1
            # Simple approximation: mean + noise
            mean = alpha / (alpha + beta)
            noise = random.gauss(0, 0.1)
            sampled.append((mean + noise, v))

        sampled.sort(key=lambda x: x[0], reverse=True)
        best = sampled[0][1]
        evo.current_variant = best.name
        self._save()
        return best

    async def prune_low_performers(self) -> dict:
        """Remove variants that consistently fail."""
        pruned = []
        for skill_name, evo in list(self._evolutions.items()):
            if evo.total_attempts < self.MIN_ATTEMPTS_TO_PRUNE:
                continue
            if evo.best_score < self.PRUNE_THRESHOLD:
                # Remove the worst variants
                evo.variants = [
                    v for v in evo.variants
                    if v.success_count + v.failure_count < self.MIN_ATTEMPTS_TO_PRUNE
                    or v.success_rate >= self.PRUNE_THRESHOLD
                ]
                pruned.append(skill_name)

        if pruned:
            self._save()
        return {"pruned": pruned, "count": len(pruned)}

    async def compose_skills(self, skill_names: list[str], composed_name: str) -> dict:
        """Compose multiple skills into a new skill."""
        all_steps = []
        composed_from = []

        for name in skill_names:
            evo = self._evolutions.get(name)
            if evo and evo.variants:
                best = max(evo.variants, key=lambda v: v.success_rate)
                all_steps.extend(best.steps)
                composed_from.append(name)

        if not all_steps:
            return {"ok": False, "error": "No steps found from source skills"}

        composed_evo = SkillEvolution(
            skill_name=composed_name,
            composed_from=composed_from,
        )
        composed_evo.variants.append(StrategyVariant(
            name="default",
            steps=all_steps,
            created_at=time.time(),
        ))

        self._evolutions[composed_name] = composed_evo
        self._save()
        return {"ok": True, "composed": composed_evo.to_dict()}

    async def get_evolution(self, skill_name: str) -> Optional[dict]:
        evo = self._evolutions.get(skill_name)
        return evo.to_dict() if evo else None

    async def get_all_evolutions(self) -> list[dict]:
        return [evo.to_dict() for evo in self._evolutions.values()]

    async def get_stats(self) -> dict:
        total_skills = len(self._evolutions)
        total_variants = sum(len(e.variants) for e in self._evolutions.values())
        avg_score = (
            sum(e.best_score for e in self._evolutions.values()) / total_skills
            if total_skills > 0 else 0
        )
        return {
            "total_skills": total_skills,
            "total_variants": total_variants,
            "avg_best_score": round(avg_score, 3),
            "total_attempts": sum(e.total_attempts for e in self._evolutions.values()),
        }


# Module-level singleton
skill_evolver = SkillEvolver()
