# JARVIS V10 — Current Architecture (Phase A Audit)

> **Source of Truth:** `docs/JARVIS_V10_MASTER_PLAN.md`. This document records the **actual** current
> state of the codebase (v6.4/v9-era) as discovered by direct source audit, so V10 tool-system work
> can integrate cleanly **without breaking or duplicating** what already exists.
>
> **Audit method:** manual read of `jarvis/` (276 `.py` files), `tests/` (34 files), `pyproject.toml`,
> `Makefile`, `README.md`. No subagents (explore agents failed: ollama alias `gemma4:12b` missing).
> **No code changes were made during this audit.**

---

## 1. System at a Glance

| Aspect | Current State |
|---|---|
| Runtime | Python 3.11+ (local-first), FastAPI + uvicorn on `127.0.0.1:8000` |
| DB | async SQLite (`aiosqlite`), WAL mode, proxied `execute/executemany/executescript/commit` |
| Config | pydantic `BaseSettings` (`jarvis/core/config.py`) + `_secret()` helper via `SecretManager` |
| LLM | `jarvis/brain/llm.py`: httpx **direct** to NVIDIA OpenAI-compatible endpoint, Ollama fallback |
| Model routing | `jarvis/brain/model_router.py`: `TaskType` StrEnum + `ModelProfile` (EWMA latency/success) |
| Eventing | `jarvis/core/events.py`: async `EventBus` (wildcards, once-listeners, history, stats) |
| Agents | 4 Kings (♠ Engineering / ♥ Personal / ♦ Research / ♣ System) + workers; v10 domains parallel scheme |
| Architectures | `jarvis/architectures/`: `AgentArchitecture` ABC (plan/execute/observe/reflect/verify/remember/recall) + registry |
| Tool surface | `jarvis/tools/` knowledge registry + `Tool` facade + v6.3.0 `ToolResult`; computer actions via `controller` singleton |
| Permissions | Trinity (`jarvis/core/permissions.py`) + computer risk classifier (`jarvis/computer/permissions.py`) |
| Browser | `jarvis/browser/` — `BrowserManager` gateway + `PlaywrightProvider` (DOM-first) |
| Web search | `jarvis/computer/search.py` — `WebSearch` (DuckDuckGo HTML + `fetch_page`) |
| Frontend | Server-rendered templates + static JS; WebSocket `/ws` real-time event bus bridge |
| Tests | `tests/` flat, run via `python3 -m unittest` (Makefile: `tests.test_anchor`), pytest configured but not the Makefile default |

---

## 2. Tool System — Current State (CRITICAL: does NOT execute tools)

`jarvis/tools/` is a **knowledge/abstraction layer, not an execution engine**:

- **`registry.py`** — tool knowledge registry (`ToolCapability`, `ToolInfo`, `ToolRegistry`): declares what tools exist, their capabilities, categories. Purely declarative.
- **`models.py`** — declarative tool metadata models.
- **`result.py`** — v6.3.0 `ToolResult` dataclass + `timed()` decorator + error capture. **This is the result contract the codebase already uses.**
- **`unified.py`** — `Tool` facade that **lazy-loads managers by name** (computer → `controller`, browser → `BrowserManager`, etc.) and dispatches to them. Single public entry point for "give me a tool".
- **`agent_tools.py`** — `FileSystemTools` (list/read/write/search) with `_resolve_path` traversal guard.

### Who uses tools today

- `jarvis/agents/workers/base.py` — `get_tools()` returns the **`controller`** object; `_extract_tool_calls` parses bracket/JSON tool syntax from LLM output.
- `jarvis/agents/workers/research.py` (♦Q WebResearchWorker) — `[TOOL: navigate/search/extract/click/type/scroll/back/get_text(...)]` bracket syntax driving `BrowserManager`.
- `jarvis/web/routers/computer.py` — `POST /api/computer/action` maps flat action names → permissions → `controller`.

### Gap for V10

There is **no unified executor loop**: no per-step iteration cap, no structured step timeout,
no kill-switch check, no before/after screenshot hook, no LEVEL-0..3 gate at the execution boundary.
`jarvis/core/reliability.py` already exposes `ReliabilityConfig` with `max_tool_iterations: int = 5`
— the natural seam for V10's `MAX_TOOL_STEPS = 20`.

---

## 3. Permission System — Current State (two parallel systems)

