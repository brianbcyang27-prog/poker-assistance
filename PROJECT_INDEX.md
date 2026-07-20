# JARVIS Project Index

**Version:** v6.2.0
**Total Files:** 492 (321 Python, 171 non-Python: templates, static JS/CSS, Arduino library, docs)

---

## 1. `jarvis/core/` — Core Infrastructure

The foundation layer. Every other module depends on these.

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `config.py` | Unified configuration via pydantic-settings. Loads from env vars, `.env`, or defaults. | `Config`, `get_config()` | `pydantic_settings` |
| `database.py` | Async SQLite database with migration support, JSON serialization, and a global `get_db()` accessor. | `Database`, `get_db()` | `aiosqlite` |
| `events.py` | Async pub/sub event bus for decoupled component communication. No component knows about others directly. | `EventBus`, `Event`, `event_bus` | stdlib only |
| `models.py` | Core data models: agent hierarchy (suit/rank/role), task, message, workspace. | `Suit`, `AgentRole`, `AgentState`, `Task`, `AgentMessage`, `Workspace` | `pydantic` |
| `reliability.py` | Centralized retry, timeout, and error handling. Replaces 100+ hardcoded values across the codebase. | `config`, `retry_with_backoff()`, `timeout_guard()`, `safe_execute()` | stdlib only |
| `capabilities.py` | Centralized registry of all tools, workers, and capabilities. Kings use this to select the right worker. | `CapabilityRegistry`, `Capability`, `registry` | stdlib only |
| `diagnostics.py` | Startup diagnostics that verify all subsystems are healthy and attempt auto-recovery. | `run_diagnostics()`, `DiagResult` | `asyncio` |
| `__init__.py` | Package exports: Config, Database, EventBus, core models. | — | — |

---

## 2. `jarvis/agents/` — Agent Hierarchy

Playing-card hierarchy: Kings (division directors) delegate to Workers (specialized executors). JARVIS is the CEO.

### `jarvis/agents/` — Top Level

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `base.py` | Base agent classes for the card hierarchy. Defines the common interface for all agents. | `BaseAgent`, `CardAgent` | `core.models` |
| `jarvis.py` | Chief Executive AI Agent — the top-level orchestrator that coordinates all Kings. | `JarvisAgent` | `agents.base`, `brain.llm` |
| `tools.py` | Tool executor bridge — agents call `tools.execute()` for computer, web, IoT, and shell actions. | `tools.execute()` | `computer`, `browser`, `iot` |

### `jarvis/agents/kings/` — Division Directors

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `base.py` | Base King class — division manager that delegates to Workers via the capability registry. | `BaseKing` | `agents.base`, `core.capabilities` |
| `engineering.py` | King of Spades — Engineering Division Director. Manages code, architecture, and build workers. | `EngineeringKing` | `agents.kings.base` |
| `personal.py` | King of Hearts — Personal Division Director. Manages calendar, memory, and personal assistant workers. | `PersonalKing` | `agents.kings.base` |
| `research.py` | King of Diamonds — Research Division Director. Manages web research, codebase analysis, and tool discovery workers. | `ResearchKing` | `agents.kings.base` |
| `system.py` | King of Clubs — System Division Director. Manages OS control, browser, and vision workers. | `SystemKing` | `agents.kings.base` |

### `jarvis/agents/workers/` — Specialized Executors

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `base.py` | Base Worker — specialized task executor with cross-agent collaboration and result reporting. | `BaseWorker` | `agents.base` |
| `engineering.py` | Engineering Workers (♠ suit): Architect, Backend, Frontend, DevOps, and QA specialists. | `ArchitectWorker`, `BackendWorker`, `FrontendWorker`, `DevOpsWorker`, `QAWorker` | `agents.workers.base` |
| `personal.py` | Personal Workers (♥ suit): Calendar, Memory, Health, and Finance specialists. | `CalendarWorker`, `MemoryWorker`, `HealthWorker`, `FinanceWorker` | `agents.workers.base` |
| `research.py` | Research Workers (♦ suit): Web research, codebase analysis, and tool discovery via BrowserManager. | `WebResearchWorker`, `CodeAnalystWorker`, `ToolDiscoveryWorker` | `agents.workers.base`, `browser.manager` |
| `system.py` | System Workers (♣ suit): OS control, browser, screen, and search workers via ComputerManager. | `OSWorker`, `BrowserWorker`, `ScreenWorker`, `SearchWorker` | `agents.workers.base`, `computer.manager` |

