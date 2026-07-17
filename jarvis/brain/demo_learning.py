"""Demo Learning — Learn from user demonstrations and replay actions.

From OpenAdapt/OSWorld pattern: record user action sequences,
abstract them into reusable workflows, and replay with variations.
"""

import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


DEMO_DIR = Path("memory_store")
DEMO_DIR.mkdir(parents=True, exist_ok=True)
DEMOS_FILE = DEMO_DIR / "demos.json"


@dataclass
class Action:
    """A single recorded action."""
    action_type: str  # click, type, navigate, scroll, keypress, wait
    target: str = ""  # element/URL/command
    value: str = ""  # text to type, key, etc.
    coordinates: tuple[float, float] = (0, 0)
    timestamp: float = 0.0
    duration_ms: float = 0.0
    context: dict = field(default_factory=dict)  # extra info (screenshot hash, etc.)

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "value": self.value,
            "coordinates": list(self.coordinates),
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Action":
        coords = d.get("coordinates", [0, 0])
        return cls(
            action_type=d["action_type"],
            target=d.get("target", ""),
            value=d.get("value", ""),
            coordinates=(coords[0], coords[1]) if len(coords) >= 2 else (0, 0),
            timestamp=d.get("timestamp", 0),
            duration_ms=d.get("duration_ms", 0),
            context=d.get("context", {}),
        )


@dataclass
class Demo:
    """A recorded demonstration (sequence of actions)."""
    id: str
    name: str
    description: str
    actions: list[Action] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: float = 0.0
    last_replayed: float = 0.0
    replay_count: int = 0
    success_count: int = 0
    source: str = "user"  # user | generated | hybrid

    @property
    def success_rate(self) -> float:
        return self.success_count / self.replay_count if self.replay_count > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
            "tags": self.tags,
            "created_at": self.created_at,
            "last_replayed": self.last_replayed,
            "replay_count": self.replay_count,
            "success_count": self.success_count,
            "success_rate": round(self.success_rate, 3),
            "source": self.source,
            "action_count": len(self.actions),
        }


