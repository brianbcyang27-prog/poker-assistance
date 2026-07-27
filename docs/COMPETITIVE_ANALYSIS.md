# JARVIS Competitive Analysis — July 2026

> Gap analysis against 6 major AI coding agent platforms
> Compiled from deep research on Claude Code, Cursor, OpenHands, Devin, Manus, Roo Code, Cline

---

## Executive Summary

JARVIS occupies a unique position: it's a **personal AI OS** (full computer control, IoT, voice, memory), not just a coding agent. The competitors below are mostly coding-focused. The key gap is **reliability and safety infrastructure**, not features.

| Dimension | JARVIS | Industry Leader | Gap |
|-----------|--------|-----------------|-----|
| Feature breadth | ★★★★★ | — | JARVIS leads (OS, IoT, voice, engineering) |
| Safety / permissions | ★★☆☆☆ | Claude Code (7-mode + ML classifier) | **CRITICAL** |
| Reliability / error handling | ★★★☆☆ | Cursor (BugBot, checkpoints) | **HIGH** |
| Context management | ★★★☆☆ | Claude Code (5-layer compaction) | HIGH |
| Multi-agent coordination | ★★★☆☆ | Claude Code (agent teams, worktrees) | MEDIUM |
| UX polish | ★★★☆☆ | Cursor (Agents Window, diffs) | MEDIUM |
| Code review / verification | ★★☆☆☆ | Cursor (BugBot + autofix) | HIGH |

---

## 1. Claude Code — The Gold Standard for Safety

### What It Does Best
- **7 permission modes** including ML classifier that evaluates every tool call with chain-of-thought reasoning
- **Hooks that can't be bypassed** — even `--dangerously-skip-permissions` respects policy hooks
- **5-layer context compaction** — budget reduction → snip → microcompact → context collapse → auto-compact
- **Sub-agents with sidechain transcripts** — parent context never polluted by child verbosity
- **Deferred tool loading** — model discovers tools on demand, keeping context lean
- **Agent teams** — lead + teammates with shared task list and direct inter-agent messaging

### What JARVIS Should Adopt

| Pattern | Description | Priority |
|---------|-------------|----------|
| **ML classifier for permissions** | LLM evaluates tool calls before execution instead of blocklists | HIGH |
| **Unbypassable hooks** | Policy hooks fire in every mode — no escape hatch | HIGH |
| **Sidechain transcripts** | Sub-agent verbosity isolated, only summaries propagate | MEDIUM |
| **Deferred tool loading** | Keep context lean; model explicitly fetches tools | MEDIUM |
| **5-layer compaction** | Progressive context reduction instead of hard truncation | HIGH |

---

## 2. Cursor — The Gold Standard for UX

### What It Does Best
- **3-stage Composer pipeline** — Indexer → Planner → Apply Model with speculative decoding (multi-file edits feel atomic)
- **Agents Window** — replaces chat with project management UI (task cards with status progression)
- **BugBot** — auto PR review with learned rules from 110K+ repos, self-improving from feedback
- **Background agents** — async VMs with full dev environments, triggered from IDE/Slack/GitHub/mobile
- **Race pattern** — dispatch same task to multiple models in parallel, pick best result
- **Always-on indexer** — incremental embeddings on every file save

### What JARVIS Should Adopt

| Pattern | Description | Priority |
|---------|-------------|----------|
| **Agents Window** | Task cards with Planning → Executing → Reviewing → Done | HIGH |
| **Checkpoints** | Snapshots before significant changes, easy rollback | HIGH |
| **Speculative file edits** | Use original as draft for apply model (10x speedup) | LOW (future) |
| **Race pattern** | Multi-model parallel dispatch for critical tasks | MEDIUM |
| **Learned rules from feedback** | Auto-refine policies from user reactions | MEDIUM |

---

## 3. OpenHands, Devin, Manus — The Sandboxed Executors

### Common Patterns
- **Docker/VM sandboxing** — all execution in isolated containers
- **Micro-agents** — small specialized workers for subtasks
- **Task queues** with step limits and timeout protection
- **File-system as unlimited context** — agents write state to files, read as needed
- **Evidence artifacts** — screenshots, logs, diffs as proof of work

### What JARVIS Should Adopt

| Pattern | Description | Priority |
|---------|-------------|----------|
| **Step limits per mission** | Hard cap on agent actions per session | HIGH |
| **Evidence artifacts** | Screenshots + diffs as proof of completion | MEDIUM |
| **File-system context** | Write state to disk, read back (vs all-in-memory) | LOW |