### `jarvis/agents/orchestration/` — Task Orchestration

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `orchestration.py` | Task orchestrator — King→Worker delegation and parallel execution management. | `TaskOrchestrator`, `OrchestrationResult` | `asyncio` |
| `dag.py` | DAG workflow engine — define and execute task dependencies with parallel execution paths. | `DAGWorkflow`, `DAGNode`, `DAGEdge` | `asyncio` |
| `pool.py` | Worker pool — manages worker lifecycle, availability, and load balancing. | `WorkerPool`, `PoolStats` | `asyncio` |

### `jarvis/agents/personas/` — Agent Identity System

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Agent persona data models: role, identity, and personality traits. | `Persona`, `AgentIdentity`, `AgentRole` | dataclasses |
| `registry.py` | Persona registry — manages agent identities, loads from JSON configs, provides random personas. | `PersonaRegistry` | `json`, `os` |

---

## 3. `jarvis/brain/` — Intelligence Layer

LLM integration, reasoning, memory, skills, RAG, and the autonomous brain loop.

### `jarvis/brain/core/` — Core Brain Facade

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `brain.py` | Main facade for all brain operations — unifies context, memory, reasoning, and decision-making. | `JARVISBrain` | `brain.core.*` |
| `context.py` | Builds unified context for every agent interaction from all memory sources. | `BrainContextManager` | `brain.core.models` |
| `decision.py` | Brain-level decision engine — decides, records explanations, and learns from outcomes. | `DecisionEngine` | `brain.core.models` |
| `memory.py` | Unified memory manager — single entry point for all memory CRUD operations. | `MemoryManager` | `brain.core.models` |
| `reasoning.py` | Evidence-based reasoning chain with memory integration and confidence scoring. | `ReasoningEngine` | `brain.core.models` |
| `models.py` | Unified brain data models: context, memory entries, reasoning results, action decisions. | `BrainContext`, `MemoryEntry`, `ReasoningResult`, `ActionDecision` | dataclasses |

### `jarvis/brain/memory/` — Human-Like Memory System

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `__init__.py` | Package entry — layered memory architecture: Working, Episodic, Personal, Journal, Graph. | — | — |
| `working.py` | Working memory — short-term context manager (7 slots, like RAM). Auto-compresses old context. | `WorkingMemory` | stdlib only |
| `episodic.py` | Episodic memory — autobiographical events from missions, conversations, and decisions. | `EpisodicMemory` | `brain.memory.graph` |
| `personal.py` | Personal memory — user profile, preferences, rules, and relationship context. | `PersonalMemory` | `brain.memory.graph` |
| `journal.py` | Daily journal — structured daily summaries with event logging, auto-summarization, and weekly reviews. | `DailyJournal` | `brain.memory.graph` |
| `graph.py` | Knowledge graph — SQLite-backed graph with nodes, edges, and Obsidian-style bidirectional links. | `KnowledgeGraph`, `Node`, `Edge`, `graph` | `sqlite3` |
| `consolidation.py` | Memory consolidation — compresses raw conversation data into episodic memories and personal patterns. | `MemoryConsolidation` | `brain.memory.*` |
| `extractor.py` | Auto-extracts knowledge from conversations into the graph. | `KnowledgeExtractor` | `brain.memory.graph` |
| `importance.py` | Importance scorer — decides what deserves long-term memory based on explicit signals and context. | `ImportanceScorer` | stdlib only |
| `note.py` | Markdown notes with Obsidian-style `[[bidirectional links]]` for persistent knowledge. | `NoteManager` | `brain.memory.graph` |
| `retrieval.py` | Memory retrieval engine — detects intent, selects memory types, ranks by relevance, compresses for context. | `MemoryRetrieval` | `brain.memory.*` |

