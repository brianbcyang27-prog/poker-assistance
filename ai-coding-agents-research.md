# AI Coding Agents & Assistants: Architecture Research

## 1. Claude Code (Anthropic)

**Core Architecture:** A simple ReAct-pattern while-loop (`assemble context → call model → dispatch tools → check permissions → execute → repeat`). Only ~1.6% of the codebase is AI decision logic; the other 98.4% is operational infrastructure (permissions, context management, tool routing, recovery).

**Tool Execution & Verification:**
- Model emits `tool_use` blocks; the harness parses, checks permissions, dispatches to tool implementations, and collects results
- Model never directly accesses filesystem, runs commands, or makes network requests — the `tool_use` protocol is the only interface
- Two execution paths: direct execution and subagent delegation
- 5 stop conditions: no tool use, max turns, context overflow, hook intervention, explicit abort

**Permissions & Safety:**
- **Deny-first** rule evaluation: deny > ask > allow. A broad deny always overrides a narrow allow
- **7 permission modes**: `plan` → `default` → `acceptEdits` → `auto` (ML classifier) → `dontAsk` → `bypassPermissions` (+ internal `bubble`)
- **Auto-mode classifier** (`yoloClassifier.ts`): Separate LLM call with internal/external permission templates. Two-stage: fast-filter + chain-of-thought
- **7 independent safety layers**: tool pre-filtering → PreToolUse hooks → deny-first rule evaluation → permission handler → sandboxing → connector controls → circuit breakers
- OS-level sandboxing (Linux bubblewrap, macOS seatbelt) for filesystem and network isolation
- Permissions are never restored on resume — trust re-established per session
- `bypassPermissions` still has circuit breakers for `rm -rf /` and `rm -rf ~`

**Context/Memory:**
- **5-layer compaction pipeline** (cheapest first): Budget Reduction → Snip → Microcompact → Context Collapse → Auto-Compact
- Context Collapse uses read-time projection (non-destructive); Auto-Compact is the last resort (full model summary)
- Subagent sidechain transcripts: only summaries return to parent (parent context protected from subagent verbosity)
- Append-oriented session storage

**Notable UX Patterns:**
- Plan mode: explore and plan without editing source files
- Subagent delegation with 6 built-in types (Explore, Plan, General-purpose, Guide, Verification, Statusline) + custom agents via `.claude/agents/*.md`
- Dynamic workflows: fan out to up to 16 concurrent and 1,000 total subagents
- Session-scoped permission state (never restored on resume)

**What Makes It Reliable:**
- Deny-first with defense-in-depth — safety does not depend on human vigilance
- Sandboxing reduces permission prompts by 84%
- Users approve ~93% of permission prompts, so the system must be safe independent of user attention

**Key Insight:** The agent loop is trivially simple. All the engineering complexity lives in the systems *around* the loop — permission gates, context management, tool routing, and recovery. Only 1.6% of code is AI decision logic.

---

## 2. Cursor

**Core Architecture:** Three-layer vertically integrated inference stack:
1. **Context Engine** — AST-based indexing, vector search, dependency graph, reranking
2. **Priompt** — Priority-based prompt budgeting (JSX components with priority scores, binary search for overflow)
3. **Model Ensemble** — Tab model (autocomplete), Fast Apply model (Llama-3-70B fine-tuned), Composer (MoE proprietary), frontier models for reasoning

**Tool Execution & Verification:**
- **Full-file rewrites** instead of diffs — deterministic matching against diffs fails ~40% of the time
- **Speculative edits**: Uses the original file as draft tokens; unchanged regions accept dozens of tokens per pass. ~1,000 tokens/sec (13x speedup)
- **Three-stage pipeline**: Indexer (embeds repo, retrieves context) → Planner LLM (writes terse edit hints per file) → Apply Model (turns hints into exact diffs via speculation)
- Multi-file edits run `(planner hint → Apply Model)` pairs in parallel
- Orchestrator runs consistency checks after parallel application; follow-up loop if checks fail

