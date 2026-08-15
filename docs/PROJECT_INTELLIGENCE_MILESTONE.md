# Project Intelligence Milestone — Architecture Summary & Implementation Contract

> JARVIS v9.0.0 · built on the Domain foundation (M1) and the JARVIS Design System
> Status: **done** — backend + frontend implemented and verified (22/22 tests, ruff clean, Playwright 0 console errors)

---

## 1. Vision (from JARVIS_VISION_RESET.md)

Projects are the first-class living entities of JARVIS. A project **owns** its
conversations, missions, artifacts, memories, research, files, reports, decisions,
execution state, and domain. The task flow becomes:

```
user message
  → intent classification (existing InteractionLayer)
  → complexity estimation (NEW)
  → project resolution / "create project?" (NEW)
  → domain selection (NEW, via domain_by_alias)
  → domain master plans & delegates (existing DomainMaster)
  → workers execute with peer context (existing DomainWorker)
  → peer review + fact checker (existing review_pipeline + research domain)
  → JARVIS responds (existing response path)
```

## 2. Already Built (do NOT rebuild)

| Piece | Location |
|---|---|
| Domain enum / DomainInfo / aliases | `jarvis/domains/models.py` |
| DomainMaster / DomainWorker / DomainMember (plan→delegate→review) | `jarvis/domains/base.py` |
| DomainRegistry + king attachment | `jarvis/domains/registry.py` |
| Education / Studio / Finance standalone masters | `jarvis/domains/{education,studio,finance}.py` |
| `/api/domains` + `/api/domains/{id}` | `jarvis/web/routers/domains.py` |
| Mission DAG SVG visualizer | `jarvis/web/static/js/mission-dag.js` (`window.MissionDAG`, polls `/api/system/dag`) |
| Mission timeline + tool cards | `jarvis/web/static/js/mission-timeline.js` (`window.MissionTimeline`, `window.ToolCard`) |
| Intent classification | `jarvis/brain/interaction/*` (used in `chat.py`) |
| Review pipeline | `jarvis/brain/review.py` (used by DomainWorker.execute_task) |
| Workspace persistence (workspaces/tasks/task_history/lessons) | `jarvis/workspace/manager.py` + `core/database.py` |
| `projects` table + ProjectMemory (legacy scan registry) | `core/database.py:85-93,409-425` + `jarvis/brain/project_memory.py` |

## 3. NEW Backend Contract — ✅ done

- `jarvis/projects/` package: `models.py`, `complexity.py`, `manager.py`, `task_flow.py`, `__init__.py` (singleton `project_manager`).
- DB: 4 new tables (`project_missions`, `project_artifacts`, `project_decisions`, `project_knowledge`) + idempotent `domain`/`progress` upgrade columns on `projects`.
- Router: full `/api/projects` CRUD + dashboard/timeline/missions/artifacts/decisions/knowledge/link-workspace/estimate.
- Chat task-flow branch (POST `/api/chat` + `/stream`): complexity → project resolve/auto-create → domain select → mission → workspace link → SSE events (`project_resolved`, `domain_selected`, `mission_start`, `mission_step`) → artifact/decision recording.
- Tests: `tests/test_projects.py` — 22 passed. `ruff check` clean on all touched files.

### 3.1 `jarvis/projects/models.py` — Pydantic models

```python
class Project(BaseModel):
    id: str            # uuid8
    name: str
    description: str = ""
    domain: str = "engineering"     # primary Domain.value
    status: str = "active"          # active | paused | archived | completed
    progress: float = 0.0
    created_at: datetime
    updated_at: datetime
    last_worked_on: datetime | None
    workspace_ids: list[str] = []   # execution workspaces
    mission_ids: list[str] = []

class ProjectMission(BaseModel):
    id: str
    project_id: str
    title: str
    goal: str
    complexity: str                 # tiny | small | mission | project
    domain: str
    status: str = "planned"         # planned | active | completed | failed
    workspace_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

class Artifact(BaseModel):
    id: str
    project_id: str
    name: str
    artifact_type: str = "note"     # note | report | code | design | research | file
    content: str = ""
    metadata: dict = {}
    created_at: datetime

class ProjectDecision(BaseModel):
    id: str
    project_id: str
    topic: str
    decision: str
    reason: str = ""
    context: str = ""
    created_at: datetime

class KnowledgeNode(BaseModel):
    id: str
    project_id: str
    label: str
    node_type: str = "concept"      # concept | domain | artifact | decision | mission
    content: str = ""
    metadata: dict = {}
    links: list[str] = []           # linked node ids (edges)
    created_at: datetime
```

