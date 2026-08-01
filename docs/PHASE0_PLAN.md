# Phase 0 Execution Plan

> **Version:** 1.0.0
> **Date:** 2026-07-30
> **Base:** JARVIS VISION_RESET.md · ARCHITECTURE_VALIDATION_REPORT.md · SYSTEM_DEPENDENCY_MAP.md
> **Goal:** Remove dead code, consolidate duplicates, eliminate conflicting architectures, simplify the codebase — while preserving all working functionality.

---

## Guiding Principles

1. **Never delete without confirming no active dependency.**
2. **Every change must be tested and verified.** After each task: `lsp_diagnostics` → run tests → manual check.
3. **Minimal change per commit.** One logical deletion per commit, easy to revert.
4. **Phase 0 is removal-first.** Refactoring (KEEP/REFACTOR/MERGE) is Phase 1+.
5. **Order by risk:** Safe deletions first (dead CSS/JS) → orphan Python packages → legacy root modules → overlapping systems.

---

## Task Sequencing

```
Priority: Impact × Risk
   High Impact / Low Risk  ───>  Do first
   High Impact / High Risk  ───>  Do carefully
   Low Impact / Low Risk    ───>  Do anytime
   Low Impact / High Risk   ───>  Consider skipping
```

---

## TASK 1: Remove Dead CSS Files

**Files to delete:**
- `web/static/css/design-tokens.css` (~800 lines, duplicated in style.css)
- `web/static/css/animations.css` (~700 lines, unreferenced)
- `web/static/css/mission-panel.css` (~427 lines, unreferenced)
- `web/static/css/memory-panel.css` (~400 lines, unreferenced)

**Why:** These CSS files are never imported (`grep -r` confirms zero references outside themselves). Their content is either duplicated in the monolithic `style.css` (6,457 lines) or dead. Removing them clears ~2,327 lines immediately.

**Expected user impact:** None — no page will look different.

**Risks:** Minimal. If somehow referenced dynamically, page styling breaks slightly.
- Verify with: `grep -r "design-tokens\|animations\|mission-panel\|memory-panel" --include="*.html" --include="*.js" --include="*.css"`

**Rollback:** `git checkout -- <files>`

**Verification:**
1. `grep` confirms no references
2. `lsp_diagnostics` on changed area (N/A for CSS)
3. Load `/` and `/dashboard` in browser — visually verify

**Estimated time:** 15 minutes

---

## TASK 2: Remove Duplicate JS File

**Files to delete:**
- `web/static/js/graph3d.js` (~500 lines)

**Why:** Duplicate of `graph-3d.js`. In-tree, only `app.js` references `graph-3d.js`. No imports reference `graph3d.js` (confirmed by grep).

**Expected user impact:** None — `graph3d.js` is not the active file.

**Risks:** Minimal.
- Verify: `grep -r "graph3d" --include="*.html" --include="*.js"` should return zero matches (excluding the file itself).

**Rollback:** `git checkout -- web/static/js/graph3d.js`

**Verification:**
1. `grep` confirms zero external references
2. Load home page — 3D neural core still renders

**Estimated time:** 5 minutes

---

## TASK 3: Remove Dead JS Files

**Files to delete:**
- `web/static/js/mission-panel.js` (dead, unused)
- `web/static/js/memory-panel.js` (dead, calls missing Hermes API)
- `web/static/js/debug-patch.js` (debug-only patcher, not for production)

**Why:** These files have zero production references. The features they supported either don't exist (Hermes memory API) or were superseded.

**Expected user impact:** None.

**Risks:** Minimal.
- Verify: `grep -r "mission-panel\|memory-panel\|debug-patch" --include="*.html" --include="*.js"`

**Rollback:** `git checkout -- <files>`

**Verification:**
1. `grep` confirms zero external references
2. Load `/` and `/dashboard` — verify no console errors

**Estimated time:** 10 minutes

---

## TASK 4: Remove Unreachable HTML Template

**Files to delete:**
- `web/templates/command-map.html` (~50 lines)

**Why:** Only route to this template is `/command-map` in `pages.py`, which is unreachable from the UI (no link or navigation target). Template references missing assets.

**Expected user impact:** None — no user can reach this page through normal navigation.

**Risks:** Minimal.

**Also fix:** Remove the `/command-map` route from `routers/pages.py` (delete or comment the route handler).

**Rollback:** `git checkout -- <files>`

**Verification:**
1. Check `/command-map` returns 404
2. Verify no links to `/command-map` in templates/JS

