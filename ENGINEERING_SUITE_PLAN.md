# JARVIS v3.3.0 — Engineering Suite Plan

## Status: COMPLETED ✅

### Completed Tasks
- [x] Engineering module structure (`jarvis/engineering/`)
- [x] Provider ABCs: CAD, PCB, Embedded, Mechanical, Simulation
- [x] 5 new workers: CAD, PCB, Firmware, Mechanical, HW Test
- [x] Engineering King updated with 13 workers
- [x] Engineering knowledge base (10 materials, 18 bearings, 8 formulas)
- [x] ToolExecutor with 17 engineering actions
- [x] Developer CLI with Rich (jarvis-cli)
- [x] Engineering API endpoints (20 routes)
- [x] Version bumped to 3.3.0

---

## Architecture Overview

Expand the Engineering Division (♠) from 8 software-only workers into a full engineering platform with 13 workers covering CAD, PCB, embedded, mechanical, and software engineering.

### New Agent Hierarchy

```
JARVIS (J)
├── Engineering King (♠K) — Engineering Division Chief
│   ├── ♠Q  ArchitectWorker (existing — software architecture)
│   ├── ♠J  BackendWorker (existing — backend engineering)
│   ├── ♠10 FrontendWorker (existing — frontend engineering)
│   ├── ♠9  ReactWorker (existing — React specialist)
│   ├── ♠8  PythonWorker (existing — Python specialist)
│   ├── ♠7  TestingWorker (existing — testing/QA)
│   ├── ♠6  DocsWorker (existing — documentation)
│   ├── ♠5  A11yWorker (existing — accessibility)
│   ├── ♠4  CADWorker (NEW — 3D modeling, parametric design)
│   ├── ♠3  PCBWorker (NEW — PCB layout, schematics, BOM)
│   ├── ♠2  FirmwareWorker (NEW — embedded systems, compile, flash)
│   ├── ♠A  MechanicalWorker (NEW — mechanical analysis, 3D print)
│   └── ♠?? HardwareTestWorker (NEW — test procedures, instruments)
├── Personal King (♥K)
├── Research King (♦K)
└── System King (♣K)
```

---

## Phase 1: Foundation (Week 1)

### 1.1 Engineering Tools Module
**File**: `jarvis/engineering/__init__.py`

Create a new top-level module for all engineering capabilities.

```
jarvis/engineering/
├── __init__.py
├── cad/
│   ├── __init__.py
│   ├── base.py          # CADProvider ABC
│   ├── fusion360.py     # Fusion 360 adapter (future API)
│   ├── onshape.py       # Onshape adapter (future API)
│   ├── blender.py       # Blender Python API
│   ├── tinkercad.py     # Tinkercad adapter
│   ├── openscad.py      # OpenSCAD script generation
│   └── exporters.py     # STL, STEP, OBJ, FBX export
├── pcb/
│   ├── __init__.py
│   ├── base.py          # PCBProvider ABC
│   ├── kicad.py         # KiCad CLI integration
│   ├── easyeda.py       # EasyEDA adapter
│   ├── schematic.py     # Schematic generation
│   ├── layout.py        # PCB layout helpers
│   ├── bom.py           # Bill of Materials manager
│   ├── gerber.py        # Gerber file generation
│   └── components.py    # Component library
├── embedded/
│   ├── __init__.py
│   ├── base.py          # EmbeddedProvider ABC
│   ├── arduino.py       # Arduino CLI integration
│   ├── esp32.py         # ESP32/PlatformIO integration
│   ├── rpi.py           # Raspberry Pi integration
│   ├── stm32.py         # STM32 integration
│   ├── micropython.py   # MicroPython integration
│   └── firmware.py      # Firmware build/flash/monitor
├── mechanical/
│   ├── __init__.py
│   ├── base.py          # MechanicalProvider ABC
│   ├── materials.py     # Material database & properties
│   ├── fasteners.py     # Fastener catalog
│   ├── bearings.py      # Bearing selection
│   ├── gears.py         # Gear system design
│   ├── motion.py        # Motion control calculations
│   └── calculators.py   # Engineering calculators
├── simulation/
│   ├── __init__.py
│   ├── base.py          # SimulationProvider ABC
│   ├── thermal.py       # Thermal analysis (future)
│   ├── stress.py        # Stress analysis (future)
│   ├── kinematic.py     # Kinematic analysis (future)
│   └── circuit.py       # Circuit simulation (future)
├── knowledge.py         # Engineering knowledge base
└── workspace.py         # Engineering project workspace
```

