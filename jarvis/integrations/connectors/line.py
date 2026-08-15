"""LINE connector — Messaging API via httpx."""

from __future__ import annotations

import httpx

from jarvis.integrations.base import ConfigField, Connector, ConnectorCategory

_API = "https://api.line.me"


class LineConnector(Connector):
    id = "line"
    name = "LINE"
    category = ConnectorCategory.MESSAGING
    description = "Verify your LINE channel and push messages to yourself."
    capabilities = ["get_profile", "send_message"]
    config_fields = [
        ConfigField(
            key="access_token",
            label="Channel Access Token",
            type="password",
            required=True,
            secret=True,
            placeholder="xxxxx=",
            help="LINE Developers console → Messaging API channel → "
            "Channel access token (long-lived).",
        ),
        ConfigField(
            key="user_id",
            label="Your User ID",
            type="text",
            required=False,
            placeholder="U...",
            help="Your LINE user ID, used for push messages. Found in the Messaging API settings.",
        ),
    ]
    requires_config = True
    needs_setup_guide = True
    setup_guide = (
        "1. Open developers.line.me and create a Messaging API channel.\n"
        "2. Issue a long-lived Channel Access Token.\n"
        "3. Copy your User ID (U…).\n"
        "4. Paste both above and hit Test."
    )

    def __init__(self, registry=None, http_client: httpx.AsyncClient | None = None):
        super().__init__(registry)
        self._http = http_client

    async def _client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return self._http
        return httpx.AsyncClient(timeout=10.0)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.config.get('access_token', '')}"}

    async def test(self) -> tuple[bool, str]:
        client = await self._client()
        async with client:
            resp = await client.get(f"{_API}/v2/profile", headers=self._headers())
            if resp.status_code == 401:
                return False, "Invalid channel access token"
            if resp.status_code != 200:
                return False, f"LINE API error {resp.status_code}"
            profile = resp.json()
            return True, f"Connected as {profile.get('displayName')}"

    async def action(self, action: str, params: dict | None = None) -> dict:
        params = params or {}
        client = await self._client()
        async with client:
            if action == "get_profile":
                resp = await client.get(f"{_API}/v2/profile", headers=self._headers())
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                return {"ok": True, "action": action, "profile": resp.json()}
            if action == "send_message":
                text = params.get("text") or params.get("message")
                to = params.get("to") or self.config.get("user_id")
                if not text or not to:
                    return {"ok": False, "error": "send_message needs text and a target user_id"}
                resp = await client.post(
                    f"{_API}/v2/bot/message/push",
                    headers=self._headers(),
                    json={"to": to, "messages": [{"type": "text", "text": text}]},
                )
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                return {"ok": True, "action": action, "sent": True}
        return {"ok": False, "error": f"Unknown line action: {action}"}