**Context Management:**
- Tree-sitter AST parsing at function/class boundaries (not arbitrary chunks)
- Merkle tree of file hashes synced every 5 minutes for incremental re-indexing
- Two-tier index: persisted index (file save) + in-memory delta (currently-open file)
- CodeLlama reranker processes up to 500K tokens per query with blob-storage KV caching
- No actual code stored on servers — only embeddings

**Permissions & Safety:**
- Shadow workspace: hidden VS Code window where AI edits are applied independently
- LSP usability: AI sees lints from its changes, can go to definitions
- Runnability: AI can run code and see output
- Shadow window killed after 15 minutes of inactivity
- Plan for FUSE-level folder proxy for perfect disk isolation

**Notable UX Patterns:**
- Speculative tab completions (sub-300ms)
- Inline diff overlays
- Background Agents
- Shadow workspace for independent iteration

**What Makes It Reliable:**
- Multi-file coherence is an architecture problem, not a model problem
- Split "decide" from "execute" — big models decide, small fine-tuned models execute
- The indexer is half the magic — always-on structure-aware index prevents reasoning against stale context

**Key Insight:** Context is an infrastructure challenge, not a prompt problem. Treat retrieval as a first-class engineering problem with indexing, embedding, caching, reranking, and priority-based budgeting.

---

## 3. OpenHands (formerly OpenDevin)

**Core Architecture:** Event-sourced state model with three main components:
1. **Agent** — Stateless reasoning-action loop (single-step `step()` execution)
2. **Event Stream** — Chronological collection of actions and observations
3. **Runtime** — Docker-sandboxed execution environment

**Tool Execution & Verification:**
- **Action–Execution–Observation** pattern: LLM generates JSON tool calls → validated into ActionEvent → executed → ObservationEvent returned
- Tools are typed (Action + Observation + ToolExecutor), auto-generate JSON schemas for LLM tool calling
- Registry-based resolution: tools are lightweight spec objects that cross process boundaries as pure JSON
- Two execution modes: **Direct** (immediate) and **Confirmation** (wait for user approval)
- **Security Analyzer** evaluates each action before execution: Low Risk (execute), Medium Risk (execute with monitoring), High Risk (block, request confirmation)

**Permissions & Safety:**
- Docker container isolation for each task session
- OS-level sandboxing (bubblewrap, seccomp on Linux; seatbelt on macOS)
- Input validation, command sanitization, path traversal prevention, resource limits
- V1 made sandboxing opt-in rather than universal (aligns with MCP assumptions)
- Defense-in-depth with fail-safe rejection

**Context/Memory:**
- **Condensers** for history compression when token limits approached
- Event-sourced state: deterministic replay from event history
- Multi-agent delegation via `AgentDelegateAction` (e.g., generalist delegates browsing to specialist)
- Skills: behavior modules that shape LLM prompts

**Notable UX Patterns:**
- Conversation factory: same code runs interactively in notebook or scales to distributed production
- Built-in REST/WebSocket server for remote execution
- Workspace interfaces: browser-based VS Code IDE, VNC desktop, persistent Chromium browser
- Agent Server: serialized config sent to remote, streams structured events back

**What Makes It Reliable:**
- Stateless agent design: holds no mutable state between steps
- Event-driven: reads from event history, writes new events
- Interruptible: each step is atomic, supports pause/resume
- AgentHub: community-contributed agents in a shared ecosystem

**Key Insight:** Sandboxing should be opt-in, not universal. The SDK unifies agent and tool execution in a single process by default, with containerization available when isolation is needed.

---

## 4. Devin

**Core Architecture:** Planner-executor split as separate LLM calls with different prompts, context budgets, and models. The most important architectural choice that most copy-cat projects skip.

```
PLANNER → decomposes ticket → structured JSON plan → runs ~once per major phase
EXECUTOR → runs one plan step at a time → decides tool calls → reports back
SHELL → bash, file I/O, git, test runners
BROWSER → headless Chrome, DOM observations
KNOWLEDGE → curated facts, user tips, past distillations
```

