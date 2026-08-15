# v9.0.0 Architecture Ownership Contract

> **Version:** 1.0.0
> **Date:** 2026-07-30
> **Status:** Active — Foundation Stabilization Phase
> **Applies To:** JARVIS v9.0.0+

---

## Purpose

Every responsibility must have exactly one owner.

This document defines the target architecture for JARVIS v9.0.0 by assigning clear ownership boundaries. No module, system, or capability should have ambiguous ownership.

Duplication of responsibility is a bug.

---

## Ownership Table

| Domain | Owner | Location | Status |
|--------|-------|----------|--------|
| Configuration | `ConfigSystem` | `jarvis/core/config.py` | ✅ KEEP |
| Database / Persistence | `Database` | `jarvis/core/database.py` | ✅ KEEP |
| Event Bus | `EventBus` | `jarvis/core/events.py` | ✅ KEEP |
| Capability Registry | `CapabilitySystem` | `jarvis/core/capabilities.py` | ✅ KEEP |
| LLM Interface | `LLM` | `jarvis/brain/llm.py` | ✅ KEEP |
| **Memory System** | `MemorySystem` | `jarvis/brain/memory/` | 🔄 CONSOLIDATE |
| **Mission Engine** | `MissionEngine` | `jarvis/mission/` | 🔄 CONSOLIDATE |
| **Tool System** | `ToolRegistry` | `jarvis/tools/` | 🔄 CONSOLIDATE |
| Agent Hierarchy | `JarvisAgent` | `jarvis/agents/` | ✅ KEEP |
| Kings | `KingBase` | `jarvis/agents/kings/` | ✅ KEEP |
| Workers | `WorkerBase` | `jarvis/agents/workers/` | ✅ KEEP |
| **Human Interaction** | `InteractionLayer` | `jarvis/brain/interaction/` | 🆕 NEW |
| **Architecture Profiles** | `ArchitectureRegistry` | `jarvis/architectures/` | 🔧 SIMPLIFY |
| Permissions / Safety | `PermissionSystem` | `jarvis/core/permissions.py` | ✅ KEEP |
| Diagnostics | `Diagnostics` | `jarvis/core/diagnostics.py` | ✅ KEEP |
| Web API | `ChatRouter` | `jarvis/web/routers/` | ✅ KEEP |
| Voice I/O | `VoiceEngine` | `jarvis/web/services/tts.py` | ✅ KEEP |
| IoT | `IoTController` | `jarvis/iot/` | ✅ KEEP |
| OS Integration | `OSIntegration` | `jarvis/os/` | ✅ KEEP |
| Computer Control | `ComputerControl` | `jarvis/computer/` | ✅ KEEP |

---

## Memory System — Ownership Contract

### Consolidation Target

```
jarvis/brain/memory/
├── working.py          # Working memory for current context
├── episodic.py         # Episodic memory (past events)
├── personal.py         # Personal preferences & user model
├── journal.py          # Journal entries & daily summaries
├── graph.py            # Knowledge graph backend
├── retrieval.py        # Unified retrieval interface (across all types)
├── consolidation.py    # Memory consolidation & importance scoring
└── __init__.py
```

### What Was REMOVED

| Old Location | Reason |
|---|---|
| `jarvis/knowledge/` | Merged into `brain/memory/graph.py` |
| `jarvis/journal/` | Merged into `brain/memory/journal.py` |
| `jarvis/memory/` (root) | Duplicate of `brain/memory/` |
| `memory/database.py` | Merged into `jarvis/core/database.py` |

### Rules

1. **All memory access flows through `brain/memory/retrieval.py`**. No direct database queries from outside the memory system.
2. **Memory types are unified behind a single `MemoryEntry` model**. No more `Episode`, `PersonalMemory`, `JournalEntry` as separate schemas at the API boundary.
3. **Consolidation is automatic**, not manual. The system decides what to keep, summarize, or archive.

---

## Mission Engine — Ownership Contract

### Consolidation Target

```
jarvis/mission/
├── planner.py          # Mission planning (DAG construction)
├── executor.py         # Mission execution & worker dispatch
├── timeline.py         # Mission timeline & progress tracking
├── replay.py           # Mission replay (debugging/audit)
├── models.py           # Mission, Stage, Task models
└── __init__.py
```

### What Was REMOVED

| Old Location | Reason |
|---|---|
| `jarvis/brain/dag_planner.py` | Moving to `mission/planner.py` |
| `jarvis/brain/mission_executor.py` | Moving to `mission/executor.py` |
| `jarvis/mission/` (existing) | Already the target location |

### Rules

1. **Mission planning and execution are separate modules** with a clear interface.
2. **Mission replay reads from database logs only** — no side effects during replay.
3. **The mission engine is the only path for multi-step task execution.** No more ad-hoc task loops.

---

## Tool System — Ownership Contract

### Consolidation Target

```
jarvis/tools/
├── registry.py         # Tool registration & metadata
├── executor.py         # Tool execution & result handling
├── permissions.py      # Permission checking & audit
├── actions/            # Individual tool implementations
│   ├── browser.py
│   ├── shell.py
│   ├── files.py
│   ├── web.py
│   └── screen.py
└── __init__.py
```

### What Was REMOVED

| Old Location | Reason |
|---|---|
| `jarvis/agents/tools.py` | Duplicate tool definitions |
| `jarvis/tools/unified.py` | Overlapping with `registry.py` |
| `jarvis/tools/agent_tools.py` | Merging into `executor.py` |
| `jarvis/computer/controller.py` | Redundant with `tools/actions/` |
| `jarvis/computer/manager.py` | Redundant with `tools/actions/` |

