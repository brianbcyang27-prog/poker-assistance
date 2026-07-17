# AI Agent System — 15-Feature Research Report

Stack: Python 3.9+, FastAPI, SQLite, httpx, asyncio  
Principle: Simplest approach that works. Zero heavy dependencies.

---

## 1. Speculative Multi-Action Prediction

**What it is:** Predict multiple actions in one LLM call, validate against live state, execute valid ones.

**Best architectural pattern:**
- **Fast Speculator + Slow Actor** (from arxiv:2510.04371 — "Speculative Actions")
- Speculator (cheap model) predicts top-k next actions while Actor (expensive model) validates
- K-branch parallel strategy: predict k guesses for next action, launch speculative calls in parallel
- Cache predicted actions; skip LLM call on cache hit
- On divergence: rollback invalid predictions, fall back to single-action mode

**How UFO³ implements it:**
- `ACTION_SEQUENCE: true` in config enables batch prediction
- `ListActionCommandInfo` manages action sequences
- Validates each predicted action against live UI Automation state before execution
- Falls back to single-action mode on validation failure
- Reports up to 51% fewer LLM calls

**How PASTE (arxiv:2603.18897) implements it:**
- Pattern-aware: mines recurring tool-call sequences from history
- Two async queues: active (authoritative) and shadow (speculative)
- Shared result cache keyed by tool name + arg hash
- Speculative jobs only run on idle resources (slack budget)
- 48.5% average task completion time reduction

**Recommended approach:**
```python
class SpeculativeExecutor:
    def __init__(self, fast_model: str, slow_model: str):
        self.speculator = LLMClient(model=fast_model)
        self.actor = LLMClient(model=slow_model)
        self.cache: dict[str, ActionPlan] = {}  # key = hash(state, context)

    async def predict_batch(self, state: AgentState) -> list[Action]:
        """Fast model predicts top-k actions."""
        prompt = build_prediction_prompt(state)
        response = await self.speculator.complete(prompt, max_tokens=512)
        return parse_action_plan(response)

    async def execute_with_speculation(self, state: AgentState) -> list[ActionResult]:
        # Speculator predicts while actor validates in parallel
        spec_task = asyncio.create_task(self.predict_batch(state))
        real_plan = await self.actor.complete(build_plan_prompt(state))
        
        spec_actions = await spec_task
        valid_actions = validate_against_state(spec_actions, state.current_state)
        
        results = []
        for action in valid_actions:
            if action in real_plan:
                results.append(await self.execute_cached(action))
            else:
                results.append(await self.execute(action))
        return results
```

**Libraries:** Pydantic (action schemas), httpx (LLM calls), hashlib (cache keys)

**Integration points:**
- Pydantic `BaseModel` for action plan JSON schemas with `model_validate_json()`
- Store action predictions in SQLite for pattern mining
- httpx for async LLM calls to both speculator and actor

---

## 2. Demonstration-Conditioned Learning

**What it is:** Record mouse/keyboard/screen during human demos, replay or learn from them.

**Best architectural pattern:**
- Event-sourced recording: every interaction is an immutable timestamped event
- Three capture channels: input events (keyboard/mouse), screen frames, accessibility tree snapshots
- Replay engine that re-executes events with optional parameterization

**How leading projects implement it:**
- **Captr (macOS):** Records `events.jsonl` with timestamped mouse/keyboard actions, accessibility tree snapshots, DOM snapshots, OBS screen recording
- **Silk:** macOS Accessibility API + CGEvent for DOM-level control, Bezier curve humanization, `isTrusted=true` events
- **mac-cua:** `CGEventPostToPid` for background input delivery, ScreenCaptureKit for screenshots, AX tree reads
- **Open Interpreter OS mode:** Screenshot → vision LLM → mouse/keyboard actions loop

**macOS APIs needed:**
- `pyobjc` for Accessibility API (`AXUIElement` tree walking)
- `CGEvent` / `CGEventPostToPid` for input synthesis
- `ScreenCaptureKit` or `CGWindowListCreateImage` for screenshots
- ` Quartz` event tap for recording

**Recommended approach:**
```python
@dataclass
class InputEvent:
    timestamp: float
    event_type: str  # "click", "type", "key_press", "scroll", "move"
    x: float | None = None
    y: float | None = None
    key: str | None = None
    text: str | None = None
    modifiers: list[str] | None = None
    app_bundle_id: str | None = None
    ax_element_ref: str | None = None  # semantic ref, not coordinates

@dataclass
class DemoRecording:
    session_id: str
    events: list[InputEvent]
    screenshots: list[bytes]  # PNG frames
    ax_trees: list[dict]     # accessibility tree snapshots
    metadata: dict           # app context, screen resolution

class DemoRecorder:
    async def start_recording(self) -> str: ...
    async def stop_recording(self) -> DemoRecording: ...
    
class DemoReplayer:
    async def replay(self, recording: DemoRecording, 
                     parameterize: dict | None = None) -> ReplayResult: ...
```

