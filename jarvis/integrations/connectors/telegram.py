"""Telegram connector — Bot API via httpx."""

from __future__ import annotations

import httpx

from jarvis.integrations.base import ConfigField, Connector, ConnectorCategory

_API = "https://api.telegram.org"


class TelegramConnector(Connector):
    id = "telegram"
    name = "Telegram"
    category = ConnectorCategory.MESSAGING
    description = "Send messages and notifications through your own Telegram bot."
    capabilities = ["send_message", "get_profile"]
    config_fields = [
        ConfigField(
            key="bot_token",
            label="Bot Token",
            type="password",
            required=True,
            secret=True,
            placeholder="123456789:AAH...",
            help="From @BotFather → /newbot. Keep it secret.",
        ),
        ConfigField(
            key="chat_id",
            label="Chat ID",
            type="text",
            required=False,
            secret=False,
            placeholder="e.g. 123456789",
            help="Your numeric chat id (message @userinfobot to find it). "
            "Used by World Monitor alerts.",
        ),
    ]
    requires_config = True
    needs_setup_guide = True
    setup_guide = (
        "1. Open Telegram and message @BotFather.\n"
        "2. Send /newbot, pick a name and username.\n"
        "3. Copy the token BotFather replies with and paste it above.\n"
        "4. Send any message to your bot, then hit Test."
    )

    def __init__(self, registry=None, http_client: httpx.AsyncClient | None = None):
        super().__init__(registry)
        self._http = http_client

    async def _client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return self._http
        return httpx.AsyncClient(timeout=10.0)

    def _url(self, method: str) -> str:
        return f"{_API}/bot{self.config.get('bot_token', '')}/{method}"

    async def test(self) -> tuple[bool, str]:
        client = await self._client()
        async with client:
            resp = await client.get(self._url("getMe"))
            if resp.status_code != 200:
                return False, f"Telegram API error {resp.status_code}: {resp.text[:200]}"
            data = resp.json()
            if not data.get("ok"):
                return False, f"Invalid bot token: {data.get('description', 'unknown error')}"
            user = data.get("result", {})
            username = user.get("username", "your bot")
            return True, f"Connected as @{username}"

    async def action(self, action: str, params: dict | None = None) -> dict:
        params = params or {}
        client = await self._client()
        async with client:
            if action == "send_message":
                chat_id = params.get("chat_id") or params.get("to")
                text = params.get("text") or params.get("message")
                if not chat_id or not text:
                    return {"ok": False, "error": "send_message needs chat_id and text"}
                resp = await client.post(
                    self._url("sendMessage"),
                    json={"chat_id": chat_id, "text": text},
                )
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                message_id = resp.json().get("result", {}).get("message_id")
                return {"ok": True, "action": action, "message_id": message_id}
            if action == "get_profile":
                resp = await client.get(self._url("getMe"))
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                return {"ok": True, "action": action, "bot": resp.json().get("result", {})}
        return {"ok": False, "error": f"Unknown telegram action: {action}"}