### 1.2 Core Provider ABCs

Each domain gets an abstract base class defining the interface:

```python
# jarvis/engineering/cad/base.py
from abc import ABC, abstractmethod

class CADProvider(ABC):
    @abstractmethod
    async def create_model(self, name: str, params: dict) -> dict: ...
    
    @abstractmethod
    async def edit_model(self, model_id: str, changes: dict) -> dict: ...
    
    @abstractmethod
    async def export(self, model_id: str, format: str, path: str) -> dict: ...
    
    @abstractmethod
    async def get_measurements(self, model_id: str) -> dict: ...
    
    @abstractmethod
    async def list_models(self, workspace: str) -> list: ...
```

```python
# jarvis/engineering/pcb/base.py
from abc import ABC, abstractmethod

class PCBProvider(ABC):
    @abstractmethod
    async def create_project(self, name: str, params: dict) -> dict: ...
    
    @abstractmethod
    async def add_component(self, project_id: str, component: dict) -> dict: ...
    
    @abstractmethod
    async def route(self, project_id: str, nets: list) -> dict: ...
    
    @abstractmethod
    async def export_gerber(self, project_id: str, path: str) -> dict: ...
    
    @abstractmethod
    async def generate_bom(self, project_id: str) -> dict: ...
    
    @abstractmethod
    async def check_drc(self, project_id: str) -> dict: ...
```

```python
# jarvis/engineering/embedded/base.py
from abc import ABC, abstractmethod

class EmbeddedProvider(ABC):
    @abstractmethod
    async def create_project(self, name: str, platform: str, params: dict) -> dict: ...
    
    @abstractmethod
    async def compile(self, project_id: str) -> dict: ...
    
    @abstractmethod
    async def upload(self, project_id: str, device: str) -> dict: ...
    
    @abstractmethod
    async def monitor(self, project_id: str, device: str) -> dict: ...
    
    @abstractmethod
    async def list_devices(self) -> list: ...
```

### 1.3 Capability Registration

Register all new engineering capabilities in the Capability Registry:

```python
# In web/main.py lifespan
engineering_caps = [
    ("cad_create_model", "♠K", CapType.TOOL, "Create 3D CAD models"),
    ("cad_export", "♠K", CapType.TOOL, "Export CAD files (STL/STEP/OBJ)"),
    ("pcb_create_project", "♠K", CapType.TOOL, "Create PCB design projects"),
    ("pcb_export_gerber", "♠K", CapType.TOOL, "Export manufacturing files"),
    ("pcb_generate_bom", "♠K", CapType.TOOL, "Generate bill of materials"),
    ("firmware_compile", "♠K", CapType.TOOL, "Compile embedded firmware"),
    ("firmware_upload", "♠K", CapType.TOOL, "Upload firmware to devices"),
    ("mechanical_calculate", "♠K", CapType.TOOL, "Engineering calculations"),
    ("simulate_thermal", "♠K", CapType.TOOL, "Thermal analysis"),
    ("simulate_stress", "♠K", CapType.TOOL, "Stress analysis"),
]
```

### 1.4 New Worker Implementations

**CADWorker (♠4)**:
```python
class CADWorker(BaseWorker):
    card_id = "♠4"
    name = "CAD Engineer"
    title = "3D Modeling Specialist"
    personality = "Precise, spatial thinker. Obsessed with dimensions and tolerances."
    
    def get_system_prompt(self):
        return """You are a CAD engineering specialist...
        Capabilities: parametric modeling, assemblies, mechanical constraints...
        Tools: cad_create_model, cad_edit_model, cad_export, cad_measure..."""
```

