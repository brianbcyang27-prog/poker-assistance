"""WhatsApp connector — placeholder (coming soon)."""

from __future__ import annotations

from jarvis.integrations.base import Connector, ConnectorCategory


class WhatsAppConnector(Connector):
    id = "whatsapp"
    name = "WhatsApp"
    category = ConnectorCategory.MESSAGING
    description = "Send and receive WhatsApp messages through the Cloud API."
    capabilities = []
    config_fields = []
    requires_config = False
    coming_soon = True
    needs_setup_guide = True
    setup_guide = (
        "WhatsApp integration is on the roadmap — Meta Cloud API access is "
        "being set up. No action needed right now."
    )

    async def test(self) -> tuple[bool, str]:
        return False, "Coming soon"