### `jarvis/brain/` — Top-Level Brain Modules

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `llm.py` | Unified LLM interface using httpx (no openai dependency). NVIDIA/OpenAI-compatible APIs with configurable timeouts. | `LLM`, `LLMResponse` | `httpx`, `core.reliability` |
| `loop.py` | Living Brain — permanent background intelligence loop. Observes environment, proposes actions, never acts autonomously. | `LivingBrain` | `brain.core`, `brain.living_models` |
| `rag.py` | RAG memory — Retrieval-Augmented Generation assembling context from conversations, knowledge graph, and skills. | `RAGMemory`, `ContextAssembly` | `brain.memory` |
| `skills.py` | Skill learning — save and reuse successful task workflows as reusable skills. | `SkillManager`, `Skill` | `json`, `pathlib` |
| `skill_evolution.py` | Skill evolution — strategy variants, auto-pruning, skill composition, and outcome-driven refinement. | `SkillEvolution` | `brain.skills` |
| `dag_planner.py` | DAG task planner — complex multi-step mission planning with dependency resolution and critical path analysis. | `DAGPlanner`, `DAGTask`, `DAGPlan` | dataclasses |
| `model_router.py` | Model router — intelligent task-to-model routing based on type, latency, cost, and historical success rates. | `ModelRouter`, `RoutingDecision` | `core.capabilities` |
| `review.py` | Agent review pipeline — quality gate after task completion. Reviews results for correctness before returning to user. | `ReviewPipeline`, `ReviewResult` | dataclasses |
| `speculative.py` | Speculative planner — predicts next steps and pre-delegates tasks to reduce perceived latency. | `SpeculativePlanner` | `brain.teams` |
| `teams.py` | Dynamic teams — on-the-fly agent team formation and mission timeline tracking. | `TeamManager`, `MissionTimeline` | dataclasses |
| `mission_executor.py` | Wires the DAG planner to the agent hierarchy. Delegates ready tasks to Kings, marks complete, emits events. | `MissionExecutor` | `brain.dag_planner`, `agents` |
| `memory_provider.py` | Pluggable memory architecture — unified MemoryProvider interface with SQLite backend, extensible to vector DBs. | `MemoryProvider`, `MemoryQuery` | `brain.memory` |
| `project_memory.py` | Project memory — remembers which project the user is working on, where code lives, and how to start it. | `ProjectMemory` | `sqlite3` |
| `world_model.py` | World model — tracks the user's computing environment: running apps, open files, system state. | `WorldModel` | `os`, `shutil`, `subprocess` |
| `privacy.py` | PII/privacy scrubber — detects and redacts sensitive info before external API calls. Regex-based, zero dependencies. | `PrivacyScrubber`, `scrubber` | `re` |
| `observability.py` | Centralized metrics, traces, and system health monitoring across all subsystems. | `Observability`, `MetricCollector` | `collections` |
| `aci.py` | Agent Communication Interface — typed messages, priority queues, message history, and broadcast for agent-to-agent comms. | `ACI`, `Message`, `MessageQueue` | `asyncio` |
| `developer.py` | Developer mode — debug endpoints, feature flags, and runtime state inspection. | `DeveloperMode` | `os` |
| `demo_learning.py` | Demo learning — learn from user demonstrations, abstract into reusable workflows, and replay with variations. | `DemoLearner` | `json` |
| `graph_analysis.py` | Knowledge graph v2 — auto entity/relation extraction, shortest path, community detection, PageRank. | `GraphAnalyzer` | `brain.memory.graph` |
| `graphify_integration.py` | Bridges Graphify knowledge graph output with JARVIS's graph analysis and visualization systems. | `GraphifyBridge` | `brain.graph_analysis` |
| `living_models.py` | Data structures for the background brain loop: predictions, proposals, observations. | `Prediction`, `Proposal`, `Observation` | dataclasses |

---

## 4. `jarvis/web/` — Web Interface

FastAPI application with routers, templates, static assets, and WebSocket real-time updates.

### `jarvis/web/` — Top Level

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `main.py` | FastAPI application factory with lifespan, static files, templates, and router mounting. | `create_app()`, `app` | `fastapi`, `uvicorn`, `jinja2` |
| `rate_limit.py` | In-memory token bucket rate limiter per IP address. | `RateLimiter`, `rate_limit()` | `collections` |
| `rate_limit_middleware.py` | Rate limiting middleware applied to all API endpoints. | `RateLimitMiddleware` | `starlette` |
| `__init__.py` | Package export: `create_app`. | — | — |

### `jarvis/web/routers/` — API Routers

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `chat.py` | Chat endpoint — user communication with JARVIS via streaming responses. | `chat()` | `fastapi` |
| `agents.py` | Agent status and hierarchy endpoints. | `get_agents()`, `get_agent()` | `fastapi` |
| `command_center.py` | Unified command center API — missions, brain, agents, tools, and self-reflection data. | `CommandCenterRouter` | `fastapi` |
| `workspace.py` | Workspace router — unified mission tracking (v6.1.0). | `get_workspace()` | `core.database` |
| `computer.py` | Computer control API — mouse, keyboard, screen, browser actions. | `ComputerRouter` | `fastapi`, `computer` |
| `memory.py` | Memory API — working memory, episodes, personal memory, journal, consolidation. | `MemoryRouter` | `fastapi`, `brain.memory` |
| `voice.py` | Voice API — TTS and STT audio endpoints. | `VoiceRouter` | `fastapi`, `voice` |
| `settings.py` | Settings API — read and update JARVIS configuration. | `SettingsRouter` | `core.config` |
| `system.py` | System API — events, capabilities, and system status for v3.1. | `SystemRouter` | `fastapi` |
| `pages.py` | HTML template pages (v6.1.0) — serves the web UI. | `PagesRouter` | `jinja2` |
| `engineering.py` | Engineering API — CAD, PCB, embedded, and simulation operations. | `EngineeringRouter` | `fastapi`, `engineering` |
| `iot.py` | IoT API — manage ESP32/Arduino devices from JARVIS. | `IoTRouter` | `fastapi`, `iot.manager` |
| `websocket.py` | WebSocket endpoint for real-time agent status and Event Bus events. | `websocket_endpoint()` | `fastapi`, `core.events` |
| `world.py` | World model API — computing environment state. | `get_world()` | `brain.world_model` |