**PCBWorker (♠3)**:
```python
class PCBWorker(BaseWorker):
    card_id = "♠3"
    name = "PCB Engineer"
    title = "Circuit Board Designer"
    personality = "Detail-oriented, understands signal integrity and power delivery."
    
    def get_system_prompt(self):
        return """You are a PCB engineering specialist...
        Capabilities: schematic design, PCB layout, component selection...
        Tools: pcb_create_project, pcb_add_component, pcb_route, pcb_export_gerber..."""
```

**FirmwareWorker (♠2)**:
```python
class FirmwareWorker(BaseWorker):
    card_id = "♠2"
    name = "Firmware Engineer"
    title = "Embedded Systems Specialist"
    personality = "Resource-conscious, understands hardware constraints."
    
    def get_system_prompt(self):
        return """You are an embedded systems specialist...
        Capabilities: Arduino, ESP32, PlatformIO, MicroPython...
        Tools: firmware_compile, firmware_upload, firmware_monitor..."""
```

**MechanicalWorker (♠A)**:
```python
class MechanicalWorker(BaseWorker):
    card_id = "♠A"
    name = "Mechanical Engineer"
    title = "Mechanical Systems Specialist"
    personality = "Understands physics, materials, and manufacturing processes."
    
    def get_system_prompt(self):
        return """You are a mechanical engineering specialist...
        Capabilities: materials science, gear systems, motion control...
        Tools: mechanical_calculate, mechanical_select_material..."""
```

**HardwareTestWorker (♠??)**:
```python
class HardwareTestWorker(BaseWorker):
    card_id = "♠??"
    name = "Hardware Test Engineer"
    title = "Test & Validation Specialist"
    personality = "Methodical, documents everything, verifies twice."
    
    def get_system_prompt(self):
        return """You are a hardware test engineer...
        Capabilities: test procedures, instrument control, data analysis...
        Tools: test_create_procedure, test_run, test_analyze..."""
```

---

## Phase 2: Tool Integration (Week 2)

### 2.1 CLI Tool Wrappers

Many engineering tools have CLI interfaces. Wrap them for JARVIS:

**KiCad CLI** (v8+):
```python
class KiCadProvider(PCBProvider):
    async def create_project(self, name, params):
        # Create .kicad_pro, .kicad_sch, .kicad_pcb
        ...
    
    async def export_gerber(self, project_id, path):
        # kicad-cli pcb export gerbers --output {path} {project.pcb}
        result = await shell_execute(f"kicad-cli pcb export gerbers --output {path} {project_file}")
        return result
```

**Arduino CLI**:
```python
class ArduinoCLIFirmware(EmbeddedProvider):
    async def compile(self, project_id):
        # arduino-cli compile --fqbn arduino:esp32:esp32 {sketch}
        result = await shell_execute(f"arduino-cli compile --fqbn {fqbn} {sketch_path}")
        return result
    
    async def upload(self, project_id, device):
        # arduino-cli upload --fqbn arduino:esp32:esp32 --port {port} {sketch}
        ...
```

**PlatformIO CLI**:
```python
class PlatformIOProvider(EmbeddedProvider):
    async def compile(self, project_id):
        # pio run -d {project_dir}
        ...
    
    async def upload(self, project_id, device):
        # pio run -t upload -d {project_dir}
        ...
```

**OpenSCAD**:
```python
class OpenSCADProvider(CADProvider):
    async def create_model(self, name, params):
        # Generate .scad script from params
        scad_content = self._generate_scad(params)
        # Write to file, render to STL
        await shell_execute(f"openscad -o {name}.stl {name}.scad")
        ...
```

**Blender Python API**:
```python
class BlenderProvider(CADProvider):
    async def create_model(self, name, params):
        # Generate Python script for Blender
        # blender --background --python script.py
        ...
```

### 2.2 Engineering ToolExecutor Actions