**Tool Execution & Verification:**
- Executor sees current step, relevant slice of working memory, and available tools
- Does NOT re-derive the plan — its only output is tool call, sub-result, or step status
- **Deterministic signals over critic LLMs**: tests, lint, type checks, HTTP/shell exit codes
- Recovery loop leans on hard signals — the world tells you about failures more reliably than any LLM critic
- Video recordings of end-to-end test runs as proof

**Permissions & Safety:**
- Sandboxed ephemeral VM per run — fresh VM each time
- Persistent state only what Devin explicitly writes to Knowledge or checks into repo
- Eliminates "agent modified global state and next run is broken" failures
- User can adjust auto-proceed timeout (default 30 seconds)

**Context/Memory (Critical Design):**
- **4 distinct memory layers**:

| Layer | Holds | Lifetime | Pruning |
|-------|-------|----------|---------|
| Working memory | Recent tool calls + results for current step | Single executor step | Cleared at step boundary |
| Step summaries | One-paragraph distillation of each completed step | Current run | Compressed when plan changes |
| Run scratchpad | Files agent decided to keep around | Current run | Explicit `forget` tool clears it |
| Knowledge | User-confirmed facts, past distillations | Across runs | Hand-curated; not auto-appended |

- Executor prompt **only ever sees** working memory + step summaries + current plan + current step
- Full trajectory is **never re-fed** to the model
- Knowledge layer is the sharpest departure from "fully autonomous" — user-curated facts

**Notable UX Patterns:**
- Interactive Planning: initial assessment → detailed plan with code citations → user approval
- Plan stored as JSON in persistent state (inspectable, editable in UI, survives crashes)
- Skills: PRs that refine instructions for future sessions
- Security Swarm: Agentic MapReduce for whole-codebase scanning

**What Makes It Reliable:**
- Heavy compute at plan boundaries; lean compute between them
- Planner invoked every few executor steps, not every turn, with compressed summary
- Plan is inspectable, editable, and durable — not freeform text in a conversation
- Knowledge is curated, not auto-appended

**Key Insight:** Deterministic checks beat critic LLMs. When the world gives you signal (exit codes, test results, HTTP status), use it — don't ask another LLM what the first one got wrong. Also: the most interesting thing about Devin is how *un-autonomous* it chose to be — constraint, structure, and human-editable state at every turn.

---

## 5. Manus

**Core Architecture:** Imperative ReAct-style outer loop driving a long-lived cloud VM. Every task gets its own isolated Ubuntu VM (networking, filesystem, headless Chromium, shell). Typical task ~50 tool calls.

**Two execution modes:**
1. **Direct Agent** — ReAct pattern for straightforward requests
2. **Flow Orchestration** — Plan-driven for complex multi-step tasks (PlanningFlow separates planning from execution)

**Tool Execution & Verification:**
- **CodeAct pattern**: Model writes executable Python as its action mechanism (not tool calls through JSON schema)
- Prevents the model from "describing what it would do instead of doing it"
- Tool collection with standardized `ToolResult`
- Context-aware state machine for tool availability — masks token logits during decoding rather than adding/removing tools

**Context Management (Context Engineering):**
- **KV-cache hit rate** as the single most important metric (10x cost difference between cached and uncached tokens)
- Append-only context with deterministic serialization
- Stable prompt prefix — no timestamps precise to the second
- **File system as ultimate context**: unlimited, persistent, directly operable by the agent
- Compression strategies designed to be restorable (URL preserved when content dropped, path preserved when document omitted)

**Attention Manipulation:**
- **Standing State Injection**: rewrites `todo.md` each step so current objectives are recited into the end of context, avoiding "lost-in-the-middle"
- **Leave wrong turns in context**: failed actions and stack traces stay so the model adapts
- **Structured variation**: different serialization templates to break pattern repetition

**Permissions & Safety:**
- Fully-isolated cloud VM per task
- Sandboxes persist for hours, auto-sleep on idle, auto-wake on user return
- Wide Research: clone fan-out for parallel processing (up to 100+ sub-agents)