### 3a. Trinity (`jarvis/core/permissions.py`)
- `permission_center` singleton; `TrinityState` = ALLOW / ASK / DENY; time-based grants.
- 12 capabilities (chat, files, terminal, browser, screen, apps, email, memory, search, network, system, settings).
- Used by the web/API layer via `permission_center.check_required(...)`.

### 3b. Computer risk classifier (`jarvis/computer/permissions.py`)
- `RiskLevel`: safe / low / medium / high / dangerous.
- `RESTRICTED_PATHS`, `DANGEROUS_COMMANDS`, per-action risk classification.
- `jarvis/computer/actions.py` — `ActionStatus`, `ActionType`, `ActionResult`; `controller._ACTION_RISKS` maps flat action names → risk levels.
- `jarvis/computer/manager.py` — `ComputerManager` central gateway: Agent → Manager → Permission check → Execution → Logging → DB → Event.

### V10 mapping
V10 LEVEL 0 (SAFE) / 1 (LOW_RISK) / 2 (CONFIRMATION) / 3 (HIGH_RISK) must be implemented as a thin,
**compatible layer over both existing systems** — not a third parallel system. LEVEL ↔ RiskLevel and
LEVEL ↔ Trinity capability tables must be explicit and documented.

---

## 4. Computer Control — Current State

`jarvis/computer/` is a complete, layered computer-control stack:

| File | Role |
|---|---|
| `actions.py` | `RiskLevel`, `ActionStatus`, `ActionType`, `ActionResult` |
| `permissions.py` | risk classifier, `RESTRICTED_PATHS`, `DANGEROUS_COMMANDS` |
| `controller.py` | **`controller` singleton facade** — flat action names, `_ACTION_RISKS` map, one entry point |
| `manager.py` | `ComputerManager` — the actual execution engine (permission → run → log → event) |
| `mouse.py` / `screen.py` / `browser.py` | macOS-native primitives (pyautogui/Quartz/AppKit surface) |
| `search.py` | `WebSearch` (DDG HTML + fetch_page), `web_search` singleton |
| `providers/` | platform abstraction (macOS provider) |

Note: `computer/browser.py` and `browser/manager.py` are **separate browser stacks** (see §5).

---

## 5. Browser Automation — Current State

`jarvis/browser/` is the V10-correct browser stack (DOM-first Playwright):

- **`manager.py`** — `BrowserManager` central gateway: BrowserState, extractor, security, session manager; emits events on completion.
- **`playwright_provider.py`** — `PlaywrightProvider` wrapping `async_playwright`; `BrowserResult(ok/data/error, to_dict())`.

`jarvis/computer/browser.py` exists as a separate (computer-control-flavored) browser helper — flag for
unification/review, but **do not delete** without confirming callers.

---

## 6. Web Access — Current State

- `WebSearch.search(query, engine="duckduckgo", max_results)` → DDG HTML scraping (no API key).
- `WebSearch.fetch_page(url, max_chars=8000)` → HTML→text extraction.
- **No provider abstraction today** — V10 requires `WebSearchProvider` interface so providers are swappable.
- Prompt-injection risk: `fetch_page` returns untrusted web content straight to the LLM context.

---

## 7. Task State / Execution Loop — Current State

- `jarvis/architectures/base.py` — `Plan`/`PlanStep`/`ExecutionResult`/`MissionContext` + `AgentArchitecture` ABC (plan → execute → observe → reflect → verify) + `ArchitectureRegistry` (hermes/native implementations).
- `jarvis/projects/task_flow.py` — v9 M2 task routing (`route_task`) for task/project intents.
- **No V10 `Task` model** (QUEUED/RUNNING/WAITING_FOR_CONFIRMATION/COMPLETED/FAILED/CANCELLED) and **no central kill switch** — this is net-new V10 work (`jarvis/tasks/task.py`).
- Timeouts exist in `jarvis/core/reliability.py` (`task_timeout=300.0`); a watchdog hook exists but is not wired to a task lifecycle.

---

## 8. Web Layer — Current State

- `jarvis/web/main.py` — `initialize_agents()` creates `JarvisAgent` + 4 Kings + `domain_registry`.
- `routers/chat.py` — `POST /api/chat` (rate_limit 15/60s), InteractionLayer intent classification, v9 task_flow routing, workspace auto-create.
- `routers/computer.py` — `POST /api/computer/action` (rate_limit 5/30s), `action_permissions` map, `permission_center.check_required`.
- `routers/websocket.py` — `_clients` set, `_event_history` ring buffer (MAX 100), `_bridge_tasks`, `EVENT_LABELS`.
- `rate_limit.py` — reusable `@rate_limit(max_requests, window_seconds)` decorator.