### 3.2 `jarvis/projects/complexity.py` — complexity estimation

```python
async def estimate_complexity(request: str) -> dict:
    """Heuristic + LLM-assisted estimate.
    Returns {level: 'tiny'|'small'|'mission'|'project', score: 0-100,
             reasons: [str], suggested_action: 'direct'|'mission'|'create_project'}"""
```

Rules: length/verbosity, imperative verbs, multiple goals (`and|then|also`), domain
keywords, file/artifact mentions. `tiny` → direct answer; `small` → single mission;
`mission` → mission under existing project or "create project?" prompt; `project` →
auto-create project + first mission.

### 3.3 `jarvis/projects/manager.py` — `ProjectManager` (async, `get_db()`-based)

Public API (module singleton `project_manager`):

```python
class ProjectManager:
    async def create_project(self, name, description="", domain="engineering") -> Project
    async def get_project(self, project_id) -> Project | None
    async def list_projects(self, status=None, limit=100) -> list[Project]
    async def update_project(self, project_id, **fields) -> Project | None
    async def touch(self, project_id) -> None                       # bump last_worked_on
    async def add_mission(self, project_id, title, goal, complexity, domain) -> ProjectMission
    async def get_mission(self, mission_id) -> ProjectMission | None
    async def list_missions(self, project_id=None, status=None) -> list[ProjectMission]
    async def update_mission(self, mission_id, **fields) -> ProjectMission | None
    async def link_workspace(self, project_id, workspace_id) -> None
    async def add_artifact(self, project_id, name, artifact_type="note", content="", metadata=None) -> Artifact
    async def list_artifacts(self, project_id, limit=100) -> list[Artifact]
    async def add_decision(self, project_id, topic, decision, reason="", context="") -> ProjectDecision
    async def list_decisions(self, project_id, limit=100) -> list[ProjectDecision]
    async def add_knowledge(self, project_id, label, node_type="concept", content="", metadata=None, links=None) -> KnowledgeNode
    async def list_knowledge(self, project_id) -> list[KnowledgeNode]
    async def dashboard(self, project_id) -> dict                   # aggregates for UI
    async def timeline(self, project_id) -> dict                    # merged mission+workspace events for DAG
    async def resolve_project_for_request(self, request) -> str | None   # name match or None
```

### 3.4 DB tables (`core/database.py`, `CREATE TABLE IF NOT EXISTS` pattern)

- `projects` — already exists (85-93 + upgraded 409-425); ensure `domain` column added idempotently.
- `project_missions` — id, project_id, title, goal, complexity, domain, status, workspace_id, created_at, started_at, completed_at
- `project_artifacts` — id, project_id, name, artifact_type, content, metadata, created_at
- `project_decisions` — id, project_id, topic, decision, reason, context, created_at
- `project_knowledge` — id, project_id, label, node_type, content, metadata, links_json, created_at
- Add CRUD methods on `Database` mirroring existing conventions (`save_project_mission`, etc.) OR route all through ProjectManager SQL — follow existing `save_*`/`get_*` naming.

### 3.5 `jarvis/web/routers/projects.py` — `/api/projects`

```
GET    /api/projects                          → {projects, total}
POST   /api/projects                          → create {name, description, domain}
GET    /api/projects/{id}                     → full project
PATCH  /api/projects/{id}                     → update fields
GET    /api/projects/{id}/dashboard           → aggregates (missions by status, artifacts, decisions, knowledge, progress)
GET    /api/projects/{id}/timeline            → {nodes, edges} for DAG view
GET    /api/projects/{id}/missions            → list
POST   /api/projects/{id}/missions            → create mission
POST   /api/projects/{id}/artifacts           → add artifact
GET    /api/projects/{id}/artifacts           → list
POST   /api/projects/{id}/decisions           → add decision
GET    /api/projects/{id}/decisions           → list
POST   /api/projects/{id}/knowledge           → add node
GET    /api/projects/{id}/knowledge           → list nodes (+edges)
POST   /api/projects/{id}/link-workspace      → {workspace_id}
```

