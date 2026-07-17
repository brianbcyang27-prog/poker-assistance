"""Web search via DuckDuckGo or Google."""
import asyncio
import json
import urllib.parse
from typing import Optional

import aiohttp


class WebSearch:
    """Performs web searches and returns results."""

    async def search_duckduckgo(self, query: str, max_results: int = 8) -> dict:
        """Search DuckDuckGo (no API key needed)."""
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    html = await resp.text()

            results = []
            import re
            # Parse HTML results
            blocks = re.findall(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</span>', html, re.DOTALL)
            for href, title, snippet in blocks[:max_results]:
                title = re.sub(r'<[^>]+>', '', title).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                # DuckDuckGo wraps URLs in a redirect
                if "uddg=" in href:
                    href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                results.append({"title": title, "url": href, "snippet": snippet})

            return {"ok": True, "results": results, "query": query}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def search(self, query: str, engine: str = "duckduckgo", max_results: int = 8) -> dict:
        """Unified search interface."""
        if engine == "duckduckgo":
            return await self.search_duckduckgo(query, max_results)
        return {"ok": False, "error": f"Unknown engine: {engine}"}

    async def fetch_page(self, url: str, max_chars: int = 8000) -> dict:
        """Fetch and extract text content from a URL."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status != 200:
                        return {"ok": False, "error": f"HTTP {resp.status}"}
                    html = await resp.text()

            # Simple HTML to text extraction
            import re
            # Remove scripts and styles
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            # Collapse whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            # Decode entities
            text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')

            return {"ok": True, "text": text[:max_chars], "url": url, "length": len(text)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


web_search = WebSearch()