**Libraries:** `pyobjc` (macOS APIs), `Pillow` (screenshots), Pydantic (event schemas)

**Integration points:**
- Store recordings as JSONL in SQLite (events) + file blobs (screenshots)
- Use recordings as few-shot examples in agent prompts
- FTS5 index over event descriptions for pattern retrieval

---

## 3. Retrieval-Augmented Execution Memory

**What it is:** RAG over agent's own execution history and learned knowledge.

**Best architectural pattern:**
- **Hybrid BM25 + optional vector search** (from AgentMemory, MEMENTO, Engrava)
- BM25-first with optional embeddings for semantic dedup
- SQLite FTS5 for keyword retrieval, Reciprocal Rank Fusion for hybrid

**How leading projects implement it:**
- **AgentMemory:** SQLite-first, BM25-only without embeddings, optional hybrid with vector. Write Guard with semantic dedup. Typed memories (identity, emotion, knowledge, event). URI paths. Lifecycle management (decay, reindex).
- **MEMENTO:** SQLite + FTS5 fact store + Git wiki. No embeddings. Keyword bridge connecting facts to wiki pages. 2-hop deep recall.
- **Engrava:** SQLite thought CRUD, edge-based knowledge graph, FTS5/BM25, optional embeddings, DreamingExtension for consolidation
- **QuackIR:** Research proving RDBMSes (SQLite FTS5, DuckDB) achieve comparable retrieval to dedicated vector DBs

**Recommended approach (embedding-free):**
```python
class ExecutionMemory:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
    
    async def init_schema(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,  -- 'execution', 'preference', 'fact', 'lesson'
                content TEXT NOT NULL,
                context TEXT,         -- JSON: task, tool, session info
                keywords TEXT,        -- comma-separated for FTS boost
                created_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(content, context, keywords, 
                           content=memories, content_rowid=rowid);
        """)
    
    async def remember(self, content: str, mem_type: str, context: dict) -> str:
        """Store memory with automatic FTS indexing."""
        mem_id = uuid.uuid4().hex
        await self.db.execute(
            "INSERT INTO memories (id, type, content, context, created_at) VALUES (?,?,?,?,?)",
            (mem_id, mem_type, content, json.dumps(context), datetime.utcnow().isoformat())
        )
        await self.db.commit()
        return mem_id
    
    async def recall(self, query: str, limit: int = 10) -> list[dict]:
        """BM25 retrieval via FTS5."""
        rows = await self.db.execute_fetchall(
            """SELECT m.*, rank FROM memories_fts 
               JOIN memories m ON memories_fts.rowid = m.rowid
               WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?""",
            (query, limit)
        )
        return [dict(r) for r in rows]
    
    async def boot(self, task_context: str) -> list[dict]:
        """Load relevant memories for new task context."""
        return await self.recall(task_context, limit=20)
```

**Libraries:** `aiosqlite` (async SQLite), FTS5 (built into SQLite), Pydantic

---

## 4. Pluggable Memory Architecture

**What it is:** Provider/interface pattern so memory backends can be swapped.