---

## 9. Recommended V10 Integration Points (build alongside, never overwrite)

1. **`jarvis/tools/base.py`** (NEW) — `Tool` protocol + `ToolSpec`/`ToolResult`/`ToolError`. Align `ToolResult` with the existing v6.3.0 `jarvis/tools/result.py` contract (field-compatible) so old callers keep working.
2. **`jarvis/tools/registry.py`** — extend the *existing* `ToolRegistry` with `execute()` dispatch; register V10 tools (computer, browser, search, filesystem) via the existing `Tool` facade naming convention.
3. **`jarvis/tools/executor.py`** (NEW) — the loop: read `ReliabilityConfig.max_tool_iterations`/`task_timeout`, enforce `MAX_TOOL_STEPS=20` override, per-step timeout, cancellation via kill switch, structured errors, before/after screenshot hooks.
4. **`jarvis/tools/permissions.py`** (NEW) — `PermissionManager` mapping LEVEL 0–3 → existing Trinity capabilities + computer `RiskLevel`. Delegates to `permission_center` and risk classifier; never re-implements policy.
5. **`jarvis/tasks/task.py`** (NEW) — `Task` state model + `TaskManager` + global kill switch; emit `task.*` events through existing `event_bus`.
6. **`jarvis/tools/web_search.py`** (NEW) — `WebSearchProvider` ABC; adapt existing `WebSearch` (DDG) as first provider; `fetch_page` output goes through prompt-injection sanitization before reaching LLM.
7. **Browser tools** — wrap the existing `BrowserManager` (DOM-first); do **not** build a second Playwright stack.

---

## 10. Do-Not-Change List (existing functionality to preserve)

- `jarvis/core/events.py` `event_bus` — central pub/sub; new code must use it.
- `jarvis/core/permissions.py` `permission_center` — Trinity state machine; V10 maps onto it.
- `jarvis/computer/controller.py` singleton + `_ACTION_RISKS` — existing API surface used by workers and web.
- `jarvis/tools/result.py` `ToolResult`/`timed` — v6.3.0 contract; V10 `ToolResult` must remain field-compatible.
- `jarvis/web/routers/*` endpoints + rate limits — existing API contract.
- `jarvis/agents/workers/*.py` `get_tools()` + `_extract_tool_calls` — prompt/tool-call contract; extend, don't replace.
- `Makefile` `test` target (`python3 -m unittest tests.test_anchor -v`) — keep green; new tests added as unittest modules (pytest config exists but is not the Makefile default).
- README/version claims — do not bump version or rewrite README during Phase 1.

---

## 11. Duplicate / Legacy Code Identified (do NOT delete; flag for V10 decision)

| Item | Status | Recommendation |
|---|---|---|
| `jarvis/tools/unified.py` `Tool` facade vs new `base.py` | partial overlap | V10 `base.py` supersedes; keep facade as compat shim |
| `jarvis/computer/browser.py` vs `jarvis/browser/manager.py` | **two browser stacks** | V10 standardizes on `jarvis/browser/`; audit callers before deprecating computer/browser.py |
| Trinity + RiskLevel + V10 LEVELs | three permission vocabularies | V10 PermissionManager maps all three; no new vocabulary |
| `architectures/` Plan/MissionContext vs new `tasks/task.py` | adjacent | Task model is lifecycle state; Architectures remain planning/execution strategy — keep separate, wire via events |
| stale `pyproject.toml` version "8.0.0" vs README "v6.4.0" | docs drift | leave for V10 final release; do not touch during Phase 1 |
| pytest config in pyproject vs unittest in Makefile | tooling drift | add V10 tests as unittest modules for Makefile compatibility |

---

## 12. Risks / Gaps for Phase 1

1. **No unified executor** — tool calls today are fire-and-forget per-worker; V10 executor is the core new component.
2. **macOS accessibility permission** unknown for screen/mouse on this machine — real-screen tests (PHASE N) may be skipped with evidence if permission not granted.
3. **Prompt injection** — `fetch_page`/browser-extracted content reaches LLM context unsanitized today.
4. **Two browser stacks** — must not create a third.
5. **Subagent tooling broken** (ollama alias) — all future audit/exploration must be manual or fixed tooling; do not depend on subagents.
6. **`max_tool_iterations=5`** default is lower than V10 spec `MAX_TOOL_STEPS=20` — executor must read env override, default to spec value.
