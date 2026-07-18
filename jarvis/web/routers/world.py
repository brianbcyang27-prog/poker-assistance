"""World router — Computing environment state for the World Model."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/world", tags=["world"])


@router.get("")
async def get_world():
    """Return full world model state."""
    from jarvis.brain.world_model import world_model
    return world_model.to_dict()


@router.get("/projects")
async def get_projects():
    """Return scanned projects with git status."""
    from jarvis.brain.world_model import world_model
    data = world_model.scan_environment()
    return {"projects": data["projects"], "total": len(data["projects"])}


@router.get("/servers")
async def get_servers():
    """Return active servers (listening ports)."""
    from jarvis.brain.world_model import world_model
    data = world_model.scan_environment()
    return {"servers": data["servers"], "total": len(data["servers"])}


@router.get("/system")
async def get_system():
    """Return system info (hostname, OS, disk, memory)."""
    from jarvis.brain.world_model import world_model
    data = world_model.scan_environment()
    return data["system"]


@router.post("/scan")
async def force_scan():
    """Force a rescan of the environment."""
    from jarvis.brain.world_model import world_model
    return world_model.force_scan()
