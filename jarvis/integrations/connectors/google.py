"""Google connector — OAuth refresh-token flow via httpx."""

from __future__ import annotations

import time

import httpx

from jarvis.integrations.base import ConfigField, Connector, ConnectorCategory

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
_GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


class GoogleConnector(Connector):
    id = "google"
    name = "Google"
    category = ConnectorCategory.PRODUCTIVITY
    description = "Calendar, Gmail, and profile info through OAuth refresh tokens."
    capabilities = ["user_info", "calendar_upcoming", "gmail_unread", "gmail_unread_with_meta"]
    config_fields = [
        ConfigField(
            key="client_id",
            label="Client ID",
            type="text",
            required=True,
            placeholder="xxxx.apps.googleusercontent.com",
            help="From Google Cloud Console → OAuth 2.0 Client IDs.",
        ),
        ConfigField(
            key="client_secret",
            label="Client Secret",
            type="password",
            required=True,
            secret=True,
            placeholder="GOCSPX-...",
            help="Same client, Secrets tab.",
        ),
        ConfigField(
            key="refresh_token",
            label="Refresh Token",
            type="password",
            required=True,
            secret=True,
            placeholder="1//0xxxx...",
            help="Obtained via the OAuth authorization code flow.",
        ),
    ]
    requires_config = True
    needs_setup_guide = True
    setup_guide = (
        "1. Google Cloud Console → enable the Calendar and Gmail APIs.\n"
        "2. Create an OAuth 2.0 Client ID (Web application).\n"
        "3. Generate a refresh token with scopes: "
        "https://www.googleapis.com/auth/calendar.readonly and gmail.readonly.\n"
        "4. Paste client_id, client_secret, and refresh_token above."
    )

    def __init__(self, registry=None, http_client: httpx.AsyncClient | None = None):
        super().__init__(registry)
        self._http = http_client
        self._access_token: str | None = None
        self._token_expires: float = 0.0

    async def _client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return self._http
        return httpx.AsyncClient(timeout=10.0)

    async def _get_access_token(self, client: httpx.AsyncClient) -> str | None:
        now = time.time()
        if self._access_token and self._token_expires > now + 60:
            return self._access_token
        resp = await client.post(
            _TOKEN_URL,
            data={
                "client_id": self.config.get("client_id", ""),
                "client_secret": self.config.get("client_secret", ""),
                "refresh_token": self.config.get("refresh_token", ""),
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        self._access_token = data.get("access_token")
        self._token_expires = now + int(data.get("expires_in", 3600))
        return self._access_token

    async def test(self) -> tuple[bool, str]:
        client = await self._client()
        async with client:
            token = await self._get_access_token(client)
            if not token:
                return False, "Failed to exchange refresh token — check credentials"
            resp = await client.get(_USERINFO_URL, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code != 200:
                return False, f"Google API error {resp.status_code}"
            user = resp.json()
            return True, f"Connected as {user.get('name') or user.get('email')}"

    async def action(self, action: str, params: dict | None = None) -> dict:
        params = params or {}
        if action not in {
            "user_info",
            "calendar_upcoming",
            "gmail_unread",
            "gmail_unread_with_meta",
        }:
            return {"ok": False, "error": f"Unknown google action: {action}"}
        client = await self._client()
        async with client:
            token = await self._get_access_token(client)
            if not token:
                return {
                    "ok": False,
                    "error": "Failed to exchange refresh token — check credentials",
                }
            headers = {"Authorization": f"Bearer {token}"}
            if action == "user_info":
                resp = await client.get(_USERINFO_URL, headers=headers)
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                return {"ok": True, "action": action, "user": resp.json()}
            if action == "calendar_upcoming":
                resp = await client.get(
                    _CALENDAR_URL,
                    params={
                        "maxResults": min(int(params.get("limit", 5)), 50),
                        "orderBy": "startTime",
                        "singleEvents": "true",
                    },
                    headers=headers,
                )
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                items = resp.json().get("items", [])
                events = [
                    {
                        "summary": e.get("summary"),
                        "start": (e.get("start") or {}).get("dateTime")
                        or (e.get("start") or {}).get("date"),
                    }
                    for e in items
                ]
                return {"ok": True, "action": action, "events": events}
            if action == "gmail_unread":
                resp = await client.get(
                    _GMAIL_URL,
                    params={
                        "q": "in:inbox is:unread",
                        "maxResults": min(int(params.get("limit", 5)), 50),
                    },
                    headers=headers,
                )
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                return {"ok": True, "action": action, "messages": resp.json().get("messages", [])}
            if action == "gmail_unread_with_meta":
                resp = await client.get(
                    _GMAIL_URL,
                    params={
                        "q": "in:inbox is:unread",
                        "maxResults": min(int(params.get("limit", 5)), 50),
                    },
                    headers=headers,
                )
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                ids = [m.get("id") for m in resp.json().get("messages", []) if m.get("id")]
                messages = []
                for msg_id in ids:
                    meta = await client.get(
                        _GMAIL_URL + "/" + msg_id,
                        params={"format": "metadata", "metadataHeaders": "Subject,From"},
                        headers=headers,
                    )
                    if meta.status_code != 200:
                        continue
                    payload = meta.json().get("payload", {})
                    header_map = {
                        h.get("name", "").lower(): h.get("value", "")
                        for h in payload.get("headers", [])
                    }
                    messages.append(
                        {
                            "id": msg_id,
                            "subject": header_map.get("subject", "(no subject)"),
                            "from": header_map.get("from", ""),
                        }
                    )
                return {"ok": True, "action": action, "messages": messages}
