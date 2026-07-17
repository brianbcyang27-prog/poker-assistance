"""Engineering API endpoints for hardware design operations."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter(prefix="/api/engineering", tags=["engineering"])


# --- Request Models ---

class CADCreateRequest(BaseModel):
    name: str
    model_type: str = "part"
    dimensions: dict = {}
    material: Optional[str] = None


class CADExportRequest(BaseModel):
    model_id: str
    format: str = "stl"
    path: Optional[str] = None


class PCBCreateRequest(BaseModel):
    name: str
    layers: int = 2
    dimensions: dict = {}


class FirmwareCreateRequest(BaseModel):
    name: str
    platform: str  # arduino, esp32, stm32, raspberry_pi, micropython
    board: Optional[str] = None


class FirmwareCompileRequest(BaseModel):
    project_id: str
    config: str = "release"


class FirmwareUploadRequest(BaseModel):
    project_id: str
    port: Optional[str] = None


class KnowledgeQueryRequest(BaseModel):
    query: str
    category: Optional[str] = None


class MaterialRecommendRequest(BaseModel):
    requirements: dict


class BearingSelectRequest(BaseModel):
    load_n: float
    speed_rpm: float
    bore_mm: Optional[float] = None


class GearRatioRequest(BaseModel):
    driver_teeth: int
    driven_teeth: int
    input_rpm: float


class BeamStressRequest(BaseModel):
    force_n: float
    length_m: float
    width_m: float
    height_m: float


# --- CAD Endpoints ---

@router.post("/cad/create")
async def cad_create(req: CADCreateRequest):
    """Create a new 3D model."""
    from ...engineering.cad.base import CADProvider
    cad = CADProvider()
    model_id = await cad.create_model(
        name=req.name,
        model_type=req.model_type,
        dimensions=req.dimensions,
        material=req.material,
    )
    return {"success": True, "model_id": model_id}


@router.post("/cad/export")
async def cad_export(req: CADExportRequest):
    """Export model to file."""
    from ...engineering.cad.base import CADProvider
    cad = CADProvider()
    path = await cad.export_model(
        model_id=req.model_id,
        format=req.format,
        path=req.path,
    )
    return {"success": True, "path": path}


@router.get("/cad/models")
async def cad_list_models():
    """List all CAD models."""
    from ...engineering.cad.base import CADProvider
    cad = CADProvider()
    models = cad.list_models()
    return {"success": True, "models": models}


# --- PCB Endpoints ---

@router.post("/pcb/create")
async def pcb_create(req: PCBCreateRequest):
    """Create a new PCB board."""
    from ...engineering.pcb.base import PCBProvider
    pcb = PCBProvider()
    board_id = await pcb.create_board(
        name=req.name,
        layers=req.layers,
        dimensions=req.dimensions,
    )
    return {"success": True, "board_id": board_id}


@router.post("/pcb/drc")
async def pcb_drc(board_id: str):
    """Run design rule check."""
    from ...engineering.pcb.base import PCBProvider
    pcb = PCBProvider()
    results = await pcb.run_drc(board_id=board_id)
    return {"success": True, "results": results}


@router.post("/pcb/export")
async def pcb_export(board_id: str, path: Optional[str] = None):
    """Export Gerber files."""
    from ...engineering.pcb.base import PCBProvider
    pcb = PCBProvider()
    export_path = await pcb.export_gerbers(board_id=board_id, path=path)
    return {"success": True, "path": export_path}


# --- Firmware Endpoints ---

@router.post("/firmware/create")
async def firmware_create(req: FirmwareCreateRequest):
    """Create a new firmware project."""
    from ...engineering.embedded.base import EmbeddedProvider
    embedded = EmbeddedProvider()
    project_id = await embedded.create_project(
        name=req.name,
        platform=req.platform,
        board=req.board,
    )
    return {"success": True, "project_id": project_id}


@router.post("/firmware/compile")
async def firmware_compile(req: FirmwareCompileRequest):
    """Compile firmware."""
    from ...engineering.embedded.base import EmbeddedProvider
    embedded = EmbeddedProvider()
    result = await embedded.compile(
        project_id=req.project_id,
        config=req.config,
    )
    return {"success": True, "result": result}


@router.post("/firmware/upload")
async def firmware_upload(req: FirmwareUploadRequest):
    """Upload firmware to device."""
    from ...engineering.embedded.base import EmbeddedProvider
    embedded = EmbeddedProvider()
    result = await embedded.upload(
        project_id=req.project_id,
        port=req.port,
    )
    return {"success": True, "result": result}


@router.get("/firmware/devices")
async def firmware_devices():
    """List connected devices."""
    from ...engineering.embedded.base import EmbeddedProvider
    embedded = EmbeddedProvider()
    devices = await embedded.list_devices()
    return {"success": True, "devices": devices}


# --- Mechanical Endpoints ---

@router.get("/mechanical/materials")
async def mechanical_materials():
    """List available materials."""
    from ...engineering.knowledge import engineering_knowledge
    materials = engineering_knowledge.list_materials()
    return {"success": True, "materials": materials}


@router.get("/mechanical/material/{name}")
async def mechanical_material(name: str):
    """Get material properties."""
    from ...engineering.knowledge import engineering_knowledge
    mat = engineering_knowledge.get_material(name)
    if not mat:
        raise HTTPException(status_code=404, detail=f"Material '{name}' not found")
    return {"success": True, "material": mat}


@router.post("/mechanical/material/recommend")
async def mechanical_recommend(req: MaterialRecommendRequest):
    """Recommend materials based on requirements."""
    from ...engineering.knowledge import engineering_knowledge
    candidates = engineering_knowledge.get_material_recommendation(req.requirements)
    return {"success": True, "candidates": candidates}


@router.post("/mechanical/bearing")
async def mechanical_bearing(req: BearingSelectRequest):
    """Select best bearing for requirements."""
    from ...engineering.knowledge import engineering_knowledge
    bearing = engineering_knowledge.select_bearing(
        load_n=req.load_n,
        speed_rpm=req.speed_rpm,
        bore_mm=req.bore_mm,
    )
    if not bearing:
        return {"success": False, "message": "No suitable bearing found"}
    return {"success": True, "bearing": bearing}


@router.post("/mechanical/gear")
async def mechanical_gear(req: GearRatioRequest):
    """Calculate gear ratio."""
    from ...engineering.knowledge import engineering_knowledge
    result = engineering_knowledge.calculate_gear_ratio(
        driver_teeth=req.driver_teeth,
        driven_teeth=req.driven_teeth,
        input_rpm=req.input_rpm,
    )
    return {"success": True, "gear": result}


@router.post("/mechanical/beam")
async def mechanical_beam(req: BeamStressRequest):
    """Calculate beam stress."""
    from ...engineering.knowledge import engineering_knowledge
    result = engineering_knowledge.calculate_beam_stress(
        force_n=req.force_n,
        length_m=req.length_m,
        width_m=req.width_m,
        height_m=req.height_m,
    )
    return {"success": True, "beam": result}


# --- Knowledge Endpoints ---

@router.post("/knowledge/query")
async def knowledge_query(req: KnowledgeQueryRequest):
    """Query the engineering knowledge base."""
    from ...engineering.knowledge import engineering_knowledge
    result = engineering_knowledge.query(req.query, req.category)
    return {"success": True, "result": result}


@router.get("/knowledge/formulas")
async def knowledge_formulas():
    """List all formulas."""
    from ...engineering.knowledge import engineering_knowledge
    formulas = list(engineering_knowledge.formulas.keys())
    return {"success": True, "formulas": formulas}


@router.get("/knowledge/formula/{name}")
async def knowledge_formula(name: str):
    """Get formula details."""
    from ...engineering.knowledge import engineering_knowledge
    formula = engineering_knowledge.formulas.get(name)
    if not formula:
        raise HTTPException(status_code=404, detail=f"Formula '{name}' not found")
    return {"success": True, "formula": formula}


# --- Summary Endpoint ---

@router.get("/summary")
async def engineering_summary():
    """Get engineering suite summary."""
    from ...engineering.knowledge import engineering_knowledge
    
    return {
        "version": "3.3.0",
        "modules": {
            "cad": "3D Modeling & Parametric Design",
            "pcb": "Circuit Board Design & Manufacturing",
            "firmware": "Embedded Systems Programming",
            "mechanical": "Mechanical Engineering Analysis",
            "simulation": "Engineering Simulation (coming soon)",
            "knowledge": "Engineering Reference Database",
        },
        "workers": [
            {"card": "♠4M", "name": "CAD Specialist"},
            {"card": "♠3", "name": "PCB Engineer"},
            {"card": "♠2", "name": "Firmware Engineer"},
            {"card": "♠4M", "name": "Mechanical Engineer"},
            {"card": "♠3T", "name": "Hardware Test Engineer"},
        ],
        "knowledge_stats": {
            "materials": len(engineering_knowledge.materials),
            "bearings": len(engineering_knowledge.bearings),
            "formulas": len(engineering_knowledge.formulas),
        },
    }