**Notable UX Patterns:**
- `todo.md` plan file maintained inside sandbox
- Wide Research for bulk parallel processing
- Browser Operator extension drives user's local browser
- Agent Resumption: auto-sleep/wake with file preservation

**What Makes It Reliable:**
- Context engineering over model capability
- KV-cache stability reduces latency and cost
- File-system-as-context avoids context window limitations
- Standing state injection prevents goal drift

**Key Insight:** If you had to choose one metric, KV-cache hit rate is the single most important for a production agent. Also: the file system is the ultimate context — unlimited, persistent, and directly operable by the agent itself. Design compression to be restorable.

---

## 6. Roo Code

**Core Architecture:** VS Code extension implementing the `Task` class which orchestrates AI-powered interactions through `recursivelyMakeClineRequests()`. Maintains two message arrays: `clineMessages` (UI) and `apiConversationHistory` (LLM).

**Tool Execution & Verification:**
- **Native tool calling protocol** (OpenAI-style function calling with `tool_use` blocks)
- Lock-based sequential processing (`presentAssistantMessageLocked`) prevents concurrent execution
- Every `tool_use` with an `id` MUST have a corresponding `tool_result` — strict protocol requirement
- Dynamic tool building: `buildNativeToolsArray()` combines native + MCP + custom tools
- `filterNativeToolsForMode()` restricts access based on mode configuration

**Permissions & Safety:**
- **Mode-based tool access**: Code Mode (full), Ask Mode (read-only), Architect Mode (design-focused), Custom Modes
- `.rooignore` (`.gitignore` syntax) prevents read/write to specific files
- `.rooprotected` forces approval for writes even with auto-approve enabled
- Auto-approval with pattern matching for commands (allow/deny lists)
- Consecutive mistake tracking: agent pauses and asks for help after threshold
- `ToolRepetitionDetector` monitors for repeating identical failures
- Shell command timeout management

**Context/Memory:**
- Two distinct message arrays: `clineMessages` (UI with timestamps, status updates) vs `apiConversationHistory` (strictly LLM format)
- Context overflow recovery: summarization first, then forced reduction (remove 25% of oldest messages)
- Checkpoint system: git-based version control for workspace snapshots and rollback

**Notable UX Patterns:**
- Mode switching (Code → Ask → Architect) changes available tools and persona
- User can provide feedback along with approval (merged into tool result)
- `new_task` for creating subtasks
- `switch_mode` for context switching
- Skills: predefined slash command workflows for complex multi-step operations

**What Makes It Reliable:**
- Mistake tracking prevents infinite loops
- Dual message arrays save tokens by excluding UI metadata from LLM context
- Checkpoint system enables rollback
- Mode-based access control limits blast radius

**Key Insight:** Separate what the user sees from what the AI receives. UI-specific metadata (timestamps, status updates) shouldn't consume LLM context tokens.

---

## 7. Cline

**Core Architecture:** VS Code extension with a layered SDK:
- `Agent` (stateless primitive) — core loop: `run() → model request → tool calls → tool results → repeat`
- `ClineCore` (full harness) — adds sessions, persistence, built-in tools, approval callbacks, scheduling

**Tool Execution & Verification:**
- Built-in tools: `bash`, `editor`, `read_files`, `apply_patch`, `search`, `fetch_web`, `ask_question`
- MCP tools loaded alongside built-ins
- Model marks each command with `requires_approval` flag based on command and arguments
- Custom tools via plugins

**Permissions & Safety:**
- **Tool policies** per tool: `{ autoApprove: true }`, `{ autoApprove: false }`, `{ enabled: false }`
- Default: enabled and auto-approve (must set policies explicitly for tools needing review)
- **Tiered permissions**: auto-approve reads, require approval for writes
- **Conditional approval logic**: approve based on what the tool is actually doing, not just which tool it is
- **YOLO Mode**: disables all safety checks — executes whatever it decides
- `.clineignore` for file access restrictions
- `CommandPermissionController` for shell execution restrictions
- **Checkpoint system**: shadow git repository for workspace snapshots, diff viewing, and rollback
- `validateWorkspacePath` prevents checkpoints in system directories
- Lifecycle hooks: pre/post-execution validation

