"""JARVIS Research Engine — Automated research and tool discovery.

Searches across:
  - GitHub repositories
  - PyPI packages
  - npm packages
  - Official documentation
  - Stack Overflow
  - Awesome Lists
  - HuggingFace
  - Docker Hub

Produces structured ResearchFindings for the mission pipeline.
"""

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from ..mission.mission import ResearchFinding, ToolCandidate

log = logging.getLogger("jarvis.research")


class ResearchEngine:
    """Automated research engine — searches the web for existing solutions.

    Priority order:
      1. Official documentation
      2. GitHub repositories
      3. Academic papers
      4. Well-maintained open source
      5. Forums/Reddit (supplementary only)
    """

    def __init__(self):
        self._search_providers = []
        self._cache: Dict[str, List[ResearchFinding]] = {}

    async def search(
        self,
        query: str,
        source: str = "github",
        limit: int = 10,
    ) -> List[ResearchFinding]:
        """Search a specific source for relevant findings.

        Args:
            query: Search query
            source: Source to search (github, pypi, npm, docs, etc.)
            limit: Max results

        Returns:
            List of ResearchFinding sorted by relevance
        """
        cache_key = f"{source}:{query}"
        if cache_key in self._cache:
            return self._cache[cache_key][:limit]

        findings = []

        try:
            if source == "github":
                findings = await self._search_github(query, limit)
            elif source == "pypi":
                findings = await self._search_pypi(query, limit)
            elif source == "npm":
                findings = await self._search_npm(query, limit)
            elif source == "docs":
                findings = await self._search_docs(query, limit)
            elif source == "stackoverflow":
                findings = await self._search_stackoverflow(query, limit)
            elif source == "awesome_lists":
                findings = await self._search_awesome(query, limit)
            elif source == "huggingface":
                findings = await self._search_huggingface(query, limit)
            elif source == "docker":
                findings = await self._search_docker(query, limit)
        except Exception as e:
            log.debug(f"Search {source} failed: {e}")

        self._cache[cache_key] = findings
        return findings[:limit]

    async def understand_goal(self, user_request: str) -> Dict[str, Any]:
        """Parse user request into structured goal.

        Returns:
            Dict with goal, constraints, keywords, domain
        """
        # Basic parsing — in production, use LLM
        keywords = user_request.lower().split()
        return {
            "goal": user_request,
            "keywords": keywords,
            "domain": self._detect_domain(user_request),
            "constraints": [],
        }

    def _detect_domain(self, request: str) -> str:
        """Detect the domain from a request."""
        request_lower = request.lower()
        if any(w in request_lower for w in ["web", "frontend", "ui", "react", "vue"]):
            return "web"
        if any(w in request_lower for w in ["api", "backend", "server", "fastapi", "flask"]):
            return "backend"
        if any(w in request_lower for w in ["ml", "ai", "model", "train", "neural"]):
            return "ml"
        if any(w in request_lower for w in ["cad", "pcb", "firmware", "embedded", "iot"]):
            return "hardware"
        if any(w in request_lower for w in ["test", "qa", "ci", "deploy"]):
            return "devops"
        return "general"

    # ── Source Implementations ─────────────────────────────

    async def _search_github(self, query: str, limit: int) -> List[ResearchFinding]:
        """Search GitHub for relevant repositories."""
        import subprocess
        try:
            # Use gh CLI if available
            proc = await asyncio.create_subprocess_exec(
                "gh", "search", "repos", query,
                "--limit", str(limit),
                "--json", "name,description,url,stargazersCount,language,updatedAt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return []

            results = json.loads(stdout.decode("utf-8", errors="replace"))
            findings = []

            for repo in results:
                findings.append(ResearchFinding(
                    source="github",
                    title=repo.get("name", ""),
                    url=repo.get("url", ""),
                    description=repo.get("description", "") or "",
                    relevance=min(repo.get("stargazersCount", 0) / 10000, 1.0),
                    stars=repo.get("stargazersCount", 0),
                    language=repo.get("language", ""),
                ))

            return findings

        except Exception as e:
            log.debug(f"GitHub search failed: {e}")
            return []

    async def _search_pypi(self, query: str, limit: int) -> List[ResearchFinding]:
        """Search PyPI for relevant packages."""
        import subprocess
        try:
            proc = await asyncio.create_subprocess_exec(
                "pip3", "index", "versions", query,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            # Basic result — in production, use PyPI JSON API
            if proc.returncode == 0:
                return [ResearchFinding(
                    source="pypi",
                    title=query,
                    url=f"https://pypi.org/project/{query}/",
                    description=f"PyPI package: {query}",
                    relevance=0.5,
                    is_official=False,
                )]
            return []

        except Exception:
            return []

    async def _search_npm(self, query: str, limit: int) -> List[ResearchFinding]:
        """Search npm for relevant packages."""
        # Placeholder — use npm registry API in production
        return []

    async def _search_docs(self, query: str, limit: int) -> List[ResearchFinding]:
        """Search official documentation."""
        # Placeholder — use web search in production
        return []

    async def _search_stackoverflow(self, query: str, limit: int) -> List[ResearchFinding]:
        """Search Stack Overflow."""
        # Placeholder — use StackExchange API in production
        return []

    async def _search_awesome(self, query: str, limit: int) -> List[ResearchFinding]:
        """Search awesome lists on GitHub."""
        return await self._search_github(f"awesome {query}", limit)

    async def _search_huggingface(self, query: str, limit: int) -> List[ResearchFinding]:
        """Search HuggingFace for models/datasets."""
        return []

    async def _search_docker(self, query: str, limit: int) -> List[ResearchFinding]:
        """Search Docker Hub."""
        return []


class DiscoveryEngine:
    """Tool and library discovery engine.

    Discovers existing tools that solve 80%+ of the problem.
    Prefer mature tools over custom implementations.
    """

    # Known good tools for common tasks
    KNOWN_TOOLS = {
        "browser": {"name": "playwright", "source": "pypi", "maturity": "mature"},
        "ocr": {"name": "tesseract", "source": "system", "maturity": "mature"},
        "vector_db": {"name": "chromadb", "source": "pypi", "maturity": "stable"},
        "speech": {"name": "kokoro", "source": "pypi", "maturity": "stable"},
        "embeddings": {"name": "sentence-transformers", "source": "pypi", "maturity": "mature"},
        "linting": {"name": "ruff", "source": "pypi", "maturity": "mature"},
        "testing": {"name": "pytest", "source": "pypi", "maturity": "mature"},
        "diagrams": {"name": "mermaid", "source": "npm", "maturity": "mature"},
        "docker": {"name": "docker", "source": "pypi", "maturity": "mature"},
        "git": {"name": "gitpython", "source": "pypi", "maturity": "mature"},
        "database": {"name": "alembic", "source": "pypi", "maturity": "mature"},
        "cad": {"name": "freecad", "source": "system", "maturity": "mature"},
        "pcb": {"name": "kicad", "source": "system", "maturity": "mature"},
        "image_segmentation": {"name": "segment-anything", "source": "pypi", "maturity": "stable"},
        "code_format": {"name": "ruff", "source": "pypi", "maturity": "mature"},
        "web_scraping": {"name": "beautifulsoup4", "source": "pypi", "maturity": "mature"},
        "http_client": {"name": "httpx", "source": "pypi", "maturity": "mature"},
        "async": {"name": "asyncio", "source": "stdlib", "maturity": "mature"},
        "cli": {"name": "click", "source": "pypi", "maturity": "mature"},
        "config": {"name": "pydantic-settings", "source": "pypi", "maturity": "mature"},
    }

    def __init__(self):
        self._discovered: Dict[str, ToolCandidate] = {}

    async def discover(
        self,
        query: str,
        findings: Optional[List[ResearchFinding]] = None,
    ) -> List[ToolCandidate]:
        """Discover tools for the given query.

        Args:
            query: What we need to solve
            findings: Research findings to inform discovery

        Returns:
            List of ToolCandidate sorted by score
        """
        candidates = []

        # Check known tools first
        query_lower = query.lower()
        for category, tool_info in self.KNOWN_TOOLS.items():
            if category in query_lower or any(kw in query_lower for kw in category.split("_")):
                candidates.append(ToolCandidate(
                    name=tool_info["name"],
                    source=tool_info["source"],
                    description=f"Known tool for {category}",
                    maturity=tool_info["maturity"],
                    score=0.9 if tool_info["maturity"] == "mature" else 0.7,
                ))

        # Add tools from research findings
        if findings:
            for finding in findings[:5]:
                candidates.append(ToolCandidate(
                    name=finding.title,
                    source=finding.source,
                    description=finding.description,
                    maturity="unknown",
                    stars=finding.stars,
                    score=finding.relevance * 0.8,
                ))

        # Deduplicate and sort
        seen = set()
        unique = []
        for c in candidates:
            if c.name not in seen:
                seen.add(c.name)
                unique.append(c)

        unique.sort(key=lambda x: x.score, reverse=True)
        self._discovered = {c.name: c for c in unique}
        return unique

    def get_tool(self, name: str) -> Optional[ToolCandidate]:
        """Get a discovered tool by name."""
        return self._discovered.get(name)

    def select_best(self, category: str) -> Optional[ToolCandidate]:
        """Select the best tool for a category."""
        for tool in self._discovered.values():
            if category.lower() in tool.description.lower():
                return tool
        return None
