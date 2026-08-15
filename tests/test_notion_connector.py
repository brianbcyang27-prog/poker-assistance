"""Tests for the Notion connector."""

import json

import httpx

from jarvis.integrations.connectors.notion import NotionConnector


def _make_connector(handler, token="secret_test"):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = NotionConnector(http_client=client)
    connector.config = {"api_token": token}
    return connector


async def test_test_ok():
    def handler(request):
        assert request.headers["notion-version"] == "2022-06-28"
        assert request.headers["authorization"] == "Bearer secret_test"
        return httpx.Response(200, json={"bot": {"owner": {"workspace_name": "Acme"}}})

    connector = _make_connector(handler)
    ok, detail = await connector.test()
    assert ok is True
    assert "Acme" in detail


async def test_test_unauthorized():
    connector = _make_connector(lambda request: httpx.Response(401, json={}))
    ok, detail = await connector.test()
    assert ok is False
    assert "Invalid token" in detail


async def test_search_action():
    def handler(request):
        assert request.method == "POST"
        body = json.loads(request.content)
        assert body["query"] == "roadmap"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "page-1",
                        "properties": {
                            "title": {"type": "title", "title": [{"plain_text": "Q3 Roadmap"}]}
                        },
                    }
                ]
            },
        )

    connector = _make_connector(handler)
    result = await connector.action("search", {"query": "roadmap"})
    assert result["ok"] is True
    assert result["results"][0]["title"] == "Q3 Roadmap"


async def test_user_info_action():
    connector = _make_connector(
        lambda request: httpx.Response(200, json={"bot": {"name": "JARVIS"}})
    )
    result = await connector.action("user_info", {})
    assert result["ok"] is True
    assert result["bot"]["name"] == "JARVIS"


async def test_unknown_action():
    connector = _make_connector(lambda request: httpx.Response(200, json={}))
    result = await connector.action("nope", {})
    assert result["ok"] is False
    assert "Unknown notion action" in result["error"]


def test_extract_title_missing_title_prop():
    page = {"id": "x", "properties": {"text": {"type": "rich_text"}}}
    assert NotionConnector._extract_title(page) == "x"