### `jarvis/web/api/` — Additional API

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `mission_replay.py` | Mission replay API — unified command center endpoints with graceful fallbacks. | `MissionReplayRouter` | `fastapi` |

### `jarvis/web/services/` — Backend Services

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `tts.py` | Voice engine service for the web interface with pluggable provider pattern. | `TTSService` | `subprocess`, `platform` |

### `jarvis/web/templates/` — HTML Templates (7 files)

`base.html`, `index.html`, `command_center.html`, `command-map.html`, `developer_dashboard.html`, `history.html`, `settings.html`

### `jarvis/web/static/` — Static Assets

| Directory | Contents |
|-----------|----------|
| `css/` | `style.css`, `command-map.css` |
| `js/` | `app.js`, `jarvis-core.js`, `command-map.js`, `card-visualization.js`, `living-interface.js`, `memory-galaxy.js`, `knowledge-graph.js`, `graph-3d.js`, `mission-dag.js`, `unified-timeline.js`, `explainability.js`, `department-identity.js`, `state-machine.js`, `audio-analyzer.js`, `voice.js` |
| `vendor/` | `three.min.js`, `EffectComposer.js`, `RenderPass.js`, `ShaderPass.js`, `CopyShader.js`, `LuminosityHighPassShader.js`, `UnrealBloomPass.js` |

---

## 5. `jarvis/workspace/` — Mission Workspace

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `manager.py` | Unified mission tracking and coordination (v6.1.0). Manages workspaces, tasks, and agent state. | `WorkspaceManager` | `core.models`, `core.database` |
| `__init__.py` | Package export: `WorkspaceManager`. | — | — |

---

## 6. `jarvis/computer/` — Computer Control

Safe computer interaction through a permission-gated manager with accessibility intelligence and vision.

### `jarvis/computer/` — Top Level

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `manager.py` | Central gateway for all computer control. Routes, permission-checks, logs, and emits events. | `ComputerManager` | `computer.*` |
| `controller.py` | Unified controller — handles browser, screen, mouse, search, and project memory in one interface. | `ComputerController` | `computer.browser`, `computer.mouse`, `computer.screen` |
| `actions.py` | Action models — risk levels, action results, and action records for the control subsystem. | `RiskLevel`, `ActionResult`, `ActionRecord` | dataclasses |
| `permissions.py` | Permission system — classifies every action into risk levels (SAFE→DANGEROUS) and enforces approval. | `PermissionSystem`, `RiskLevel` | `core.config` |
| `mouse.py` | Mouse and keyboard control via native macOS Accessibility commands. | `MouseController` | `subprocess` |
| `screen.py` | Screen capture and analysis. | `ScreenCapture` | `subprocess`, `pathlib` |
| `browser.py` | Browser automation via Playwright — navigation, interaction, screenshots. | `BrowserAutomation` | `playwright` |
| `search.py` | Web search via DuckDuckGo or Google with result parsing. | `WebSearch` | `aiohttp` |
| `observer.py` | Screen observer — active window detection, UI element inspection, screen capture for vision models. | `ScreenObserver` | `computer.accessibility` |
| `sandbox.py` | Sandboxed execution — temporary dirs, resource limits, output capture, rollback support. | `Sandbox` | `tempfile`, `subprocess` |

### `jarvis/computer/accessibility/` — Semantic UI Control

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `element.py` | UIElement — semantic representation of any on-screen UI element with type, role, state, bounds. | `UIElement`, `ElementType` | dataclasses |
| `base.py` | Abstract accessibility provider interface for cross-platform support. | `AccessibilityProvider` (ABC) | `abc` |
| `macos.py` | macOS Accessibility Provider — inspects UI via AppleScript/osascript. No external dependencies. | `macOSAccessibility` | `asyncio` |
| `linux.py` | Linux Accessibility Provider — stub for AT-SPI2 (not yet implemented). | `LinuxAccessibility` | — |
| `windows.py` | Windows Accessibility Provider — stub for UI Automation API (not yet implemented). | `WindowsAccessibility` | — |
| `manager.py` | AccessibilityManager — JARVIS's semantic eyes. Loads platform provider, maintains UI state. | `AccessibilityManager` | `computer.accessibility.*` |
| `tree.py` | AccessibilityTree — structured traversal and search of UI elements with find/filter methods. | `AccessibilityTree` | `computer.accessibility.element` |

