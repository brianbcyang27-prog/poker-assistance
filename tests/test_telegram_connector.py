"""Tests for the Telegram connector."""

import httpx

from jarvis.integrations.connectors.telegram import TelegramConnector


def _make_connector(handler, token="123:abc"):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = TelegramConnector(http_client=client)
    connector.config = {"bot_token": token}
    return connector


async def test_test_ok():
    def handler(request):
        assert request.url.path == "/bot123:abc/getMe"
        return httpx.Response(200, json={"ok": True, "result": {"username": "my_test_bot"}})

    connector = _make_connector(handler)
    ok, detail = await connector.test()
    assert ok is True
    assert "@my_test_bot" in detail


async def test_test_invalid_token():
    def handler(request):
        return httpx.Response(200, json={"ok": False, "description": "Unauthorized"})

    connector = _make_connector(handler)
    ok, detail = await connector.test()
    assert ok is False
    assert "Invalid bot token" in detail


async def test_test_http_error():
    def handler(request):
        return httpx.Response(500, text="boom")

    connector = _make_connector(handler)
    ok, detail = await connector.test()
    assert ok is False
    assert "500" in detail


async def test_send_message():
    def handler(request):
        assert request.url.path == "/bot123:abc/sendMessage"
        assert request.method == "POST"
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    connector = _make_connector(handler)
    result = await connector.action("send_message", {"chat_id": 999, "text": "hello"})
    assert result["ok"] is True
    assert result["message_id"] == 42


async def test_send_message_missing_params():
    connector = _make_connector(lambda request: httpx.Response(200, json={}))
    result = await connector.action("send_message", {})
    assert result["ok"] is False
    assert "chat_id and text" in result["error"]


async def test_get_profile():
    def handler(request):
        return httpx.Response(200, json={"ok": True, "result": {"id": 1, "username": "bot"}})

    connector = _make_connector(handler)
    result = await connector.action("get_profile", {})
    assert result["ok"] is True
    assert result["bot"]["username"] == "bot"


async def test_unknown_action():
    connector = _make_connector(lambda request: httpx.Response(200, json={}))
    result = await connector.action("nope", {})
    assert result["ok"] is False
    assert "Unknown telegram action" in result["error"]
