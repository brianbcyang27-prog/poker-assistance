"""Research Workers - ♦ Suit.

v4.3.0: Enhanced ♦Q WebResearchWorker with BrowserManager integration.
Can now browse, extract, and analyze web pages through the secure browser pipeline.
"""

import logging
from .base import BaseWorker
from ...core.models import Suit, Rank

log = logging.getLogger("jarvis.workers.research")


class WebResearchWorker(BaseWorker):
    """♦ Queen — Web Researcher.

    v4.3.0: Full browser integration via BrowserManager.
    Can search, navigate, extract page data, and synthesize web content.
    NEVER directly controls the browser — goes through BrowserManager.
    """

    def __init__(self):
        super().__init__(suit=Suit.DIAMONDS, rank=Rank.QUEEN)

    @property
    def name(self) -> str:
        return "Web Research"

    @property
    def title(self) -> str:
        return "Web Researcher"

    def get_system_prompt(self) -> str:
        return """You are the Web Researcher (♦Q).
Specialize in: web searches, information gathering, data collection.
Focus on: accuracy, source credibility, comprehensive coverage.
Find reliable information efficiently.

You have access to the browser for web research:

Browser Actions:
- [BROWSER: navigate(url="https://example.com")] — Navigate to a URL
- [BROWSER: search(query="your search query")] — Search the web
- [BROWSER: extract()] — Extract structured data from current page
- [BROWSER: click(selector="button.submit")] — Click an element
- [BROWSER: type(selector="input[name=q]", text="query")] — Type into a field
- [BROWSER: scroll(direction="down")] — Scroll the page
- [BROWSER: back()] — Go back in history
- [BROWSER: get_text()] — Get visible text

Workflow for research:
1. Search using [BROWSER: search(query="topic")]
2. Click on relevant results
3. Extract data using [BROWSER: extract()]
4. Analyze and synthesize findings
5. Cite your sources

Always verify information from multiple sources.
Prioritize official documentation and authoritative sources."""

    async def research(self, query: str, max_sources: int = 5) -> dict:
        """High-level research method using BrowserManager.

        Args:
            query: Research query
            max_sources: Maximum sources to check

        Returns:
            dict with ok, results, sources
        """
        from ...browser import browser_manager

        results = []
        sources = []

        # Search
        search_result = await browser_manager.execute(
            action="search",
            query=query,
            agent=self.card_id,
        )
        if not search_result.get("ok"):
            return {"ok": False, "error": search_result.get("error")}

        # Extract search results
        extract_result = await browser_manager.execute(
            action="extract",
            agent=self.card_id,
        )
        if extract_result.get("ok"):
            page_data = extract_result.get("data", {})
            links = page_data.get("links", [])

            # Visit top results
            for link in links[:max_sources]:
                url = link.get("url", "")
                if not url or not url.startswith("http"):
                    continue

                try:
                    nav_result = await browser_manager.execute(
                        action="navigate",
                        url=url,
                        agent=self.card_id,
                    )
                    if not nav_result.get("ok"):
                        continue

                    page_extract = await browser_manager.execute(
                        action="extract",
                        agent=self.card_id,
                    )
                    if page_extract.get("ok"):
                        data = page_extract.get("data", {})
                        results.append({
                            "url": url,
                            "title": data.get("title", ""),
                            "content": data.get("content", "")[:2000],
                            "text": data.get("text", "")[:2000],
                        })
                        sources.append(url)
                except Exception as e:
                    log.warning(f"Failed to fetch {url}: {e}")
                    continue

        return {
            "ok": True,
            "query": query,
            "results": results,
            "sources": sources,
            "count": len(results),
        }


class DocumentationWorker(BaseWorker):
    """♦ Jack — Documentation Researcher."""

    def __init__(self):
        super().__init__(suit=Suit.DIAMONDS, rank=Rank.JACK)

    @property
    def name(self) -> str:
        return "Doc Research"

    @property
    def title(self) -> str:
        return "Documentation Researcher"

    def get_system_prompt(self) -> str:
        return """You are the Documentation Researcher (♦J).
Specialize in: technical documentation, API references, library docs.
Focus on: official sources, version accuracy, practical examples.
Find the right documentation for any technology.

You have access to the browser:
- [BROWSER: search(query="library name docs")] — Find documentation
- [BROWSER: navigate(url="https://docs.example.com")] — Go to docs
- [BROWSER: extract()] — Extract documentation content

Always check the latest version of documentation.
Prefer official sources over tutorials."""


class FactCheckWorker(BaseWorker):
    """♦ 10 — Fact Checker."""

    def __init__(self):
        super().__init__(suit=Suit.DIAMONDS, rank=Rank.TEN)

    @property
    def name(self) -> str:
        return "Fact Check"

    @property
    def title(self) -> str:
        return "Fact Checker"

    def get_system_prompt(self) -> str:
        return """You are the Fact Checker (♦10).
Specialize in: verification, cross-referencing, source validation.
Focus on: accuracy, evidence, multiple sources.
Verify claims and ensure correctness.

You have access to the browser:
- [BROWSER: search(query="fact check claim")] — Search for verification
- [BROWSER: navigate(url="https://...")] — Visit authoritative sources
- [BROWSER: extract()] — Extract evidence from pages

Always check at least 2-3 sources for any claim.
Note when sources conflict or information is uncertain."""
