"""Tests for coming-soon connectors and the registry wiring."""

from jarvis.integrations.base import ConnectorStatus
from jarvis.integrations.connectors import register_connectors
from jarvis.integrations.connectors.instagram import InstagramConnector
from jarvis.integrations.connectors.whatsapp import WhatsAppConnector
from jarvis.integrations.registry import IntegrationRegistry


async def test_whatsapp_coming_soon():
    connector = WhatsAppConnector()
    assert connector.coming_soon is True
    assert connector.requires_config is False
    ok, detail = await connector.test()
    assert ok is False
    assert "Coming soon" in detail
    info = connector.info().to_dict()
    assert info["coming_soon"] is True
    assert info["status"] == ConnectorStatus.AVAILABLE.value


async def test_instagram_coming_soon():
    connector = InstagramConnector()
    assert connector.coming_soon is True
    ok, detail = await connector.test()
    assert ok is False
    assert "Coming soon" in detail


def test_register_connectors_registers_all_eight():
    registry = IntegrationRegistry()
    register_connectors(registry)
    ids = {c.id for c in registry.all()}
    assert ids == {
        "apple",
        "telegram",
        "github",
        "notion",
        "google",
        "line",
        "whatsapp",
        "instagram",
    }
    infos = registry.info_all()
    assert len(infos) == 8
    for info in infos:
        assert info["name"]
        assert info["category"] in {"apple", "messaging", "productivity", "dev", "social"}
