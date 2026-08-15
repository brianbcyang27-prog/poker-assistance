"""Connector base class and shared types for the integration framework."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum

log = logging.getLogger("jarvis.integrations")


class ConnectorStatus(StrEnum):
    AVAILABLE = "available"
    NEEDS_CONFIG = "needs_config"
    CONFIGURED = "configured"
    CONNECTED = "connected"
    ERROR = "error"


class ConnectorCategory(StrEnum):
    APPLE = "apple"
    MESSAGING = "messaging"
    PRODUCTIVITY = "productivity"
    DEV = "dev"
    SOCIAL = "social"


@dataclass
class ConfigField:
    key: str
    label: str
    type: str = "text"
    required: bool = True
    placeholder: str = ""
    help: str = ""
    secret: bool = False
    options: list[str] = field(default_factory=list)


@dataclass
class IntegrationInfo:
    id: str
    name: str
    category: str
    description: str
    capabilities: list[str]
    config_fields: list[ConfigField]
    requires_config: bool
    status: str = ConnectorStatus.AVAILABLE
    configured: bool = False
    connected: bool = False
    last_checked: float | None = None
    error: str | None = None
    needs_setup_guide: bool = False
    setup_guide: str = ""
    coming_soon: bool = False

    def to_dict(self, with_secrets: bool = False) -> dict:
        fields = []
        for f in self.config_fields:
            entry = {
                "key": f.key,
                "label": f.label,
                "type": f.type,
                "required": f.required,
                "placeholder": f.placeholder,
                "help": f.help,
                "secret": f.secret,
                "options": f.options,
            }
            if with_secrets and f.secret:
                entry["has_value"] = self.config_has.get(f.key, False)
            fields.append(entry)
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "capabilities": self.capabilities,
            "config_fields": fields,
            "requires_config": self.requires_config,
            "status": self.status,
            "configured": self.configured,
            "connected": self.connected,
            "last_checked": self.last_checked,
            "error": self.error,
            "needs_setup_guide": self.needs_setup_guide,
            "setup_guide": self.setup_guide,
            "coming_soon": self.coming_soon,
        }


class Connector:
    """Base class for all integrations.

    Subclasses declare ``id``/``name``/``category``/``capabilities`` and
    implement ``test()`` plus ``action()``. Credentials live in ``self.config``
    and are persisted by the registry through ``load_config``/``save_config``.
    """

    id: str = "base"
    name: str = "Base"
    category: ConnectorCategory = ConnectorCategory.PRODUCTIVITY
    description: str = ""
    capabilities: list[str] = []
    config_fields: list[ConfigField] = []
    requires_config: bool = False
    needs_setup_guide: bool = False
    setup_guide: str = ""
    coming_soon: bool = False

    def __init__(self, registry=None):
        self._registry = registry
        self.config: dict = {}
        self.status = (
            ConnectorStatus.NEEDS_CONFIG if self.requires_config else ConnectorStatus.AVAILABLE
        )
        self.configured = False
        self.connected = False
        self.last_checked: float | None = None
        self.error: str | None = None

    # ── lifecycle hooks ────────────────────────────────────────────

    async def load_config(self) -> None:
        if self._registry is not None:
            await self._registry._load_connector_config(self)

    async def save_config(self) -> None:
        if self._registry is not None:
            await self._registry._save_connector_config(self)

    async def test(self) -> tuple[bool, str]:
        """Verify connectivity. Returns (ok, detail)."""
        raise NotImplementedError

    async def disconnect(self) -> None:
        self.configured = False
        self.connected = False
        self.config = {}
        self.error = None
        if self.requires_config:
            self.status = ConnectorStatus.NEEDS_CONFIG
        else:
            self.status = ConnectorStatus.AVAILABLE
        if self._registry is not None:
            await self._registry._save_connector_config(self)

    async def action(self, action: str, params: dict | None = None) -> dict:
        """Execute a connector capability. Always returns a dict."""
        raise NotImplementedError(f"{self.id} does not expose actions")

    # ── state helpers ─────────────────────────────────────────────

    def mark_connected(self) -> None:
        self.status = ConnectorStatus.CONNECTED
        self.connected = True
        self.configured = True
        self.error = None
        self.last_checked = time.time()

    def mark_error(self, message: str) -> None:
        self.status = ConnectorStatus.ERROR
        self.connected = False
        self.error = message
        self.last_checked = time.time()

    def info(self) -> IntegrationInfo:
        info = IntegrationInfo(
            id=self.id,
            name=self.name,
            category=str(self.category.value),
            description=self.description,
            capabilities=list(self.capabilities),
            config_fields=list(self.config_fields),
            requires_config=self.requires_config,
            status=str(self.status.value),
            configured=self.configured,
            connected=self.connected,
            last_checked=self.last_checked,
            error=self.error,
            needs_setup_guide=self.needs_setup_guide,
            setup_guide=self.setup_guide,
            coming_soon=self.coming_soon,
        )
        info.config_has = {f.key: bool(self.config.get(f.key)) for f in self.config_fields}
        return info

    async def run_test(self) -> dict:
        """Test wrapper that updates connector state. Returns status payload."""
        try:
            ok, detail = await self.test()
        except Exception as exc:  # noqa: BLE001 — connector boundaries surface any error
            log.exception("Integration %s test crashed", self.id)
            self.mark_error(str(exc))
            return {"ok": False, "detail": str(exc), "status": self.status.value}
        if ok:
            self.mark_connected()
            return {"ok": True, "detail": detail, "status": self.status.value}
        self.mark_error(detail)
        return {"ok": False, "detail": detail, "status": self.status.value}