**Context/Memory:**
- Message state kept internally by `AgentRuntime`
- `restore(messages)` for external persistence
- Rejection counts as a response — agent doesn't get stuck in a loop

**Notable UX Patterns:**
- Human-in-the-loop approval with feedback (denied tools get feedback text/images)
- Auto-approve with OS notifications for long-running commands
- SDK modes: `auto`, `hub`, `remote`, `local`
- Agent teams and multi-agent spawning

**What Makes It Reliable:**
- Rejection doesn't cause loops — it counts as a response
- Checkpoint system for safe rollback
- Conditional approval logic (context-aware, not just tool-name-based)

**Key Insight:** When a tool is rejected, the rejection counts as a response. The agent adjusts its approach rather than looping. This prevents the infinite-loop failure mode common in agent systems.

---

## 8. Open Interpreter

**Core Architecture:** Central `OpenInterpreter` class orchestrating message-passing between LLM and Computer. Four primary classes:
1. `OpenInterpreter` — central orchestrator, manages `messages` list
2. `Computer` — code execution through `run()` method
3. `Llm` — language model interface via `litellm`
4. Terminal interface — user interaction

**Tool Execution & Verification:**
- LLM generates code blocks → parsed by `respond()` function → executed via `computer.run()`
- Supports multiple languages through language detection from `format` field
- Hallucination pattern detection and correction (e.g., `executeexecute`, JSON-wrapped code)
- Output streaming with `active_line` tracking
- `max_output` limit (2800 chars) to prevent runaway output

**Permissions & Safety:**
- **Sandbox modes**: `read-only`, `workspace-write`, `danger-full-access`
- **Approval policies**: `untrusted` (ask before state changes), `on-request` (sandbox runs, ask before escalation), `never` (sandbox only)
- OS-level sandboxing: macOS seatbelt, Linux bubblewrap/seccomp
- Safe mode: Semgrep static analysis before execution
- `auto_run` disabled when `safe_mode` is enabled
- Confirmation chunks provide execution interception point
- Edit option allows code modification before execution

**Context/Memory:**
- `interpreter.messages` list maintains complete conversation history
- Automatic conversation persistence to disk
- Conversation history can be loaded and replayed

**Notable UX Patterns:**
- Streaming interface (generators yielding response chunks)
- Inline code execution with live output
- Loop mode with breakers ("The task is done.", "The task is impossible.")
- OS control mode for system-wide interaction
- Skills path for custom capabilities

**What Makes It Reliable:**
- Multiple safety layers: default human approval, optional scanning, conversation tracking, output limits
- Code editing before execution (middle ground between approve/deny)
- Denial message injection so LLM adjusts approach

**Key Insight:** The confirmation chunk is always generated by the response function, but whether it's displayed depends on `auto_run`. This creates a clean interception point that separates generation from execution.

---

## 9. Continue

**Core Architecture:** Four-layer message-passing architecture:
1. **IDE Layer** — Platform-specific extensions (VS Code, IntelliJ) implementing `IDE` interface
2. **Core Layer** — Business logic in `Core` class (80+ message types)
3. **Configuration Layer** — Multi-source config via `ConfigHandler` + profile management
4. **GUI Layer** — React + Redux shared across IDEs via webview

**Tool Execution & Verification:**
- Platform-agnostic `IDE` interface: file operations, editor manipulation, Git integration, LSP queries, UI interactions
- VS Code runs Core in-process (no serialization overhead)
- IntelliJ runs Core as separate Node.js process communicating via JSON over stdin/stdout
- Cancellable operations via `AbortController` map
- Typed protocol definitions with compile-time guarantees

**Context Management:**
- **Context Providers** (`IContextProvider` interface): retrieve data from various sources and package as `ContextItem` objects
- Built-in providers: `@file`, `@folder`, `@codebase`, `@terminal`, `@diff`, `@open`, `@url`, `@jira`, etc.
- `@codebase` uses retrieval pipeline: vector search → reranking → repo map retrieval (LLM selects 5-10 most relevant files)
- `RepoMapContextProvider` generates high-level repository structure overview
- MiniSearch for intelligent file sorting in submenus

