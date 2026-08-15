"""Tests for the GitHub connector."""

import httpx

from jarvis.integrations.connectors.github import GitHubConnector


def _make_connector(handler, token="ghp_test"):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = GitHubConnector(http_client=client)
    connector.config = {"token": token}
    return connector


async def test_test_ok():
    def handler(request):
        assert request.headers["authorization"] == "Bearer ghp_test"
        return httpx.Response(200, json={"login": "octocat", "name": "Mona"})

    connector = _make_connector(handler)
    ok, detail = await connector.test()
    assert ok is True
    assert "octocat" in detail


async def test_test_unauthorized():
    connector = _make_connector(lambda request: httpx.Response(401, json={}))
    ok, detail = await connector.test()
    assert ok is False
    assert "Invalid token" in detail


async def test_user_info_action():
    def handler(request):
        return httpx.Response(200, json={"login": "octocat", "public_repos": 8, "followers": 12})

    connector = _make_connector(handler)
    result = await connector.action("user_info", {})
    assert result["ok"] is True
    assert result["user"]["login"] == "octocat"
    assert result["user"]["public_repos"] == 8


async def test_list_repos_action():
    def handler(request):
        assert "sort=updated" in str(request.url)
        return httpx.Response(
            200,
            json=[{"name": "hello-world", "language": "Python", "description": None}],
        )

    connector = _make_connector(handler)
    result = await connector.action("list_repos", {"limit": 5})
    assert result["ok"] is True
    assert result["repos"][0]["name"] == "hello-world"


async def test_action_error():
    connector = _make_connector(lambda request: httpx.Response(403, text="rate limited"))
    result = await connector.action("user_info", {})
    assert result["ok"] is False
    assert "rate limited" in result["error"]


async def test_unknown_action():
    connector = _make_connector(lambda request: httpx.Response(200, json={}))
    result = await connector.action("nope", {})
    assert result["ok"] is False
    assert "Unknown github action" in result["error"]
