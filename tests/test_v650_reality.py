"""JARVIS v6.5.0 Reality & Productization Tests.

Tests that all core features work together.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    from jarvis.web.main import create_app, lifespan
    app = create_app()
    async with lifespan(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=30.0) as c:
            yield c


class TestV650Reality:
    """Test v6.5.0 core features."""

    @pytest.mark.anyio
    async def test_server_starts(self, client):
        """Test that server starts and responds."""
        r = await client.get("/api/system/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    @pytest.mark.anyio
    async def test_frontend_loads(self, client):
        """Test that frontend loads."""
        r = await client.get("/")
        assert r.status_code == 200
        assert "JARVIS" in r.text

    @pytest.mark.anyio
    async def test_chat_works(self, client):
        """Test chat streaming endpoint."""
        r = await client.get("/api/chat/stream?message=hello&session_id=test_v650")
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

    @pytest.mark.anyio
    async def test_memory_works(self, client):
        """Test memory system."""
        r = await client.get("/api/memory/episodes")
        assert r.status_code == 200

    @pytest.mark.anyio
    async def test_tools_visible(self, client):
        """Test that tools are registered."""
        r = await client.get("/api/system/capabilities")
        assert r.status_code == 200
        data = r.json()
        assert len(data["capabilities"]) > 0

    @pytest.mark.anyio
    async def test_computer_permission(self, client):
        """Test computer permission system."""
        r = await client.get("/api/system/permissions")
        assert r.status_code == 200
        data = r.json()
        assert "permissions" in data
        assert len(data["permissions"]) > 0

    @pytest.mark.anyio
    async def test_golden_core_renders(self, client):
        """Test that golden core container exists in frontend."""
        r = await client.get("/")
        assert r.status_code == 200
        assert "golden-core-container" in r.text

    @pytest.mark.anyio
    async def test_developer_mode_toggle(self, client):
        """Test that developer mode toggle exists."""
        r = await client.get("/")
        assert r.status_code == 200
        assert "dev-mode-toggle" in r.text

    @pytest.mark.anyio
    async def test_memory_health(self, client):
        """Test memory health check."""
        r = await client.get("/api/memory/health")
        assert r.status_code == 200
        data = r.json()
        assert "healthy" in data

    @pytest.mark.anyio
    async def test_workflows_available(self, client):
        """Test that workflows are available."""
        r = await client.get("/api/computer/workflows")
        assert r.status_code == 200
        data = r.json()
        assert "workflows" in data
        assert len(data["workflows"]) > 0

    @pytest.mark.anyio
    async def test_permissions_update(self, client):
        """Test permission update."""
        r = await client.post("/api/system/permissions", json={
            "permission": "browser",
            "enabled": True
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
