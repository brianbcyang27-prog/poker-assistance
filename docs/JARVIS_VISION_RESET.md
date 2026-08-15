# JARVIS Vision Reset — Personal AI Operating System

> **Version:** 1.0.0
> **Date:** 2026-07-30
> **Status:** Research Synthesis & Roadmap

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Research Synthesis](#2-research-synthesis)
3. [The New JARVIS Vision](#3-the-new-jarvis-vision)
4. [Pillar 1: Living Projects](#4-pillar-1-living-projects)
5. [Pillar 2: Daily Life Integration](#5-pillar-2-daily-life-integration)
6. [Pillar 3: Autonomous Engineering](#6-pillar-3-autonomous-engineering)
7. [Pillar 4: Experience Design](#7-pillar-4-experience-design)
8. [Comprehensive Roadmap](#8-comprehensive-roadmap)

---

## 1. Executive Summary

JARVIS has extraordinary raw capability — 291 Python files, 23 specialized agents, 223 API endpoints, a 5-layer memory system, computer control, voice I/O, IoT integration, and a 10-stage mission pipeline. No product in the market combines this breadth of backend power.

But the frontend is broken, the navigation is app-centric, there is no daily life integration, and the user's first experience is a confusing dark screen with a chat input.

**The opportunity** is not to add more features. It is to transform JARVIS from a powerful backend with a broken UI into the **world's first true Personal AI Operating System** — one that understands the user's life, projects, and daily routines; that works autonomously in the background; and that feels calm, premium, and intentional.

After analyzing 18+ products (ChatGPT, Claude, Cursor, Raycast, Arc, Linear, Notion AI, Devin, Manus, OpenHands, Perplexity, Lindy, and more) and 15+ design principles (Apple HIG, Cognitive Load, Fitts/Hick/Miller/Gestalt, Calm Technology, AI Trust Research, and more), the path forward is clear:

### The Critical Insight

No product today combines **personal life management** (calendar, email, routines) with **deep agentic capability** (code, research, computer control). Lindy owns personal admin. Notion owns workspace memory. Manus owns agent orchestration. Devin owns deep code execution. Perplexity owns trustable answers.

**JARVIS already has all four capabilities in its backend.** The challenge is unifying them in one premium experience.

### What Must Change

| Current State | Target State |
|---|---|
| App-centric navigation (Home, Chat, Projects, etc.) | User-centric context (the user's day, projects, and needs) |
| Dead code and broken pages | Clean, modular, tested codebase |
| TODO lists that require manual maintenance | Living Projects that auto-generate next actions |
| Dashboard feel with too many panels | Calm, contextual interface that adapts to what you're doing |
| No daily life awareness | Morning/evening briefings, ambient awareness |
| Engineer-first transparency | Calibrated transparency — show the right level for each moment |
| 10 competing visualization systems | One coherent visual language with Golden Core as anchor |

---

## 2. Research Synthesis

### 2.1 What the Best Products Do Right

| Product | Key Insight for JARVIS |
|---------|----------------------|
| **ChatGPT** | Make context durable. Workspaces + projects + memory across sessions. Voice mode as primary interface. |
| **Claude.ai** | Outputs are artifacts, not just text. Project-scoped memory keeps context clean. Let users edit AI outputs. |
| **Raycast** | One command surface for everything. Extensions make third-party tools feel first-party. Keyboard-first, always available. |
| **Arc** | Contexts as spaces (work/personal/research). Command bar as universal input. Browser as organized environment, not tab chaos. |
| **Linear** | Ruthless state clarity. Every item knows its status, what changed, and what happens next. Progress language over feature count. |
| **Notion AI** | AI embedded in knowledge, not bolted on. Permission-aware retrieval. Inline AI actions (summarize, generate, autofill). |
| **Perplexity** | Trust is a UX pattern, not a feature. Layered citations: inline → popover → sidebar → full audit. Evidence in the reading flow. |
| **Devin** | Agent orchestration > single agent. Child sessions with isolated VMs. Persistent session state. Review/fix loops. |
| **Manus** | Workspace substrate, not chat. Projects preserve shared instructions. Parallel agents for research. MCP connectors for cross-app actions. |
| **OpenHands** | Open control plane. Backend-swappable agents. Self-hosted. Full inspectability. |
| **Cursor** | Autonomy slider: suggestion → draft → execute → monitor → report. One product, multiple modes. |
| **Lindy** | Personal admin as primary interface. Email triage, scheduling, reminders, meeting prep. |

### 2.2 Design Research Synthesis

| Principle | JARVIS Application |
|-----------|-------------------|
| **Cognitive Load** | Max 5 navigation items. Progressive disclosure. Show summary first, detail on demand. |
| **Fitts's Law** | Primary actions at screen edges. Large targets (44pt+). Keyboard shortcuts for everything. |
| **Hick's Law** | Fewer choices, faster decisions. Command palette converts browsing into searching. Contextual actions only. |
| **AI Trust** | Show reasoning summary, not raw chain-of-thought. Pair outputs with confidence + source trail. Progressive transparency. |
| **Motion Design** | Motion communicates state, causality, and intent. Never decorative. Short, contextual, outcome-linked. |
| **Ambient Computing** | Glanceable, interruptible, resumable. Proactive only when signal is high + time-sensitive + reversible. Background work lane. |
| **OS Metaphor** | Menu bar (status) + Dock (pinned) + Notification center (triage) + Control center (toggles) + Switcher (contexts). |
| **Living Projects** | Show health, momentum, risk, freshness, blockers. Leading indicators over vanity metrics. One recommended next action. |
| **Briefing UX** | Compressed decision surface. Voice = summary, Cards = evidence. 30-45 seconds. Only what's actionable. |

### 2.3 Current Codebase Assessment

**Strengths to Preserve:**
- 4 Kings / 23 Workers agent hierarchy — genuinely innovative AI architecture
- 5-layer memory system (working, episodic, personal, journal, knowledge graph)
- Computer control (macOS accessibility, browser, mouse/keyboard)
- Voice I/O (TTS/STT with providers)
- IoT integration (ESP32/Arduino)
- Mission pipeline (10-stage: understand → research → plan → execute → verify → test → review → remember → evolve)
- Security system (AES-256-GCM, Keychain, audit logging)
- 1,162 tests across 39 files

**Critical Problems to Fix:**
- 8,000+ lines of dead Python code (14 orphaned packages)
- Dead templates and broken routes
- Race conditions in chat session creation
- Two competing Three.js Graph3D implementations
- Monolithic style.css duplicates design-tokens.css and animations.css
- No build system for frontend
- 16 dead functions in app.js (17.4%)
- Event listener accumulation (settings opened 3× = 3× handler registration)
- No daily life features, no living projects
- First-run experience is confusing

---

## 3. The New JARVIS Vision

### Core Identity

> JARVIS is the world's first Personal AI Operating System.
> Not a chatbot. Not a coding assistant. Not an automation tool.
> A true OS that helps a person live, learn, create, and work.

### Design Philosophy

**Calm. Elegant. Fast. Premium. Alive.**

These five words guide every decision:

| Principle | Meaning |
|-----------|---------|
| **Calm** | Technology recedes into the background. The Golden Core is an ambient presence, not a demanding interface. |
| **Elegant** | Apple-quality craftsmanship. Intentional typography, spacing, motion, and hierarchy. Nothing unnecessary. |
| **Fast** | Zero-latency perception. Optimistic updates. Keyboard-first. Skeleton loading. 60fps animations. |
| **Premium** | Glass morphism, spring physics, deep space color. Feels like a luxury product, not a developer tool. |
| **Alive** | The Golden Core breathes. Projects have pulse. The interface responds with purpose. Motion communicates state. |

### The Golden Core Is Permanent

The 3D Golden Neural Core is the permanent visual identity of JARVIS. It is:
- The **ambient presence** — always visible, always communicating state
- The **identity anchor** — JARVIS's face, not a logo
- The **state communicator** — idle, listening, thinking, planning, executing, verifying, success, error
- The **creative constraint** — everything else must work around it, not compete with it

### Key Product Pillars

1. **Living Projects** — Projects become living entities with vision, goals, health, and auto-generated next best actions. No manual TODO maintenance.
2. **Daily Life Integration** — Morning/evening briefings. Calendar, weather, overnight AI work. Ambient awareness of what matters.
3. **Autonomous Engineering** — Every task follows a rigorous lifecycle. Never skip verification. Never claim success without evidence.
4. **Experience Design** — Calm, contextual, premium. The interface adapts to what you're doing. The Golden Core is the constant.

---

## 4. Pillar 1: Living Projects

### The Core Problem

Traditional project management requires manual maintenance. You create tasks, update statuses, move cards. This breaks down because maintaining the system becomes work in itself.

### The Living Project Model

Every project is a **living entity** with:

| Property | Description | Example |
|----------|-------------|---------|
| **Vision** | Why this project exists | "Build a personal AI OS" |
| **Goals** | What success looks like | "v1.0 release with 90% user satisfaction" |
| **Progress** | How far along | "42% — Phase 2 of 6" |
| **Health Score** | How healthy is it | "Good — momentum slowing" |
| **Momentum** | Active velocity | "3 commits/day" |
| **Risk** | What could go wrong | "Dependency on library X upgrade" |
| **Blockers** | What's stuck | "Awaiting API key from vendor" |
| **Freshness** | When last updated | "Last active: 2 hours ago" |
| **Decision Log** | Key decisions with rationale | "Decided to use SQLite over PostgreSQL for simplicity" |
| **Next Best Action** | What to do next | "Review PR #42 — unblocks deployment" |
| **Confidence Score** | How sure we are of timeline | "70% — risk of scope creep" |

### The "Next Best Action" Engine

This is the most important feature. The NBA is generated automatically by analyzing:

1. **Project state** — What's in progress, what's blocked
2. **Codebase activity** — Recent commits, open PRs, CI failures
3. **Previous decisions** — What patterns have been established
4. **Dependency changes** — Updated libraries, breaking changes
5. **Known risks** — What could derail progress
6. **Time since last activity** — What's gone stale
7. **User context** — What the user is doing right now

The NBA should be:
- **Specific** — "Review PR #42" not "Work on the project"
- **Actionable** — "Approve the migration PR" not "Think about architecture"
- **Contextual** — Only shown when the user has time/energy for it
- **Confidence-tagged** — "High confidence: this unblocks 3 other tasks"

### UI Pattern: The Project Card

```
┌─────────────────────────────────────────────────────┐
│  ▲ JARVIS Vision Reset                Pulse: ▂▃▄▇   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  Health: ● Good    Momentum: ●●●○○   Risk: ●●○○○  │
│                                                     │
│  Progress: ████████░░░░░░░ 42%                      │
│                                                     │
│  Next Best Action:                                   │
│  → Review PR #42 (high confidence)                  │
│    "Unblocks deployment pipeline"                   │
│                                                     │
│  Active Blockers: 1                                  │
│  ! Awaiting API key — vendor ticket #3821           │
│                                                     │
│  Recent: Updated 2h ago · 3 commits today           │
└─────────────────────────────────────────────────────┘
```

### What This Replaces

| Current JARVIS | Living Projects |
|---|---|
| Workspace with manual tasks | Auto-tracking project with NBA |
| Static project list | Living cards with pulse |
| User must decide what's next | AI suggests NBA with rationale |
| No cross-project awareness | AI connects dependencies across projects |
| No confidence scoring | Confidence + risk visible at a glance |

---

## 5. Pillar 2: Daily Life Integration

### The Core Problem

When you open your computer, you have to manually check:
- What's on my calendar today?
- What happened overnight?
- What should I work on?
- What's urgent?

Current JARVIS shows you a blank chat input.

### The Briefing System

When the computer starts (or on demand), JARVIS offers a morning/evening briefing.

#### Morning Briefing Structure (30-45 seconds spoken)

1. **Greeting** — Time-appropriate, personalized
2. **Calendar** — First meeting, conflicts, travel time
3. **Overnight Changes** — AI work completed, PR updates, CI results
4. **Project Pulse** — Health changes, new blockers, progress
5. **One Recommendation** — Highest-impact action for today
6. **Weather & Context** — Quick glanceable info

#### Visual Briefing Cards

Each spoken item has a synchronized visual card:

```
┌─ Morning Briefing ─────────────────────────┐
│                                            │
│  Good morning, Brian.                      │
│                                            │
│  📅 Calendar                               │
│  10:00 — Design Review (30min)             │
│  14:00 — Sprint Planning (1hr)             │
│                                            │
│  🌙 Overnight                              │
│  PR #42 passed CI ✓                        │
│  Research on motion design complete (3 new │
│  sources added to project memory)          │
│                                            │
│  📊 Project Health                         │
│  JARVIS Vision Reset: ● Good (+2% today)   │
│  Golden Core: ● Critical (WebGL perf issue)│
│                                            │
│  🎯 Recommended                             │
│  Review PR #42 — it unblocks deployment    │
│                                            │
│  [Dismiss]  [Deep Dive]  [Customize]       │
└────────────────────────────────────────────┘
```

### Ambient Awareness

The Golden Core and task bar show peripheral status:
- Idle: Slow pulse (waiting)
- Background work: Subtle glow (AI working)
- Needs attention: Gentle notification
- Error: Red pulse (needs human)

Always visible: What JARVIS is currently doing, what's pending, and one-click access to context.

### Afternoon/Evening Briefing

- What was accomplished
- What's still pending
- Overnight scheduled work
- One question for reflection: "Do you want me to work on anything overnight?"

---

## 6. Pillar 3: Autonomous Engineering

### The Core Problem

AI agents frequently claim success without evidence. They skip verification, hallucinate results, and leave users unsure whether work was actually done correctly.

### The Engineering Lifecycle

Every engineering task follows exactly this lifecycle:

```
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │ Understand │────→│ Research │────→│   Plan   │
  └──────────┘     └──────────┘     └────┬─────┘
                                         │
  ┌──────────┐     ┌──────────┐     ┌────▼─────┐
  │ Improve  │←────│ Review   │←────│ Implement│
  └──────────┘     └────┬─────┘     └──────────┘
                        │
                   ┌────▼─────┐     ┌──────────┐
                   │  Verify  │←────│   Test   │
                   └──────────┘     └──────────┘
                        │
                   ┌────▼─────┐
                   │Document  │
                   └──────────┘
```

### Non-Negotiable Rules

| Rule | Why |
|------|-----|
| **Never skip Understand** | Without understanding the problem, you can't solve it. |
| **Never skip Research** | Without research, you'll repeat mistakes. |
| **Never skip Plan** | Without a plan, you don't know where you're going. |
| **Never skip Verify** | Without verification, you don't know if it works. |
| **Never skip Test** | Without tests, you have no safety net. |
| **Never skip Review** | Without review, you miss blind spots. |
| **Never skip Document** | Without documentation, knowledge is lost. |
| **Never claim success without evidence** | Screenshots, logs, test results, or it didn't happen. |

### Evidence Requirements

Every completed task must produce:
- **Test results** — Which tests passed/failed
- **Verification artifacts** — Screenshots, logs, or metrics
- **Code diffs** — What changed, in diff view
- **Review status** — Peer/self-review results
- **Documentation** — What was learned, what was produced

### The Mission Card

Every task gets a mission card that visualizes the lifecycle:

```
┌─ Mission: Add living project NBA engine ────┐
│                                              │
│  [✓] Understand   [✓] Research   [✓] Plan    │
│  [→] Implement    [ ] Verify     [ ] Test    │
│  [ ] Review       [ ] Improve    [ ] Doc     │
│                                              │
│  Current: Implementing NBA algorithm          │
│  Duration: 12min · Confidence: 85%            │
│  Evidence: test_nba_generation.py passes (4/4)│
└──────────────────────────────────────────────┘
```

---

## 7. Pillar 4: Experience Design

### 7.1 Interface Architecture

The new JARVIS interface uses a **contextual layer system**:

```
Layer -1: Golden Core (WebGL, fixed, ambient)
Layer  0: Background (deep space gradient)
Layer  1: Primary Content (contextual, adaptive)
Layer  2: Secondary Panels (slide-in, translucent)
Layer  3: Tool/Mission cards (inline, elevated)
Layer  4: Modals/Overlays (focus, dimmed background)
Layer  5: Toasts/Notifications (top, temporary)
```

### 7.2 Primary Views (Adaptive, Not Fixed)

Instead of 6+ fixed workspaces, the interface adapts to what the user is doing:

| Context | Primary View | Secondary Panels |
|---------|-------------|------------------|
| **Idle** | Golden Core + Briefing + Input | Project pulse, ambient status |
| **Conversation** | Chat + Streaming | Agent stream (collapsible) |
| **Research** | Sources + Synthesis | Agent stream, citations |
| **Coding** | Files + Diff + Tests | Agent stream, preview |
| **Computer Control** | Screen view + Actions | Action log, permissions |
| **Memory/Knowledge** | Knowledge graph + Search | Detail panel |
| **Projects** | Living project cards | Pulse, risks, NBA |
| **Settings** | Categorized + Searchable | Quick toggles |

### 7.3 Golden Core State Machine

| State | Visual | Panel Behavior |
|-------|--------|---------------|
| **Idle** | Slow cyan pulse, particles drift | Input visible, minimal UI |
| **Listening** | Bright cyan, particles converge to center | Input active, subtle glow |
| **Thinking** | Blue shift, slow rotation, spiral particles | Subtle "thinking" indicator |
| **Planning** | Gold accent, expanding rings | Plan card appears |
| **Executing** | Green tint, outward pulse | Mission card with progress |
| **Verifying** | Amber, check pulse | Verification results |
| **Success** | Bright green burst, particles disperse upward | Celebration micro-animation |
| **Error** | Red pulse, shake, scatter | Error card with recovery actions |

### 7.4 Navigation

Reduced from 7+ items to **5 primary destinations**:

```
  [Home]  [Chat]  [Projects]  [Memory]  [Settings]
```

- **Home**: Golden Core + Briefing + Quick Input (the default)
- **Chat**: Conversation with adaptive context
- **Projects**: Living project cards
- **Memory**: Knowledge graph, search, timeline
- **Settings**: Categorized, searchable

Dev mode (Cmd+Shift+D) reveals: Agents, Diagnostics, Logs, Computer Control.

### 7.5 The Command Bar (⌘K)

Raycast-inspired universal command palette. Always available via ⌘K:
- Type to search everything (projects, memories, conversations, settings)
- Commands for every action
- AI suggestions in the results
- Quick actions without leaving keyboard

### 7.6 Typography & Space

- **Typeface**: SF Pro Display / system-ui
- **Scale**: 11px (caption), 13px (body), 15px (large body), 18px (h3), 22px (h2), 28px (h1)
- **Grid**: 8px base unit. Spacing: 8/16/24/32/48px
- **Radius**: 8px (cards), 12px (panels), 16px (modals), 9999px (pills)
- **Motion**: Spring physics (damping: 0.8, stiffness: 180, mass: 1)

### 7.7 Color System

```
--color-bg-deepest: #080d16    (Deep space)
--color-bg-deep: #0d1420       (Background)
--color-bg-elevated: #111a2a   (Panels)
--color-bg-card: #142038       (Cards)
--color-bg-glass: rgba(20, 32, 56, 0.7)  (Glass)
--color-brand: #00d4ff         (Cyan accent)
--color-accent: #ffd700        (Gold / Golden Core)
--color-success: #30d158
--color-warning: #ff9f0a
--color-error: #ff453a
--color-text-primary: #f0f0f5
--color-text-secondary: #a0a0b0
--color-text-muted: #606070
```

### 7.8 Interaction Principles

| Principle | Implementation |
|-----------|---------------|
| **Keyboard first** | Every action has a shortcut. ⌘K is the universal entry point. |
| **Zero latency perception** | Optimistic UI updates. Skeleton loading. No spinners for <300ms. |
| **Contextual actions** | Show relevant controls only when relevant. No permanent toolbars. |
| **Undo everything** | Every mutation can be undone. Checkpoints before changes. |
| **Calm defaults** | No notifications for low-confidence events. No random suggestions. |
| **Progressive disclosure** | Summary first, detail on demand. Tool cards collapsed by default. |

---

## 8. Comprehensive Roadmap

### Prioritization Framework

Work is prioritized by **impact** (user value × frequency of use) divided by **effort**:

```
Priority = (User Value × Frequency) / Effort
```

### Phase 0: Codebase Hygiene (Week 1)

**Purpose:** Clean the foundation before building anything new.
**User Value:** Zero direct value, but unblocks everything else.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Delete 14 orphaned Python packages (~5,000 lines) | 1h | Low | None |
| Delete dead templates (index.html, command_center.html, settings.html) | 30min | Low | None |
| Fix 3 broken onclick handlers | 30min | Low | None |
| Fix session creation race condition in chat | 1h | Medium | None |
| Fix event listener accumulation (voice setup) | 30min | Low | None |
| Fix 4 broken imports in living_dashboard/manager.py | 30min | Low | None |
| Consolidate two Graph3D implementations into one | 2h | Medium | None |
| Remove debug-patch.js from production path | 15min | Low | None |
| Lazy-load JS files per workspace | 2h | Medium | None |
| Run and fix all 1,162 tests | 2h | Medium | None |

**Exit criteria:** Zero dead code. Zero undefined function handlers. All 1,162 tests passing. No duplicate implementations.

---

### Phase 1: Living Projects Foundation (Week 2)

**Purpose:** Replace the manual workspace/task system with living project entities.
**User Value:** HIGH — users get auto-generated next actions instead of blank canvases.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Design Living Project data model (vision, goals, health, NBA, confidence) | 1d | Medium | Phase 0 |
| Implement Project storage layer (extend database.py) | 1d | Medium | Phase 0 |
| Build Health Score engine (activity, freshness, blockers, risk) | 1d | Medium | None |
| Build Next Best Action engine (project state + codebase + dependencies + risks) | 2d | High | Project data model |
| Build Confidence Score system (completion certainty, risk-weighted) | 1d | Medium | NBA engine |
| Build Project Pulse visualization (WebGL or Canvas mini-graph) | 1d | Medium | None |
| Create Living Project Card component (HTML/CSS/JS) | 1d | Medium | Phase 0 frontend cleanup |
| Add Project API endpoints (CRUD + health + NBA) | 1d | Low | Project data model |
| Wire Projects view into navigation | 0.5d | Low | Project cards |
| Add auto-detection of projects from filesystem | 1d | Medium | None |

**Exit criteria:** Projects auto-detected. NBA generated for each project. Pulse visible on project cards. Confidence scores displayed.

---

### Phase 2: Daily Briefing System (Week 3)

**Purpose:** Make JARVIS aware of the user's day. Morning/evening briefings.
**User Value:** VERY HIGH — changes the first experience from "blank chat" to "useful information."

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Calendar integration (read macOS Calendar via AppleScript/CalDAV) | 1d | Medium | None |
| Design briefing data model (events, overnight changes, recommendations) | 0.5d | Low | None |
| Build Briefing generation engine (calendar + projects + overnight work) | 2d | High | Living Projects (Phase 1) |
| Build Briefing spoken output (TTS integration with timing) | 1d | Medium | None |
| Create Briefing visual cards (HTML/CSS with synchronized highlights) | 1.5d | Medium | None |
| Build "overnight AI work" tracking (what did JARVIS do while away) | 1d | Medium | Living Projects |
| Add Briefing trigger (startup / on-demand) | 0.5d | Low | Briefing engine |
| Add Briefing customization UI (what to include/exclude) | 1d | Low | Settings redesign (Phase 5) |
| Weather integration (simple API call) | 0.5d | Low | None |

**Exit criteria:** Morning briefing shows calendar, overnight changes, project health, and one recommendation. Spoken + visual cards synchronized. Can be dismissed or deep-dived.

---

### Phase 3: Experience Redesign (Weeks 4-5)

**Purpose:** Transform the UI from developer dashboard to premium personal OS.
**User Value:** VERY HIGH — this is what users see every interaction.

#### 3a: Design System Cleanup (Week 4)

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Consolidate design-tokens.css, animations.css into style.css (or proper modular system) | 1d | Medium | Phase 0 |
| Build proper CSS module system (token → primitives → components → features) | 1d | Medium | None |
| Standardize typography to 6-size scale | 0.5d | Low | None |
| Standardize spacing to 8px grid | 0.5d | Low | None |
| Standardize border-radius to 3-value system | 0.5d | Low | None |
| Create unified component library (buttons, cards, inputs, badges, toasts) | 2d | Medium | CSS system |
| Add spring physics animation system (centralized) | 1d | Medium | None |
| Add glass morphism effects (consistent backdrop-filter, borders) | 0.5d | Low | None |
| Implement prefers-reduced-motion support | 0.5d | Low | None |
| Add dark/light mode support | 1d | Medium | CSS system |

#### 3b: Navigation & Layout Redesign (Week 4-5)

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Reduce navigation to 5 items: Home, Chat, Projects, Memory, Settings | 0.5d | Low | Phase 0 |
| Implement contextual panel system (slide-in/out based on context) | 2d | High | None |
| Create Home/Idle view (Golden Core + Briefing + Input) | 2d | Medium | Briefing (Phase 2) |
| Redesign Chat view (full-width, collapsible agent stream) | 1d | Medium | None |
| Redesign Projects view (living cards, pulse, NBA) | 1d | Medium | Living Projects (Phase 1) |
| Redesign Memory view (knowledge graph + search) | 1.5d | Medium | None |
| Redesign Settings view (categorized, searchable) | 1d | Medium | None |
| Remove all dev-only elements from default view | 0.5d | Low | None |
| Add ⌘K command palette (enhance existing) | 1d | Medium | None |
| Implement workspace transitions (slide/fade with spring physics) | 1d | Medium | Animation system |

#### 3c: Golden Core Enhancement (Week 5)

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Implement 8-state Golden Core state machine | 2d | High | Phase 0 Graph3D consolidation |
| Add smooth state transitions (interpolated, not abrupt) | 1d | Medium | State machine |
| Add particle system reactions per state | 1d | Medium | State machine |
| Add contextual labels (current task on/near core) | 0.5d | Low | State machine |
| Optimize WebGL performance for laptop/battery | 1d | Medium | None |
| Add Canvas 2D fallback for low-end devices | 1d | Medium | None |

**Exit criteria:** Navigation has 5 items. Home shows Golden Core + briefing + input. Contextual panels work. Golden Core has 8 smooth states. All animations use spring physics. Dev elements hidden by default.

---

### Phase 4: Autonomous Engineering Lifecycle (Week 6)

**Purpose:** Ensure every task follows the rigorous lifecycle. Never skip verification.
**User Value:** HIGH — builds trust that work is done correctly.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Design Engineering Lifecycle data model (9 stages with guardrails) | 0.5d | Low | None |
| Build lifecycle enforcement engine (can't skip stages) | 1d | Medium | None |
| Create Mission Card component (shows lifecycle progress) | 1d | Medium | CSS system (Phase 3) |
| Add evidence collection (auto-capture screenshots, test results, diffs) | 2d | High | None |
| Build verification gate (must pass tests, lint, types to proceed) | 1d | Medium | None |
| Add review step (self-review + optional peer) | 1d | Medium | None |
| Create documentation auto-generation from lifecycle | 1d | Medium | None |
| Wire lifecycle into mission executor | 1d | Medium | Lifecycle data model |

**Exit criteria:** Every task goes through lifecycle. Verification is mandatory. Evidence is collected. Cannot claim success without proof.

---

### Phase 5: Settings & Polish (Week 7)

**Purpose:** Make the product feel finished and configurable.
**User Value:** MEDIUM-HIGH — settings are the last mile of UX.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Redesign settings as categorized, searchable panels | 1d | Medium | CSS system (Phase 3) |
| Add AI Model configuration (model, temp, max tokens) | 0.5d | Low | None |
| Add Voice configuration (TTS/STT providers, voices) | 0.5d | Low | None |
| Add Appearance configuration (theme, density, motion) | 0.5d | Low | CSS system |
| Add Permissions UI (granular, with audit log) | 1d | Medium | None |
| Add Integrations configuration (MCP, webhooks, APIs) | 1d | Medium | None |
| Add Briefing customization (what to include) | 0.5d | Low | Briefing (Phase 2) |
| Add About/Version page | 0.5d | Low | None |

---

### Phase 6: Voice & Multimodal (Week 8)

**Purpose:** Make voice a first-class interface.
**User Value:** MEDIUM — high delight factor, differentiator.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Enhance TTS integration (better provider support, timing) | 1d | Medium | None |
| Enhance STT integration (wake word, always-listening mode) | 2d | High | None |
| Voice-first briefing mode (spoken + visual cards synchronized) | 1d | Medium | Briefing (Phase 2) |
| Voice commands for common actions | 1d | Medium | Voice enhancements |
| Voice cloning UI polish | 0.5d | Low | None |

---

### Phase 7: Memory & Knowledge (Week 9)

**Purpose:** Make memory feel intelligent and useful.
**User Value:** MEDIUM — powerful but not daily use for everyone.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Knowledge graph visualization (force-directed WebGL) | 2d | High | None |
| Semantic search across all memory types | 1d | Medium | None |
| Cross-session recall (remember context across restarts) | 1d | Medium | Memory system |
| Memory consolidation visualization (show what was learned) | 1d | Medium | None |
| Forget/Privacy UI (manage what's remembered) | 1d | Medium | None |

---

### Phase 8: Performance & Reliability (Week 10)

**Purpose:** Ship-quality hardening.
**User Value:** MEDIUM — invisible but critical.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Bundle optimization (lazy loading, code splitting) | 1d | Medium | Phase 3 |
| 60fps animation verification | 0.5d | Low | Phase 3 |
| Memory leak detection (JS + Python) | 1d | Medium | None |
| Lighthouse > 90 for all pages | 1d | Medium | Phase 3 |
| Auth middleware on all web endpoints | 1d | Medium | None |
| 3-tier permission model (allow/ask/deny) | 1.5d | Medium | None |
| Step limits per mission | 0.5d | Low | Phase 4 |
| Auto-checkpoint before mutations | 1d | Medium | None |
| Cost tracking per mission | 1d | Low | None |
| Accessibility audit (WCAG 2.1 AA) | 1.5d | Medium | Phase 3 |

---

### Phase 9: Advanced Features (Week 11-12)

**Purpose:** Differentiators that push beyond competitors.
**User Value:** HIGH — unique capabilities.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| Plugin/Extension system (SDK for third-party tools) | 3d | High | Phase 5 |
| Multi-model routing (task-to-model optimized dispatch) | 2d | High | None |
| Sub-agent context isolation (sidechain transcripts) | 1d | Medium | None |
| Sandboxed execution (Docker/container for untrusted code) | 2d | High | None |
| MCP (Model Context Protocol) client | 1d | Medium | None |
| Cross-device sync (encrypted) | 3d | High | None |

---

### Phase 10: Launch Readiness (Week 13)

**Purpose:** Final polish before public release.

| Task | Effort | Risk | Dependency |
|------|--------|------|------------|
| User documentation (guides, FAQ, API reference) | 2d | Low | All phases |
| First-run onboarding (new user flow) | 1d | Medium | Phase 3 |
| Demo mode (show what JARVIS can do without setup) | 1d | Medium | All phases |
| Video tutorials (3-5 min each) | 2d | Low | All phases |
| Performance benchmarking vs v8.0.0 | 1d | Low | Phase 8 |

---

## Milestone Summary

| Milestone | Timeline | Key Deliverable | Success Metric |
|-----------|----------|-----------------|----------------|
| **M0: Foundation** | Week 1 | Clean codebase, no dead code, all tests pass | Zero critical bugs, 1,162 tests passing |
| **M1: Living Projects** | Week 2 | Auto-detected projects with NBA, health, confidence | Projects show valid NBA on first load |
| **M2: Daily Briefing** | Week 3 | Morning briefing with calendar, projects, overnight work | Briefing generates in <2s, relevant >80% of days |
| **M3: Premium UX** | Weeks 4-5 | Redesigned interface, 5-item nav, contextual panels, Golden Core states | Lighthouse >90, user task completion >95% |
| **M4: Engineering Rigor** | Week 6 | Mandatory lifecycle, evidence collection, verification gates | 100% of tasks pass verification, zero "success without evidence" claims |
| **M5: Polish** | Week 7 | Categorized settings, design system complete | Settings load <500ms, all components use design tokens |
| **M6: Voice** | Week 8 | Voice-first briefing, TTS/STT enhancements | Voice briefing < spoken duration target |
| **M7: Memory** | Week 9 | Knowledge graph visualization, cross-session recall | Memory recall precision >90% |
| **M8: Hardening** | Week 10 | Performance, security, accessibility | Lighthouse Performance >90, Accessibility 100, no high-severity security issues |
| **M9: Advanced** | Weeks 11-12 | Plugins, sandbox, multi-model routing | Plugin SDK documented, sandbox passes security review |
| **M10: Launch** | Week 13 | Docs, onboarding, demos | New user completes first task in <2min |

---

## Success Criteria for v1.0

| Metric | Target | How Measured |
|--------|--------|-------------|
| Morning briefing relevance | >80% of briefings contain actionable items | User feedback, dismissal rate |
| NBA accuracy | >70% of NBAs are valid next steps | User acceptance rate |
| Task completion with evidence | 100% of tasks produce verification artifacts | Automated audit |
| Zero "claimed success without evidence" | 100% compliance | Lifecycle enforcement logs |
| Lighthouse Performance | >90 | Lighthouse CI |
| Lighthouse Accessibility | 100 | Lighthouse CI |
| User task completion | >95% | Session analysis |
| Error recovery rate | >90% self-recovery | Error tracking |
| Dead code | 0 lines | Import analysis |
| Tests passing | 100% (1,162+) | pytest |
| Bundle size (gzipped) | <200KB | Build analysis |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| NBA engine produces irrelevant suggestions | Medium | High | Start with simple heuristics, iterate with user feedback |
| Briefing feels overwhelming | Medium | High | Allow full customization; start minimal, expand optionally |
| Frontend rebuild takes longer than estimated | High | Medium | Prioritize Phase 0 (CSS consolidation) over full rewrite; iterative improvements |
| Dead code deletion breaks something unexpected | Medium | High | Comprehensive test suite before deletion; git blame for confidence |
| Golden Core WebGL performance on low-end devices | Medium | Medium | Canvas 2D fallback, reduced particle count, battery-aware rendering |
| Users resist new navigation (change aversion) | Medium | Low | Keep old nav as "developer mode" for transition period |
| Calendar integration fragile (macOS permission changes) | Medium | Medium | Multiple provider options (CalDAV, AppleScript, manual) |
| Voice briefing feels gimmicky | Medium | Medium | Make briefing default to text-only; voice is opt-in enhancement |

---

*This document represents the complete product vision reset for JARVIS v9.0.0.*
*Next step: Review with team, finalize milestone sequencing, begin Phase 0 implementation.*