Register in `create_app()`; init `project_manager` global in `main.py` lifespan.
**Do NOT touch the existing `run()` uvicorn fix** in `main.py` (uncommitted).

### 3.6 Task-flow routing in `web/routers/chat.py` (both `POST /api/chat` and `/stream`)

Insert AFTER intent classification (line ~79 POST / ~233 stream), BEFORE the
architecture fork. New branch activates only for `task`/`project` intents with
complexity >= `small`; `chat`/`question`/`command` keep the existing path untouched.

Flow (per request):
1. `complexity = await estimate_complexity(message)`
2. If `suggested_action == 'create_project'`: resolve existing project by name match, else auto-create `{name: <slug>, description: message[:120]}` and return its id.
3. Resolve project_id (existing or created); `touch(project_id)`.
4. Select domain via `domain_by_alias` from domain keywords in message; default `engineering`.
5. `add_mission(project_id, title=message[:60], goal=message, complexity=level, domain=...)`.
6. Create/link a workspace for execution; store workspace_id on mission.
7. Emit SSE events (stream only): `project_resolved`, `domain_selected`, `mission_start`.
8. Execute via `web_main.domain_registry.get(domain).execute_task(task)` (master plans → workers → review). Workers already run `review_pipeline` (fact-checking gate) internally.
9. Record result as artifact + decision; update mission status; emit `mission_step` events per member result.
10. Return/stream the assembled response.

Must NOT break the existing Hermes / native-JARVIS forks for non-task intents.
Fact-checker: reuse `review_pipeline` (already invoked in `DomainWorker.execute_task`);
the research-domain fact-check worker remains a follow-up in M2 — document this.

## 4. NEW Frontend Contract — ✅ done

- `base.html`: 3 nav buttons, 3 workspace containers, 3 right-context panels, `mission-views.css` link.
- `app.js` `switchWorkspace()`: lazy-load + init blocks for Projects/Execution/Knowledge (`window.*` singleton pattern — NOTE: bare class names shadow the singleton per global-lexical-binding semantics; always use `window.X`).
- `command-palette.js`: Navigate (Projects/Execution/Knowledge) + New Project.
- `mission-views.css` (new, additive): `.mv-*` classes, design tokens, domain accent chips, glass cards.
- `project-dashboard.js`, `execution-view.js`, `knowledge-graph.js` — all three views live and verified (Playwright, 0 console errors).
- Execution reuses `window.MissionDAG`/`window.MissionTimeline` (loaded at startup, v8.0.0 — lazy-load is conditional on `typeof` to avoid duplicate `class` declaration errors).
- Timeline adapter: backend emits `{nodes:[{id,label,status,...}], edges:[{source,target}]}`; adapted to MissionDAG's `{name,layer}` + `{from,to}` at the component boundary.

### 4.1 Workspaces (SPA shell — `base.html` + `app.js`)

New nav items + containers + sidebar contexts (design tokens, glass cards):

| Workspace | Nav label | Container id | Right-context id |
|---|---|---|---|
| Projects | Projects | `#projects-container` | `right-projects` |
| Execution | Execution | `#execution-container` | `right-execution` |
| Knowledge | Knowledge | `#knowledge-container` | `right-knowledge` |

- Extend `switchWorkspace()` (app.js:699-795) to handle the three new ids.
- Lazy-load via existing `_loadScript` mechanism: `project-dashboard.js`, `execution-view.js`, `knowledge-graph.js`.
- Command palette: add `Projects`, `Execution`, `Knowledge`, `New Project`.
- Golden core constraint: states stay `idle | listening | thinking | working | speaking` only (user requirement) — map `planning/delegating/reviewing` → `working`, `mission_active` → `working`.

### 4.2 `project-dashboard.js` → `window.ProjectDashboard`

