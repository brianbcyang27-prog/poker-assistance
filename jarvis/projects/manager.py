"""ProjectManager — async persistence layer for first-class projects (v9.0.0 M2)."""

import json
import logging
import re
from datetime import datetime

from ..core.database import get_db
from ..domains.models import domain_by_alias
from .models import Artifact, KnowledgeNode, Project, ProjectDecision, ProjectMission

logger = logging.getLogger(__name__)

_PROJECT_SAFE_FIELDS = {"name", "description", "domain", "status", "progress", "last_worked_on"}
_MISSION_SAFE_FIELDS = {
    "title",
    "goal",
    "complexity",
    "domain",
    "status",
    "workspace_id",
    "started_at",
    "completed_at",
}


class ProjectManager:
    """CRUD + aggregates for projects, missions, artifacts, decisions, knowledge."""

    # ── projects ──────────────────────────────────────────────────────────

    async def create_project(
        self, name: str, description: str = "", domain: str = "engineering"
    ) -> Project:
        db = await get_db()
        existing = await self.get_project(name)
        if existing is not None:
            return existing
        now = datetime.now().isoformat()
        await db._db.execute(
            """INSERT INTO projects
               (name, path, description, language, domain, status, progress,
                created_at, updated_at)
               VALUES (?, '', ?, 'unknown', ?, 'active', 0.0, ?, ?)""",
            (name, description, domain, now, now),
        )
        await db._db.commit()
        cursor = await db._db.execute("SELECT last_insert_rowid() AS rid")
        row = await cursor.fetchone()
        project_id = str(row["rid"])
        return await self.get_project(project_id)

    async def get_project(self, project_id: str) -> Project | None:
        db = await get_db()
        cursor = await db._db.execute(
            "SELECT * FROM projects WHERE id = ? OR name = ?", (project_id, project_id)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_project(dict(row))

    async def list_projects(self, status: str | None = None, limit: int = 100) -> list[Project]:
        db = await get_db()
        if status:
            cursor = await db._db.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = await db._db.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?", (limit,)
            )
        rows = await cursor.fetchall()
        return [self._row_to_project(dict(row)) for row in rows]

    async def update_project(self, project_id: str, **fields) -> Project | None:
        db = await get_db()
        updates = {k: v for k, v in fields.items() if k in _PROJECT_SAFE_FIELDS}
        if not updates:
            return await self.get_project(project_id)
        updates["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = ?" for k in updates)
        await db._db.execute(
            f"UPDATE projects SET {sets} WHERE id = ?", (*updates.values(), project_id)
        )
        await db._db.commit()
        return await self.get_project(project_id)

    async def touch(self, project_id: str) -> None:
        db = await get_db()
        await db._db.execute(
            "UPDATE projects SET last_worked_on = ?, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), datetime.now().isoformat(), project_id),
        )
        await db._db.commit()

    async def resolve_project_for_request(self, request: str) -> str | None:
        """Return an existing project id whose name appears in the request."""
        projects = await self.list_projects(limit=100)
        lowered = request.lower()
        for project in projects:
            if project.name.lower() in lowered:
                return project.id
        return None

    # ── missions ──────────────────────────────────────────────────────────

    async def add_mission(
        self,
        project_id: str,
        title: str,
        goal: str,
        complexity: str = "small",
        domain: str = "engineering",
    ) -> ProjectMission:
        db = await get_db()
        mission = ProjectMission(
            project_id=project_id,
            title=title,
            goal=goal,
            complexity=complexity,
            domain=domain,
        )
        await db._db.execute(
            """INSERT INTO project_missions
               (id, project_id, title, goal, complexity, domain, status,
                created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)""",
            (
                mission.id,
                project_id,
                title,
                goal,
                complexity,
                domain,
                mission.created_at.isoformat(),
            ),
        )
        await db._db.commit()
        return mission

    async def get_mission(self, mission_id: str) -> ProjectMission | None:
        db = await get_db()
        cursor = await db._db.execute(
            "SELECT * FROM project_missions WHERE id = ?", (mission_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return ProjectMission.model_validate(dict(row))

    async def list_missions(
        self, project_id: str | None = None, status: str | None = None
    ) -> list[ProjectMission]:
        db = await get_db()
        sql = "SELECT * FROM project_missions"
        clauses = []
        params: list = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC"
        cursor = await db._db.execute(sql, params)
        rows = await cursor.fetchall()
        return [ProjectMission.model_validate(dict(row)) for row in rows]

    async def update_mission(self, mission_id: str, **fields) -> ProjectMission | None:
        db = await get_db()
        updates = {k: v for k, v in fields.items() if k in _MISSION_SAFE_FIELDS}
        if not updates:
            return await self.get_mission(mission_id)
        sets = ", ".join(f"{k} = ?" for k in updates)
        await db._db.execute(
            f"UPDATE project_missions SET {sets} WHERE id = ?", (*updates.values(), mission_id)
        )
        await db._db.commit()
        return await self.get_mission(mission_id)

    async def link_workspace(self, project_id: str, workspace_id: str) -> None:
        """Attach an execution workspace to the project and bump its activity."""
        await self.update_project(project_id, last_worked_on=datetime.now().isoformat())
        missions = await self.list_missions(project_id=project_id)
        for mission in missions:
            if mission.workspace_id is None:
                await self.update_mission(mission.id, workspace_id=workspace_id)
                break

    # ── artifacts ─────────────────────────────────────────────────────────

    async def add_artifact(
        self,
        project_id: str,
        name: str,
        artifact_type: str = "note",
        content: str = "",
        metadata: dict | None = None,
    ) -> Artifact:
        db = await get_db()
        artifact = Artifact(
            project_id=project_id,
            name=name,
            artifact_type=artifact_type,
            content=content,
            metadata=metadata or {},
        )
        await db._db.execute(
            """INSERT INTO project_artifacts
               (id, project_id, name, artifact_type, content, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                artifact.id,
                project_id,
                name,
                artifact_type,
                content,
                json.dumps(artifact.metadata),
                artifact.created_at.isoformat(),
            ),
        )
        await db._db.commit()
        return artifact

    async def list_artifacts(self, project_id: str, limit: int = 100) -> list[Artifact]:
        db = await get_db()
        cursor = await db._db.execute(
            "SELECT * FROM project_artifacts WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_artifact(dict(row)) for row in rows]

    # ── decisions ─────────────────────────────────────────────────────────

    async def add_decision(
        self,
        project_id: str,
        topic: str,
        decision: str,
        reason: str = "",
        context: str = "",
    ) -> ProjectDecision:
        db = await get_db()
        decision_row = ProjectDecision(
            project_id=project_id, topic=topic, decision=decision, reason=reason, context=context
        )
        await db._db.execute(
            """INSERT INTO project_decisions
               (id, project_id, topic, decision, reason, context, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                decision_row.id,
                project_id,
                topic,
                decision,
                reason,
                context,
                decision_row.created_at.isoformat(),
            ),
        )
        await db._db.commit()
        return decision_row

    async def list_decisions(self, project_id: str, limit: int = 100) -> list[ProjectDecision]:
        db = await get_db()
        cursor = await db._db.execute(
            "SELECT * FROM project_decisions WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        )
        rows = await cursor.fetchall()
        return [ProjectDecision.model_validate(dict(row)) for row in rows]

    # ── knowledge graph ───────────────────────────────────────────────────

    async def add_knowledge(
        self,
        project_id: str,
        label: str,
        node_type: str = "concept",
        content: str = "",
        metadata: dict | None = None,
        links: list[str] | None = None,
    ) -> KnowledgeNode:
        db = await get_db()
        node = KnowledgeNode(
            project_id=project_id,
            label=label,
            node_type=node_type,
            content=content,
            metadata=metadata or {},
            links=links or [],
        )
        await db._db.execute(
            """INSERT INTO project_knowledge
               (id, project_id, label, node_type, content, metadata, links_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.id,
                project_id,
                label,
                node_type,
                content,
                json.dumps(node.metadata),
                json.dumps(node.links),
                node.created_at.isoformat(),
            ),
        )
        await db._db.commit()
        return node

    async def list_knowledge(self, project_id: str) -> list[KnowledgeNode]:
        db = await get_db()
        cursor = await db._db.execute(
            "SELECT * FROM project_knowledge WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_knowledge(dict(row)) for row in rows]

    # ── aggregates ────────────────────────────────────────────────────────

    async def dashboard(self, project_id: str) -> dict:
        """Aggregate project data for the dashboard view."""
        project = await self.get_project(project_id)
        if project is None:
            return {}
        missions = await self.list_missions(project_id=project_id)
        artifacts = await self.list_artifacts(project_id=project_id)
        decisions = await self.list_decisions(project_id=project_id)
        knowledge = await self.list_knowledge(project_id=project_id)

        mission_statuses = {"planned": 0, "active": 0, "completed": 0, "failed": 0}
        for mission in missions:
            mission_statuses[mission.status] = mission_statuses.get(mission.status, 0) + 1

        completed = mission_statuses["completed"]
        progress = (completed / len(missions) * 100) if missions else project.progress

        current_mission = None
        for mission in missions:
            if mission.status in ("planned", "active"):
                current_mission = mission
                break
        if current_mission is None and missions:
            current_mission = missions[0]

        confidence = self._dashboard_confidence(artifacts)
        recent_activity = self._recent_activity(missions, artifacts, decisions)

        domain = domain_by_alias(project.domain)
        return {
            "project": project.model_dump(mode="json"),
            "domain_label": domain.label if domain else project.domain,
            "missions": [m.model_dump(mode="json") for m in missions],
            "artifacts": [a.model_dump(mode="json") for a in artifacts],
            "decisions": [d.model_dump(mode="json") for d in decisions],
            "knowledge": [k.model_dump(mode="json") for k in knowledge],
            "mission_statuses": mission_statuses,
            "progress": round(progress, 1),
            "current_mission": current_mission.model_dump(mode="json") if current_mission else None,
            "confidence": confidence,
            "recent_activity": recent_activity,
        }

    @staticmethod
    def _dashboard_confidence(artifacts) -> float | None:
        """Confidence from the newest mission report artifact, if present."""
        reports = [a for a in artifacts if a.artifact_type == "report"]
        if not reports:
            return None
        newest = reports[-1]
        match = re.search(r"\*\*Confidence\*\*:\s*([0-9.]+)", newest.content or "")
        if not match:
            return None
        try:
            return round(float(match.group(1)), 2)
        except ValueError:  # pragma: no cover - defensive against malformed artifacts
            return None

    @staticmethod
    def _recent_activity(missions, artifacts, decisions) -> list[dict]:
        """Newest activity feed merging missions, artifacts, and decisions."""
        entries = []
        for mission in missions:
            when = mission.completed_at or mission.started_at or mission.created_at
            if when is not None:
                entries.append(
                    {"kind": "mission", "label": mission.title, "status": mission.status, "when": when}
                )
        for artifact in artifacts:
            entries.append(
                {"kind": "artifact", "label": artifact.name, "status": artifact.artifact_type, "when": artifact.created_at}
            )
        for decision in decisions:
            entries.append(
                {"kind": "decision", "label": decision.topic, "status": "", "when": decision.created_at}
            )
        entries.sort(key=lambda e: e["when"], reverse=True)
        return entries[:8]

    async def timeline(self, project_id: str) -> dict:
        """Merge missions into {nodes, edges} for the DAG view."""
        missions = await self.list_missions(project_id=project_id)
        nodes = []
        edges = []
        prev_id = None
        for mission in missions:
            nodes.append(
                {
                    "id": mission.id,
                    "label": mission.title,
                    "status": mission.status,
                    "complexity": mission.complexity,
                    "domain": mission.domain,
                    "type": "mission",
                }
            )
            if prev_id is not None:
                edges.append({"source": prev_id, "target": mission.id})
            prev_id = mission.id
        return {"nodes": nodes, "edges": edges, "project_id": project_id}

    # ── row → model helpers ───────────────────────────────────────────────

    def _row_to_project(self, row: dict) -> Project:
        row = dict(row)
        row.setdefault("description", "")
        row.setdefault("domain", "engineering")
        row.setdefault("status", "active")
        row.setdefault("progress", 0.0)
        row.setdefault("workspace_ids", [])
        row.setdefault("mission_ids", [])
        workspace_ids = row.get("workspace_ids") or []
        mission_ids = row.get("mission_ids") or []
        if isinstance(workspace_ids, str):
            workspace_ids = json.loads(workspace_ids) if workspace_ids else []
        if isinstance(mission_ids, str):
            mission_ids = json.loads(mission_ids) if mission_ids else []
        return Project(
            id=str(row["id"]),
            name=row["name"],
            description=row.get("description", ""),
            domain=row.get("domain", "engineering"),
            status=row.get("status", "active"),
            progress=float(row.get("progress") or 0.0),
            created_at=row.get("created_at") or datetime.now(),
            updated_at=row.get("updated_at") or datetime.now(),
            last_worked_on=row.get("last_worked_on"),
            workspace_ids=workspace_ids,
            mission_ids=mission_ids,
        )

    def _row_to_artifact(self, row: dict) -> Artifact:
        row = dict(row)
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        row["metadata"] = metadata or {}
        return Artifact.model_validate(row)

    def _row_to_knowledge(self, row: dict) -> KnowledgeNode:
        row = dict(row)
        links = row.pop("links_json", "[]")
        if isinstance(links, str):
            links = json.loads(links) if links else []
        row["links"] = links or []
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        row["metadata"] = metadata or {}
        return KnowledgeNode.model_validate(row)


project_manager = ProjectManager()