**Model Routing:**
- `ILLM` interface and `BaseLLM` abstraction supporting 40+ AI providers
- `ConfigHandler` manages model configuration, profiles, MCP server integration
- Model fallback when unavailable
- Tab-autocomplete via `CompletionProvider` and `NextEditProvider`

**Notable UX Patterns:**
- `@` mentions to scope questions to specific context providers
- Pass-through routing for efficiency (webview ↔ Core without going through IDE)
- 70+ registered commands in VS Code
- TipTap-based rich chat input
- Hot reloading for development

**What Makes It Reliable:**
- Strict message protocol separation between layers
- Platform-agnostic Core with IDE-specific implementations
- Typed IPC codegen for compile-time guarantees across runtimes

**Key Insight:** The `IDE` interface abstraction is the key contract. By defining a common interface for file operations, editor manipulation, LSP queries, and UI interactions, the core logic remains platform-agnostic while platform-specific implementations handle the details.

---

## 10. Warp

**Core Architecture:** Block-based terminal model. Instead of one big character grid, Warp uses an ordered list of typed, self-contained blocks. Built in Rust with GPU-accelerated rendering (Metal on macOS, Vulkan on Linux).

**Block Model:**
- Each block wraps a command and its output as first-class data structures
- `BlockList`: ordered sequence of terminal blocks and rich content blocks
- `SumTree` for O(log n) viewport queries across thousands of blocks
- `FlatStorage` for efficient scrollback (no per-cell allocation)
- Shell integration hooks (`preexec`/`precmd`) for block boundary detection

**AI Integration:**
- **Input classification pipeline**: heuristic classifier → ONNX BERT-based model → decision logic
- Auto-detects whether input is shell command or natural language query
- Agent conversation blocks render inline alongside commands
- Commands agents run on your behalf show as compact summaries, expandable on demand
- `InputMode`: Shell or AI, with autodetection

**Tool Execution & Verification:**
- Slash command system: `/agent`, `/open-file`, `/handoff`, `/add-mcp`, `/skills`
- Queued prompt system: multiple prompts executed sequentially
- Reordering, inline editing, and immediate submission for queued prompts
- `SkillManager` for natural language inputs triggering specific agent routines

**Context Management:**
- Blocks as structured context: command, output, exit code, working directory, timestamp
- AI serializes block data (not raw text) for prompts
- Hidden blocks for background operations (e.g., tab completion generation)
- Secret detection and redaction in real-time

**Notable UX Patterns:**
- GPU-accelerated sub-16ms frame times
- Blocks as shareable links
- Semantic selection (bracket-pair matching)
- Inline agent conversations in the same scroll stream
- Open-source client with proprietary backend

**What Makes It Reliable:**
- Block model provides structure that traditional terminals lack
- Shell integration for accurate block boundary detection
- Virtualized rendering handles thousands of blocks

**Key Insight:** The block model's defining property is that the `BlockList` doesn't care what's inside a block — it only needs each block's height. This abstraction allowed the same system to grow from "better terminal" into an ADE without being reinvented.

---

## 11. Raycast AI