**Best architectural pattern:**
- Abstract `MemoryProvider` ABC (from Hermes Agent's `plugins/memory/`)
- Registry pattern: `memory.register("sqlite", SqliteMemory)`, `memory.register("redis", RedisMemory)`
- Single-select active provider configured at startup

**How Hermes implements it:**
- Three-layer: `MemoryStore` → `MemoryManager` → `MemoryProvider`
- `MemoryProvider` ABC as plugin interface
- Frozen-snapshot model for prompt cache protection
- Only one provider active at a time

**Recommended approach:**
```python
from abc import ABC, abstractmethod

class MemoryProvider(ABC):
    @abstractmethod
    async def remember(self, content: str, mem_type: str, **kwargs) -> str: ...
    
    @abstractmethod
    async def recall(self, query: str, limit: int = 10) -> list[dict]: ...
    
    @abstractmethod
    async def boot(self, context: str) -> list[dict]: ...
    
    @abstractmethod
    async def forget(self, memory_id: str) -> bool: ...

class SqliteMemoryProvider(MemoryProvider):
    """Default: SQLite + FTS5, zero external deps."""
    ...

class HybridMemoryProvider(MemoryProvider):
    """SQLite + optional embeddings via httpx to local API."""
    ...

class MemoryManager:
    def __init__(self):
        self._providers: dict[str, MemoryProvider] = {}
        self._active: str = "sqlite"
    
    def register(self, name: str, provider: MemoryProvider): ...
    def set_active(self, name: str): ...
    
    @property
    def provider(self) -> MemoryProvider:
        return self._providers[self._active]
```

**Integration:** FastAPI dependency injection: `def get_memory(request: Request) -> MemoryManager: ...`

---

## 5. Knowledge Graph Integration

**What it is:** Entity-relation graph for structured knowledge, backed by SQLite.

**Best architectural pattern:**
- **SQLite durable store + NetworkX in-memory mirror** (from Thoth)
- SQLite stores entities + relations (WAL mode)
- NetworkX `MultiDiGraph` rebuilt on startup from SQLite
- All reads hit NetworkX; writes go to SQLite first, then update graph

**How Thoth implements it:**
- `entities` table: id, type, subject, description, aliases, tags, properties (JSON)
- `relations` table: source_id, target_id, relation_type, confidence, properties
- NetworkX `MultiDiGraph` loaded from SQLite at startup
- FAISS index for semantic recall of entities
- `get_subgraph()` extracts neighborhood for visualization

**How Engrava implements it:**
- Edge-based graph with types: ASSOCIATED, DEPENDS_ON, DERIVED_FROM, CONSOLIDATED_FROM
- Integrated with FTS5 hybrid search
- DreamingExtension for automatic consolidation

**Recommended approach:**
```python
class KnowledgeGraph:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph()
    
    async def init_schema(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT DEFAULT '',
                properties TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                target_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                relation_type TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                properties TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(source_id, target_id, relation_type)
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts 
                USING fts5(subject, description, entity_type);
        """)
    
    async def load_graph(self):
        """Populate NetworkX from SQLite."""
        entities = await self.db.execute_fetchall("SELECT * FROM entities")
        relations = await self.db.execute_fetchall("SELECT * FROM relations")
        self._graph = nx.MultiDiGraph()
        for e in entities:
            self._graph.add_node(e["id"], **dict(e))
        for r in relations:
            if r["source_id"] in self._graph and r["target_id"] in self._graph:
                self._graph.add_edge(r["source_id"], r["target_id"], **dict(r))
    
    async def add_entity(self, entity_type: str, subject: str, description: str = "") -> str: ...
    async def add_relation(self, source_id: str, target_id: str, relation_type: str) -> str: ...
    def get_neighbors(self, entity_id: str, hops: int = 2) -> list[dict]: ...
    def get_subgraph(self, entity_id: str, hops: int = 2) -> dict: ...
```

**Libraries:** `networkx` (in-memory graph algorithms), `aiosqlite`, FTS5

---

## 6. Agent Computer Interface

**What it is:** Semantic actions wrapping shell commands for safe, observable computer control.

**Best architectural pattern:**
- Semantic action vocabulary (from E2B, mac-cua, Silk)
- Every action returns structured result with status, error, screenshot
- Safety layer: command classification (read/write/destructive), approval gates
- Accessibility-tree-first approach (from mac-cua: "reads apps through AX tree, acts through background-targeted input")

**How leading projects implement it:**
- **E2B:** `screenshot()` → `leftClick(x,y)` → `write(text)` → `press(keys)` loop. Desktop SDK wraps all OS interactions.
- **mac-cua:** `CGEventPostToPid` for background input (never touches global cursor). ScreenCaptureKit for window capture. AX tree for element discovery.
- **Open Interpreter:** LLM emits code blocks → `exec()` in sandboxed environment → stdout/stderr back to LLM. Computer module for screenshots + mouse/keyboard.
- **Silk:** Accessibility API element discovery → Bezier curve humanization → CGEvent. `click "Submit" --app Chrome` semantic interface.

**Recommended approach:**
```python
class ActionResult(BaseModel):
    success: bool
    output: str | None = None
    error: str | None = None
    screenshot_path: str | None = None
    ax_tree_hash: str | None = None  # for change detection

class AgentComputerInterface:
    """Semantic actions over shell + accessibility APIs."""
    
    async def screenshot(self, app: str | None = None) -> bytes: ...
    async def get_ui_tree(self, app: str) -> dict: ...
    async def click(self, x: float, y: float, app: str | None = None) -> ActionResult: ...
    async def click_element(self, selector: str, app: str) -> ActionResult: ...
    async def type_text(self, text: str, app: str | None = None) -> ActionResult: ...
    async def press_key(self, key: str, modifiers: list[str] | None = None) -> ActionResult: ...
    async def scroll(self, direction: str, amount: int, app: str | None = None) -> ActionResult: ...
    async def run_shell(self, command: str, timeout: float = 30.0) -> ActionResult: ...
    async def open_app(self, bundle_id: str) -> ActionResult: ...
    
    def classify_action(self, action: str) -> str:
        """Returns 'read', 'write', 'destructive', 'external'."""
        ...
```

**Libraries:** `pyobjc` (macOS), `asyncio.subprocess` (shell), Pydantic (schemas)

---

## 7. DAG Mission Planner

**What it is:** Decompose missions into DAGs with dependencies, execute in parallel.

**Best architectural pattern:**
- LLM generates task DAG as JSON
- Topological sort for execution order
- `asyncio.gather` for parallel independent tasks
- Dynamic replanning after each round (from LazyBridge ReplanEngine)

**How leading projects implement it:**
- **LazyBridge ReplanEngine:** Planner emits `PlanRound` each turn with tasks + `done` flag. Tasks with `parallel=True` run via `asyncio.gather`. Checkpoint/resume via Store.
- **llm_agent_scheduler:** `PlannerAgent` decomposes into DAG. `Scheduler` uses `asyncio.Semaphore` for concurrency control. Dependencies checked before execution.
- **LangDAG:** Nodes + edges + conditional routing. `arun_dag()` for async. Snapshot on error + `resume_dag()`.
- **Hermes Kanban:** SQLite-backed task board with auto-decomposition, swarm topology, per-task model overrides.

**Recommended approach:**
```python
class TaskNode(BaseModel):
    id: str
    name: str
    tool: str
    kwargs: dict[str, Any] = {}
    dependencies: list[str] = []  # task IDs that must complete first
    parallel: bool = True
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None

class MissionPlan(BaseModel):
    mission_id: str
    goal: str
    tasks: list[TaskNode]
    max_rounds: int = 10

class DAGPlanner:
    def __init__(self, llm: LLMClient, tools: dict[str, Callable]):
        self.llm = llm
        self.tools = tools
    
    async def plan(self, goal: str, available_tools: list[dict]) -> MissionPlan:
        """LLM generates task DAG from goal."""
        prompt = build_planning_prompt(goal, available_tools)
        response = await self.llm.complete(prompt, response_format=MissionPlan)
        return MissionPlan.model_validate_json(response)
    
    async def execute(self, plan: MissionPlan) -> dict:
        """Execute DAG with dependency resolution."""
        completed = set()
        while len(completed) < len(plan.tasks):
            ready = [t for t in plan.tasks 
                    if t.id not in completed and t.status == "pending"
                    and all(d in completed for d in t.dependencies)]
            
            if not ready:
                break  # deadlock or all done
            
            parallel_tasks = [t for t in ready if t.parallel]
            sequential_tasks = [t for t in ready if not t.parallel]
            
            # Run parallel batch
            if parallel_tasks:
                results = await asyncio.gather(*[
                    self._execute_task(t) for t in parallel_tasks
                ])
                for t, r in zip(parallel_tasks, results):
                    t.result = r
                    t.status = "completed"
                    completed.add(t.id)
            
            # Run sequential tasks
            for t in sequential_tasks:
                t.result = await self._execute_task(t)
                t.status = "completed"
                completed.add(t.id)
        
        return {t.id: t.result for t in plan.tasks}
```

**Libraries:** Pydantic (task schemas), `asyncio` (parallel execution), `toposort` or manual topo-sort

---

## 8. Agent Review Pipeline

**What it is:** Self-review of agent outputs before execution. Confidence-based routing.

**Best architectural pattern:**
- **LLM-as-Judge pattern** (from MindStudio): second model evaluates before execution
- Structured verdict: `{verdict, confidence, reason, suggested_action}`
- Retry loop with feedback (cap at 2-3 retries)
- Confidence-tiered routing: high → auto-execute, medium → log + proceed, low → block + escalate
- Panel judging: multiple judges vote

**How leading projects implement it:**
- **Confidence-Aware Routing (arxiv:2510.01237):** Pre-generation assessment using semantic alignment + convergence analysis + learned confidence. Routes to local/RAG/large-model/human based on confidence.
- **DiSRouter:** Each agent self-assesses competence. Cascade of agents ordered by cost. "I don't know" triggers escalation.
- **Hermes per-turn verifier:** Tool outcomes verified each turn, with indent preservation and failure escalation.

**Recommended approach:**
```python
class ReviewVerdict(BaseModel):
    verdict: str  # "pass", "fail", "needs_revision"
    confidence: float  # 0.0 - 1.0
    reason: str
    suggested_revision: str | None = None

class ReviewPipeline:
    def __init__(self, judge_model: str, max_retries: int = 2):
        self.judge = LLMClient(model=judge_model)
        self.max_retries = max_retries
    
    async def review(self, task: str, output: str, criteria: list[str]) -> ReviewVerdict:
        prompt = build_review_prompt(task, output, criteria)
        response = await self.judge.complete(prompt, response_format=ReviewVerdict)
        return ReviewVerdict.model_validate_json(response)
    
    async def execute_with_review(self, task: str, executor: Callable, 
                                   criteria: list[str]) -> Any:
        for attempt in range(self.max_retries + 1):
            output = await executor(task)
            verdict = await self.review(task, str(output), criteria)
            
            if verdict.verdict == "pass" or verdict.confidence > 0.9:
                return output
            elif verdict.verdict == "needs_revision" and attempt < self.max_retries:
                task = f"{task}\n\nPrevious attempt had issues: {verdict.reason}\n{verdict.suggested_revision}"
                continue
            else:
                raise ReviewFailedError(verdict)
```

---

## 9. Dynamic Team Assembly

**What it is:** Select workers based on task requirements, track performance.

**Best architectural pattern:**
- **Retrieval-based team building** (from Captain Agent)
- Register workers with capabilities, track success rates
- RAG over worker profiles to find best matches
- Dynamic: rebuild team per subtask, not fixed upfront

**How Captain Agent implements it:**
- Lists roles needed for subtask
- Retrieves candidate agents by capability match
- Agent selector links roles to best candidates
- Falls back to agent generation for unmatched roles
- Reflector provides feedback; team rebuilt if needed

**Recommended approach:**
```python
class WorkerProfile(BaseModel):
    worker_id: str
    name: str
    capabilities: list[str]
    model: str
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    total_tasks: int = 0
    cost_per_task_usd: float = 0.0

class TeamAssembler:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
    
    async def find_workers(self, required_capabilities: list[str], 
                          top_k: int = 5) -> list[WorkerProfile]:
        """Find best workers by capability match + performance."""
        rows = await self.db.execute_fetchall("""
            SELECT * FROM workers 
            WHERE capabilities LIKE ? OR capabilities LIKE ? OR ...
            ORDER BY success_rate DESC, avg_latency_ms ASC
            LIMIT ?
        """, [f"%{cap}%" for cap in required_capabilities] + [top_k])
        return [WorkerProfile(**dict(r)) for r in rows]
    
    async def record_outcome(self, worker_id: str, task_id: str, 
                            success: bool, latency_ms: float, cost_usd: float):
        """Update worker performance stats."""
        await self.db.execute("""
            UPDATE workers SET 
                total_tasks = total_tasks + 1,
                success_rate = (success_rate * total_tasks + ?) / (total_tasks + 1),
                avg_latency_ms = avg_latency_ms * 0.7 + ? * 0.3
            WHERE worker_id = ?
        """, (1.0 if success else 0.0, latency_ms, worker_id))
        await self.db.commit()
```

---

## 10. Agent Observability

**What it is:** Structured logging, decision tracing, metrics for agent runs.

**Best architectural pattern:**
- **OpenTelemetry GenAI conventions** (from opentelemetry.io, AgentTrace)
- Three-surface taxonomy: cognitive (reasoning), operational (method calls), contextual (external I/O)
- Span per model call, tool execution, and retrieval
- Decision-logging contract: intent, why, context_source, risk, reversible
- Correlation IDs across agent handoffs

**How AgentTrace implements it:**
- Runtime observer pattern: wraps agent methods without code modification
- JSONL logs + OTel spans export
- Cognitive surface: prompts, completions, reasoning chains, confidence
- Contextual surface: HTTP, SQL, cache operations via auto-instrumentation

**Recommended approach:**
```python
import logging, json, time, uuid

logger = logging.getLogger("agent")

class DecisionTracer:
    """Structured decision tracing without OTel dependency."""
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.span_id = 0
    
    def start_span(self, name: str, parent_id: str | None = None) -> str:
        span_id = f"{self.run_id}:{self.span_id}"
        self.span_id += 1
        logger.info(json.dumps({
            "event": "span_start",
            "run_id": self.run_id,
            "span_id": span_id,
            "parent_id": parent_id,
            "name": name,
            "ts": time.time()
        }))
        return span_id
    
    def log_decision(self, span_id: str, intent: str, why: str, 
                     context_source: str, risk: str, reversible: bool):
        logger.info(json.dumps({
            "event": "decision",
            "run_id": self.run_id,
            "span_id": span_id,
            "intent": intent,
            "why": why,
            "context_source": context_source,
            "risk": risk,
            "reversible": reversible,
            "ts": time.time()
        }))
    
    def end_span(self, span_id: str, status: str = "ok", 
                 tokens_used: int = 0, cost_usd: float = 0.0):
        logger.info(json.dumps({
            "event": "span_end",
            "run_id": self.run_id,
            "span_id": span_id,
            "status": status,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "ts": time.time()
        }))
```

**Libraries:** Python `logging` (structured JSON), `structlog` (optional, for better formatting)

---

## 11. Event Bus

**What it is:** Async pub/sub for decoupled agent components.

**Best architectural pattern:**
- **In-process pub/sub with wildcard topics** (from agent-event-bus)
- Dot-separated topic namespaces: `tool.call.start`, `model.response`, `mission.complete`
- Wildcard matching: `tool.*` matches all tool events
- Sync + async handlers
- Optional history buffer for debugging

**How agent-event-bus implements it:**
- `EventBus` / `AsyncEventBus` classes
- `bus.on("tool.*", handler)` with wildcard support
- `bus.emit_async("tool.call.end", data={...})`
- `bus.once("mission.failed", handler)` for one-shot listeners
- Zero deps, ~200 lines of code

**How AgentBus implements it:**
- Typed topics: `Topic[InboundChat]`, `Topic[ToolRequest]`
- Nodes subscribe/publish to topics
- `source_node` set by bus (identity can't be faked)
- System topics auto-registered: lifecycle, heartbeat, backpressure

**Recommended approach:**
```python
import asyncio, re
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class Event:
    topic: str
    data: dict
    timestamp: float = field(default_factory=time.time)

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[Event] = []
        self._history_max: int = 1000
    
    def on(self, topic_pattern: str, handler: Callable):
        self._handlers[topic_pattern].append(handler)
    
    def once(self, topic_pattern: str, handler: Callable):
        async def wrapper(*args, **kwargs):
            self._handlers[topic_pattern].remove(wrapper)
            await handler(*args, **kwargs)
        self._handlers[topic_pattern].append(wrapper)
    
    async def emit(self, topic: str, data: dict):
        event = Event(topic=topic, data=data)
        self._history.append(event)
        if len(self._history) > self._history_max:
            self._history = self._history[-self._history_max:]
        
        for pattern, handlers in self._handlers.items():
            if self._matches(pattern, topic):
                for handler in handlers:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
    
    def _matches(self, pattern: str, topic: str) -> bool:
        regex = pattern.replace(".", r"\.").replace("*", "[^.]+")
        return bool(re.fullmatch(regex, topic))
```

**Libraries:** `asyncio` only. Zero external deps.

---

## 12. Capability Registry

**What it is:** Service discovery for tools and agents. Register, discover, select.

**Best architectural pattern:**
- **Tool registry with semantic search** (from agent-tool-registry, Hermes)
- SQLite for structured metadata + FTS5 for semantic search
- Reliability tracking per tool (success rate, latency EWMA)
- Framework adapters: convert registry entry to OpenAI/Anthropic/LangChain tool format

**How Hermes implements it:**
- `tools/registry.py`: central registry, 70+ tools across 28 toolsets
- Each tool file self-registers at import time
- Registry handles schema collection, dispatch, availability checking
- Toolset system for platform-specific groupings

**How agent-tool-registry implements it:**
- FastAPI server + SQLite + ChromaDB
- POST `/tools` to register with JSON Schema I/O
- GET `/tools/search` for semantic search
- GET `/recommend` for best tool by task + cost budget
- POST `/tools/{id}/ping` for reliability tracking

**Recommended approach:**
```python
class ToolEntry(BaseModel):
    tool_id: str
    name: str
    description: str
    category: str
    tags: list[str] = []
    input_schema: dict = {}  # JSON Schema
    output_schema: dict = {}
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    cost_per_call_usd: float = 0.0
    total_calls: int = 0

class CapabilityRegistry:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
    
    async def register(self, entry: ToolEntry): ...
    async def search(self, query: str, top_k: int = 5) -> list[ToolEntry]:
        """FTS5 semantic search over tool descriptions."""
        ...
    async def recommend(self, task: str, budget_usd: float | None = None) -> ToolEntry:
        """Rank by similarity * reliability, filter by budget."""
        ...
    async def ping(self, tool_id: str, success: bool, latency_ms: float):
        """Update reliability stats."""
        ...
    def to_openai_tool(self, entry: ToolEntry) -> dict:
        """Convert to OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": entry.name,
                "description": entry.description,
                "parameters": entry.input_schema
            }
        }
```

---

## 13. Model Router

**What it is:** Route requests to the best LLM based on task type, complexity, cost.

**Best architectural pattern:**
- **Task classification → model mapping** (from NVIDIA LLM Router)
- **Confidence-based routing** (from Confidence-Aware Routing)
- **Pareto-optimal cost-performance** (from OmniRouter)
- Simple: classify task → select model → proxy request

**How NVIDIA LLM Router implements it:**
- Pre-trained classifier model categorizes prompts (code gen, chatbot, summarization, etc.)
- Config maps task categories to specific models
- OpenAI-compatible proxy interface
- Manual override option

**Recommended approach (no ML router needed):**
```python
class ModelConfig(BaseModel):
    name: str
    api_url: str
    api_key: str
    model_id: str
    cost_per_1k_tokens: float
    max_tokens: int
    strengths: list[str]  # ["code", "reasoning", "creative", "fast"]

class ModelRouter:
    def __init__(self, models: list[ModelConfig]):
        self.models = models
        self.task_classifier = LLMClient(model="gpt-4o-mini")  # cheap classifier
    
    async def route(self, task: str, task_type: str | None = None) -> ModelConfig:
        if task_type is None:
            task_type = await self._classify(task)
        return self._select_model(task_type)
    
    async def _classify(self, task: str) -> str:
        """Classify task into category using cheap model."""
        response = await self.task_classifier.complete(
            f"Classify this task into one of: code, reasoning, creative, summarization, chat, translation.\n\nTask: {task}",
            max_tokens=20
        )
        return response.strip().lower()
    
    def _select_model(self, task_type: str) -> ModelConfig:
        """Select best model for task type (cheapest that handles it)."""
        # Sort by cost, return first that has the capability
        candidates = [m for m in self.models if task_type in m.strengths]
        return min(candidates, key=lambda m: m.cost_per_1k_tokens)
```

**Libraries:** httpx (API calls), Pydantic (config)

---

## 14. Mission Timeline

**What it is:** Event-sourced timeline of agent execution for replay and debugging.

**Best architectural pattern:**
- **Event sourcing: append-only event log, state derived by replay** (from ESAA, Waypoint, Rewind)
- Immutable events in SQLite (JSONL or structured table)
- State = replay of events from start
- Checkpoints for resume after crash
- Replay engine: re-run with new code against historical events

**How leading projects implement it:**
- **ESAA:** `.roadmap/activity.jsonl` append-only store. `event_seq` ordered, no gaps. Read models are deterministic projections. Replay verifies projections match event store.
- **Waypoint:** `@checkpoint` decorator. PostgreSQL append-only journal. Cached LLM responses return instantly on replay (zero token cost). Crash → resume from last checkpoint.
- **Rewind:** Event store + CRDT resolver + time-travel engine. "Rewind to before that bad call" and get real answer. Snapshot compactor bounds growth.

**Recommended approach:**
```python
class MissionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    mission_id: str
    seq: int  # monotonically increasing per mission
    event_type: str  # "mission_started", "task_planned", "task_started", "task_completed", "task_failed", "review_passed", "mission_completed"
    payload: dict
    timestamp: float = Field(default_factory=time.time)

class MissionTimeline:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
    
    async def init_schema(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS mission_events (
                event_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp REAL NOT NULL,
                UNIQUE(mission_id, seq)
            );
            CREATE INDEX IF NOT EXISTS idx_events_mission ON mission_events(mission_id);
        """)
    
    async def append(self, event: MissionEvent):
        await self.db.execute(
            "INSERT INTO mission_events (event_id, mission_id, seq, event_type, payload, timestamp) VALUES (?,?,?,?,?,?)",
            (event.event_id, event.mission_id, event.seq, event.event_type, 
             json.dumps(event.payload), event.timestamp)
        )
        await self.db.commit()
    
    async def get_timeline(self, mission_id: str) -> list[MissionEvent]:
        rows = await self.db.execute_fetchall(
            "SELECT * FROM mission_events WHERE mission_id = ? ORDER BY seq",
            (mission_id,)
        )
        return [MissionEvent(**{**dict(r), "payload": json.loads(r["payload"])}) for r in rows]
    
    async def get_state_at(self, mission_id: str, seq: int) -> dict:
        """Replay events up to seq to reconstruct state."""
        events = await self.get_timeline(mission_id)
        state = {}
        for e in events:
            if e.seq > seq:
                break
            state = apply_event(state, e)  # state machine
        return state
    
    async def replay_mission(self, mission_id: str) -> dict:
        """Full replay for debugging."""
        events = await self.get_timeline(mission_id)
        return reconstruct_state(events)
```

**Libraries:** `aiosqlite`, Pydantic, `json`

---

## 15. Autonomous Skill Evolution

**What it is:** Track skill success rates, auto-deprecate failing skills, evolve from experience.

**Best architectural pattern:**
- **Success rate tracking + automatic deprecation** (from Hermes Skills)
- Skills stored as reusable procedure records
- Every skill execution records outcome
- Background curation: promote high-success, archive low-success
- Self-improvement: skill updated based on failure feedback

**How Hermes implements it:**
- Skills are procedural memory: stored procedures the agent creates and reuses
- Skills self-improve during use (updated when they produce better results)
- `Curator` runs background maintenance (archive/prune/list-archived)
- Progressive-disclosure architecture: skills loaded on demand

**Recommended approach:**
```python
class Skill(BaseModel):
    skill_id: str
    name: str
    description: str
    procedure: str  # markdown or code
    category: str
    success_rate: float = 1.0
    total_uses: int = 0
    successful_uses: int = 0
    avg_latency_ms: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used: str | None = None
    deprecated: bool = False
    version: int = 1

class SkillEvolver:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
    
    async def record_use(self, skill_id: str, success: bool, latency_ms: float):
        """Track skill performance."""
        await self.db.execute("""
            UPDATE skills SET 
                total_uses = total_uses + 1,
                successful_uses = successful_uses + ?,
                success_rate = (CAST(successful_uses AS REAL) + ?) / (total_uses + 1),
                avg_latency_ms = avg_latency_ms * 0.7 + ? * 0.3,
                last_used = ?
            WHERE skill_id = ?
        """, (1 if success else 0, 1 if success else 0, latency_ms,
              datetime.utcnow().isoformat(), skill_id))
        await self.db.commit()
    
    async def curate(self, min_uses: int = 5, deprecation_threshold: float = 0.3):
        """Background: deprecate low-performing skills."""
        await self.db.execute("""
            UPDATE skills SET deprecated = 1 
            WHERE total_uses >= ? AND success_rate < ? AND deprecated = 0
        """, (min_uses, deprecation_threshold))
        await self.db.commit()
    
    async def get_active_skills(self, category: str | None = None) -> list[Skill]:
        query = "SELECT * FROM skills WHERE deprecated = 0"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY success_rate DESC"
        rows = await self.db.execute_fetchall(query, params)
        return [Skill(**dict(r)) for r in rows]
    
    async def improve_skill(self, skill_id: str, feedback: str, new_procedure: str):
        """Update skill based on failure feedback."""
        skill = await self.get_skill(skill_id)
        skill.procedure = new_procedure
        skill.version += 1
        # Store old version for history
        await self.db.execute(
            "INSERT INTO skill_history (skill_id, version, procedure, feedback, created_at) VALUES (?,?,?,?,?)",
            (skill_id, skill.version - 1, skill.procedure, feedback, datetime.utcnow().isoformat())
        )
        await self.db.execute(
            "UPDATE skills SET procedure = ?, version = version + 1 WHERE skill_id = ?",
            (new_procedure, skill_id)
        )
        await self.db.commit()
```

**Libraries:** `aiosqlite`, Pydantic, `asyncio` (background curation tasks)

---

## Summary: Dependency Matrix

| Feature | Core Deps | Optional Deps |
|---------|-----------|---------------|
| 1. Speculative Prediction | Pydantic, httpx | — |
| 2. Demo Recording | pyobjc (macOS), Pillow | — |
| 3. Execution Memory | aiosqlite, FTS5 | sentence-transformers |
| 4. Pluggable Memory | ABC, aiosqlite | — |
| 5. Knowledge Graph | networkx, aiosqlite | — |
| 6. Computer Interface | pyobjc, asyncio.subprocess | — |
| 7. DAG Planner | Pydantic, asyncio | — |
| 8. Review Pipeline | httpx (LLM), Pydantic | — |
| 9. Team Assembly | aiosqlite, Pydantic | — |
| 10. Observability | logging (stdlib) | structlog |
| 11. Event Bus | asyncio (stdlib) | — |
| 12. Capability Registry | aiosqlite, FTS5 | — |
| 13. Model Router | httpx, Pydantic | — |
| 14. Mission Timeline | aiosqlite, Pydantic | — |
| 15. Skill Evolution | aiosqlite, Pydantic | — |

**New dependencies needed:** `pyobjc` (macOS features), `networkx` (graph). Everything else uses the existing stack.

**Cross-cutting patterns:**
- Pydantic for all data models and JSON schema generation
- `aiosqlite` for all database access (async, WAL mode)
- FTS5 for all text search (memory, registry, knowledge graph)
- Event sourcing for timeline and replay
- httpx for all external API calls
- asyncio for all concurrency