Add engineering actions to `jarvis/agents/tools.py`:

```python
# New tool actions for engineering
ENGINEERING_TOOLS = {
    # CAD
    "cad_create_model": "Create a 3D CAD model",
    "cad_edit_model": "Edit an existing CAD model",
    "cad_export": "Export CAD model to STL/STEP/OBJ/FBX",
    "cad_measure": "Get measurements from a CAD model",
    "cad_list_models": "List models in workspace",
    
    # PCB
    "pcb_create_project": "Create a new PCB design project",
    "pcb_add_component": "Add component to schematic",
    "pcb_route": "Route PCB traces",
    "pcb_export_gerber": "Export Gerber manufacturing files",
    "pcb_generate_bom": "Generate bill of materials",
    "pcb_check_drc": "Run design rule check",
    "pcb_list_components": "Search component library",
    
    # Embedded
    "firmware_create_project": "Create embedded project",
    "firmware_compile": "Compile firmware",
    "firmware_upload": "Upload firmware to device",
    "firmware_monitor": "Monitor serial output",
    "firmware_list_devices": "List connected devices",
    
    # Mechanical
    "mechanical_calculate": "Run engineering calculation",
    "mechanical_select_material": "Select material by properties",
    "mechanical_gear_design": "Design gear system",
    "mechanical_bearing_select": "Select bearing for load",
    
    # Simulation (architecture only)
    "simulate_thermal": "Thermal analysis (future)",
    "simulate_stress": "Stress analysis (future)",
    "simulate_kinematic": "Kinematic analysis (future)",
}
```

### 2.3 Engineering Knowledge Base

**File**: `jarvis/engineering/knowledge.py`

```python
class EngineeringKnowledge:
    """Engineering knowledge base integrated with RAG system."""
    
    # Material properties database
    MATERIALS = {
        "aluminum_6061": {
            "name": "Aluminum 6061-T6",
            "density": 2.70,  # g/cm³
            "yield_strength": 276,  # MPa
            "ultimate_strength": 310,  # MPa
            "elastic_modulus": 68.9,  # GPa
            "thermal_conductivity": 167,  # W/m·K
            "machinability": "excellent",
            "cost": "low",
            "applications": ["enclosures", "structural", "automotive"],
        },
        # ... 50+ materials
    }
    
    # Fastener catalog
    FASTENERS = {
        "m3_button_head": {
            "name": "M3 Button Head Screw",
            "size": "M3",
            "thread_pitch": 0.5,
            "head_diameter": 5.7,
            "head_height": 1.7,
            "drive": "hex_socket",
            "material": "stainless_steel",
        },
        # ... catalog
    }
    
    # Engineering formulas
    FORMULAS = {
        "beam_deflection": "δ = (F × L³) / (3 × E × I)",
        "gear_ratio": "GR = N₂ / N₁",
        "powerTransmission": "P = τ × ω",
        "thermal_resistance": "R = L / (k × A)",
        "pcb_trace_width": "w = (I / (k × ΔT^b))^(1/c)",
    }
    
    async def query(self, question: str) -> dict:
        """Query engineering knowledge."""
        ...
    
    async def get_material(self, name: str) -> dict:
        """Get material properties."""
        ...
    
    async def calculate(self, formula: str, params: dict) -> dict:
        """Run engineering calculation."""
        ...
```

---

## Phase 3: Engineering Workspace (Week 3)

### 3.1 Project Workspace

Extend the existing WorkspaceManager for engineering:

```python
class EngineeringWorkspace:
    """Engineering project workspace with file organization."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.base_dir = Path(f"workspaces/{project_id}")
    
    def create_structure(self):
        """Create engineering project directory structure."""
        dirs = [
            "cad/models",
            "cad/exports",
            "cad/assemblies",
            "pcb/schematics",
            "pcb/layouts",
            "pcb/gerber",
            "pcb/bom",
            "firmware/src",
            "firmware/include",
            "firmware/lib",
            "firmware/config",
            "documentation",
            "images",
            "datasheets",
            "simulation/results",
            "manufacturing",
        ]
        for d in dirs:
            (self.base_dir / d).mkdir(parents=True, exist_ok=True)
    
    def get_project_files(self) -> dict:
        """Get all files organized by category."""
        ...
    
    def get_file_relationships(self) -> list:
        """Get relationships between project files."""
        ...
```

