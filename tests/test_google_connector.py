"""Tests for the Google connector."""

import httpx

from jarvis.integrations.connectors.google import GoogleConnector

GOOD_CREDS = {
    "client_id": "cid",
    "client_secret": "csec",
    "refresh_token": "rtok",
}


def _make_connector(handler, creds=None):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = GoogleConnector(http_client=client)
    connector.config = dict(creds or GOOD_CREDS)
    return connector


async def test_test_ok():
    def handler(request):
        if request.url.path == "/token":
            assert "grant_type=refresh_token" in request.content.decode()
            return httpx.Response(200, json={"access_token": "atok", "expires_in": 3600})
        if request.url.path == "/oauth2/v3/userinfo":
            return httpx.Response(200, json={"name": "Ada", "email": "ada@example.com"})
        return httpx.Response(404, json={})

    connector = _make_connector(handler)
    ok, detail = await connector.test()
    assert ok is True
    assert "Ada" in detail


async def test_test_token_exchange_failure():
    def handler(request):
        return httpx.Response(400, json={"error": "invalid_grant"})

    connector = _make_connector(handler)
    ok, detail = await connector.test()
    assert ok is False
    assert "refresh token" in detail


async def test_calendar_upcoming_action():
    def handler(request):
        if request.url.path == "/token":
            return httpx.Response(200, json={"access_token": "atok", "expires_in": 3600})
        if "calendar" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"summary": "Standup", "start": {"dateTime": "2026-08-10T09:00:00Z"}}
                    ]
                },
            )
        return httpx.Response(404, json={})

    connector = _make_connector(handler)
    result = await connector.action("calendar_upcoming", {"limit": 5})
    assert result["ok"] is True
    assert result["events"][0]["summary"] == "Standup"


async def test_gmail_unread_action():
    def handler(request):
        if request.url.path == "/token":
            return httpx.Response(200, json={"access_token": "atok", "expires_in": 3600})
        if "gmail.googleapis.com" in request.url.host:
            assert "is%3Aunread" in str(request.url)
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        return httpx.Response(404, json={})

    connector = _make_connector(handler)
    result = await connector.action("gmail_unread", {"limit": 5})
    assert result["ok"] is True
    assert result["messages"] == [{"id": "m1"}]


async def test_action_without_creds():
    connector = _make_connector(lambda request: httpx.Response(400, json={}), creds={})
    result = await connector.action("user_info", {})
    assert result["ok"] is False


async def test_unknown_action():
    connector = _make_connector(lambda request: httpx.Response(200, json={}))
    result = await connector.action("nope", {})
    assert result["ok"] is False
    assert "Unknown google action" in result["error"]