**Estimated time:** 10 minutes

---

## TASK 5: Remove Orphaned Python Packages (Safe Batch)

**Packages to delete:** These have **zero active production imports**. Only self-imports and test files reference them.

| Package | Files | Lines |
|---------|-------|-------|
| `architecture_graph/` | 4 | ~680 |
| `living_dashboard/` | 3 | ~270 |
| `projects/` | 2 | ~540 |
| `journal/` (root) | 2 | ~410 |
| `suggestions/` | 2 | ~390 |
| `eng_intel/` | 3 | ~670 |
| `codebase_index/` | 4 | ~750 |
| `repo_intelligence/` | 3 | ~985 |
| `refactoring/` | 3 | ~710 |
| `planner/` (empty) | 1 | ~50 |
| `memory/` (empty stub) | 1 | ~1 |

Also remove their corresponding test files:
- `tests/test_eng_intel.py`
- `tests/test_refactoring.py`
- `tests/test_repo_intelligence.py`
- `tests/test_architecture_graph.py` (if exists)

**Why:** These packages are dead code. They bloat the codebase by ~5,400 lines, create confusion (what's active vs. abandoned), and add module resolution overhead. The vision demands a lean, maintainable system.

**Expected user impact:** None (if confirmed no active imports).
- **Partial risk:** `living_dashboard/` has a 3rd-party import via `tests/test_living_dashboard.py` — if that test references any module that imports `living_dashboard`, removal could break the test. Check first.

**Verification of zero-dependency (per package):**
```python
# For each package: confirm the only imports are self-references
grep -r "from jarvis\.\(architecture_graph\|living_dashboard\|projects\|journal\|suggestions\|eng_intel\|codebase_index\|repo_intelligence\|refactoring\)" --include="*.py" jarvis/
# Should return ZERO results (minus __init__.py self-imports)
```

**Also check:** `grep -r "architecture_graph\|living_dashboard\|projects\|journal\|suggestions\|eng_intel\|codebase_index\|repo_intelligence\|refactoring\|planner\|memory" --include="*.py" --include="*.md" --include="*.toml" --include="*.cfg" --include="*.ini" --include="*.json" .`

**Note:** The root `memory/` check must be careful — `grep` for `from jarvis\.memory` will match `jarvis/brain/memory/`. Use `from jarvis\.memory\b` or `import jarvis.memory` and exclude `jarvis/brain/memory/`.

**Rollback:** `git checkout -- <deleted-package-dir>` per-package, or `git revert <commit-hash>`.

**Verification:**
1. Import test: `python -c "from jarvis.web.main import app; print('OK')"` — must succeed
2. Run pytest core tests: `pytest tests/test_memory.py tests/test_core.py tests/test_database.py tests/test_v630.py -q`
3. Run server: `python -m jarvis.web.main` — must start with all checks passing

**Estimated time:** 30 minutes (per package), ~3h total

---

## TASK 6: Remove Legacy Root-Level Modules

**Files to delete:**
- `/brain/` (legacy — 5 files, ~300 lines)
- `/config/` (legacy — 2 files, ~150 lines)
- `/memory/` (legacy — already empty stub above)
- `/safety/` (legacy — 2 files, ~100 lines)

**Why:** These are top-level modules that predate the `jarvis/` package structure. They are entirely superseded by their `jarvis/` equivalents and add only confusion.

**Verification of zero-dependency:**
```bash
grep -r "from brain\|from config\|from memory\|from safety\|import brain\|import config\|import memory\|import safety" --include="*.py" jarvis/
grep -r "from brain\|from config\|from memory\|from safety\|import brain\|import config\|import memory\|import safety" --include="*.py" tests/
```

**Expected user impact:** None.

**Risks:** Low — modern imports all go through `jarvis.brain`, `jarvis.core.config`, `jarvis.brain.memory`, `jarvis.security`.

**Rollback:** `git checkout -- <file-path>`

**Verification:**
1. Python import test: `python -c "from jarvis.web.main import app"` — must succeed
2. Run tests: `pytest tests/test_memory.py tests/test_core.py -q`

**Estimated time:** 15 minutes

---

## TASK 7: Fix Broken Frontend-Backend Contracts

### 7a: Fix `/api/sessions` → `/api/chat/sessions`
**Files:**
- `web/static/js/app.js` — change `fetch("/api/sessions")` to `fetch("/api/chat/sessions")`

**Why:** Frontend calls an old API path that doesn't exist. The actual endpoint lives at `/api/chat/sessions`.

**Expected user impact:** If any UI element navigates sessions, it will start working.

**Risks:** Low — backend endpoint already exists.

**Verification:** Check `/api/chat/sessions` returns 200. Check frontend no longer logs 404 for this path.

### 7b: Fix `/api/system/dag` (Add DAG endpoint or remove call)
**Files:**
- `web/static/js/mission-dag.js` — remove the DAG fetch call, or add a backend endpoint

**Why:** Frontend calls `/api/system/dag` which returns 404. This shows a broken UI element.

**Recommendation:** Remove the call from `mission-dag.js` (it's a broken visualization, not a core feature). Add a stub endpoint later if needed.

**Risks:** Low — removing a broken call fixes a console error.

### 7c: Remove Hermes architecture memory call
**Files:**
- `web/static/js/memory-panel.js` (already slated for removal in TASK 3 — this resolves it)

### 7d: Add `/api/voice/generate` or remove frontend call
**Files:**
- Check frontend JS for this call — if it's in a dead code path, it'll be handled naturally
- If in active code, add a stub endpoint to `routers/voice.py`

### 7e: Fix `/api/computer/actions` — return dynamic action list
**Files:**
- `routers/computer.py` — replace static list with dynamic enumeration from `computer/controller.py` or `computer/manager.py`

**Estimated time (all of Task 7):** 2 hours

---

## TASK 8: Merge Overlapping Systems (Phase 1 Preparation)

These tasks identify consolidation points but **do not execute the merge** — the actual merge is Phase 1 work. Phase 0 merely documents the plan and adds TODO markers.

### 8a: `tools/unified.py` vs `agents/tools.py`
- **Current state:** Both manage tool execution. `agents/tools.py` has the older `ToolExecutor`; `tools/` is the newer unified layer.
- **Phase 0 action:** Confirm migration path, add `DEPRECATED` marker to `agents/tools.py`
- **Verification:** No active callers remain via `grep -r "ToolExecutor" --include="*.py" jarvis/`

### 8b: `mission/` vs `workspace/` vs `brain/mission_executor.py`
- **Current state:** Three overlapping systems for mission/workspace management.
- **Phase 0 action:** Document the overlap, note the canonical entry point (`mission/` is the most complete)
- **No code changes** — defer to Phase 1.

### 8c: `knowledge/` (root) → merge into `brain/memory/`
- **Current state:** `knowledge/` provides graph models imported by `brain/core/memory.py`
- **Phase 0 action:** Move models into `brain/memory/graph.py`, update import
- **Impact:** Minimal — affects 2 import statements

---

## Summary Execution Order

| Order | Task | Est. Time | Risk | Impact |
|-------|------|-----------|------|--------|
| 1 | Remove dead CSS (4 files) | 15min | 🟢 None | ~2,327 lines removed |
| 2 | Remove duplicate JS (1 file) | 5min | 🟢 None | ~500 lines removed |
| 3 | Remove dead JS (3 files) | 10min | 🟢 None | ~1,300 lines removed |
| 4 | Remove unreachable template + route | 10min | 🟢 None | ~50 lines removed |
| 5 | Remove orphaned Python packages (11) | 3h | 🟡 Low | ~5,400 lines removed |
| 6 | Remove legacy root modules (4) | 15min | 🟢 None | ~550 lines removed |
| 7 | Fix frontend-backend contract breaks | 2h | 🟡 Low | Fixes 5 bugs |
| 8 | Merge prep (documentation + markers) | 30min | 🟢 None | Documents Phase 1 |
| **Total Phase 0** | | **~6.5h** | | **~10,000+ lines removed** |

---

## Verification Checklist (Run After All Tasks)

```bash
# 1. LSP diagnostics — no import errors
python -c "from jarvis.web.main import app"

# 2. Server starts
python -m jarvis.web.main &
sleep 3

# 3. Health endpoint
curl http://127.0.0.1:8000/api/system/health

# 4. Core pages load
curl -o /dev/null -s -w "%{http_code}" http://127.0.0.1:8000/
curl -o /dev/null -s -w "%{http_code}" http://127.0.0.1:8000/dashboard

# 5. API endpoints respond
curl -o /dev/null -s -w "%{http_code}" http://127.0.0.1:8000/api/agents
curl -o /dev/null -s -w "%{http_code}" http://127.0.0.1:8000/api/system/health

# 6. Run core tests (skip known-hanging ones)
pytest tests/test_memory.py tests/test_database.py tests/test_core.py -q

# 7. Kill server
kill %1
```
