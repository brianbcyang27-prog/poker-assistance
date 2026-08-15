"""GitHub connector — REST API via httpx."""

from __future__ import annotations

import httpx

from jarvis.integrations.base import ConfigField, Connector, ConnectorCategory

_API = "https://api.github.com"


class GitHubConnector(Connector):
    id = "github"
    name = "GitHub"
    category = ConnectorCategory.DEV
    description = "Read your profile, starred repos, and recent activity."
    capabilities = ["user_info", "list_repos"]
    config_fields = [
        ConfigField(
            key="token",
            label="Personal Access Token",
            type="password",
            required=True,
            secret=True,
            placeholder="ghp_...",
            help="Settings → Developer settings → Personal access tokens → Fine-grained. "
            "Repo read scope is enough.",
        )
    ]
    requires_config = True
    needs_setup_guide = True
    setup_guide = (
        "1. Open github.com → Settings → Developer settings → Personal access tokens.\n"
        "2. Generate a fine-grained token with 'Contents: Read-only'.\n"
        "3. Paste the token above and hit Test."
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
            "Authorization": f"Bearer {self.config.get('token', '')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def test(self) -> tuple[bool, str]:
        client = await self._client()
        async with client:
            resp = await client.get(f"{_API}/user", headers=self._headers())
            if resp.status_code == 401:
                return False, "Invalid token — check permissions"
            if resp.status_code != 200:
                return False, f"GitHub API error {resp.status_code}"
            user = resp.json()
            return True, f"Connected as {user.get('login')} ({user.get('name') or 'no name'})"

    async def action(self, action: str, params: dict | None = None) -> dict:
        params = params or {}
        client = await self._client()
        async with client:
            if action == "user_info":
                resp = await client.get(f"{_API}/user", headers=self._headers())
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                user = resp.json()
                return {
                    "ok": True,
                    "action": action,
                    "user": {
                        "login": user.get("login"),
                        "name": user.get("name"),
                        "public_repos": user.get("public_repos"),
                        "followers": user.get("followers"),
                        "bio": user.get("bio"),
                    },
                }
            if action == "list_repos":
                per_page = min(int(params.get("limit", 10)), 100)
                resp = await client.get(
                    f"{_API}/user/repos",
                    params={"sort": "updated", "per_page": per_page},
                    headers=self._headers(),
                )
                if resp.status_code != 200:
                    return {"ok": False, "error": resp.text[:300]}
                repos = [
                    {
                        "name": r.get("name"),
                        "language": r.get("language"),
                        "description": r.get("description"),
                    }
                    for r in resp.json()
                ]
                return {"ok": True, "action": action, "repos": repos}
        return {"ok": False, "error": f"Unknown github action: {action}"}