- Project cards grid: name, domain chip (domain color), progress bar, mission/artifact/decision counts, status, last worked.
- "New Project" button + inline form (name, description, domain select).
- Project detail panel: tabs for Missions / Artifacts / Decisions / Knowledge, fed by `/api/projects/{id}/*`.
- Design-system compliant: 4px grid, `--space-*` tokens, glass cards, gold/cyan accents.

### 4.3 `execution-view.js` → `window.ExecutionView`

- Live execution console: mission status header, member activity stream (WS `worker.started/completed/error`, `king.*` events via living-interface-style listeners), mission timeline (reuse `window.MissionTimeline`), DAG (reuse `window.MissionDAG` fed by `/api/projects/{id}/timeline` or `/api/system/dag`).
- Golden core integration: drive `working`/`thinking` from execution events.

### 4.4 `knowledge-graph.js` → `window.KnowledgeGraph`

- SVG node-link graph from `/api/projects/{id}/knowledge` (nodes + edges).
- Nodes colored by `node_type`; click node → detail card (content + links).
- Fallback empty state.

### 4.5 CSS

- Reuse existing `tokens.css` variables; add a dedicated `jarvis/web/static/css/mission-views.css` for new views (linked from base.html). Do NOT rewrite `style.css` wholesale — append/additive only.

## 5. Implementation Rules (from PHASE0_PLAN.md)

1. **Incremental** — small commits, one logical unit each.
2. **Never broken builds** — `ruff check` clean; server must boot; existing tests for touched areas must pass.
3. **Never break APIs** — all existing endpoints/routes keep their shapes; new endpoints are additive.
4. Verify after each task: `lsp_diagnostics` → targeted tests → live check.

## 6. Test Strategy

- New tests: `tests/test_projects.py` (ProjectManager CRUD + complexity + domain task-flow + dashboard + timeline). The planned separate `tests/test_project_tasks.py` was folded into `test_projects.py` (22 tests, all passing). Follow existing pytest patterns (async, tmp sqlite DB).
- Run targeted: `pytest tests/test_projects.py -q -o addopts="" -p no:cacheprovider` plus any existing tests touching `core/database.py`, `chat.py`, `domains/`.
- **Never** run the full suite in one process (known anyio hang when `test_v650_reality` + `test_v900` combine — environmental flakiness, unrelated to this milestone).

## 7. Deliverables — ✅ all complete

1. This architecture summary (updated with `[x]` completion marks).
2. Files changed:
   - **New (backend):** `jarvis/projects/{__init__,models,complexity,manager,task_flow}.py`, `jarvis/web/routers/projects.py`, `tests/test_projects.py`
   - **Modified (backend):** `jarvis/web/main.py` (router include + `project_manager` global), `jarvis/web/routers/chat.py` (task-flow branch + SSE), `jarvis/core/database.py` (4 tables + `projects` upgrade columns)
   - **New (frontend):** `jarvis/web/static/js/{project-dashboard,execution-view,knowledge-graph}.js`, `jarvis/web/static/css/mission-views.css`
   - **Modified (frontend):** `jarvis/web/templates/base.html`, `jarvis/web/static/js/{app,command-palette}.js`
3. Screenshots (dark theme): [`docs/screenshot-projects.png`](screenshot-projects.png), [`docs/screenshot-execution.png`](screenshot-execution.png), [`docs/screenshot-knowledge.png`](screenshot-knowledge.png).
4. Tech-debt notes:
   - **Fact-checker M2 follow-up** — research-domain fact-check worker still pending; `review_pipeline` already gates worker output.
   - **ProjectMemory legacy merge** — `jarvis/brain/project_memory.py` (legacy scan registry) not yet merged into the new `ProjectManager`; card-id compatibility aliases still needed.
   - **List endpoint lacks artifact/decision counts** — dashboard cards conditionally hide counts when absent (avoid fake zeros).
   - **No DELETE /api/projects/{id}** — 405; acceptable per contract but cleanup of smoke-test rows requires manual DB work or a future route.
5. Next milestone recommendation: **M3 — Live Execution Integration**: wire real mission execution state into the Execution view (WS `worker.*`/`king.*` activity stream), drive the golden core from `mission_step` events, add WS-pushed mission/project updates, and merge legacy ProjectMemory into `ProjectManager` with compat aliases.