class DemoLearner:
    """Records, abstracts, and replays user demonstrations."""

    def __init__(self):
        self._demos: dict[str, Demo] = {}
        self._recording: Optional[str] = None  # currently recording demo id
        self._current_actions: list[Action] = []
        self._load()

    def _load(self):
        if DEMOS_FILE.exists():
            try:
                data = json.loads(DEMOS_FILE.read_text())
                for demo_data in data:
                    demo = Demo(
                        id=demo_data["id"],
                        name=demo_data["name"],
                        description=demo_data.get("description", ""),
                        tags=demo_data.get("tags", []),
                        created_at=demo_data.get("created_at", 0),
                        last_replayed=demo_data.get("last_replayed", 0),
                        replay_count=demo_data.get("replay_count", 0),
                        success_count=demo_data.get("success_count", 0),
                        source=demo_data.get("source", "user"),
                    )
                    demo.actions = [Action.from_dict(a) for a in demo_data.get("actions", [])]
                    self._demos[demo.id] = demo
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        data = [d.to_dict() for d in self._demos.values()]
        DEMOS_FILE.write_text(json.dumps(data, indent=2))

    async def start_recording(self, name: str, description: str = "", tags: list[str] = None) -> str:
        """Start recording a new demo."""
        demo_id = f"demo_{int(time.time())}_{name.lower().replace(' ', '_')[:30]}"
        self._recording = demo_id
        self._current_actions = []
        self._demos[demo_id] = Demo(
            id=demo_id,
            name=name,
            description=description,
            tags=tags or [],
            created_at=time.time(),
        )
        logger.info(f"Demo recording started: {name}")
        return demo_id

    async def record_action(self, action: Action):
        """Record an action during a demo."""
        if not self._recording:
            return
        action.timestamp = time.time()
        self._current_actions.append(action)

    async def stop_recording(self) -> Optional[Demo]:
        """Stop recording and save the demo."""
        if not self._recording:
            return None

        demo = self._demos.get(self._recording)
        if demo:
            demo.actions = self._current_actions
            self._save()
            logger.info(f"Demo recorded: {demo.name} ({len(demo.actions)} actions)")

        self._recording = None
        self._current_actions = []
        return demo

    async def get_demo(self, demo_id: str) -> Optional[Demo]:
        return self._demos.get(demo_id)

    async def list_demos(self, tag: Optional[str] = None) -> list[Demo]:
        demos = list(self._demos.values())
        if tag:
            demos = [d for d in demos if tag in d.tags]
        return sorted(demos, key=lambda d: d.created_at, reverse=True)

    async def abstract_actions(self, demo_id: str) -> dict:
        """Abstract specific actions into reusable patterns."""
        demo = self._demos.get(demo_id)
        if not demo:
            return {"error": "Demo not found"}

        patterns = []
        for action in demo.actions:
            pattern = {
                "type": action.action_type,
                "parametrized_target": self._parametrize(action.target),
                "parametrized_value": self._parametrize(action.value),
            }
            patterns.append(pattern)

        return {
            "demo_id": demo_id,
            "patterns": patterns,
            "action_count": len(patterns),
        }

    def _parametrize(self, value: str) -> str:
        """Replace specific values with parameters."""
        import re
        # Replace URLs with {{URL}}
        value = re.sub(r'https?://[^\s]+', '{{URL}}', value)
        # Replace file paths with {{PATH}}
        value = re.sub(r'/[\w/\\.-]+', '{{PATH}}', value)
        # Replace timestamps with {{TIME}}
        value = re.sub(r'\d{4}-\d{2}-\d{2}', '{{DATE}}', value)
        # Replace numbers with {{NUM}}
        value = re.sub(r'\b\d{3,}\b', '{{NUM}}', value)
        return value

    async def replay(self, demo_id: str, variations: dict = None) -> dict:
        """Replay a demo with optional variations."""
        demo = self._demos.get(demo_id)
        if not demo:
            return {"error": "Demo not found"}

        demo.replay_count += 1
        demo.last_replayed = time.time()

        replay_plan = []
        for action in demo.actions:
            plan = action.to_dict()
            # Apply variations
            if variations:
                if action.target in variations:
                    plan["target"] = variations[action.target]
                if action.value in variations:
                    plan["value"] = variations[action.target]
            replay_plan.append(plan)

        self._save()
        return {
            "demo_id": demo_id,
            "plan": replay_plan,
            "action_count": len(replay_plan),
            "replay_count": demo.replay_count,
        }

    async def record_replay_outcome(self, demo_id: str, success: bool):
        """Record whether a replay was successful."""
        demo = self._demos.get(demo_id)
        if demo and success:
            demo.success_count += 1
            self._save()

    async def find_similar(self, description: str) -> list[Demo]:
        """Find demos similar to a description."""
        import re
        keywords = set(re.findall(r'\w{3,}', description.lower()))
        scored = []
        for demo in self._demos.values():
            demo_words = set(re.findall(r'\w{3,}', (demo.name + " " + demo.description).lower()))
            overlap = len(keywords & demo_words)
            if overlap > 0:
                scored.append((overlap, demo))
        scored.sort(key=lambda x: (-x[0], -x[1].success_rate))
        return [d for _, d in scored]

    async def delete_demo(self, demo_id: str) -> bool:
        if demo_id in self._demos:
            del self._demos[demo_id]
            self._save()
            return True
        return False

    def get_stats(self) -> dict:
        total = len(self._demos)
        total_actions = sum(len(d.actions) for d in self._demos.values())
        avg_success = (
            sum(d.success_rate for d in self._demos.values()) / total
            if total > 0 else 0
        )
        return {
            "total_demos": total,
            "total_actions": total_actions,
            "avg_success_rate": round(avg_success, 3),
            "recording": self._recording is not None,
            "sources": {
                "user": sum(1 for d in self._demos.values() if d.source == "user"),
                "generated": sum(1 for d in self._demos.values() if d.source == "generated"),
                "hybrid": sum(1 for d in self._demos.values() if d.source == "hybrid"),
            },
        }


# Module-level singleton
demo_learner = DemoLearner()
