# Paperclip Architecture Research

**Date:** 2026-07-24
**Purpose:** Architectural analysis of Paperclip (paperclipai/paperclip) for inspiration on Jarvis development.

---

## What Is Paperclip?

Paperclip is an **open-source control plane for orchestrating virtual companies composed of AI agents**. It treats AI coordination like organizational management software — agents have org charts, reporting lines, budgets, and governance policies. 74.6k GitHub stars, MIT license, TypeScript/Node.js.

**Key Insight:** Paperclip is a *control plane*, not an execution plane. It orchestrates agents; it doesn't run them.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 6, React Router 7, Radix UI, Tailwind CSS 4, TanStack Query |
| Backend | Node.js 20+, Express.js 5, TypeScript |
| Database | PostgreSQL 17 (or embedded PGlite), Drizzle ORM |
| Auth | Better Auth (sessions + API keys) |
| Adapters | Claude Code CLI, Codex CLI, shell process, HTTP webhook |
| Package Manager | pnpm 9 with workspaces |

---

## Core Architecture

```
┌─────────────────────────────────────┐
│  React UI (Vite)                    │
│  Dashboard, org management, tasks   │
├─────────────────────────────────────┤
│  Express.js REST API (Node.js)      │
│  Routes, services, auth, adapters   │
├─────────────────────────────────────┤
│  PostgreSQL (Drizzle ORM)           │
│  Schema, migrations, embedded mode  │
├─────────────────────────────────────┤
│  Adapters                           │
│  Claude Code, Codex,                │
│  Process, HTTP                      │
└─────────────────────────────────────┘
```

---

## Key Design Patterns

### 1. Heartbeat Execution Model (Critical Pattern)

Agents are **stateless LLMs** that don't run continuously. Instead:

1. **Trigger** — Scheduler, manual invoke, or event (assignment, mention) fires
2. **Context Assembly** — Server builds context from memory, task history, pending inbox
3. **Adapter Invocation** — Server calls adapter's `execute()` with full context
4. **Agent Work** — Agent checks out task, does work, updates status
5. **Result Capture** — Server captures stdout, usage/cost data, session state
6. **Run Record** — Server persists run result, costs, and session state for next heartbeat

**Heartbeat Triggers:**
- **Schedule (Timer):** Periodic wakeups (e.g., every 60 minutes)
- **Assignment:** New Issue assigned to the agent
- **On-Demand:** Manual trigger from the Board or @-mention
- **Automation (Routines):** Scheduled workflows at company level

**Why This Matters for Jarvis:** Your `LivingBrain` loop is similar but could benefit from this structured context-assembly-then-execute pattern.

### 2. Hierarchical Org Structure

```
Board (Human)
  └── CEO Agent
       ├── Manager Agent (Engineering)
       │    ├── Worker Agent (Backend)
       │    ├── Worker Agent (Frontend)
       │    └── Worker Agent (DevOps)
       ├── Manager Agent (Marketing)
       └── Manager Agent (Finance)
```

- Every company starts with a **CEO Agent** reporting to the Board
- Strict reporting hierarchy — all agents report to a manager or CEO
- **Delegation Path:** Top-down (goals → issues) and bottom-up (escalation)
- Context flows through hierarchy: executives see summaries, ICs see detailed tickets

**Jarvis Parallel:** Your King → Worker hierarchy (♠ Engineering, ♥ Personal, ♦ Research, ♣ System) is conceptually identical but uses playing cards instead of corporate titles.

### 3. Issues as Atomic Tasks

Issues are the primary unit of work with AI-specific features:

- **Atomic Checkout:** `paperclipCheckoutIssue()` — prevents race conditions on same task
- **Single-Assignee:** Only one agent works on an issue at a time
- **Execution Policy:** Defines autonomy level (done independently vs. requires review)
- **Status Lifecycle:** `open → in_progress → review → done` (or `blocked`)

### 4. Goals → Projects → Workspaces

Work organized in three tiers:
1. **Goals:** The "Why" — high-level objectives
2. **Projects:** The "Where" — specific repos/folders
3. **Workspaces:** The "How" — isolated runtime environment (Docker, local, cloud)

