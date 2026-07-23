# DAAS Agent Loop — Diagnose, Assemble, Take Action, Assess

## Overview

A structured agent execution loop for JARVIS where every user request goes through four phases:

```
DIAGNOSE → ASSEMBLE → TAKE ACTION → ASSESS
   ↑                                      |
   └──────────── if fails ────────────────┘
```

The goal: make JARVIS think before coding, research before building, and verify everything works.

---

## Current State

### What Exists (but is mostly stubs)

| Component | File | Status |
|---|---|---|
| AutonomousLoop | `jarvis/mission/loop.py` | 8 steps, all return hardcoded data |
| MissionPipeline | `jarvis/mission/pipeline.py` | 10 stages, research works, rest is stubs |
| LivingBrain | `jarvis/brain/loop.py` | Background loop, mostly empty |
| ResearchEngine | `jarvis/research/__init__.py` | GitHub search works via `gh` CLI |
| DiscoveryEngine | `jarvis/research/__init__.py` | Known tools database works |
| ToolRegistry | `jarvis/tools/registry.py` | 15+ tools registered |
| Diagnostics | `jarvis/core/diagnostics.py` | Startup health checks work |

### Key Gap

The plumbing is there, but nothing actually runs. The loops call methods that return fake results.

---

## Phase 1: DIAGNOSE

**Purpose:** Make sure the agent understands the task, direction, and problems before doing anything.

### What It Should Do

1. **Parse the user request** into structured goals, constraints, and success criteria using LLM
2. **Scan the existing codebase** to understand what we're working with (codebase-memory-mcp)
3. **Clarify ambiguity** — ask the user questions if the request is vague
4. **Identify dependencies** — what tools, libraries, APIs are needed
5. **Assess scope** — is this a 5-minute fix or a multi-hour project?

### Implementation Notes

- This is the **hardest part to get right** — most agents skip this and jump to coding
- Use the LLM (NVIDIA API) for structured parsing, not regex
- Should produce a `DiagnosisResult` with: goal, constraints, success_criteria, scope, risks
- If scope is too large, suggest breaking into sub-missions

### Files to Modify

- `jarvis/mission/loop.py` — rewrite `_observe` and `_understand` to use LLM
- `jarvis/mission/mission.py` — add `DiagnosisResult` dataclass

---

## Phase 2: ASSEMBLE

**Purpose:** Build a detailed work plan using research and tool discovery.

### What It Should Do

1. **Research online** including GitHub (find useful repos, libraries, patterns)
2. **Discover tools** that solve 80%+ of the problem (prefer mature tools over custom)
3. **Plan the architecture** — file-by-file, module-by-module
4. **Check existing codebase patterns** — don't invent new ones if old ones work
5. **Produce a detailed plan** with: files to modify, new files, dependencies, risks

### What Already Works

- `ResearchEngine._search_github()` — uses `gh search repos`, returns structured findings
- `DiscoveryEngine.discover()` — matches queries against known good tools
- `ToolRegistry.get_for_task()` — recommends tools by keyword matching

### What Needs Building

- LLM-powered planning that uses research findings to create a file-by-file plan
- Integration with codebase-memory-mcp to understand existing patterns
- Tool installation step (pip install, npm install, brew install)

### Implementation Notes

- The research step should be parallelized (search GitHub, PyPI, npm, docs simultaneously)
- Plans should be stored in the mission object for the assess phase to verify against
- Should reject tools that don't meet maturity/quality thresholds

### Files to Modify

- `jarvis/mission/pipeline.py` — rewrite `_stage_research`, `_stage_discover`, `_stage_plan`
- `jarvis/research/__init__.py` — add LLM-powered planning, fill in placeholder sources

---

## Phase 3: TAKE ACTION

**Purpose:** Actually execute the plan — write code, install tools, run commands.

### What It Should Do

1. **Execute step-by-step** — not all at once, one file at a time
2. **Write code** that follows existing codebase patterns
3. **Install dependencies** when needed
4. **Run shell commands** for build/test steps
5. **Produce verifiable output** — each step should have a clear "done" signal

### Implementation Notes

- Use `subprocess` + `asyncio` with timeout/resource limits (not Docker — too heavy for local)
- Each step should be atomic — if it fails, we can retry just that step
- Should have a **sandbox mode** where changes are staged but not committed
- Need to track which files were created/modified for rollback

### Safety Concerns

- Never execute arbitrary user code
- Limit shell command timeout to 60s
- Log all commands executed
- Don't modify files outside the project directory

### Files to Create/Modify

- `jarvis/mission/executor.py` — new: safe command execution engine
- `jarvis/mission/loop.py` — rewrite `_act` to use the executor

---

## Phase 4: ASSESS

**Purpose:** Verify the product works as expected, bugs are fixed, quality is good.

### What It Should Do

1. **Run tests** — pytest, npm test, etc.
2. **Lint and type check** — ruff, mypy, eslint
3. **Verify UI** — Playwright screenshots if applicable
4. **Check existing features** — run the v6.5.0 test suite to catch regressions
5. **Assess code quality** — style, error handling, documentation
6. **Loop back** if something fails — go to Take Action with fixes

### Quality Bar

- All existing tests must pass
- No new lint errors
- Code follows existing patterns
- UI renders correctly (if applicable)
- Error handling is present

### Implementation Notes

- Should produce a `AssessmentReport` with: tests_passed, tests_failed, lint_errors, issues_found
- If assessment fails, generate a "fix plan" and loop back to Take Action
- Maximum 3 retry loops to prevent infinite fixing
- Store lessons learned in memory for future missions

### Files to Modify

- `jarvis/mission/pipeline.py` — rewrite `_stage_verify`, `_stage_test`, `_stage_review`
- `jarvis/mission/loop.py` — rewrite `_verify` and `_reflect` to use real verification

---

## Integration Points

### How It Connects to JARVIS

1. **Chat → MissionPipeline** — user message triggers the loop
2. **ResearchEngine → GitHub** — `gh search repos` for finding solutions
3. **codebase-memory-mcp** — understand existing code patterns
4. **NVIDIA LLM** — structured reasoning at each phase
5. **ToolRegistry** — recommend and install tools
6. **Memory** — store lessons for future missions

### API Endpoints Needed

- `POST /api/mission/run` — start a mission with the DAAS loop
- `GET /api/mission/{id}/status` — check mission progress
- `GET /api/mission/{id}/report` — get final assessment report

---

## Implementation Order

### Phase 1: Foundation (do first)
1. Wire LLM into `_observe` and `_understand` (Diagnose)
2. Make research findings feed into planning (Assemble)
3. Add a basic LLM-powered planner

### Phase 2: Execution (do second)
4. Build safe command executor
5. Wire executor into `_act` (Take Action)
6. Track file changes for rollback

### Phase 3: Verification (do third)
7. Wire pytest/lint into `_verify` (Assess)
8. Add Playwright screenshot verification
9. Build the retry loop (Assess → Take Action)

### Phase 4: Polish (do last)
10. Add progress streaming to frontend
11. Store mission reports in memory
12. Add mission history UI

---

## Success Criteria

- User says "build me X" → JARVIS Diagnoses → Assembles plan → Takes Action → Assesses
- If assessment fails, it fixes issues automatically (up to 3 retries)
- Final report shows: what was built, tests passed, quality score
- All existing features still work after the mission

---

*Created: 2026-07-22*
*Status: Planning*
