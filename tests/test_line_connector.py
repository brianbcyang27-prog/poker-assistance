"""Tests for the LINE connector."""

import json

import httpx

from jarvis.integrations.connectors.line import LineConnector


def _make_connector(handler, token="tok123", user_id="U123"):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = LineConnector(http_client=client)
    connector.config = {"access_token": token, "user_id": user_id}
    return connector


async def test_test_ok():
    def handler(request):
        assert request.headers["authorization"] == "Bearer tok123"
        return httpx.Response(200, json={"displayName": "Brian"})

    connector = _make_connector(handler)
    ok, detail = await connector.test()
    assert ok is True
    assert "Brian" in detail


async def test_test_unauthorized():
    connector = _make_connector(lambda request: httpx.Response(401, json={}))
    ok, detail = await connector.test()
    assert ok is False
    assert "Invalid channel access token" in detail


async def test_get_profile_action():
    connector = _make_connector(
        lambda request: httpx.Response(200, json={"displayName": "Brian", "userId": "U123"})
    )
    result = await connector.action("get_profile", {})
    assert result["ok"] is True
    assert result["profile"]["displayName"] == "Brian"


async def test_send_message_action():
    def handler(request):
        assert request.url.path == "/v2/bot/message/push"
        body = json.loads(request.content)
        assert body["to"] == "U123"
        assert body["messages"][0]["text"] == "hello"
        return httpx.Response(200, json={"sentMessages": [{"id": "1"}]})

    connector = _make_connector(handler)
    result = await connector.action("send_message", {"text": "hello"})
    assert result["ok"] is True
    assert result["sent"] is True


async def test_send_message_missing_target():
    connector = _make_connector(lambda request: httpx.Response(200, json={}), user_id="")
    result = await connector.action("send_message", {"text": "hello"})
    assert result["ok"] is False
    assert "needs text and a target" in result["error"]


async def test_unknown_action():
    connector = _make_connector(lambda request: httpx.Response(200, json={}))
    result = await connector.action("nope", {})
    assert result["ok"] is False
    assert "Unknown line action" in result["error"]
