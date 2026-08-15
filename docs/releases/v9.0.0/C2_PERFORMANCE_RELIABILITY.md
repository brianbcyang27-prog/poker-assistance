# C2 — Performance & Reliability

> Phase: Foundation
> Date: 2026-07-30
> Status: Planning
> Dependencies: C1 (Instant Startup)

## Overview

C1 made JARVIS start instantly. C2 makes it stay performant and reliable — fixing the problems that show up after 5 minutes of use: unbounded missions, invisible permission decisions, no safety net before dangerous actions, and unnecessary startup costs for infrequent subsystems.

Two tracks, parallel:

```
C2
├── 🟢 Performance Track (P0-P5)
│   ├── P0: Pre-warm LLM on idle
│   ├── P1: Pre-compile agent templates
│   ├── P2: Lazy-load voice router
│   ├── P3: Lazy-load architecture registry
│   └── P5: Startup metrics dashboard
│
└── 🟡 Reliability Track
    ├── R1: Mission budgets (step limits + timeouts)
    ├── R2: Permission audit trail
    └── R3: Pre-action snapshots
```

---

## 🟢 Performance Track

### P0 — Pre-warm LLM on idle

**Currently**: First chat call pays the ~5s Ollama probe. C1 made this lazy (deferred from startup), but the penalty hits the first user interaction.

**Fix**: After server startup, schedule an async background task that calls `llm.is_available()` once so the first user interaction is fast.

**File**: `jarvis/web/main.py` — add a background `prewarm_llm()` task after `yield`
**Effort**: ~30 min

```python
async def _prewarm_llm():
    """Trigger the one-time Ollama probe in background."""
    from jarvis.brain.llm import llm

    available = await llm.is_available()
    log.info("LLM pre-warm complete: available=%s", available)
```

### P1 — Pre-compile agent templates

**Currently**: Agent system prompts are rendered from Jinja2 templates at agent creation time during startup. This adds ~0.5s per agent (76 agents).

**Fix**: Render all agent templates at build/install time. Store as cached Python strings loaded at import time. Tradeoff: requires a build step, but startup is faster.

**Alternative (lighter)**: Cache the rendered prompts in a module-level dict after first render. On subsequent startups, load from cache.

**Files**: `jarvis/agents/*/`, `jarvis/web/templates/agents/`
**Effort**: ~2h for cache approach

### P2 — Lazy-load voice engine

**Currently**: `voice_engine.load()` runs at startup (line 250 in `web/main.py`), importing Piper/Kokoro/OpenAI TTS providers even if voice is never used.

**Fix**: Defer `voice_engine.load()` to first voice API call. The `voice_engine` singleton stays created (cheap), but `load()` (which downloads models) runs on demand.

**File**: `jarvis/web/services/tts.py` — make `load()` lazy
**Effort**: ~1h

### P3 — Lazy-load architecture registry

**Currently**: `JarvisNativeArchitecture.initialize()` and `HermesArchitecture.initialize()` run at startup. These register architectures that may never be used.

**Fix**: Register architectures lazily — store the class/factory, call `initialize()` on first `get_architecture()` or `list_architectures()`.

**Files**: `jarvis/web/main.py` (lines 196-231), `jarvis/architectures/`
**Effort**: ~2h

### P5 — Startup metrics dashboard

**Currently**: `StartupTimer` records timing but only exposes via `/api/system/startup-timing` JSON. No visual representation.

**Fix**: Add a startup-time card to the developer dashboard (`/dashboard`) showing:
- CLI launch time
- Server ready time
- First AI response time
- First voice response time
- Total time from CLI to first response
- Comparison vs previous startup

**Files**: `jarvis/web/templates/developer_dashboard.html`, `jarvis/web/static/js/app.js`
**Effort**: ~2h

---

## 🟡 Reliability Track

### R1 — Mission budgets (step limits + timeouts)

**Currently**: Missions can run forever. `MissionExecutor.execute_mission()` loops `while True` with no step cap, no wall-clock timeout, no watchdog. `DAGPlanner` has `_max_missions = 50` but it is never enforced.

**Fix**:

1. **Add `MissionBudget` dataclass** to `jarvis/brain/mission_executor.py`:
   ```python
   @dataclass
   class MissionBudget:
       max_steps: int = 100  # max DAG nodes to process
       max_duration_s: int = 600  # wall-clock timeout (10 min default)
       max_cost: float = 0.0  # future: token budget
   ```

2. **Wire into `execute_mission()`**: Track step count and elapsed time. Raise `MissionBudgetExceeded` if exceeded.

3. **Expose via `create_and_execute()`**: Accept optional `budget` parameter. Default to sensible limits.

4. **Emit events**: On budget exceeded, emit `mission.budget_exceeded` event with details.

5. **Add cancellation propagation**: `MissionManager.cancel()` currently marks failed but doesn't interrupt in-flight tasks. Wire `asyncio.Task.cancel()` into the running executor.

**Files**: `jarvis/brain/mission_executor.py`, `jarvis/brain/dag_planner.py`, `jarvis/mission/manager.py`, `jarvis/core/events.py`
**Effort**: ~4h