### `jarvis/computer/applications/` — Application Profiles

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `base.py` | Application profile base — describes known UI patterns for each app (buttons, menus, shortcuts). | `ApplicationProfile`, `app_registry` | dataclasses |
| `chrome.py` | Google Chrome browser profile. | `profile` | `applications.base` |
| `vscode.py` | Visual Studio Code profile. | `profile` | `applications.base` |
| `terminal.py` | macOS Terminal.app profile. | `profile` | `applications.base` |
| `finder.py` | macOS Finder file manager profile. | `profile` | `applications.base` |
| `blender.py` | Blender 3D creation suite profile. | `profile` | `applications.base` |
| `fusion360.py` | Autodesk Fusion 360 CAD profile. | `profile` | `applications.base` |

### `jarvis/computer/providers/` — Platform Providers

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `macos.py` | macOS platform provider — AppleScript UI automation, screencapture, NSWorkspace. | `macOSProvider` | `os`, `subprocess` |

---

## 7. `jarvis/mission/` — Mission Pipeline

Legacy pipeline, now unified with workspace for v6.1.0.

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `mission.py` | Mission data model — represents a single autonomous mission with status, stages, and results. | `Mission`, `MissionStage`, `MissionStatus` | dataclasses |
| `manager.py` | MissionManager — persistent long-running mission lifecycle manager. | `MissionManager` | `json`, `pathlib` |
| `pipeline.py` | Autonomous Research & Execution Engine — 10-stage pipeline from goal understanding to verification. | `MissionPipeline` | `asyncio` |
| `loop.py` | AutonomousLoop — observe→understand→plan→act→verify→reflect→remember→improve cycle. | `AutonomousLoop` | `brain.core` |
| `replay/recorder.py` | MissionRecorder — records mission events to JSON files. | `MissionRecorder` | `json`, `pathlib` |
| `replay/replay.py` | MissionReplay — analyze and replay recorded missions for learning. | `MissionReplay` | `mission.replay.models` |
| `replay/models.py` | Mission replay data models — events, reports, and queries. | `MissionEvent`, `MissionReport`, `MissionEventType` | dataclasses |

---

## 8. `jarvis/browser/` — Secure Browser Automation

Centralized browser management through BrowserManager with security checks.

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `manager.py` | Central gateway — every browser action goes through BrowserManager → Security Check → Playwright → Extraction → Memory. | `BrowserManager` | `browser.*` |
| `playwright_provider.py` | Playwright wrapper — browser launch, navigation, element interaction, screenshots, cookies. | `PlaywrightProvider` | `playwright` |
| `security.py` | Browser security — permission rules for web actions with risk levels (SAFE→DANGEROUS). | `BrowserSecurity` | `computer.permissions` |
| `extractor.py` | Webpage extractor — pulls structured data: title, text, links, forms, tables, images. | `PageExtractor` | `playwright` |
| `browser_state.py` | Browser state tracking — current URL, navigation history, tabs, active elements, downloads. | `BrowserState` | dataclasses |
| `sessions.py` | Persistent browser sessions — cookies, login state, multiple profiles, database-backed. | `SessionManager` | `sqlite3` |

---

## 9. Other Top-Level Modules

### `jarvis/browser/` — (see section 8)

### `jarvis/brain/` — (see section 3)

### `jarvis/vision/` — Computer Vision

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `manager.py` | VisionManager — unified vision interface coordinating capture, analysis, detection, grounding, and memory. | `VisionManager` | `vision.*` |
| `analyzer.py` | Vision Analyzer — understands what's on screen by combining screenshots with vision model analysis. | `VisionAnalyzer` | `vision.providers` |
| `detector.py` | Object Detector — finds specific UI elements (buttons, menus) in screenshots. | `ObjectDetector` | `vision.providers.base` |
| `grounding.py` | Grounding engine — converts visual understanding into actionable click/type commands. | `GroundingEngine` | `computer.manager` |
| `screenshot.py` | Screenshot capture — full screen, app window, and region capture with metadata. | `ScreenshotCapture` | `subprocess` |
| `memory.py` | Vision Memory — stores screenshot history, visual workflows, and object location caches. | `VisionMemory` | `json` |
| `providers/base.py` | Abstract vision provider interface for pluggable model backends. | `VisionProvider` (ABC), `VisionResult`, `DetectedObject` | `abc` |
| `providers/cloud.py` | Cloud vision — NVIDIA and OpenAI-compatible APIs (GPT-4V, etc.). | `CloudVisionProvider` | `httpx` |
| `providers/local.py` | Local vision — Ollama (LLaVA, Qwen2.5-VL, MiniCPM-V). | `LocalVisionProvider` | `httpx` |

