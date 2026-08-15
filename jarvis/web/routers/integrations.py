"""Integration API endpoints.

GET    /api/integrations               → all connectors + status
GET    /api/integrations/{id}          → single connector detail
POST   /api/integrations/{id}/config   → save credentials
POST   /api/integrations/{id}/test     → verify connectivity
POST   /api/integrations/{id}/disconnect → clear credentials
POST   /api/integrations/{id}/action   → invoke a connector capability
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.integrations import get_registry

log = logging.getLogger("jarvis.integrations")

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class ConfigUpdate(BaseModel):
    config: dict = Field(default_factory=dict)


class ActionRequest(BaseModel):
    action: str
    params: dict = Field(default_factory=dict)


def _registry():
    return get_registry()


@router.get("")
async def list_integrations():
    return {"integrations": _registry().info_all()}


@router.get("/{integration_id}")
async def get_integration(integration_id: str):
    connector = _registry().get(integration_id)
    if connector is None:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {integration_id}")
    return {"integration": connector.info().to_dict()}


@router.post("/{integration_id}/config")
async def save_integration_config(integration_id: str, update: ConfigUpdate):
    try:
        connector = await _registry().save_config(integration_id, update.config)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "integration": connector.info().to_dict()}


@router.post("/{integration_id}/test")
async def test_integration(integration_id: str):
    try:
        return await _registry().test(integration_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(integration_id: str):
    try:
        connector = await _registry().disconnect(integration_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "integration": connector.info().to_dict()}


@router.post("/{integration_id}/action")
async def run_integration_action(integration_id: str, request: ActionRequest):
    try:
        return await _registry().run_action(integration_id, request.action, request.params)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# === Repo Research & Install ===


class ResearchRequest(BaseModel):
    url: str


class InstallRequest(BaseModel):
    url: str


@router.post("/research")
async def research_repo(request: ResearchRequest):
    """Investigate a GitHub repo URL and report benefits, cons, and install plan."""
    from jarvis.web.services.repo_research import research

    report = await asyncio.to_thread(research, request.url)
    if not report.get("ok"):
        raise HTTPException(status_code=400, detail=report.get("error", "Research failed"))
    return report


@router.post("/install")
async def install_repo(request: InstallRequest):
    """Install a previously researched repo (clone + whitelisted build step)."""
    from jarvis.web.services.repo_research import install

    result = await asyncio.to_thread(install, request.url)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Install failed"))
    return result


@router.post("/uninstall")
async def uninstall_repo(request: InstallRequest):
    """Remove a previously installed repo (pip uninstall or clone removal)."""
    from jarvis.web.services.repo_research import uninstall

    result = await asyncio.to_thread(uninstall, request.url)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Uninstall failed"))
    return result


@router.get("/research/list")
async def research_history():
    """List all researched and installed repos."""
    from jarvis.web.services.repo_research import history

    return {"repos": history()}