### 5. Adapter System (BYOA — Bring Your Own Agent)

Adapters bridge Paperclip to any agent runtime:

```typescript
interface ServerAdapterModule {
  execute(ctx: AdapterExecutionContext): Promise<AdapterExecutionResult>;
  testEnvironment(): Promise<TestResult>;
  listSkills(): Promise<Skill[]>;
  syncSkills(): Promise<void>;
  sessionCodec: SessionCodec;
  models: Model[];
}
```

Built-in adapters: `claude_local`, `codex_local`, `process`, `http`
Swap runtimes by changing an agent's `adapterType` field.

### 6. Plugin System (Isolated Processes)

- Plugins run as **isolated Node.js processes**
- Communication over JSON-RPC 2.0
- Plugin manifest: `tools`, `jobs`, `webhooks`, `launchers`, `ui.slots`, `configSchema`
- State scoped: `instance / company / project / issue / agent`
- Lifecycle: `installed → ready → disabled/error → uninstalled`

### 7. Approval & Governance

- Agents cannot perform "High-Stakes" actions without explicit Approval
- Actions requiring approval: hiring agents, modifying strategy, exceeding budgets
- Approval records signed by human or superior agent

### 8. Budget & Cost Control

- **Budget Policies** per agent/company
- **Cost Events** tracked per API call
- **Budget Incidents** when limits exceeded
- Agents pause (not crash) when budget exceeded

---

## Database Schema (90+ Tables)

| Domain | Key Tables |
|--------|-----------|
| Org | `companies`, `agents`, `agent_config_revisions`, `agent_api_keys` |
| Work | `issues`, `issue_comments`, `issue_approvals`, `issue_documents`, `issue_work_products` |
| Goals | `goals`, `projects`, `project_workspaces` |
| Execution | `heartbeat_runs`, `heartbeat_run_events`, `execution_workspaces` |
| Finance | `cost_events`, `finance_events`, `budget_policies`, `budget_incidents` |
| Plugins | `plugins`, `plugin_config`, `plugin_state`, `plugin_jobs`, `plugin_webhooks` |
| Auth | `auth_users`, `auth_sessions`, `board_api_keys`, `company_memberships` |
| Audit | `activity_log` |

---

## Request Flow: Task Creation → Execution → Completion

```
1. Board creates Goal → CEO Agent breaks into Issues
2. CEO delegates Issues to Manager Agents
3. Manager assigns Issues to Worker Agents
4. Heartbeat trigger fires on Worker Agent
5. Worker calls paperclipCheckoutIssue() via MCP tool → atomic checkout
6. Adapter.execute() → AI runtime (Claude Code, etc.) performs work
7. During execution, realtime logs stream back via onLog() callback
8. On completion, token usage recorded in costEvents
9. Issue status transitions to done; entry written to activity_log
10. UI reflects update in realtime over WebSocket
```

---

## Comparison: Paperclip vs Jarvis

| Aspect | Paperclip | Jarvis |
|--------|-----------|--------|
| **Language** | TypeScript/Node.js | Python |
| **Database** | PostgreSQL (Drizzle ORM) | SQLite (aiosqlite) |
| **Agent Model** | Stateless heartbeats | Persistent background loop (`LivingBrain`) |
| **Hierarchy** | Corporate (CEO → Manager → Worker) | Playing cards (JARVIS → Kings → Workers) |
| **Task System** | Issues with atomic checkout | Tasks with event bus |
| **Memory** | External (plugin-based) | Built-in 5-layer memory (Working, Episodic, Personal, Journal, Graph) |
| **Frontend** | React + Vite | FastAPI + Jinja2 templates |
| **Adapter Model** | Pluggable adapters (Claude, Codex, HTTP) | Direct LLM calls via httpx |
| **Governance** | Approval system + budget policies | Safety module + privacy scrubber |
| **Voice** | None | Built-in voice I/O (Whisper + TTS) |
| **Computer Control** | None | Full OS control (accessibility tree, keyboard, mouse) |
| **Scope** | Multi-company SaaS platform | Single-user personal AI OS |

