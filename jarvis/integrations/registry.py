"""Integration registry — connector lifecycle, credential persistence, dispatch."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from jarvis.integrations.base import Connector, ConnectorStatus

if TYPE_CHECKING:
    from jarvis.core.database import Database

log = logging.getLogger("jarvis.integrations")

_registry: IntegrationRegistry | None = None


def get_registry(db: Database | None = None) -> IntegrationRegistry:
    """Return the process-wide registry singleton."""
    global _registry
    if _registry is None:
        _registry = IntegrationRegistry(db)
    return _registry


class IntegrationRegistry:
    """Owns every registered connector and its persisted state.

    Credentials live in SQLite ``preferences`` rows keyed
    ``integration.<id>.config`` (JSON) and ``integration.<id>.status``.
    """

    def __init__(self, db: Database | None = None):
        self._db = db
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        connector._registry = self
        self._connectors[connector.id] = connector
        log.info("Registered integration connector: %s", connector.id)

    def get(self, integration_id: str) -> Connector | None:
        return self._connectors.get(integration_id)

    def all(self) -> list[Connector]:
        return list(self._connectors.values())

    def _require_db(self) -> Database:
        if self._db is None:
            from jarvis.core.database import get_db

            self._db = get_db()
        return self._db

    async def init(self) -> None:
        for connector in self._connectors.values():
            await self._load_connector_config(connector)
        log.info("Integration registry initialized: %d connectors", len(self._connectors))

    # ── persistence ───────────────────────────────────────────────

    async def _load_connector_config(self, connector: Connector) -> None:
        try:
            db = self._require_db()
            raw = await db.get_preference(f"integration.{connector.id}.config")
            if raw:
                data = json.loads(raw)
                connector.config = data.get("config", {}) or {}
                connector.configured = bool(data.get("configured", False))
                connector.connected = bool(data.get("connected", False))
                connector.last_checked = data.get("last_checked")
                connector.error = data.get("error")
                connector.status = data.get("status", connector.status)
                if connector.requires_config and not connector.config:
                    connector.status = ConnectorStatus.NEEDS_CONFIG
                elif connector.connected:
                    connector.status = ConnectorStatus.CONNECTED
                elif connector.config:
                    connector.status = ConnectorStatus.CONFIGURED
        except Exception as exc:  # noqa: BLE001 — never crash startup on bad state
            log.warning("Failed to load config for %s: %s", connector.id, exc)

    async def _save_connector_config(self, connector: Connector) -> None:
        db = self._require_db()
        payload = json.dumps(
            {
                "config": connector.config,
                "configured": connector.configured,
                "connected": connector.connected,
                "last_checked": connector.last_checked,
                "error": connector.error,
                "status": str(connector.status.value),
            }
        )
        await db.set_preference(f"integration.{connector.id}.config", payload)

    # ── API operations ────────────────────────────────────────────

    async def save_config(self, integration_id: str, config: dict) -> Connector:
        connector = self.get(integration_id)
        if connector is None:
            raise KeyError(f"Unknown integration: {integration_id}")
        merged = dict(connector.config)
        merged.update({k: v for k, v in config.items() if v not in (None, "")})
        connector.config = merged
        connector.configured = bool(merged)
        connector.status = (
            ConnectorStatus.CONNECTED
            if connector.connected
            else ConnectorStatus.CONFIGURED
        )
        connector.error = None
        await self._save_connector_config(connector)
        return connector

    async def test(self, integration_id: str) -> dict:
        connector = self.get(integration_id)
        if connector is None:
            raise KeyError(f"Unknown integration: {integration_id}")
        if connector.requires_config and not connector.config:
            return {"ok": False, "detail": "No credentials configured yet"}
        result = await connector.run_test()
        await self._save_connector_config(connector)
        return result

    async def disconnect(self, integration_id: str) -> Connector:
        connector = self.get(integration_id)
        if connector is None:
            raise KeyError(f"Unknown integration: {integration_id}")
        await connector.disconnect()
        await self._save_connector_config(connector)
        return connector

    async def run_action(self, integration_id: str, action: str, params: dict) -> dict:
        connector = self.get(integration_id)
        if connector is None:
            raise KeyError(f"Unknown integration: {integration_id}")
        if connector.requires_config and not connector.connected:
            return {"ok": False, "error": f"{connector.name} is not connected"}
        try:
            result = await connector.action(action, params or {})
        except Exception as exc:  # noqa: BLE001 — connector boundary
            log.exception("Integration %s action %s failed", integration_id, action)
            return {"ok": False, "error": str(exc)}
        if isinstance(result, dict) and "ok" not in result:
            result["ok"] = True
        return result

    def info_all(self) -> list[dict]:
        return [c.info().to_dict() for c in self._connectors.values()]
