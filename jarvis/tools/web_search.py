"""V10 Web Search — provider ABC, DDG adapter, prompt-injection sanitizer (PHASE G).

Implements architecture checklist item 6:

* ``WebSearchProvider`` — abstract contract every search provider implements.
* ``DuckDuckGoProvider`` — adapts the existing v6.3.0 ``WebSearch`` client
  (:mod:`jarvis.computer.search`) as the first provider, without modifying it.
* ``sanitize_fetched_text`` — prompt-injection sanitization. **Every**
  ``fetch_page`` result passes through this before it can reach the LLM, so
  hostile page content (instruction overrides, hidden text, LLM control-token
  smuggling) is neutralized and delimited as untrusted data.
* ``WebSearchTool`` / ``FetchPageTool`` — V10 executables registered on the
  shared ``tool_registry`` so the executor (PHASE E) can dispatch them.

Result contract: tools return the canonical :class:`jarvis.tools.result.ToolResult`
— no new result types. Failure modes use the stable ``ToolError`` codes
(``timeout``, ``execution_error``, ``invalid_params``).
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Any

from jarvis.computer.search import WebSearch, web_search
from jarvis.core.reliability import config as reliability_config
from jarvis.tools.base import (
    ParamSpec,
    Tool,
    ToolError,
    ToolResult,
    ToolSpec,
)
from jarvis.tools.registry import tool_registry

__all__ = [
    "sanitize_fetched_text",
    "WebSearchProvider",
    "DuckDuckGoProvider",
    "WebSearchTool",
    "FetchPageTool",
    "duckduckgo_provider",
    "web_search_tool",
    "fetch_page_tool",
]

# ──────────────────────────────────────────────────────────────────────────────
# Prompt-injection sanitization
# ──────────────────────────────────────────────────────────────────────────────

#: Invisible / zero-width code points that attackers use to hide instructions
#: from human eyes while the LLM still sees them.
_INVISIBLE_CHARS = "".join(
    [
        "\u200b",  # zero-width space
        "\u200c",  # zero-width non-joiner
        "\u200d",  # zero-width joiner
        "\u2060",  # word joiner
        "\u2061",  # function application
        "\u2062",  # invisible times
        "\u2063",  # invisible separator
        "\u2064",  # invisible plus
        "\u200e",  # left-to-right mark
        "\u200f",  # right-to-left mark
        "\u202a",  # left-to-right embedding
        "\u202b",  # right-to-left embedding
        "\u202c",  # pop directional formatting
        "\u202d",  # left-to-right override
        "\u202e",  # right-to-left override
        "\ufeff",  # zero-width no-break space
        "\u00ad",  # soft hyphen
    ]
)
_INVISIBLE_TABLE = str.maketrans("", "", _INVISIBLE_CHARS)

#: Imperative instruction-override and control-token smuggling patterns. These
#: are unambiguous attack vectors, matched case-insensitively; legitimate prose
#: (e.g. a tech article mentioning "system prompt") is intentionally left alone.
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "ignore all previous instructions / prompts / context"
    re.compile(
        r"\bignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+"
        r"(?:instructions?|prompts?|context|messages?)\b",
        re.IGNORECASE,
    ),
    # "disregard all previous instructions / context"
    re.compile(
        r"\bdisregard\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+"
        r"(?:instructions?|prompts?|context|messages?)\b",
        re.IGNORECASE,
    ),
    # "reveal / show / output / print your (system|hidden|initial) prompt"
    re.compile(
        r"\b(?:reveal|show|output|print|display)\s+(?:your|the|its)\s+"
        r"(?:system|hidden|initial|underlying)\s+"
        r"(?:prompt|instructions?|directives?|system\s+message)\b",
        re.IGNORECASE,
    ),
    # Role-override framing ("you are now an AI ...")
    re.compile(
        r"\byou\s+are\s+now\s+(?:an\s+)?(?:ai|assistant|agent|gpt|model|jarvis)\b",
        re.IGNORECASE,
    ),
    # LLM control-token smuggling (ChatML, Llama, etc.)
    re.compile(
        r"<\|\s*(?:im_start|im_end|system|assistant|user|endoftext|startoftext)\s*\|>",
        re.IGNORECASE,
    ),
    re.compile(r"\[/\s*INST\s*\]|\[\s*INST\s*\]", re.IGNORECASE),
)

#: Placeholder inserted where an injection vector was removed, so the LLM can
#: see that content was deliberately stripped.
_INJECTION_MARK = "[ content removed: potential instruction injection ]"

#: Delimiters wrapping sanitized page content so the LLM treats it as untrusted
#: data rather than instructions.
UNTRUSTED_START = "[UNTRUSTED WEB CONTENT START]"
UNTRUSTED_END = "[UNTRUSTED WEB CONTENT END]"


def sanitize_fetched_text(text: str, max_chars: int = 8000) -> str:
    """Sanitize fetched page text against prompt injection before the LLM.

    Applies, in order:

    1. Strip invisible / zero-width Unicode characters.
    2. Remove HTML comments (a classic hidden-instruction container).
    3. Replace known instruction-override / control-token patterns with a
       visible removal marker.
    4. Collapse runs of whitespace.
    5. Wrap the result in ``UNTRUSTED_START`` / ``UNTRUSTED_END`` delimiters
       and truncate to ``max_chars``.

    Args:
        text: Raw extracted page text (HTML already stripped by the fetcher).
        max_chars: Hard cap on the returned string, delimiters included.

    Returns:
        Sanitized, delimited, truncated text. Always non-empty when the input
        contained any visible content.
    """
    if not text:
        return ""

    # 1. Invisible / zero-width characters.
    text = text.translate(_INVISIBLE_TABLE)
    # 2. HTML comments (including multi-line).
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # 3. Known injection patterns → visible removal marker.
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub(_INJECTION_MARK, text)
    # 4. Collapse whitespace.
    text = re.sub(r"\s+", " ", text).strip()
    # 5. Delimit as untrusted data, then truncate.
    wrapped = f"{UNTRUSTED_START} {text} {UNTRUSTED_END}"
    if len(wrapped) <= max_chars:
        return wrapped
    return wrapped[:max_chars]


# ──────────────────────────────────────────────────────────────────────────────
# Provider contract
# ──────────────────────────────────────────────────────────────────────────────


class WebSearchProvider(ABC):
    """Abstract web search / page-fetch provider.

    Implementations are stateless by convention (matching the V10 ``Tool``
    contract): all per-call state flows through arguments, so providers can be
    shared safely across concurrent executions.
    """

    #: Stable provider identifier (e.g. ``"duckduckgo"``).
    name: str = ""

    @abstractmethod
    async def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Run a web search and return ``[{title, url, snippet}, ...]``.

        Raises:
            ToolError: ``invalid_params`` for empty queries, ``timeout`` when
                the provider exceeds its deadline, ``execution_error`` when the
                provider reports a failure.
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_page(self, url: str, max_chars: int = 8000) -> str:
        """Fetch a URL and return **sanitized** page text.

        The returned text MUST have passed through prompt-injection
        sanitization (``sanitize_fetched_text``) so it is safe to hand to an
        LLM.

        Raises:
            ToolError: ``invalid_params`` for bad URLs, ``timeout`` on
                deadline expiry, ``execution_error`` on fetch failure.
        """
        raise NotImplementedError


class DuckDuckGoProvider(WebSearchProvider):
    """First web-search provider: adapts the existing v6.3.0 DDG client.

    Wraps :class:`jarvis.computer.search.WebSearch` (HTML-scrape based, no API
    key) without modifying it. The client is injectable for tests.
    """

    name = "duckduckgo"

    def __init__(
        self,
        client: WebSearch | None = None,
        http_timeout: float | None = None,
    ) -> None:
        self._client = client if client is not None else web_search
        self._timeout = (
            http_timeout if http_timeout is not None else reliability_config.http_timeout
        )

    def _raise(self, code: str, message: str, tool: str, recoverable: bool) -> None:
        raise ToolError(message, code=code, tool=tool, recoverable=recoverable)

    async def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if not query or not query.strip():
            self._raise(
                ToolError.INVALID_PARAMS,
                "query must be a non-empty string",
                "web_search",
                recoverable=False,
            )
        try:
            raw = await asyncio.wait_for(
                self._client.search(
                    query.strip(), engine="duckduckgo", max_results=max(1, int(limit))
                ),
                timeout=self._timeout,
            )
        except TimeoutError:
            self._raise(
                ToolError.TIMEOUT,
                f"web search timed out after {self._timeout:.1f}s",
                "web_search",
                recoverable=True,
            )
        if not raw.get("ok"):
            self._raise(
                ToolError.EXECUTION_ERROR,
                str(raw.get("error") or "web search failed"),
                "web_search",
                recoverable=True,
            )
        results = raw.get("results") or []
        return [r for r in results if isinstance(r, dict)]

    async def fetch_page(self, url: str, max_chars: int = 8000) -> str:
        if not url or not url.strip():
            self._raise(
                ToolError.INVALID_PARAMS,
                "url must be a non-empty string",
                "fetch_page",
                recoverable=False,
            )
        try:
            raw = await asyncio.wait_for(
                self._client.fetch_page(
                    url.strip(), max_chars=max(200, int(max_chars))
                ),
                timeout=self._timeout,
            )
        except TimeoutError:
            self._raise(
                ToolError.TIMEOUT,
                f"page fetch timed out after {self._timeout:.1f}s",
                "fetch_page",
                recoverable=True,
            )
        if not raw.get("ok"):
            self._raise(
                ToolError.EXECUTION_ERROR,
                str(raw.get("error") or "page fetch failed"),
                "fetch_page",
                recoverable=True,
            )
        return sanitize_fetched_text(raw.get("text", ""), max_chars=int(max_chars))


# ──────────────────────────────────────────────────────────────────────────────
# V10 executable tools
# ──────────────────────────────────────────────────────────────────────────────


class WebSearchTool(Tool):
    """V10 executable: search the web and return ranked results."""

    spec = ToolSpec(
        name="web_search",
        description="Search the web and return ranked results (title, url, snippet).",
        parameters=(
            ParamSpec("query", type="string", description="The search query", required=True),
            ParamSpec(
                "limit",
                type="integer",
                description="Maximum number of results to return",
                default=8,
            ),
        ),
        permission_level=1,  # LOW_RISK — automatic, audited
        capability="network",  # Trinity capability (default ALLOW)
        risk_level="safe",
        category="research",
        examples=("web_search(query='python asyncio patterns')",),
        version="1.0.0",
    )

    def __init__(self, provider: WebSearchProvider | None = None) -> None:
        self._provider = provider if provider is not None else duckduckgo_provider

    async def run(self, params: dict[str, Any]) -> ToolResult:
        try:
            query = str(params["query"])
            limit = int(params.get("limit", 8))
            results = await self._provider.search(query, limit=limit)
        except ToolError as e:
            return self._tool_error(e)
        return ToolResult(
            ok=True,
            data={"query": query, "count": len(results), "results": results},
            tool=self.name,
            artifacts=[{"type": "search_results", "count": len(results)}],
        )

    def _tool_error(self, e: ToolError) -> ToolResult:
        return ToolResult(
            ok=False,
            error=str(e),
            tool=self.name,
            errors=[e.to_dict()],
            artifacts=[{"type": "error", **e.to_dict()}],
            recovery=(
                "Check network connectivity or try a different query" if e.recoverable else None
            ),
        )


class FetchPageTool(Tool):
    """V10 executable: fetch a URL and return sanitized page text."""

    spec = ToolSpec(
        name="fetch_page",
        description=(
            "Fetch a URL and return sanitized text content, safe to use as context."
        ),
        parameters=(
            ParamSpec("url", type="string", description="Full URL to fetch", required=True),
            ParamSpec(
                "max_chars",
                type="integer",
                description="Maximum characters to return",
                default=8000,
            ),
        ),
        permission_level=1,  # LOW_RISK — automatic, audited
        capability="network",  # Trinity capability (default ALLOW)
        risk_level="safe",
        category="research",
        examples=("fetch_page(url='https://example.com')",),
        version="1.0.0",
    )

    def __init__(self, provider: WebSearchProvider | None = None) -> None:
        self._provider = provider if provider is not None else duckduckgo_provider

    async def run(self, params: dict[str, Any]) -> ToolResult:
        try:
            url = str(params["url"])
            max_chars = int(params.get("max_chars", 8000))
            text = await self._provider.fetch_page(url, max_chars=max_chars)
        except ToolError as e:
            return ToolResult(
                ok=False,
                error=str(e),
                tool=self.name,
                errors=[e.to_dict()],
                artifacts=[{"type": "error", **e.to_dict()}],
                recovery=(
                    "Check the URL or network connectivity" if e.recoverable else None
                ),
            )
        return ToolResult(
            ok=True,
            data={"url": url, "text": text, "length": len(text)},
            tool=self.name,
            artifacts=[{"type": "page_text", "url": url, "length": len(text)}],
        )


# ──────────────────────────────────────────────────────────────────────────────
# Singletons + registration
# ──────────────────────────────────────────────────────────────────────────────

#: Default provider instance — adapts the existing v6.3.0 DDG client.
duckduckgo_provider = DuckDuckGoProvider()

#: Executable V10 tool instances, registered so the executor can dispatch them.
web_search_tool = WebSearchTool()
fetch_page_tool = FetchPageTool()
tool_registry.register_tool(web_search_tool)
tool_registry.register_tool(fetch_page_tool)
