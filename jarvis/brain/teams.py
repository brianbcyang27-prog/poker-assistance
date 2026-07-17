"""Dynamic Teams + Mission Timeline — Agent team formation and mission tracking.

Dynamic Teams: On-the-fly agent team formation based on task requirements.
Mission Timeline: Visual timeline of mission progress with milestones.
"""

import time
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class TeamMember:
    """A member of a dynamic team."""
    agent_id: str
    role: str  # lead, executor, reviewer, observer
    capabilities: list[str] = field(default_factory=list)
    workload: float = 0.0  # 0-1 current load
    joined_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "capabilities": self.capabilities,
            "workload": round(self.workload, 2),
            "joined_at": self.joined_at,
        }


@dataclass
class DynamicTeam:
    """A dynamically formed team for a specific mission."""
    id: str
    name: str
    mission_id: str
    members: list[TeamMember] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    disband_at: float = 0  # auto-disband time
    status: str = "active"  # active | disbanded

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mission_id": self.mission_id,
            "members": [m.to_dict() for m in self.members],
            "created_at": self.created_at,
            "status": self.status,
            "member_count": len(self.members),
        }


class DynamicTeamManager:
    """Forms and manages dynamic agent teams."""

    def __init__(self):
        self._teams: dict[str, DynamicTeam] = {}
        self._agent_capabilities: dict[str, list[str]] = {}

    def register_agent_capabilities(self, agent_id: str, capabilities: list[str]):
        """Register what an agent can do."""
        self._agent_capabilities[agent_id] = capabilities

    async def form_team(
        self,
        team_name: str,
        mission_id: str,
        required_capabilities: list[str],
        max_members: int = 5,
    ) -> DynamicTeam:
        """Form a team based on required capabilities."""
        team_id = f"team_{int(time.time())}_{team_name.lower().replace(' ', '_')[:20]}"

        # Score agents by capability match
        scored = []
        for agent_id, caps in self._agent_capabilities.items():
            overlap = len(set(caps) & set(required_capabilities))
            if overlap > 0:
                scored.append((overlap, agent_id, caps))

        scored.sort(key=lambda x: -x[0])
        members = []
        for _, agent_id, caps in scored[:max_members]:
            members.append(TeamMember(
                agent_id=agent_id,
                role="executor" if len(members) > 0 else "lead",
                capabilities=caps,
            ))

        team = DynamicTeam(
            id=team_id,
            name=team_name,
            mission_id=mission_id,
            members=members,
        )
        self._teams[team_id] = team
        logger.info(f"Team formed: {team_name} with {len(members)} members for {mission_id}")
        return team

    async def add_member(self, team_id: str, member: TeamMember) -> bool:
        team = self._teams.get(team_id)
        if not team or team.status != "active":
            return False
        team.members.append(member)
        return True

    async def remove_member(self, team_id: str, agent_id: str) -> bool:
        team = self._teams.get(team_id)
        if not team:
            return False
        team.members = [m for m in team.members if m.agent_id != agent_id]
        return True

    async def disband_team(self, team_id: str) -> bool:
        team = self._teams.get(team_id)
        if team:
            team.status = "disbanded"
            return True
        return False

    async def get_team(self, team_id: str) -> Optional[DynamicTeam]:
        return self._teams.get(team_id)

    async def get_teams_for_mission(self, mission_id: str) -> list[DynamicTeam]:
        return [t for t in self._teams.values() if t.mission_id == mission_id]

    def get_stats(self) -> dict:
        active = sum(1 for t in self._teams.values() if t.status == "active")
        total_members = sum(len(t.members) for t in self._teams.values())
        return {
            "total_teams": len(self._teams),
            "active_teams": active,
            "total_members": total_members,
            "registered_agents": len(self._agent_capabilities),
        }


# ===== Mission Timeline =====

@dataclass
class TimelineEvent:
    """An event on the mission timeline."""
    timestamp: float
    event_type: str  # started, milestone, completed, failed, delegated, reviewed
    node_id: str
    node_name: str
    description: str = ""
    agent_id: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "description": self.description,
            "agent_id": self.agent_id,
        }


class MissionTimeline:
    """Tracks and visualizes mission progress as a timeline."""

    def __init__(self):
        self._events: dict[str, list[TimelineEvent]] = {}  # mission_id -> events

    def record_event(
        self,
        mission_id: str,
        event_type: str,
        node_id: str,
        node_name: str,
        description: str = "",
        agent_id: str = "",
        metadata: dict = None,
    ):
        """Record a timeline event."""
        if mission_id not in self._events:
            self._events[mission_id] = []

        event = TimelineEvent(
            timestamp=time.time(),
            event_type=event_type,
            node_id=node_id,
            node_name=node_name,
            description=description,
            agent_id=agent_id,
            metadata=metadata or {},
        )
        self._events[mission_id].append(event)

    def get_timeline(self, mission_id: str, limit: int = 100) -> list[dict]:
        """Get timeline events for a mission."""
        events = self._events.get(mission_id, [])
        return [e.to_dict() for e in events[-limit:]]

    def get_duration(self, mission_id: str) -> float:
        """Get total mission duration in seconds."""
        events = self._events.get(mission_id, [])
        if len(events) < 2:
            return 0
        return events[-1].timestamp - events[0].timestamp

    def get_milestones(self, mission_id: str) -> list[dict]:
        """Get milestone events."""
        events = self._events.get(mission_id, [])
        milestones = [e for e in events if e.event_type in ("milestone", "completed", "failed")]
        return [e.to_dict() for e in milestones]

    def get_agent_activity(self, mission_id: str) -> dict:
        """Get activity per agent."""
        events = self._events.get(mission_id, [])
        activity = {}
        for e in events:
            if e.agent_id:
                if e.agent_id not in activity:
                    activity[e.agent_id] = {"events": 0, "tasks_completed": 0}
                activity[e.agent_id]["events"] += 1
                if e.event_type == "completed":
                    activity[e.agent_id]["tasks_completed"] += 1
        return activity

    def visualize(self, mission_id: str) -> dict:
        """Get timeline data for visualization."""
        events = self._events.get(mission_id, [])
        if not events:
            return {"events": [], "duration": 0}

        start = events[0].timestamp
        vis_events = []
        for e in events:
            vis_events.append({
                **e.to_dict(),
                "offset_ms": (e.timestamp - start) * 1000,
            })

        return {
            "events": vis_events,
            "duration": self.get_duration(mission_id),
            "milestones": self.get_milestones(mission_id),
        }


# Module-level singletons
team_manager = DynamicTeamManager()
mission_timeline = MissionTimeline()
