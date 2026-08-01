# System Dependency Map

> **Version:** 1.0.0
> **Date:** 2026-07-30
> **Base:** JARVIS v8.0.0
> **Status:** Pre-Phase 0 Analysis

---

## 1. High-Level Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (Browser)"]
        SPA["Single Page App
base.html + app.js + state-machine.js"]
        WS["WebSocket
ws-manager.js"]
        HUD["Living Interface
living-interface.js"]
    end

    subgraph API["API Layer (FastAPI)"]
        ROUTERS["16 Routers
~150 endpoints"]
        API_MOD["API Module
api/__init__.py"]
        WS_HANDLER["WebSocket Handler
websocket.py"]
    end

    subgraph Agents["Agent System"]
        JARVIS["JARVIS Agent
jarvis.py"]
        KINGS["4 Division Kings
👑 Engineering 👑 Personal
👑 Research 👑 System"]
        WORKERS["23 Specialized Workers
♠♥♦♣ hierarchy"]
        TOOLS["Tool Layer
tools/unified.py + registry"]
    end

    subgraph Brain["Brain / AI"]
        LLM["LLM Client
llm.py"]
        MEMORY["Memory System
working/episodic/personal/journal"]
        RAG["RAG Engine
rag.py"]
        ACI["Agent Communication
aci.py"]
        DAG["DAG Planner
dag_planner.py"]
        CONTEXT["Context Builder
brain/core/context.py"]
    end

    subgraph Core["Core Infrastructure"]
        DB["Async SQLite
core/database.py"]
        CONFIG["Config
core/config.py"]
        EVENTS["Event Bus
core/events.py"]
        DIAG["Diagnostics
core/diagnostics.py"]
        MODELS["Shared Models
core/models.py"]
    end

    subgraph Systems["System Modules"]
        COMPUTER["Computer Control
computer/"]
        BROWSER["Browser Automation
browser/"]
        VOICE["Voice I/O
voice/"]
        VISION["Vision System
vision/"]
        SECURITY["Security Layer
security/"]
        OS["OS Integration
os/"]
        IOT["IoT Devices
iot/"]
    end

    subgraph Workspace["Workspace / Mission"]
        WS_MGR["Workspace Manager
workspace/manager.py"]
        MISSION["Mission Pipeline
mission/"]
        REPLAY["Mission Replay
mission/replay/"]
    end

    SPA --> ROUTERS
    SPA --> WS
    WS --> WS_HANDLER
    HUD --> WS
    ROUTERS --> API_MOD
    API_MOD --> LLM
    API_MOD --> MEMORY
    API_MOD --> WS_MGR
    API_MOD --> COMPUTER
    API_MOD --> BROWSER
    API_MOD --> VOICE
    API_MOD --> VISION

    WS_HANDLER --> JARVIS
    JARVIS --> KINGS
    KINGS --> WORKERS
    WORKERS --> TOOLS
    TOOLS --> COMPUTER
    TOOLS --> BROWSER
    TOOLS --> VISION
    TOOLS --> MISSION

    WS_HANDLER --> LLM
    WS_HANDLER --> MEMORY

    LLM --> CONTEXT
    CONTEXT --> MEMORY
    MEMORY --> DB
    RAG --> MEMORY
    ACI --> KINGS

    JARVIS --> LLM
    JARVIS --> DAG
    DAG --> MISSION
    MISSION --> WS_MGR

    EVENTS --> DB
    EVENTS --> WS_HANDLER
    CONFIG --> MODELS
    DB --> CONFIG
    DIAG --> DB
    DIAG --> CONFIG
    DIAG --> LLM

    SECURITY --> DB
    OS --> EVENTS
    IOT --> WS_HANDLER

    COMPUTER --> VISION
    COMPUTER --> SECURITY
    BROWSER --> SECURITY
```

---

## 2. Backend Module Dependency Graph

```mermaid
graph LR
    subgraph Core
        DB[core/database.py]
        CFG[core/config.py]
        EVT[core/events.py]
        DIA[core/diagnostics.py]
        MDL[core/models.py]
    end

    subgraph Brain
        LLM[brain/llm.py]
        RAG[brain/rag.py]
        ACI[brain/aci.py]
        DAG[brain/dag_planner.py]
        MEM[brain/memory/]
        CTX[brain/core/context.py]
    end

    subgraph Agents
        JA[jarvis.py]
        KG[kings/]
        WK[workers/]
        PS[personas/]
    end

    subgraph Tools
        TU[tools/unified.py]
        TR[tools/registry.py]
        AT[agents/tools.py]
    end

    subgraph Systems
        CM[computer/]
        BR[browser/]
        VC[voice/]
        VS[vision/]
        SC[security/]
        OS[os/]
        IT[iot/]
    end

    subgraph Web
        RT[routers/]
        AM[api/]
        WS[websocket.py]
    end

    subgraph Workspace
        WKSP[workspace/]
        MS[mision/]
        MR[mision/replay/]
    end

    subgraph Orphans["↗ Orphaned (REMOVE)"]
        AG[architecture_graph/]
        LD[living_dashboard/]
        PJ[projects/]
        JN[journal/]
        SG[suggestions/]
        EI[eng_intel/]
        CI[codebase_index/]
        RI[repo_intelligence/]
        RF[refactoring/]
        PL[planner/]
        MEMR[memory/]
        KW[knowledge/]
        DC[decisions/]
    end

    DB --> CFG
    EVT --> DB
    DIA --> DB
    DIA --> CFG
    DIA --> LLM
    MDL --> CFG

    LLM --> CFG
    RAG --> MEM
    RAG --> DB
    ACI --> LLM
    DAG --> MS
    MEM --> DB
    CTX --> MEM

    JA --> LLM
    JA --> DAG
    JA --> ACI
    KG --> WK
    KG --> JA
    WK --> TU
    WK --> AT
    PS --> JA

    TU --> TR
    TU --> CM
    TU --> BR
    TU --> VS
    TU --> MS
    AT --> TR

    CM --> VS
    CM --> SC
    BR --> SC
    VS --> BR
    SC --> DB
    OS --> EVT
    WS --> EVT

    RT --> AM
    AM --> LLM
    AM --> MEM
    AM --> CM
    AM --> BR
    AM --> WKSP
    AM --> MS
    WS --> JA
    WS --> LLM
    WS --> MEM
    WS --> EVT

    WKSP --> MDL
    MS --> MDL
    MR --> MS

    KW -.->|"incorrect"| MEM
    DC -.->|"decisions.md"| MR
```

### Legend

| Arrow | Meaning |
|-------|---------|
| `A --> B` | A imports / depends on B |
| `A -.-> B` | Weak / situational dependency |

---

## 3. Frontend Component Tree

```mermaid
graph TB
    subgraph Templates["Templates"]
        BASE["base.html
Root SPA Shell"]
    end

    subgraph CSS["Stylesheets"]
        STYLE["style.css
6,457 lines (monolithic)"]
    end

    subgraph Core["Core JS"]
        APP["app.js
Main controller, routing, state"]
        SM["state-machine.js
Application state model"]
        WS["ws-manager.js
WebSocket client"]
    end

    subgraph Features["Feature Modules"]
        CORE["jarvis-core.js🎯
Arc reactor + particle field"]
        GRAPH["graph-3d.js🎯
3D neural core visualization"]
        LIVING["living-interface.js🎯
Realtime HUD"]

        CHAT["chat-background.js🎯
3D particle chat backdrop"]
        VOICE["voice.js🎯
Speech recog + command"]

        DASH["workspace-manager.js🎯
5-pane workspace state"]

        PALETTE["command-palette.js🎯
⌘K command palette"]
        COMP["computer-control.js🎯
Screen control panel"]

        VISION["vision-experience.js🎯
Vision capture for computer"]
        VEXP["voice-experience.js🎯
Premium voice UI"]
        DT["digital-twin.js🎯
State avatar"]
        EXPLAIN["explainability.js🎯
Explanation overlay"]

        AUDIO["audio-analyzer.js🎯
Audio visualizer"]

        TIMELINE["mission-timeline.js🎯
Execution timeline"]
        DAG["mission-dag.js⚠️
DAG view (broken)"]
    end

    subgraph Dead["Dead / Orphaned JS"]
        G3D["graph3d.js✖️
Duplicate of graph-3d.js"]
        MP["mission-panel.js✖️
Dead, unused"]
        MEP["memory-panel.js✖️
Calls missing API"]
        DP["debug-patch.js✖️
Debug-only patcher"]
    end

    subgraph Pages["Page Routes"]
        HOME["/ (Home)
Home + Neural Core + command palette"]
        DASHBOARD["/dashboard
Workspace + agents + metrics"]
        SETTINGS["/settings
Config interface"]
    end

    APP --> SM
    APP --> WS
    WS --> LIVING

    HOME --> CORE
    HOME --> GRAPH
    HOME --> PALETTE
    HOME --> CHAT
    HOME --> VOICE
    HOME --> VEXP
    HOME --> AUDIO

    DASHBOARD --> DASH
    DASHBOARD --> COMP
    DASHBOARD --> VISION
    DASHBOARD --> DT
    DASHBOARD --> EXPLAIN
    DASHBOARD --> TIMELINE
    DASHBOARD --> DAG

    APP -.->|dead routes| G3D
    APP -.->|dead routes| MP
    APP -.->|dead routes| MEP
```

---

## 4. API → Backend Mapping

```mermaid
graph LR
    subgraph FrontendCalls["Frontend → API"]
        FC["app.js / ws-manager.js"]
        F_CHAT["POST /api/chat"]
        F_MEM["GET /api/memory/episodic"]
        F_MEM2["GET /api/memory/personal"]
        F_WORK["GET /api/workspace"]
        F_SYS["GET /api/system/*"]
        F_WS["WS /ws"]

        F_DAG["GET /api/system/dag⚠️ MISSING"]
        F_SESS["GET /api/sessions⚠️ WRONG PATH"]
        F_HERMES["GET /api/architectures/hermes/memory⚠️ MISSING"]
        F_VOICE["POST /api/voice/generate⚠️ MISSING"]
        F_ACTIONS["GET /api/computer/actions⚠️ STATIC"]
    end

    subgraph Routers["Backend Routers"]
        CHAT["routers/chat.py"]
        AGENTS["routers/agents.py"]
        MEMORY["routers/memory.py"]
        VOICE["routers/voice.py"]
        COMPUTER["routers/computer.py"]
        SYSTEM["routers/system.py"]
        PAGES["routers/pages.py"]
        WORKSPACE["routers/workspace.py"]
        SETTINGS["routers/settings.py"]
        AUTH["routers/auth.py"]
        SECURITY["routers/security.py"]
        IOT["routers/iot.py"]
        ENG["routers/engineering.py"]
        WORLD["routers/world.py"]
        CK["routers/checkpoints.py"]
        MR["api/mission_replay.py"]
        WS_H["websocket.py"]
    end

    F_CHAT --> CHAT
    F_MEM --> MEMORY
    F_MEM2 --> MEMORY
    F_WORK --> WORKSPACE
    F_SYS --> SYSTEM
    F_WS --> WS_H

    F_DAG -.->|"❌ 404"| SYSTEM
    F_SESS -.->|"❌ 404"| CHAT
    F_HERMES -.->|"❌ 404"| SYSTEM
    F_VOICE -.->|"❌ 404"| VOICE
    F_ACTIONS -.->|"⚠️ static list"| COMPUTER

    CHAT --> LLM[brain/llm.py]
    CHAT --> MEM[brain/memory/]
    MEMORY --> MEM
    SYSTEM --> DIA[core/diagnostics.py]
    SYSTEM --> MEM
    SYSTEM --> DB[core/database.py]
    WS_H --> LLM
    WS_H --> MEM
    WS_H --> AG[agents/jarvis.py]
    WS_H --> EVT[core/events.py]
    COMPUTER --> CM[computer/]
    VOICE --> VC[voice/]
    AGENTS --> AG
    WORKSPACE --> WS_M[workspace/manager.py]
    IOT --> IO[iot/]
    ENG --> EN[engineering/]
    SECURITY --> SC[security/]
    SETTINGS --> CFG[core/config.py]
```

---

## 5. Database Schema Map

```mermaid
erDiagram
    agents {
        int id PK
        text name
        text agent_type
        text role
        text status
        text metadata
    }

    conversation_history {
        int id PK
        text session_id
        text role
        text content
        text metadata
        datetime timestamp
    }

    memories {
        int id PK
        text memory_type
        text content
        text tags
        real importance
        datetime created_at
        datetime last_accessed
        int access_count
    }

    episodic_memory {
        int id PK
        text episode_id
        text content
        text context
        text outcome
        real importance
        datetime timestamp
    }

    personal_memory {
        int id PK
        text key
        text value
        text category
        real confidence
        datetime updated_at
    }

    working_memory {
        int id PK
        text context_id
        text key
        text value
        datetime expires_at
    }

    journal_entries {
        int id PK
        text entry_id
        text content
        text mood
        text tags
        datetime created_at
    }

    settings {
        text key PK
        text value
    }

    mission_milestones {
        int id PK
        text mission_id
        text milestone_id
        text title
        text status
        int order
    }

    checkpoints {
        int id PK
        text checkpoint_id
        text context
        text state_data
        datetime created_at
    }

    capabilities {
        text name PK
        text description
        text version
        text status
        text metadata
    }

    memory_graph {
        int id PK
        text source_id
        text target_id
        text relationship
        real weight
        text metadata
    }

    missions {
        text id PK
        text name
        text description
        text status
        text stages
        text current_stage
        text dag_data
        datetime created_at
        datetime updated_at
    }

    conversation_history }o--|| agents : "agent_id FK"
    memories }o--|| agents : "agent_id FK"
    episodic_memory }o--|| agents : "agent_id FK"
    mission_milestones }o--|| missions : "mission_id FK"
    memory_graph }o--|| memories : "source_id"
    memory_graph }o--|| memories : "target_id"
```

---

## 6. Memory System Architecture

```mermaid
flowchart LR
    subgraph API["API Layer"]
        REST["REST Endpoints
/memory/episodic
/memory/personal
/memory/journal"]
        WS_MEM["WebSocket
memory events"]
    end

    subgraph Managers["Memory Managers"]
        WM["WorkingMemory
short-term, TTL-expiring
core/models.py"]
        EM["EpisodicMemory
experiences + outcomes
brain/memory/episodic.py"]
        PM["PersonalMemory
user facts + preferences
brain/memory/personal.py"]
        JM["JournalMemory
daily entries + mood
brain/memory/journal.py"]
    end

    subgraph CrossCutting["Cross-Cutting"]
        CONSOL["Consolidation
brain/memory/consolidation.py"]
        IMPORT["Importance Scoring
brain/memory/importance.py"]
        EXTRACT["Extraction
brain/memory/extraction.py"]
        GRAPH["Memory Graph
brain/memory/graph.py"]
        RETRIEVAL["Retrieval
brain/memory/retrieval.py"]
        NOTES["Notes
brain/memory/notes.py"]
    end

    subgraph Storage["Storage"]
        DB[(Async SQLite
core/database.py)]
    end

    subgraph Consumers["Consumers"]
        CHAT["Chat Router"]
        AGENT["JARVIS Agent"]
        RAG["RAG Engine"]
        CONTEXT["Context Builder
brain/core/context.py"]
    end

    REST --> WM
    REST --> EM
    REST --> PM
    REST --> JM

    WS_MEM --> WM
    WS_MEM --> EM
    WS_MEM --> PM
    WS_MEM --> JM

    WM --> DB
    EM --> DB
    PM --> DB
    JM --> DB

    EM --> CONSOL
    PM --> CONSOL
    EM --> IMPORT
    PM --> IMPORT

    CONSOL --> EXTRACT
    EXTRACT --> GRAPH

    RETRIEVAL --> EM
    RETRIEVAL --> PM
    RETRIEVAL --> JM

    CHAT --> RETRIEVAL
    AGENT --> RETRIEVAL
    CONTEXT --> WM
    CONTEXT --> PM
    RAG --> RETRIEVAL
```

---

## 7. Agent Hierarchy (Kings → Workers)

```mermaid
graph TB
    J["JARVIS Agent
jarvis.py
Chief Executive AI"]

    subgraph ENG["👑 Engineering King
kings/engineering_king.py"]
        EA["♠Q Architect Worker"]
        EB["♠J Backend Worker"]
        EF["♠10 Frontend Worker"]
        ER["♠9 React Worker"]
        EP["♠8 Python Worker"]
        ET["♠7 Testing Worker"]
        ED["♠6 Docs Worker"]
        EA11["♠5 A11y Worker"]
    end

    subgraph PER["👑 Personal King
kings/personal_king.py"]
        PC["♥Q Calendar Worker"]
        PE["♥J Email Worker"]
        PT["♥10 Tasks Worker"]
        PS["♥9 Scheduling Worker"]
    end

    subgraph RES["👑 Research King
kings/research_king.py"]
        RW["♦Q Web Research Worker"]
        RD["♦J Documentation Worker"]
        RF["♦10 Fact Check Worker"]
    end

    subgraph SYS["👑 System King
kings/system_king.py"]
        SF["♣Q Files Worker"]
        ST["♣J Terminal Worker"]
        SA["♣10 Applications Worker"]
    end

    J --> ENG
    J --> PER
    J --> RES
    J --> SYS

    ENG --> EA
    ENG --> EB
    ENG --> EF
    ENG --> ER
    ENG --> EP
    ENG --> ET
    ENG --> ED
    ENG --> EA11

    PER --> PC
    PER --> PE
    PER --> PT
    PER --> PS

    RES --> RW
    RES --> RD
    RES --> RF

    SYS --> SF
    SYS --> ST
    SYS --> SA
```

---

## 8. Event Flow

```mermaid
sequenceDiagram
    participant User as User Browser
    participant SPA as SPA (app.js)
    participant WS as WebSocket
    participant JARVIS as JARVIS Agent
    participant KING as Division King
    participant WORKER as Worker
    participant TOOL as Tool Layer
    participant SYSTEM as System Module
    participant MEM as Memory System
    participant DB as SQLite DB

    User->>SPA: types command
    SPA->>WS: send message via WebSocket
    WS->>JARVIS: route to agent
    JARVIS->>JARVIS: select King (card-based dispatch)
    JARVIS->>KING: delegate task
    KING->>WORKER: assign to worker
    WORKER->>TOOL: execute tool call
    TOOL->>SYSTEM: system operation (browser/computer/etc)
    SYSTEM-->>TOOL: result
    TOOL-->>WORKER: formatted result
    WORKER-->>KING: completion
    KING-->>JARVIS: result synthesized
    JARVIS->>MEM: store in memory
    MEM->>DB: persist
    JARVIS-->>WS: stream response
    WS-->>SPA: update UI
    SPA-->>User: display result

    Note over JARVIS,WORKER: Context from brain/core/context.py<br/>Memory from brain/memory/
    Note over TOOL,SYSTEM: Gate via security layer
    Note over MEM,DB: Episodic + Personal + Journal
```

---

## 9. Data Flow Architecture

```mermaid
flowchart LR
    subgraph Input["Input Channels"]
        CLI["CLI
cli.py"]
        REST["REST API
16 routers"]
        WS["WebSocket
/ws"]
        VOICE_IN["Voice
speech recognition"]
    end

    subgraph Processing["Processing"]
        AGENT["Agent System
kings → workers"]
        LLM["LLM Pipeline
context → prompt → response"]
        DAG["Mission DAG
pipeline execution"]
    end

    subgraph Output["Output Channels"]
        REST_OUT["REST Response"]
        WS_OUT["WebSocket Stream"]
        UI["UI Update
app.js → DOM"]
        VOICE_OUT["TTS
voice/"]
        COMP_CTRL["Computer Control
click/type/scroll"]
        FILE_SYS["File System
os/ + security/"]
    end

    subgraph StorageLayer["Storage Layer"]
        DB[(SQLite)]
        MEM_SYS["Memory System
5 providers + graph"]
    end

    CLI --> AGENT
    REST --> AGENT
    REST --> LLM
    WS --> AGENT
    WS --> LLM
    VOICE_IN --> WS

    AGENT --> LLM
    AGENT --> DAG
    DAG --> MEM_SYS

    LLM --> WS_OUT
    LLM --> UI
    AGENT --> REST_OUT
    AGENT --> WS_OUT
    AGENT --> COMP_CTRL
    AGENT --> VOICE_OUT
    AGENT --> FILE_SYS

    MEM_SYS --> DB
    LLM --> MEM_SYS
```

---

## 10. Deployment Architecture

```mermaid
graph TB
    subgraph Host["Host Machine (macOS)"]
        subgraph JARVIS["JARVIS Process"]
            WEB["Uvicorn Server
127.0.0.1:8000"]
            AGENTS_POOL["Agent Pool
4 kings, 23 workers"]
            DB_FILE["jarvis.db
SQLite file"]
            STATIC["Static Assets
web/static/"]
        end

        subgraph System["System Integration"]
            MENUBAR["Menu Bar
os/menubar.py"]
            NOTIF["Notifications
os/notifications.py"]
            HOTKEYS["Global Hotkeys
os/hotkeys.py"]
            CLIPBOARD["Clipboard
os/clipboard.py"]
        end

        subgraph External["External"]
            LLM_API["NVIDIA API
LLM endpoint"]
            BROWSER_CHROM["Playwright
Browser instance"]
        end

        subgraph User["User"]
            BROWSER["Web Browser
http://127.0.0.1:8000"]
            TERM["Terminal
CLI via `jarvis`"]
        end
    end

    BROWSER --> WEB
    TERM --> WEB
    WEB --> AGENTS_POOL
    WEB --> DB_FILE
    WEB --> STATIC
    AGENTS_POOL --> LLM_API
    AGENTS_POOL --> BROWSER_CHROM
    MENUBAR --> WEB
    NOTIF --> WEB
    HOTKEYS --> WEB
    CLIPBOARD --> WEB
```
