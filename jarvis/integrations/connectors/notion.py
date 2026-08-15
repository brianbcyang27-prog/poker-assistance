"""Notion connector — REST API via httpx."""

from __future__ import annotations

import httpx

from jarvis.integrations.base import ConfigField, Connector, ConnectorCategory

_API = "https://api.notion.com"
_VERSION = "2022-06-28"


class NotionConnector(Connector):
    id = "notion"
    name = "Notion"
    category = ConnectorCategory.PRODUCTIVITY
    description = "Read your workspace identity and search pages and databases."
    capabilities = ["user_info", "search"]
    config_fields = [
        ConfigField(
            key="api_token",
            label="Integration Token",
            type="password",
            required=True,
            secret=True,
            placeholder="secret_...",
            help="notion.so/my-integrations → New integration. "
            "Must be shared with pages you want to search.",
        )
    ]
    requires_config = True
    needs_setup_guide = True
    setup_guide = (
        "1. Open notion.so/my-integrations and create an integration.\n"
        "2. Copy the 'Internal Integration Secret' token.\n"
        "3. Share the pages/databases you want JARVIS to read with that integration.\n"
        "4. Paste the token above and hit Test."
    )

    def __init__(self, registry=None, http_client: httpx.AsyncClient | None = None):
        super().__init__(registry)
        self._http = http_client

    async def _client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return self._http
        return httpx.AsyncClient(timeout=10.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config.get('api_token', '')}",
            "Notion-Version": _VERSION,
        }

    async def test(self) -> tuple[bool, str]:
        client = await self._client()
        async with client:
            resp = await client.get(f"{_API}/v1/users/me", headers=self._headers())
            if resp.status_code == 401:
                return False, "Invalid token"
            if resp.status_code != 200:
                return False, f"Notion API error {resp.status_code}"
            user = resp.json().get("bot", {})
            return True, f"Connected as {user.get('owner', {}).get('workspace_name', 'workspace')}"

    async def action(self, action: str, params: dict | None = None) -> dict:
        params = params or {}
        client = await self._client()
        async with client:
            if action == "user_info":
                resp = await client.get(f"{_API}/v1/users/me", headers=self._headers())
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                return {"ok": True, "action": action, "bot": resp.json().get("bot", {})}
            if action == "search":
                query = params.get("query", "")
                body = {"page_size": min(int(params.get("limit", 10)), 100)}
                if query:
                    body["query"] = query
                resp = await client.post(
                    f"{_API}/v1/search", json=body, headers=self._headers()
                )
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                results = [
                    {"id": r.get("id"), "title": self._extract_title(r)}
                    for r in resp.json().get("results", [])
                ]
                return {"ok": True, "action": action, "results": results}
        return {"ok": False, "error": f"Unknown notion action: {action}"}

    @staticmethod
    def _extract_title(page: dict) -> str:
        props = page.get("properties") or {}
        for prop in props.values():
            if prop.get("type") != "title":
                continue
            for part in prop.get("title", []):
                if part.get("plain_text"):
                    return part["plain_text"]
        return page.get("id", "untitled")