---

## What Jarvis Already Has That Paperclip Doesn't

1. **5-Layer Memory System** — Working, Episodic, Personal, Journal, Knowledge Graph (Paperclip outsources this to plugins)
2. **Computer Control** — Full OS-level control via accessibility tree, keyboard, mouse
3. **Voice I/O** — Whisper transcription + TTS
4. **World Model** — Tracks running apps, open files, system state
5. **Knowledge Graph** — Obsidian-style bidirectional links, auto entity extraction
6. **Privacy Scrubber** — PII detection before external API calls
7. **Model Router** — Intelligent task-to-model routing
8. **DAG Task Planner** — Complex multi-step mission planning
9. **Skill Evolution** — Skills that improve over time
10. **Speculative Planning** — Pre-delegates tasks to reduce latency

---

## What Jarvis Could Adopt From Paperclip

### HIGH PRIORITY

1. **Heartbeat Pattern for Idle Agents**
   - Your Workers could use periodic heartbeats to check for work rather than only responding to direct calls
   - Enables background monitoring and proactive actions
   - Implement: Timer-based triggers that assemble context and check task inbox

2. **Atomic Task Checkout**
   - Prevent race conditions when multiple workers might claim same task
   - Paperclip's `checkout/release` pattern ensures single-assignee
   - Your `WorkerPool` could enforce exclusive task locks

3. **Approval/Governance Layer**
   - Formalize when agents need human approval before acting
   - Your `safety/` module exists but could be more structured
   - Add explicit approval records for high-stakes actions (file deletion, API calls, purchases)

4. **Budget/Cost Tracking Per Agent**
   - Track token usage and API costs per King/Worker
   - Set budget policies, pause agents when limits exceeded
   - Your `brain/observability.py` could be extended with cost Events

5. **Execution Policy Configuration**
   - Define per-agent autonomy levels
   - Some workers can complete tasks independently; others require review
   - Maps to your `ReviewPipeline` but more configurable

### MEDIUM PRIORITY

6. **Adapter Pattern**
   - Abstract LLM calls behind an adapter interface
   - Swap between NVIDIA, OpenAI, Anthropic, local models per agent
   - Your `ModelRouter` does this loosely; formalize with adapter interface

7. **Plugin System**
   - Isolated processes for extending capabilities
   - Your `plugins/` exists but could be more formalized
   - JSON-RPC communication for safety isolation

8. **Structured Activity Log**
   - Paperclip's `activity_log` table tracks every decision
   - Your `journal/` and `timeline/` modules do this but could be unified

9. **Real-time WebSocket Updates**
   - Paperclip streams execution logs and status via WebSocket
   - Your web dashboard could benefit from live task progress

### LOW PRIORITY

10. **Multi-Company/Multi-User**
    - Paperclip is designed for multi-tenant SaaS
    - Not relevant for Jarvis (single-user personal AI) but good architectural pattern

11. **Org Chart UI**
    - Visual org chart for agent hierarchy
    - Your dashboard shows agents but a dedicated org view could help

---

## Recommended Architecture Evolution for Jarvis

```
Current State:
  JARVIS (CEO) → Kings (4) → Workers (23)
  Direct LLM calls, event bus, SQLite

Target State (Paperclip-Inspired):
  JARVIS (CEO) → Kings (4) → Workers (23)
  ├── Heartbeat Scheduler (periodic wakeups)
  ├── Atomic Task Checkout (prevent race conditions)
  ├── Approval Gate (human-in-the-loop for high-stakes)
  ├── Budget Tracker (per-agent cost controls)
  ├── Adapter Layer (swappable LLM backends)
  └── Activity Log (unified audit trail)
```

---

## Key Takeaway

Paperclip and Jarvis solve the same problem from opposite directions:
- **Paperclip** = Enterprise control plane for managing many AI agents as a virtual company
- **Jarvis** = Personal AI operating system with deep system integration

The best patterns to borrow are the **operational** ones (heartbeats, atomic checkout, governance, cost control) rather than the **organizational** ones (org charts, multi-tenancy), since Jarvis is a single-user system with already-strong memory and tool integration.