### Rules

1. **All tool definitions in one place.** No tools defined inside agent modules.
2. **Permission checks happen in `permissions.py`, not in individual tools.**
3. **Every tool has a risk level** (SAFE, MODERATE, DANGEROUS) and an audit log entry.

---

## Human Interaction Layer — Ownership Contract

### Location

```
jarvis/brain/interaction/
├── intent_classifier.py    # Classify messages into intent categories
├── conversation_mode.py    # Track conversation state & mode
├── response_policy.py      # Control response behavior based on context
└── __init__.py
```

### Intent Categories

| Category | Example | Behavior |
|---|---|---|
| `CHAT` | "hi", "how are you" | Direct friendly response, no capability dump |
| `TASK` | "build a website" | Full agent pipeline with delegation |
| `PROJECT` | "continue BlockFlow" | Load project context, resume work |
| `COMMAND` | "open Safari" | Route to capability/tool system |
| `AUTOMATION` | "daily briefing" | Trigger routine workflow |
| `QUESTION` | "what is the weather" | Answer from context or research |

### Rules

1. **Capability dumps are NEVER shown in CHAT mode** — `developer_mode` flag only.
2. **Classification happens BEFORE the message enters the agent pipeline.**
3. **The interaction layer is the single entry point for all user messages.**

---

## Architecture Profiles — Ownership Contract

### Simplification Target

| Current | Target |
|---|---|
| 2 architectures (Native + Hermes) | 1 architecture (JARVIS Native) |
| Hermes w/ broken frontend bridge | Hermes deferred to v9.2+ |
| `architectures/native/` | Simplified to single path in `chat.py` |

### Rules

1. **Default architecture is always JARVIS Native.**
2. **Hermes code is preserved but not wired** — can be re-enabled when complete.
3. **Architecture switching is removed from user-facing settings** until Hermes is production-ready.

---

## Module Boundaries & Communication

### Allowed Cross-Module Calls

| From | To | Via |
|---|---|---|
| `web/routers/` | `brain/interaction/` | Direct import |
| `brain/interaction/` | `agents/jarvis.py` | `process_user_request()` |
| `agents/jarvis.py` | `agents/kings/` | `execute_task()` |
| `agents/kings/` | `agents/workers/` | `execute_task()` |
| `agents/workers/` | `tools/registry.py` | `execute_action()` |
| Any | `core/database.py` | `get_db()` |
| Any | `brain/memory/retrieval.py` | `store()` / `retrieve()` |

### Forbidden Patterns

1. **Workers importing routers.** Workers must never import from `web/`.
2. **Routers importing agents directly.** Must go through `jarvis.agents.jarvis.JarvisAgent`.
3. **Tools importing kings/workers.** Tools are stateless — no agent awareness.
4. **Memory bypassing the unified `retrieval.py` interface.** No direct database calls for memory operations.

---

## Verification Gates

Every module change must pass:

1. **Ownership check**: Does the change respect the ownership table?
2. **Boundary check**: Does it follow allowed cross-module calls?
3. **Duplication check**: Does it introduce or perpetuate duplication?

---

## Appendix: Removed Modules (v9.0.0)

| Module | Reason | Removal Date |
|---|---|---|
| `jarvis/architecture_graph/` | Dead code, no active dependencies | v9.0.0 |
| `jarvis/codebase_index/` | Dead code, no active dependencies | v9.0.0 |
| `jarvis/eng_intel/` | Dead code, no active dependencies | v9.0.0 |
| `jarvis/journal/` | Merged into `brain/memory/journal.py` | v9.0.0 |
| `jarvis/living_dashboard/` | Dead code, web app never imported it | v9.0.0 |
| `jarvis/projects/` | Dead code, no active dependencies | v9.0.0 |
| `jarvis/refactoring/` | Dead code, no active dependencies | v9.0.0 |
| `jarvis/repo_intelligence/` | Dead code, no active dependencies | v9.0.0 |
| `jarvis/suggestions/` | Dead code, no active dependencies | v9.0.0 |
| `jarvis/memory/` (root) | Duplicate of `brain/memory/` | v9.0.0 |
| `jarvis/planner/` | Dead code, no active dependencies | v9.0.0 |
| `jarvis/dashboard/` | Dead code, orphaned package | v9.0.0 |
| `jarvis/vision/` | Dead code, orphaned package | v9.0.0 |
| `brain/` (root) | Moved to `jarvis/brain/` | v9.0.0 |
| `config/` (root) | Moved to `jarvis/core/config.py` | v9.0.0 |
| `memory/` (root) | Duplicate, removed | v9.0.0 |
| `safety/` (root) | Duplicate of `jarvis/core/permissions.py` | v9.0.0 |
| `web/static/css/design-tokens.css` | Duplicated in style.css | v9.0.0 |
| `web/static/css/animations.css` | Unused | v9.0.0 |
| `web/static/css/mission-panel.css` | Unused | v9.0.0 |
| `web/static/css/memory-panel.css` | Unused | v9.0.0 |
| `web/static/js/graph3d.js` | Duplicate of graph-3d.js | v9.0.0 |
| `web/static/js/mission-panel.js` | Dead feature | v9.0.0 |
| `web/static/js/memory-panel.js` | Dead feature | v9.0.0 |
| `web/static/js/debug-patch.js` | Debugging leftover | v9.0.0 |
| `web/templates/command-map.html` | Unreachable route | v9.0.0 |
