"""Integration framework — pluggable connectors for external services.

JARVIS connects to the user's world through a unified connector registry:

    Apple (local macOS)   → Calendar, Reminders, Contacts, Mail
    Messaging             → Telegram, LINE, WhatsApp
    Productivity          → Google Calendar/Gmail, Notion
    Dev                   → GitHub
    Social                → Instagram

Each connector implements the :class:`Connector` base and registers itself
with the :class:`IntegrationRegistry`. The registry persists credentials
in SQLite (via the existing preferences table) and exposes a REST API
through ``jarvis/web/routers/integrations.py``.

Status lifecycle:

    available    → works with zero configuration (e.g. Apple local APIs)
    needs_config → requires credentials before use
    configured   → credentials saved, not yet verified
    connected    → ``test()`` passed; ready to act
    error        → last ``test()`` failed (``error`` carries the reason)
"""

from jarvis.integrations.base import (
    ConfigField,
    Connector,
    ConnectorCategory,
    ConnectorStatus,
    IntegrationInfo,
)
from jarvis.integrations.registry import IntegrationRegistry, get_registry

__all__ = [
    "ConfigField",
    "Connector",
    "ConnectorCategory",
    "ConnectorStatus",
    "IntegrationInfo",
    "IntegrationRegistry",
    "get_registry",
]