### 3.2 File Intelligence

```python
class EngineeringFileIntel:
    """Recognize and understand engineering file formats."""
    
    FILE_TYPES = {
        # CAD
        ".stl": {"type": "cad", "format": "STL", "description": "3D mesh"},
        ".step": {"type": "cad", "format": "STEP", "description": "CAD exchange"},
        ".obj": {"type": "cad", "format": "OBJ", "description": "3D model"},
        ".f3d": {"type": "cad", "format": "Fusion360", "description": "Fusion 360 archive"},
        ".scad": {"type": "cad", "format": "OpenSCAD", "description": "Parametric model"},
        
        # PCB
        ".kicad_pcb": {"type": "pcb", "format": "KiCad", "description": "PCB layout"},
        ".kicad_sch": {"type": "pcb", "format": "KiCad", "description": "Schematic"},
        ".brd": {"type": "pcb", "format": "Eagle", "description": "PCB layout"},
        ".sch": {"type": "pcb", "format": "Eagle", "description": "Schematic"},
        ".gbr": {"type": "pcb", "format": "Gerber", "description": "Manufacturing"},
        
        # Embedded
        ".ino": {"type": "firmware", "format": "Arduino", "description": "Arduino sketch"},
        ".cpp": {"type": "firmware", "format": "C++", "description": "C++ source"},
        ".h": {"type": "firmware", "format": "C++", "description": "C++ header"},
        ".py": {"type": "firmware", "format": "Python", "description": "MicroPython"},
        
        # Documentation
        ".pdf": {"type": "doc", "format": "PDF", "description": "Document"},
        ".png": {"type": "image", "format": "PNG", "description": "Image"},
    }
    
    def analyze_file(self, path: str) -> dict:
        """Analyze an engineering file."""
        ...
    
    def find_related_files(self, path: str) -> list:
        """Find files related to the given file."""
        ...
```

---

## Phase 4: Developer CLI (Week 4)

### 4.1 CLI Structure

**File**: `jarvis/cli.py` (rewrite)

```python
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

console = Console()

@click.group()
@click.version_option(version="3.3.0")
def cli():
    """JARVIS — AI Engineering Operating System"""
    pass

# === Chat ===
@cli.command()
@click.argument("message", required=False)
@click.option("--session", "-s", help="Session ID")
def chat(message, session):
    """Interactive chat with JARVIS"""
    ...

# === Missions ===
@cli.group()
def mission():
    """Mission management"""
    pass

@mission.command("list")
def mission_list():
    """List active missions"""
    ...

@mission.command("create")
@click.argument("goal")
def mission_create(goal):
    """Create a new mission"""
    ...

@mission.command("status")
@click.argument("mission_id")
def mission_status(mission_id):
    """Show mission status"""
    ...

# === Agents ===
@cli.command()
def agents():
    """Show agent hierarchy"""
    table = Table(title="JARVIS Agent Hierarchy")
    table.add_column("Card", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("State", style="green")
    ...
    console.print(table)

# === Memory ===
@cli.group()
def memory():
    """Memory operations"""
    pass

@memory.command("search")
@click.argument("query")
def memory_search(query):
    """Search memory"""
    ...

# === Workspace ===
@cli.group()
def workspace():
    """Workspace management"""
    pass

# === Engineering ===
@cli.group()
def engineer():
    """Engineering operations"""
    pass

@engineer.command("cad")
@click.argument("action")
def engineer_cad(action):
    """CAD operations"""
    ...

@engineer.command("pcb")
@click.argument("action")
def engineer_pcb(action):
    """PCB operations"""
    ...

@engineer.command("firmware")
@click.argument("action")
def engineer_firmware(action):
    """Firmware operations"""
    ...

# === System ===
@cli.command()
def doctor():
    """System health check"""
    ...

@cli.command()
def config():
    """Configuration management"""
    ...

@cli.command()
def update():
    """Update JARVIS"""
    ...

if __name__ == "__main__":
    cli()
```

