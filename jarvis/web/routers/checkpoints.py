"""Checkpoint API endpoints for JARVIS v8.0.0."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from jarvis.core.checkpoint import checkpoint_manager

router = APIRouter(prefix="/api/checkpoints", tags=["checkpoints"])


class FileCheckpointRequest(BaseModel):
    file_path: str
    description: Optional[str] = ""


class RestoreRequest(BaseModel):
    checkpoint_id: str


@router.post("/file")
async def create_file_checkpoint(req: FileCheckpointRequest):
    """Create a checkpoint before modifying a file."""
    cp = checkpoint_manager.create_file_checkpoint(
        file_path=req.file_path,
        description=req.description,
    )
    if not cp:
        raise HTTPException(status_code=400, detail="File not found or checkpoint failed")
    return {"ok": True, "checkpoint": cp.to_dict()}


@router.post("/file/restore")
async def restore_file_checkpoint(req: RestoreRequest):
    """Restore a file from checkpoint."""
    ok = checkpoint_manager.restore_file_checkpoint(req.checkpoint_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Checkpoint not found or restore failed")
    return {"ok": True, "checkpoint_id": req.checkpoint_id}


class MissionCheckpointRequest(BaseModel):
    mission_id: str
    state: dict
    description: Optional[str] = ""


@router.post("/mission")
async def create_mission_checkpoint(req: MissionCheckpointRequest):
    """Create a checkpoint for mission state."""
    cp = checkpoint_manager.create_mission_checkpoint(
        mission_id=req.mission_id,
        state=req.state,
        description=req.description,
    )
    return {"ok": True, "checkpoint": cp.to_dict()}


@router.post("/mission/restore")
async def restore_mission_checkpoint(req: RestoreRequest):
    """Restore mission state from checkpoint."""
    state = checkpoint_manager.restore_mission_checkpoint(req.checkpoint_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return {"ok": True, "state": state}


@router.get("")
async def list_checkpoints(type: Optional[str] = None, limit: int = 50):
    """List checkpoints."""
    cps = checkpoint_manager.list_checkpoints(type_filter=type, limit=limit)
    return {"checkpoints": [cp.to_dict() for cp in cps]}


@router.delete("/{checkpoint_id}")
async def delete_checkpoint(checkpoint_id: str):
    """Delete a checkpoint."""
    ok = checkpoint_manager.delete_checkpoint(checkpoint_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return {"ok": True, "checkpoint_id": checkpoint_id}