### `jarvis/voice/` — Speech I/O

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `stt.py` | Speech-to-Text interface. | `SpeechToText` | `pathlib` |
| `tts.py` | Text-to-Speech supporting multiple backends (macOS say, espeak). | `TextToSpeech` | `subprocess`, `platform` |

### `jarvis/os/` — OS Integration

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `manager.py` | Unified OS control interface — orchestrates notifications, clipboard, hotkeys, menubar, and file watching. | `OSManager` | `os.*` |
| `clipboard.py` | Clipboard management — read, write, and monitor the system clipboard with history. | `ClipboardManager` | `subprocess` |
| `hotkeys.py` | Global hotkey registration and handling via macOS shortcuts. | `HotkeyManager` | `subprocess` |
| `notifications.py` | macOS notification system — sends system notifications via osascript. | `NotificationManager` | `subprocess` |
| `menubar.py` | Menu bar manager — display status items in the macOS menu bar. | `MenuBarManager` | `subprocess` |
| `watcher.py` | File system watcher — monitor directories for changes using polling. | `FileWatcher` | `os`, `pathlib` |

### `jarvis/knowledge/` — Second Brain Knowledge Graph

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Second Brain data models — entities, relationships, importance levels. | `EntityType`, `Entity`, `Relationship`, `ImportanceLevel` | dataclasses |
| `graph.py` | SQLite-backed KnowledgeGraph with CRUD, traversal, and search. | `KnowledgeGraph` | `sqlite3` |
| `relationships.py` | Relationship engine — creation, traversal, strengthening, and suggestion of connections. | `RelationshipEngine` | `knowledge.graph` |

### `jarvis/second_brain/` — Semantic Search

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Search data models — query, results, stats with keyword/semantic/graph modes. | `SearchQuery`, `SearchResult`, `SearchMode` | dataclasses |
| `search.py` | Semantic search engine over the knowledge graph with keyword, graph-traversal, and hybrid modes. | `SecondBrainSearch` | `knowledge.graph` |

### `jarvis/self_improvement/` — Self-Debugging & Learning

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Self-improvement data models — error records, recovery plans, lessons, severity levels. | `ErrorRecord`, `RecoveryPlan`, `Lesson`, `ErrorSeverity` | dataclasses |
| `error_memory.py` | Persistent error storage and pattern recognition across sessions. | `ErrorMemory` | `json`, `sqlite3` |
| `lessons.py` | Lesson engine — extract, store, and apply lessons from errors and experience. | `LessonEngine` | `json` |
| `recovery.py` | Auto-recovery — diagnose errors, apply fixes, manage dependencies. | `AutoRecovery` | `subprocess`, `shutil` |

### `jarvis/plugins/` — Plugin SDK

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Plugin data models — manifest, metadata, and type registry (TOOL, AGENT, ROUTER, etc.). | `Plugin`, `PluginManifest`, `PluginType` | dataclasses |
| `manager.py` | PluginManager — discover, load, and execute JARVIS plugins from filesystem. | `PluginManager` | `importlib`, `pathlib` |

### `jarvis/tools/` — Tool Intelligence

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Tool intelligence data models — categories (CAD, PCB, firmware, etc.), capabilities. | `ToolInfo`, `ToolCapability`, `ToolCategory` | dataclasses |
| `registry.py` | Tool registry — manages JARVIS tool knowledge and recommendations. | `ToolRegistry` | `json`, `pathlib` |

### `jarvis/privacy/` — Privacy Controls

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Privacy data models — settings, audit entries, access controls. | `PrivacySettings`, `AuditEntry` | dataclasses |
| `manager.py` | Privacy Manager — controls observation permissions and maintains an immutable audit trail. | `PrivacyManager` | `json`, `os` |

### `jarvis/memory_privacy/` — Memory Privacy

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Memory privacy data models — forgotten topics, privacy levels, audit entries. | `MemoryPrivacySettings`, `PrivacyLevel`, `AuditEntry` | dataclasses |
| `manager.py` | Controls what gets remembered and forgotten. Manages forgotten topics and export data. | `MemoryPrivacyManager` | `json` |

### `jarvis/preferences/` — Preference Learning

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Preference data models — categories, confidence scores, profiles. | `Preference`, `PreferenceCategory`, `PreferenceProfile` | dataclasses |
| `engine.py` | Preference learning engine — tracks user preferences with confidence scores and auto-bootstrap. | `PreferenceEngine` | `json` |

### `jarvis/decisions/` — Decision Memory

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Decision memory data models — impact levels, categories, outcomes. | `Decision`, `DecisionImpact`, `DecisionQuery` | dataclasses |
| `engine.py` | Decision memory engine — records, queries, and evolves past decisions. | `DecisionEngine` | `json` |