**Core Architecture:** Four-runtime hybrid architecture:
1. **Host app** — Native shell (Swift/AppKit on macOS, C#/.NET/WPF on Windows)
2. **Web frontend** — React + TypeScript (shared across platforms)
3. **Node backend** — Long-lived process for business logic, extension runtime
4. **Rust core** — Performance-critical: data layer, cloud sync schema, file indexer

**Tool Execution & Verification:**
- Extension system with V8 worker isolation per extension
- JSON-RPC protocol over stdio for cross-process communication
- Typed IPC codegen for compile-time guarantees across all four runtimes
- Extensions only send registered messages (no arbitrary calling into Raycast code)
- Rate limits on AI requests from extensions

**AI Integration:**
- AI Chat, Quick AI, AI Commands
- MCP server support (stdio and HTTP transports)
- `@`-mention scoping for tools and servers
- Custom AI extensions with Tools, Instructions, and Evals
- Model selection from 50+ models across providers (OpenAI, Anthropic, Google, Meta, Mistral, etc.)
- Automatic model fallback when unavailable

**Permissions & Safety:**
- MCP tools require approval by default (configurable per-server)
- Extension isolation via V8 workers with memory limits
- Extensions that get too greedy are stopped without warning
- Session IDs for cross-boundary communication
- OAuth handling for HTTP MCP servers

**Context/Memory:**
- Custom Rust file indexer: scans entire hard drives within seconds
- File system events for real-time index updates
- Extension-provided context via MCP servers
- Notes for persistent context

**Notable UX Patterns:**
- Sub-millisecond response times for launcher
- Hot reloading (UI changes in <1 second)
- Custom React reconciler for native rendering across process boundaries
- Translucent windows with native overlays
- One team, two platforms (macOS + Windows)

**What Makes It Reliable:**
- Four-runtime architecture with typed IPC codegen
- System WebView (not bundled Chromium) for native feel
- V8 worker isolation prevents extension crashes from affecting the app
- Custom reconciler bridges React to native AppKit/WPF

**Key Insight:** The custom React reconciler is the key architectural decision. By implementing a reconciler that translates React's virtual DOM to native AppKit/WPF components across process boundaries, Raycast gets web development speed with native performance. The reconciler computes a JSON representation, diffs with JSON Patch, and only sends minimal updates.

---

## Cross-Cutting Patterns

### Permission Models (Ranked by Sophistication)

| System | Model |
|--------|-------|
| Claude Code | Deny-first, 7 modes, ML classifier, hooks, OS sandboxing |
| Devin | Ephemeral VM per run, knowledge curated by user |
| OpenHands | Docker isolation, security analyzer (risk levels), opt-in sandboxing |
| Cline | Tool policies, conditional approval, checkpoint rollback |
| Roo Code | Mode-based access, `.rooprotected`, mistake tracking |
| Open Interpreter | Sandbox modes + approval policies, safe mode with Semgrep |
| Manus | Cloud VM isolation, tool-masking state machine |
| Cursor | Shadow workspace, LSP-based verification |
| Continue | IDE-level integration, no explicit permission model |
| Warp | Block-level isolation, secret detection |
| Raycast | Extension V8 isolation, MCP approval defaults |

### Context Management Patterns

| Pattern | Used By |
|---------|---------|
| File system as context | Manus, Devin, OpenHands |
| AST-based semantic chunking | Cursor |
| KV-cache optimization | Manus |
| Standing state injection (todo.md) | Manus, Devin |
| Layered compaction pipeline | Claude Code, Roo Code |
| Priority-based prompt budgeting | Cursor (Priompt) |
| Subagent summary isolation | Claude Code, Devin |
| Deterministic replay | OpenHands (event-sourced) |

### Verification Patterns

| Pattern | Used By |
|---------|---------|
| Deterministic signals over critic LLMs | Devin |
| LSP/lint feedback loops | Cursor, OpenHands |
| Git-based checkpoints/rollback | Cline, Roo Code |
| Test execution as verification | Devin, OpenHands |
| Video recording as proof | Devin |
| Shadow workspace for independent iteration | Cursor |
| Security analyzer (risk levels) | OpenHands |

### Key Architectural Decisions

1. **Separate planning from execution** (Devin, Manus, Claude Code) — different prompts, context budgets, and models for each
2. **Deny-first with defense-in-depth** (Claude Code) — safety independent of human vigilance
3. **Structure-aware indexing** (Cursor) — AST parsing at semantic boundaries, not arbitrary chunks
4. **File system as unlimited context** (Manus) — externalized memory beyond context windows
5. **Speculative execution against original** (Cursor) — use existing content as draft tokens
6. **Event-sourced state** (OpenHands) — deterministic replay from immutable event history
7. **Block-based terminal** (Warp) — treating commands as data structures enables AI integration
8. **Typed IPC across runtimes** (Raycast) — compile-time guarantees for multi-runtime architecture