### 4.2 Rich Terminal Output

```python
# Streaming response with Rich
from rich.live import Live
from rich.markdown import Markdown

async def stream_chat(message: str):
    """Stream chat response with Rich rendering."""
    with Live(console=console, refresh_per_second=10) as live:
        async for chunk in chat_stream(message):
            live.update(Markdown(chunk))
```

### 4.3 Shell Auto-completion

```python
# Click completion
@cli.command()
@click.option("--complete", is_flag=True, expose_value=False, 
              is_eager=True, callback=complete)
def main(complete):
    ...
```

---

## Phase 5: Web UI Updates (Week 4)

### 5.1 Engineering Dashboard

Add engineering-specific UI to the web interface:

- CAD model viewer (Three.js with STL/STEP import)
- PCB layout viewer (SVG rendering)
- Firmware terminal (serial monitor)
- BOM table with cost estimation
- Manufacturing file download

### 5.2 API Endpoints

```python
# New engineering router
router = APIRouter(prefix="/api/engineering", tags=["engineering"])

@router.post("/cad/model")
async def create_cad_model(params: dict):
    ...

@router.get("/cad/models")
async def list_cad_models():
    ...

@router.post("/pcb/project")
async def create_pcb_project(params: dict):
    ...

@router.post("/pcb/gerber")
async def export_gerber(project_id: str):
    ...

@router.post("/firmware/compile")
async def compile_firmware(project_id: str):
    ...

@router.post("/firmware/upload")
async def upload_firmware(project_id: str, device: str):
    ...

@router.get("/knowledge/materials")
async def get_materials():
    ...

@router.post("/calculate")
async def engineering_calculate(formula: str, params: dict):
    ...
```

---

## Implementation Order

### Week 1: Foundation
1. Create `jarvis/engineering/` module structure
2. Implement provider ABCs (CAD, PCB, Embedded, Mechanical)
3. Add new workers (CADWorker, PCBWorker, FirmwareWorker, MechanicalWorker, HardwareTestWorker)
4. Register capabilities
5. Update Engineering King with engineering-specific planning

### Week 2: Tool Integration
1. Implement CLI wrappers (KiCad, Arduino CLI, PlatformIO, OpenSCAD)
2. Add engineering actions to ToolExecutor
3. Build engineering knowledge base
4. Implement material database and calculators

### Week 3: Workspace & Files
1. Extend WorkspaceManager for engineering projects
2. Implement file intelligence (format recognition, relationships)
3. Add engineering project structure templates
4. Integrate with Graphify for code+hardware knowledge graph

### Week 4: CLI & UI
1. Build Developer CLI with Rich
2. Add engineering API endpoints
3. Update web UI with engineering dashboard
4. Add streaming support for CLI

### Week 5: Polish & Test
1. Test all engineering workflows end-to-end
2. Add error handling and retry logic
3. Write documentation
4. Git commit and push

---

## Key Design Decisions

1. **Provider Pattern**: Each CAD/PCB/embedded platform gets a provider ABC. This allows swapping implementations without changing workers.

2. **CLI Wrappers First**: Most engineering tools (KiCad, Arduino CLI, PlatformIO) have CLI interfaces. Wrap these first, add API integrations later.

3. **Knowledge Base Integration**: Engineering knowledge (materials, formulas, components) integrates with the existing RAG system for context-aware assistance.

4. **Shared Backend**: The CLI and web interface use the same backend services. No duplicate logic.

5. **Observable Engineering**: All engineering actions emit events, get recorded in the mission timeline, and are available for replay/explainability.

6. **Future Simulation**: Define simulation interfaces now, implement later. This allows simulation engines to be added without changing higher-level logic.
