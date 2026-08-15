# JARVIS Architecture Migration Guide

## Overview
Documentation for migrating from single-architecture JARVIS to pluggable multi-architecture system.

---

## Before Migration (v7.x)

### Single Architecture
- Hardcoded Kings/Workers hierarchy
- Direct agent calls in chat router
- No abstraction layer
- Settings only for model/config

### Files Affected
- `jarvis/web/routers/chat.py` - Direct agent streaming
- `jarvis/agents/jarvis.py` - Main agent class
- `jarvis/agents/kings/` - King implementations
- `jarvis/agents/workers/` - Worker implementations
- `jarvis/web/main.py` - Agent initialization

---

## After Migration (v8.0+)

### Pluggable Architecture System
```
jarvis/architectures/
├── __init__.py          # Exports, registry
├── base.py              # AgentArchitecture interface
├── settings.py          # Configuration persistence
├── registry.py          # Architecture registry
├── native/
│   ├── __init__.py
│   └── architecture.py  # Wraps existing system
└── hermes/
    ├── __init__.py
    └── architecture.py  # New Hermes-inspired system
```

### Key Abstractions

#### AgentArchitecture Interface
```python
class AgentArchitecture(ABC):
    @abstractmethod
    async def plan(self, goal: str, context: MissionContext) -> Plan: ...

    @abstractmethod
    async def execute(self, plan: Plan, context: MissionContext) -> ExecutionResult: ...

    @abstractmethod
    async def observe(self, action: str, result: Any, context: MissionContext) -> Observation: ...

    @abstractmethod
    async def reflect(
        self, mission: MissionContext, results: List[ExecutionResult]
    ) -> Reflection: ...

    @abstractmethod
    async def verify(
        self, step: PlanStep, result: Any, context: MissionContext
    ) -> VerificationResult: ...

    @abstractmethod
    async def remember(self, content: str, type: str, context: MissionContext) -> str: ...

    @abstractmethod
    async def recall(
        self, query: str, context: MissionContext, limit: int = 10
    ) -> List[MemoryItem]: ...
```

#### MissionContext
```python
@dataclass
class MissionContext:
    user_id: str
    session_id: str
    goal: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

#### Plan & PlanStep
```python
@dataclass
class Plan:
    goal: str
    steps: List[PlanStep]
    estimated_duration: float
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class PlanStep:
    id: str
    description: str
    agent_type: str  # planner, executor, researcher, coder, reviewer
    tool: Optional[str]
    args: Dict[str, Any]
    depends_on: List[str]
    verification_criteria: List[str]
```

---

## Migration Steps

### Step 1: Create Architecture Layer (COMPLETED)
- Created `jarvis/architectures/` package
- Implemented `AgentArchitecture` interface
- Built `ArchitectureRegistry`
- Added `ArchitectureSettings` persistence

### Step 2: Implement Native Architecture Wrapper (COMPLETED)
- `JarvisNativeArchitecture` wraps existing Kings/Workers
- Delegates to `JarvisAgent` for compatibility
- Maintains all existing behavior

### Step 3: Implement Hermes Architecture (COMPLETED)
- Hierarchical planning with specialized agents
- Multi-layer memory system
- Skill extraction
- Structured verification
- Reflection loops

### Step 4: Integrate with Web Layer (COMPLETED)
- Architecture initialization in lifespan
- Settings API endpoints
- Chat router uses active architecture
- Global `get_architecture()` function

### Step 5: Settings UI (COMPLETED)
- Architecture panel in Settings
- Switch between Native/Hermes
- Persistent selection
- Restart notification

---

## Breaking Changes

### None (Backward Compatible)
- All existing APIs unchanged
- Native architecture = default behavior
- Existing agents/workers/tools work identically
- Database schema unchanged

### New Requirements
- Python 3.10+ (dataclasses, typing)
- Architecture settings file: `jarvis_architecture_settings.json`

---

## Migration Checklist

| Item | Status | Notes |
|------|--------|-------|
| Architecture package created | ✅ | |
| Base interface defined | ✅ | |
| Registry implemented | ✅ | |
| Settings persistence | ✅ | |
| Native wrapper | ✅ | |
| Hermes implementation | ✅ | |
| Web integration | ✅ | |
| Settings API | ✅ | |
| Settings UI | ✅ | |
| Chat router updated | ✅ | Uses active architecture |
| Tests updated | ⏳ | Need architecture tests |
| Documentation | ✅ | This guide |

---

## Testing Architecture Switching

### Via API
```bash
# Get current architecture
curl http://localhost:8000/api/settings/architecture

# Switch to Hermes
curl -X POST http://localhost:8000/api/settings/architecture/switch \
  -H "Content-Type: application/json" \
  -d '{"architecture": "hermes"}'

# Switch back to Native
curl -X POST http://localhost:8000/api/settings/architecture/switch \
  -H "Content-Type: application/json" \
  -d '{"architecture": "native"}'
```

### Via UI
1. Open Settings (gear icon)
2. Click "AI Architecture" in sidebar
3. Select architecture
4. Click "Switch Architecture"
5. Restart server (required for full effect)

---

## Architecture Comparison

| Feature | Native | Hermes |
|---------|--------|--------|
| Planning | King-based | Hierarchical planner |
| Execution | Worker delegation | Specialized agents |
| Memory | Conversation + vector | 6-layer (working/short/long/episodic/semantic/skills) |
| Verification | Implicit | Explicit LLM-based |
| Reflection | None | Post-mission loops |
| Skills | None | Extracted from success |
| Sub-agents | Workers | Dynamic spawning |
| Tool Manager | Centralized | Per-agent + shared |
| Context | Session | Mission + layers |

---

## Rollback Plan

If issues arise:
1. Settings API: `POST /api/settings/architecture/switch` with `{"architecture": "native"}`
2. Or delete `jarvis_architecture_settings.json`
3. Restart server
4. System reverts to Native (default)

---

## Future Architectures

To add new architecture:
1. Create `jarvis/architectures/new_arch/architecture.py`
2. Implement `AgentArchitecture` interface
3. Register in `jarvis/architectures/__init__.py`
4. Add to registry in `main.py` lifespan
5. Add settings schema in `settings.py`

---

*Migration completed: 2026-07-29*
*Version: 8.0.0*