---

## 4. Roo Code / Cline — The Approval-First Models

### Common Patterns
- **Step-by-step approval** — user approves every file edit and terminal command
- **Checkpoint/restore** — save state before each action, restore on failure
- **Multi-model support** — route different tasks to different models
- **Cost tracking per task** — show exact cost of each operation
- **Custom modes** — code mode (full access), architect mode (read-only), ask mode (no edits)

### What JARVIS Should Adopt

| Pattern | Description | Priority |
|---------|-------------|----------|
| **Cost tracking per mission** | Show LLM cost in mission dashboard | MEDIUM |
| **Checkpoint before mutations** | Auto-save before file writes, terminal runs | HIGH |
| **Mode system** | code/architect/ask modes with different permissions | MEDIUM |

---

## 5. Cross-Cutting Gaps — Where JARVIS Falls Behind

### CRITICAL Gaps (Must Fix for v7.6)

1. **No permission system** — All 67+ computer actions execute without authorization
   - Competitors: Claude Code has 7 modes + ML classifier; even basic tools require approval
   - Fix: Implement 3-tier permission model (allow / ask / deny) per action category

2. **No step limits** — Agents can run unbounded
   - Competitors: Manus caps at configurable steps; Claude Code has depth limits
   - Fix: Add `max_steps` per mission, `max_actions` per agent session

3. **No checkpoints** — No way to roll back changes
   - Competitors: Roo Code checkpoints every file write; Cursor snapshots before changes
   - Fix: Auto-checkpoint before mutations, store diffs for rollback

4. **No auth on web UI** — Full computer control exposed to network
   - Competitors: All require authentication; Paperclip has Better Auth
   - Fix: Add session-based auth middleware

### HIGH Gaps (Should Fix)

5. **No context compaction** — Long conversations hit context limits
   - Competitors: Claude Code has 5-layer compaction pipeline
   - Fix: Implement progressive summarization

6. **No sub-agent isolation** — All agents share same context
   - Competitors: Claude Code has sidechain transcripts, worktree isolation
   - Fix: Isolated context per sub-agent, summaries only to parent

7. **No evidence artifacts** — No proof of work
   - Competitors: Devin records video, Manus captures screenshots, Cursor has video
   - Fix: Auto-capture screenshots after key actions

8. **No cost tracking** — Can't see LLM usage per mission
   - Competitors: Roo Code, Cline track per-task costs
   - Fix: Log token usage and cost per agent/mission

### MEDIUM Gaps (Nice to Have)

9. **No learned rules** — No feedback loop
   - Fix: Track user approvals/denials, refine policies over time

10. **No multi-model routing** — Single model for everything
    - Fix: Route by task type (fast model for simple tasks, powerful for complex)

11. **No race pattern** — No parallel model dispatch
    - Fix: For critical decisions, dispatch to multiple models and pick consensus

---

## 6. JARVIS Unique Advantages (Don't Lose These)

| Advantage | Why It Matters |
|-----------|----------------|
| **Full OS control** | No competitor has mouse, keyboard, screen, clipboard, OS notifications |
| **Voice I/O with cloning** | Unique — no competitor has voice interaction |
| **IoT integration** | Smart home control built-in |
| **5-layer memory** | Episodic + working + personal + graph + semantic |
| **Engineering tools** | CAD, PCB, firmware — unique for personal AI |
| **Self-evolution** | Autonomous improvement with git commits |
| **23 specialized agents** | More agents than any competitor |
| **Privacy scrubber** | Real-time PII protection in LLM messages |
| **223 API endpoints** | Most comprehensive API of any AI agent |

---

## 7. Recommended Priority Order for v7.6

### Phase 1: Safety Hardening (Week 1)
1. Auth middleware on all web endpoints
2. 3-tier permission model (allow/ask/deny per action)
3. Shell injection fixes in `mouse.py` and `_apply_replacements`
4. Step limits per mission

### Phase 2: Reliability (Week 2)
5. Auto-checkpoint before mutations
6. Context compaction for long conversations
7. Cost tracking per mission
8. Evidence artifacts (screenshots after key actions)

### Phase 3: UX Polish (Week 3)
9. Agents Window with task card status
10. Mode system (code/architect/ask)
11. Progress indicators for long-running actions
12. Checkpoint/restore UI

### Phase 4: Intelligence (Week 4)
13. Sub-agent context isolation
14. Multi-model routing
15. Learned rules from user feedback
16. Race pattern for critical decisions

---

*Compiled: 2026-07-25 | Target: v7.6.0 release*
