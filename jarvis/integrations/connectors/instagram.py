"""Instagram connector — placeholder (coming soon)."""

from __future__ import annotations

from jarvis.integrations.base import Connector, ConnectorCategory


class InstagramConnector(Connector):
    id = "instagram"
    name = "Instagram"
    category = ConnectorCategory.SOCIAL
    description = "Connect your Instagram account for insights and posts."
    capabilities = []
    config_fields = []
    requires_config = False
    coming_soon = True
    needs_setup_guide = True
    setup_guide = (
        "Instagram integration is on the roadmap — Meta Graph API access is "
        "being set up. No action needed right now."
    )

    async def test(self) -> tuple[bool, str]:
        return False, "Coming soon"