### R2 — Permission audit trail

**Currently**: `PermissionCenter` logs state changes via `log.info()` only. No append-only audit log. No per-decision trail for allow/deny/grant/revoke. The separate `security/audit.py` only covers secret operations.

**Fix**:

1. **Add `PermissionAuditEntry` dataclass** to `jarvis/core/permissions.py`:
   ```python
   @dataclass
   class PermissionAuditEntry:
       id: str
       timestamp: float
       permission_name: str
       action: str  # "check", "grant", "revoke", "set_state"
       result: str  # "allow", "deny", "ask"
       detail: str  # caller context, duration if grant
   ```

2. **Add in-memory ring buffer** (last 1000 entries) to `PermissionCenter`.

3. **Persist to SQLite** on write (async, non-blocking).

4. **Wire audit into every `check()`, `set_state()`, `grant()`, `revoke_grant()`**.

5. **Expose via API**: `GET /api/settings/permissions/audit?limit=50`.

6. **Add web UI panel**: Show recent decisions in Settings → Permissions.

**Files**: `jarvis/core/permissions.py`, `jarvis/web/routers/settings.py`, `jarvis/core/database.py`
**Effort**: ~4h

### R3 — Pre-action snapshots

**Currently**: `ComputerController._write_file()`, `_create_file()`, and `_shell_execute()` execute potentially destructive operations with no pre-action state saving. If a write command corrupts a file, there's no automatic rollback.

**Fix**:

1. **Wire `CheckpointManager` into `ComputerController`**: Before each `_write_file`/`_create_file` call, create a file checkpoint.

2. **For shell commands**: Create a workspace checkpoint before executing commands that modify files (detected by keywords: `rm`, `mv`, `cp`, `dd`, `>`, `|`).

3. **Add `undo` capability**: After a dangerous action completes (success or failure), the system can offer "Undo this change" which restores the checkpoint.

4. **Auto-cleanup**: After 1 hour, delete checkpoints for successful non-destructive operations.

**Files**: `jarvis/computer/controller.py`, `jarvis/core/checkpoint.py`
**Effort**: ~3h

---

## Files Changed Summary

| File | Change | Effort |
|------|--------|--------|
| `jarvis/web/main.py` | P0: add background LLM pre-warm task | ~30min |
| `jarvis/web/main.py` | P3: lazy architecture init | ~2h |
| `jarvis/agents/*/` | P1: template caching | ~2h |
| `jarvis/web/services/tts.py` | P2: lazy voice engine load | ~1h |
| `jarvis/web/templates/developer_dashboard.html` | P5: startup metrics card | ~1h |
| `jarvis/web/static/js/app.js` | P5: metrics visualization | ~1h |
| `jarvis/brain/mission_executor.py` | R1: MissionBudget, step caps, timeout | ~3h |
| `jarvis/brain/dag_planner.py` | R1: enforce max_missions, cancellation | ~1h |
| `jarvis/mission/manager.py` | R1: cancel → propagate to in-flight tasks | ~1h |
| `jarvis/core/permissions.py` | R2: audit entries, ring buffer, persistence | ~3h |
| `jarvis/web/routers/settings.py` | R2: audit API endpoint | ~30min |
| `jarvis/core/database.py` | R2: audit table | ~30min |
| `jarvis/computer/controller.py` | R3: pre-action checkpoints | ~2h |
| `jarvis/core/checkpoint.py` | R3: shell command detection, cleanup | ~1h |
| `jarvis/web/static/css/style.css` | P5+R2: metrics card + audit panel styles | ~1h |
| **Total** | | **~22h** |

---

## Success Criteria

### Performance Gate
- [ ] First chat response after cold start: no 5s Ollama probe penalty
- [ ] Server startup: architecture init doesn't block serve
- [ ] Voice engine loads on first voice API call, not at server start
- [ ] Developer dashboard shows startup timing breakdown
- [ ] Auto-agent-state loaded from cache

### Reliability Gate
- [ ] Mission hits step limit → emits `mission.budget_exceeded` → stops gracefully
- [ ] Mission exceeds wall-clock timeout → same clean stop
- [ ] Cancel actually stops the running task (not just marks failed)
- [ ] Permission check/grant/revoke creates an audit entry
- [ ] Audit API returns last N decisions with timestamps
- [ ] Dangerous file write creates pre-action checkpoint
- [ ] Checkpoint restore returns file to pre-action state

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM pre-warm during high CPU startup | Low | Low | Schedule with 5s delay, catch errors silently |
| Mission budget kills legitimate long missions | Medium | Medium | Start with generous defaults (100 steps, 10 min). Configurable. |
| Audit SQLite writes slow down permission checks | Low | Medium | Ring buffer first, flush async. Sync flush only on critical. |
| Checkpoint overhead on file writes | Low | Low | Async copy. Only for files > threshold (1KB). |
| Template caching on first startup doesn't help first run | Certain | Low | Cache primes on installation. First startup still benefits from cache. |

---

*Part of JARVIS v9.0.0 Foundation Phase — Continues from C1 Instant Startup*