### `jarvis/learning/` — Continuous Learning

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Learning data models — records and skill updates from missions. | `LearningRecord`, `SkillUpdate` | dataclasses |
| `engine.py` | Continuous Learning Engine — learn from every completed mission. | `LearningEngine` | `json`, `hashlib` |

### `jarvis/consolidation/` — Memory Consolidation

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Consolidation data models — actions, results, duplicate groups. | `ConsolidationAction`, `ConsolidationResult`, `DuplicateGroup` | dataclasses |
| `engine.py` | Memory consolidation engine — deduplication, merging, and cleanup of stored memories. | `ConsolidationEngine` | `asyncio`, `json` |

### `jarvis/extraction/` — Memory Extraction

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Extraction data models — types (fact, decision), importance levels. | `ExtractedType`, `ImportanceLevel`, `ExtractionResult` | dataclasses |
| `extractor.py` | Automatic knowledge extraction from conversations into the memory system. | `MemoryExtractor` | `json`, `re` |

### `jarvis/context/` — Context Engine

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Context data models — CurrentContext for tracking environment state. | `CurrentContext` | dataclasses |

### `jarvis/safety/` — Safety Validation

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `validator.py` | Safety validator — checks operations against safety rules before execution. | `SafetyValidator` | `re`, `core.config` |

### `jarvis/engineering/` — Hardware Engineering Suite

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `knowledge.py` | Engineering knowledge base — materials, formulas, and component databases. | `Material`, `Formula` | dataclasses |
| `cad/base.py` | Abstract CAD provider — Fusion 360, Onshape, Blender, Tinkercad, OpenSCAD interfaces. | `CADProvider` (ABC) | `abc` |
| `pcb/base.py` | Abstract PCB provider — KiCad, EasyEDA, Fusion Electronics, Altium interfaces. | `PCBProvider` (ABC) | `abc` |
| `embedded/base.py` | Abstract embedded provider — Arduino, ESP32/PlatformIO, Raspberry Pi, STM32, MicroPython. | `EmbeddedProvider` (ABC) | `abc` |
| `mechanical/base.py` | Abstract mechanical provider — materials, fasteners, bearings, gears, motion calculations. | `MechanicalProvider` (ABC) | `abc` |
| `simulation/base.py` | Abstract simulation provider — thermal, stress, kinematic, circuit simulation interfaces. | `SimulationProvider` (ABC) | `abc` |

### `jarvis/iot/` — IoT Device Integration

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `manager.py` | IoT Device Manager — discovers and controls ESP32/Arduino devices via mDNS or manual config. | `DeviceManager` | `json` |
| `protocol.py` | IoT communication protocol — HTTP JSON over WiFi between JARVIS and ESP32 devices. | `IoTProtocol` | `aiohttp` |
| `arduino_library/` | Arduino library `JarvisIoT` — C++ library for ESP32/Arduino with examples (BasicCommand, SensorMonitor, ServoControl). | — | C++ |

### `jarvis/monitoring/` — Self-Monitoring

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Monitoring data models — component health, status, metric snapshots. | `ComponentStatus`, `ComponentHealth`, `HealthStatus`, `MetricSnapshot` | dataclasses |
| `monitor.py` | Monitor — self-monitoring and diagnostics engine with memory tracking and health checks. | `Monitor` | `tracemalloc`, `os` |

### `jarvis/dashboard/` — Engineering Dashboard

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Dashboard data models — metrics, health reports, and code quality issues. | `HealthIssue`, `HealthReport`, `ProjectMetrics` | dataclasses |
| `collector.py` | Dashboard collector — orchestrates all analyzers into ProjectMetrics. | `Dashboard` | `dashboard.analyzers` |
| `analyzers.py` | Specialized code analyzers — health, tests, security, performance, complexity. | `CodeHealthAnalyzer`, `ComplexityAnalyzer`, `SecurityAnalyzer` | `ast`, `hashlib` |

### `jarvis/living_dashboard/` — Real-Time Dashboard

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Living Dashboard data models — worker status, subsystem health. | `WorkerStatus` | dataclasses |
| `manager.py` | Aggregates data from all JARVIS subsystems into a single WebSocket-ready dashboard payload. | `LivingDashboardManager` | `os` |

### `jarvis/eng_intel/` — Engineering Intelligence

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Engineering Intelligence data models — issue categories, severity levels. | `IssueCategory` | dataclasses |
| `engine.py` | Eight built-in analyzers for continuous code analysis — duplication, naming, docs, complexity, dead code, stale APIs, missing tests, architectural drift. | `EngIntelEngine` | `ast`, `hashlib` |

