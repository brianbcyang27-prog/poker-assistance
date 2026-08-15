"""Connector implementations. Each module registers one or more Connector subclasses."""

from __future__ import annotations

import logging

from jarvis.integrations.base import Connector

log = logging.getLogger("jarvis.integrations")


def register_connectors(registry) -> None:
    """Register every available connector into the given registry."""
    from .apple import AppleConnector
    from .github import GitHubConnector
    from .google import GoogleConnector
    from .instagram import InstagramConnector
    from .line import LineConnector
    from .notion import NotionConnector
    from .telegram import TelegramConnector
    from .whatsapp import WhatsAppConnector

    for connector_cls in (
        AppleConnector,
        TelegramConnector,
        GitHubConnector,
        NotionConnector,
        GoogleConnector,
        LineConnector,
        WhatsAppConnector,
        InstagramConnector,
    ):
        if isinstance(connector_cls, type) and issubclass(connector_cls, Connector):
            registry.register(connector_cls())
        else:
            log.warning("Skipping invalid connector registration: %r", connector_cls)