### `jarvis/refactoring/` — Refactoring Engine

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Refactoring data models — issue categories, risk levels, severity, proposals. | `IssueCategory`, `RiskLevel`, `Severity`, `RefactorProposal` | dataclasses |
| `engine.py` | Autonomous refactoring engine — scans codebases and generates proposals (never auto-applies). | `RefactoringEngine` | `ast`, `hashlib` |

### `jarvis/repo_intelligence/` — Repository Intelligence

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Repository data models — dependency nodes, project profiles. | `DependencyNode` | dataclasses |
| `analyzer.py` | Analyzes any Git repository and produces a comprehensive project profile. | `RepoAnalyzer` | `ast`, `glob` |

### `jarvis/codebase_index/` — Codebase Indexing

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Indexing data models — symbols, files, and search results. | `IndexEntry`, `SymbolInfo` | dataclasses |
| `indexer.py` | Main codebase indexing engine — indexes every symbol in a repository for fast search. | `CodebaseIndexer` | `ast`, `os` |
| `search.py` | Search engine for the codebase index — fuzzy matching, symbol lookup. | `CodebaseSearch` | `difflib`, `re` |

### `jarvis/docs_engine/` — Documentation Engine

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Documentation data models — module docs, project docs. | `ModuleDoc`, `ProjectDocs` | dataclasses |
| `engine.py` | Auto-generates project documentation from source code analysis. | `DocsEngine` | `ast`, `pathlib` |

### `jarvis/journal/` — Daily Journal

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Journal data models — event categories, daily entries, weekly reviews. | `EventCategory` | dataclasses |

### `jarvis/projects/` — Project Awareness

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Project data models — build status, project registry. | `BuildStatus` | dataclasses |

### `jarvis/timeline/` — Personal Timeline

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Timeline data models — event types, queries, summaries. | `TimelineEvent`, `TimelineEventType`, `TimelineQuery` | dataclasses |
| `engine.py` | Timeline engine — stores and queries personal events chronologically with natural language queries. | `TimelineEngine` | `json`, `datetime` |

### `jarvis/suggestions/` — Smart Suggestions

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Suggestion data models — categories, confidence scores. | `SuggestionCategory` | dataclasses |

### `jarvis/architecture_graph/` — Architecture Visualization

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `models.py` | Architecture graph data models — nodes, edges, modules. | `ArchNode`, `ArchEdge` | dataclasses |
| `analyzer.py` | Analyzes repository structure for architecture visualization. | `ArchAnalyzer` | `ast` |
| `graph.py` | Builds a live architecture graph of any repository. | `ArchitectureGraph` | `json` |

### `jarvis/planner/` — Architecture Planner

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `__init__.py` | Takes research findings and tool candidates, produces structured ArchitecturePlan with modules, files, dependencies, and estimates. | `ArchitecturePlanner` | — |

### `jarvis/research/` — Research Engine

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `__init__.py` | Automated research and tool discovery across GitHub repositories and PyPI packages. | `ResearchEngine` | — |

### `jarvis/execution/` — Execution Engine

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `__init__.py` | Executes architecture plans via code generation and automated review (lint, type, format checks). | `ExecutionEngine` | — |

### `jarvis/review/` — Self Review

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `__init__.py` | Post-mission review and learning extraction — reviews outcomes and identifies improvements. | `SelfReview` | — |

### `jarvis/testing/` — Testing Engine

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `__init__.py` | Automated test generation, execution, and repair. Generates comprehensive tests and auto-repairs failures. | `TestingEngine` | — |

### `jarvis/verification/` — Verification Engine

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `__init__.py` | Verifies implementations via browser rendering checks and vision analysis. | `VerificationEngine` | — |

### `jarvis/memory/` — Memory Package

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `__init__.py` | Package re-export of `Database` and `get_db` from core. | — | `core.database` |

### `jarvis/cli.py` — Terminal UI

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `cli.py` | JARVIS TUI — full-screen terminal user interface with Rich console. | `JARVISTUI` | `rich` |

### `jarvis/cli_v2.py` — Developer CLI

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|-------------|
| `cli_v2.py` | Developer CLI (v5.2.0) — `jarvis doctor`, dev commands. | `cli()` | `rich` |

---

## Dependency Graph (High Level)

```
web/ ──→ routers/ ──→ agents/ ──→ brain/ ──→ core/
                              │         │
                              │         ├──→ brain/memory/
                              │         ├──→ brain/core/
                              │         └──→ brain/llm.py
                              │
                              ├──→ computer/ ──→ core/
                              ├──→ browser/ ──→ computer/
                              ├──→ vision/ ──→ computer/
                              ├──→ iot/
                              ├──→ engineering/
                              ├──→ os/
                              └──→ tools/
```

**Core** is the foundation. **Brain** is the intelligence. **Agents** orchestrate. **Web** exposes everything.
