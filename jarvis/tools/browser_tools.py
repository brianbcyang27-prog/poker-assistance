"""V10 Browser Control — V10 executables wrapping ``BrowserManager`` (PHASE H).

Implements architecture checklist item 7:

* A full set of V10 tools (``browser_navigate``, ``browser_click``,
  ``browser_extract``, ...) wrapping the existing
  :class:`jarvis.browser.manager.BrowserManager` browser stack, without
  modifying it.
* ``permission_level`` is derived from the manager's own risk table
  (``BROWSER_ACTION_RISKS``) so the executor gate (PHASE E) matches the
  manager's runtime security classification exactly: safe→0, low→1,
  medium→2, high→3, dangerous→3, unknown→medium→2. Actions absent from the
  table (e.g. ``evaluate``, ``get_cookies``, ``extract_text``) keep the
  manager's ``"medium"`` fallback — the tool layer never re-interprets
  policy.
* The manager already enforces the approval policy internally
  (``BrowserSecurity``/``_apply_policy``); this module only declares intent
  and maps results onto the canonical ``ToolResult``.

Result contract: tools return the canonical
:class:`jarvis.tools.result.ToolResult` — no new result types. Failure modes
use the stable ``ToolError`` codes (``permission_denied``, ``not_found``,
``execution_error``, ``invalid_params``).
"""

from __future__ import annotations

from typing import Any

from jarvis.browser import browser_manager
from jarvis.browser.security import BROWSER_ACTION_RISKS
from jarvis.tools.base import ParamSpec, Tool, ToolError, ToolResult, ToolSpec
from jarvis.tools.registry import tool_registry

__all__ = [
    "BrowserNavigateTool",
    "BrowserSearchTool",
    "BrowserClickTool",
    "BrowserTypeTool",
    "BrowserScrollTool",
    "BrowserPressKeyTool",
    "BrowserExtractTool",
    "BrowserExtractTextTool",
    "BrowserScreenshotTool",
    "BrowserGetContentTool",
    "BrowserGetTextTool",
    "BrowserBackTool",
    "BrowserForwardTool",
    "BrowserReloadTool",
    "BrowserNewTabTool",
    "BrowserCloseTabTool",
    "BrowserWaitForTool",
    "BrowserEvaluateTool",
    "BrowserGetPageInfoTool",
    "BrowserGetCookiesTool",
    "browser_navigate_tool",
    "browser_search_tool",
    "browser_click_tool",
    "browser_type_tool",
    "browser_scroll_tool",
    "browser_press_key_tool",
    "browser_extract_tool",
    "browser_extract_text_tool",
    "browser_screenshot_tool",
    "browser_get_content_tool",
    "browser_get_text_tool",
    "browser_back_tool",
    "browser_forward_tool",
    "browser_reload_tool",
    "browser_new_tab_tool",
    "browser_close_tab_tool",
    "browser_wait_for_tool",
    "browser_evaluate_tool",
    "browser_get_page_info_tool",
    "browser_get_cookies_tool",
]

# ──────────────────────────────────────────────────────────────────────────────
# Risk → permission mapping (single source of truth: BROWSER_ACTION_RISKS)
# ──────────────────────────────────────────────────────────────────────────────

#: V10 permission LEVEL for each manager risk class (0 SAFE .. 3 HIGH_RISK).
_RISK_TO_LEVEL = {"safe": 0, "low": 1, "medium": 2, "high": 3, "dangerous": 3}


def _risk(action: str) -> str:
    """Return the manager's runtime risk classification for ``action``.

    Mirrors ``BROWSER_ACTION_RISKS.get(action, "medium")`` exactly — actions
    absent from the table are classified *medium* at runtime, so the tool
    layer must report the same level or the declared intent would diverge
    from what ``BrowserManager.execute`` actually enforces.
    """
    return BROWSER_ACTION_RISKS.get(action, "medium")


def _permission_level(risk: str) -> int:
    """Map a risk string to the V10 permission LEVEL (0-3)."""
    return _RISK_TO_LEVEL.get(risk, 2)


# ──────────────────────────────────────────────────────────────────────────────
# Shared plumbing
# ──────────────────────────────────────────────────────────────────────────────


class _BrowserTool(Tool):
    """Shared plumbing for every browser tool.

    Subclasses declare ``action`` (the ``BrowserManager.execute`` action
    string) and a ``ToolSpec``; ``run`` delegates to the manager and maps the
    canonical result dict onto ``ToolResult``. Instances are stateless by
    convention: the manager handle is the only per-instance state.
    """

    #: Manager action wrapped by this tool (name without the leading ``_``).
    action: str = ""

    def __init__(self, manager: Any | None = None) -> None:
        #: Injectable for tests; defaults to the shared manager singleton.
        self._manager = manager if manager is not None else browser_manager

    def _tool_error(self, code: str, message: str, recoverable: bool) -> ToolResult:
        error = ToolError(message, code=code, tool=self.name, recoverable=recoverable)
        return ToolResult(
            ok=False,
            error=message,
            tool=self.name,
            errors=[error.to_dict()],
            artifacts=[{"type": "error", **error.to_dict()}],
            recovery=("Retry the action or check browser state" if recoverable else None),
        )

    def _artifacts(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Subclass hook: extra success artifacts derived from ``data``."""
        return []

    def _success(self, result: dict[str, Any]) -> ToolResult:
        payload = {
            k: v
            for k, v in result.items()
            if k not in ("ok", "error", "risk_level", "duration_ms")
        }
        # Unwrap the provider payload when it is the only remaining key, so
        # the LLM sees the data directly (e.g. {"url", "title"} for navigate).
        if list(payload) == ["data"] and isinstance(payload["data"], dict):
            payload = payload["data"]
        artifacts = [{"type": "browser", "action": self.action}]
        artifacts.extend(self._artifacts(payload))
        return ToolResult(
            ok=True,
            data=payload or None,
            tool=self.name,
            duration_ms=float(result.get("duration_ms", 0) or 0),
            artifacts=artifacts,
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        """Execute ``action`` through the manager and map the result."""
        try:
            result = await self._manager.execute(self.action, agent="jarvis", **params)
        except Exception as e:  # boundary: any manager failure becomes a ToolError
            return self._tool_error(ToolError.EXECUTION_ERROR, str(e), recoverable=True)

        if result.get("ok"):
            return self._success(result)

        message = str(result.get("error") or "browser action failed")
        if result.get("requires_approval") or message.startswith("Permission"):
            return self._tool_error(ToolError.PERMISSION_DENIED, message, recoverable=False)
        if "Unknown action" in message:
            return self._tool_error(ToolError.NOT_FOUND, message, recoverable=False)
        return self._tool_error(ToolError.EXECUTION_ERROR, message, recoverable=True)


# ──────────────────────────────────────────────────────────────────────────────
# V10 executable tools
# ──────────────────────────────────────────────────────────────────────────────


class BrowserNavigateTool(_BrowserTool):
    """V10 executable: navigate the browser to a URL."""

    action = "navigate"
    risk_value = _risk("navigate")

    spec = ToolSpec(
        name="browser_navigate",
        description="Navigate the browser to a URL and wait for the page to load.",
        parameters=(
            ParamSpec("url", type="string", description="Full URL to navigate to", required=True),
            ParamSpec(
                "wait_until",
                type="string",
                description="Navigation wait condition (e.g. domcontentloaded)",
                default="domcontentloaded",
            ),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_navigate(url='https://example.com')",),
        version="1.0.0",
    )

    def _artifacts(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        if data.get("url"):
            return [{"type": "navigation", "url": data.get("url"), "title": data.get("title")}]
        return []


class BrowserSearchTool(_BrowserTool):
    """V10 executable: search the web in the browser."""

    action = "search"
    risk_value = _risk("search")

    spec = ToolSpec(
        name="browser_search",
        description="Search the web in the browser using a search engine and return the page.",
        parameters=(
            ParamSpec("query", type="string", description="The search query", required=True),
            ParamSpec(
                "engine",
                type="string",
                description="Search engine (google, duckduckgo, bing)",
                default="google",
            ),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_search(query='python asyncio patterns')",),
        version="1.0.0",
    )

    def _artifacts(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        if data.get("url"):
            return [{"type": "navigation", "url": data.get("url"), "title": data.get("title")}]
        return []


class BrowserClickTool(_BrowserTool):
    """V10 executable: click an element on the current page."""

    action = "click"
    risk_value = _risk("click")

    spec = ToolSpec(
        name="browser_click",
        description="Click an element on the current page identified by a CSS selector.",
        parameters=(
            ParamSpec(
                "selector",
                type="string",
                description="CSS selector of the element",
                required=True,
            ),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_click(selector='button#submit')",),
        version="1.0.0",
    )


class BrowserTypeTool(_BrowserTool):
    """V10 executable: type text into an input element."""

    action = "type"
    risk_value = _risk("type")

    spec = ToolSpec(
        name="browser_type",
        description="Type text into an input element identified by a CSS selector.",
        parameters=(
            ParamSpec(
                "selector",
                type="string",
                description="CSS selector of the input",
                required=True,
            ),
            ParamSpec("text", type="string", description="Text to type", required=True),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_type(selector='input#q', text='asyncio')",),
        version="1.0.0",
    )


class BrowserScrollTool(_BrowserTool):
    """V10 executable: scroll the current page."""

    action = "scroll"
    risk_value = _risk("scroll")

    spec = ToolSpec(
        name="browser_scroll",
        description="Scroll the current page by a pixel amount.",
        parameters=(
            ParamSpec(
                "direction",
                type="string",
                description="Scroll direction (up or down)",
                default="down",
            ),
            ParamSpec(
                "amount",
                type="integer",
                description="Pixels to scroll",
                default=500,
            ),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_scroll(direction='down', amount=500)",),
        version="1.0.0",
    )


class BrowserPressKeyTool(_BrowserTool):
    """V10 executable: press a keyboard key in the current page."""

    action = "press_key"
    risk_value = _risk("press_key")

    spec = ToolSpec(
        name="browser_press_key",
        description="Press a keyboard key in the current page (e.g. Enter, Escape).",
        parameters=(
            ParamSpec("key", type="string", description="Key name to press", required=True),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_press_key(key='Enter')",),
        version="1.0.0",
    )


class BrowserExtractTool(_BrowserTool):
    """V10 executable: extract structured data from the current page."""

    action = "extract"
    risk_value = _risk("extract")

    spec = ToolSpec(
        name="browser_extract",
        description=(
            "Extract structured data (title, headings, links) from the current page."
        ),
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_extract()",),
        version="1.0.0",
    )


class BrowserExtractTextTool(_BrowserTool):
    """V10 executable: extract the visible text of the current page."""

    action = "extract_text"
    risk_value = _risk("extract_text")

    spec = ToolSpec(
        name="browser_extract_text",
        description="Extract the visible text content of the current page.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_extract_text()",),
        version="1.0.0",
    )


class BrowserScreenshotTool(_BrowserTool):
    """V10 executable: screenshot the current page."""

    action = "screenshot"
    risk_value = _risk("screenshot")

    spec = ToolSpec(
        name="browser_screenshot",
        description="Take a screenshot of the current page and return its file path.",
        parameters=(
            ParamSpec(
                "path",
                type="string",
                description="Destination path; defaults to a temp file",
                default=None,
            ),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_screenshot()",),
        version="1.0.0",
    )

    def _artifacts(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        if data.get("path"):
            return [{"type": "screenshot", "path": data.get("path")}]
        return []


class BrowserGetContentTool(_BrowserTool):
    """V10 executable: get the raw HTML of the current page."""

    action = "get_content"
    risk_value = _risk("get_content")

    spec = ToolSpec(
        name="browser_get_content",
        description="Get the raw HTML content of the current page.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_get_content()",),
        version="1.0.0",
    )


class BrowserGetTextTool(_BrowserTool):
    """V10 executable: get the visible text of the current page."""

    action = "get_text"
    risk_value = _risk("get_text")

    spec = ToolSpec(
        name="browser_get_text",
        description="Get the visible text content of the current page.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_get_text()",),
        version="1.0.0",
    )


class BrowserBackTool(_BrowserTool):
    """V10 executable: go back in browser history."""

    action = "back"
    risk_value = _risk("back")

    spec = ToolSpec(
        name="browser_back",
        description="Go back one step in browser history.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_back()",),
        version="1.0.0",
    )


class BrowserForwardTool(_BrowserTool):
    """V10 executable: go forward in browser history."""

    action = "forward"
    risk_value = _risk("forward")

    spec = ToolSpec(
        name="browser_forward",
        description="Go forward one step in browser history.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_forward()",),
        version="1.0.0",
    )


class BrowserReloadTool(_BrowserTool):
    """V10 executable: reload the current page."""

    action = "reload"
    risk_value = _risk("reload")

    spec = ToolSpec(
        name="browser_reload",
        description="Reload the current page.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_reload()",),
        version="1.0.0",
    )


class BrowserNewTabTool(_BrowserTool):
    """V10 executable: open a new browser tab."""

    action = "new_tab"
    risk_value = _risk("new_tab")

    spec = ToolSpec(
        name="browser_new_tab",
        description="Open a new browser tab, optionally navigating to a URL.",
        parameters=(
            ParamSpec(
                "url",
                type="string",
                description="URL to open in the new tab (blank for about:blank)",
                default="",
            ),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_new_tab(url='https://example.com')",),
        version="1.0.0",
    )


class BrowserCloseTabTool(_BrowserTool):
    """V10 executable: close the current browser tab."""

    action = "close_tab"
    risk_value = _risk("close_tab")

    spec = ToolSpec(
        name="browser_close_tab",
        description="Close the current browser tab.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_close_tab()",),
        version="1.0.0",
    )


class BrowserWaitForTool(_BrowserTool):
    """V10 executable: wait for an element to appear."""

    action = "wait_for"
    risk_value = _risk("wait_for")

    spec = ToolSpec(
        name="browser_wait_for",
        description="Wait for an element identified by a CSS selector to appear.",
        parameters=(
            ParamSpec(
                "selector",
                type="string",
                description="CSS selector to wait for",
                required=True,
            ),
            ParamSpec(
                "timeout",
                type="integer",
                description="Maximum wait time in milliseconds",
                default=10000,
            ),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_wait_for(selector='div#results')",),
        version="1.0.0",
    )


class BrowserEvaluateTool(_BrowserTool):
    """V10 executable: run JavaScript in the current page."""

    action = "evaluate"
    risk_value = _risk("evaluate")

    spec = ToolSpec(
        name="browser_evaluate",
        description="Execute a JavaScript expression in the current page.",
        parameters=(
            ParamSpec(
                "expression",
                type="string",
                description="JavaScript expression to evaluate",
                required=True,
            ),
        ),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_evaluate(expression='document.title')",),
        version="1.0.0",
    )


class BrowserGetPageInfoTool(_BrowserTool):
    """V10 executable: get the current page's URL and title."""

    action = "get_page_info"
    risk_value = _risk("get_page_info")

    spec = ToolSpec(
        name="browser_get_page_info",
        description="Get the current page's URL and title.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_get_page_info()",),
        version="1.0.0",
    )


class BrowserGetCookiesTool(_BrowserTool):
    """V10 executable: get the current browser context's cookies."""

    action = "get_cookies"
    risk_value = _risk("get_cookies")

    spec = ToolSpec(
        name="browser_get_cookies",
        description="Get all cookies of the current browser context.",
        parameters=(),
        permission_level=_permission_level(risk_value),
        capability="browser",
        risk_level=risk_value,
        category="browser",
        examples=("browser_get_cookies()",),
        version="1.0.0",
    )

    def _artifacts(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        cookies = data.get("cookies")
        if isinstance(cookies, list):
            return [{"type": "cookies", "count": len(cookies)}]
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Singletons + registration
# ──────────────────────────────────────────────────────────────────────────────

#: Executable V10 tool instances, registered so the executor can dispatch them.
#: All share the module-level ``browser_manager`` singleton unless injected.
browser_navigate_tool = BrowserNavigateTool()
browser_search_tool = BrowserSearchTool()
browser_click_tool = BrowserClickTool()
browser_type_tool = BrowserTypeTool()
browser_scroll_tool = BrowserScrollTool()
browser_press_key_tool = BrowserPressKeyTool()
browser_extract_tool = BrowserExtractTool()
browser_extract_text_tool = BrowserExtractTextTool()
browser_screenshot_tool = BrowserScreenshotTool()
browser_get_content_tool = BrowserGetContentTool()
browser_get_text_tool = BrowserGetTextTool()
browser_back_tool = BrowserBackTool()
browser_forward_tool = BrowserForwardTool()
browser_reload_tool = BrowserReloadTool()
browser_new_tab_tool = BrowserNewTabTool()
browser_close_tab_tool = BrowserCloseTabTool()
browser_wait_for_tool = BrowserWaitForTool()
browser_evaluate_tool = BrowserEvaluateTool()
browser_get_page_info_tool = BrowserGetPageInfoTool()
browser_get_cookies_tool = BrowserGetCookiesTool()

_register_tools = (
    browser_navigate_tool,
    browser_search_tool,
    browser_click_tool,
    browser_type_tool,
    browser_scroll_tool,
    browser_press_key_tool,
    browser_extract_tool,
    browser_extract_text_tool,
    browser_screenshot_tool,
    browser_get_content_tool,
    browser_get_text_tool,
    browser_back_tool,
    browser_forward_tool,
    browser_reload_tool,
    browser_new_tab_tool,
    browser_close_tab_tool,
    browser_wait_for_tool,
    browser_evaluate_tool,
    browser_get_page_info_tool,
    browser_get_cookies_tool,
)
for _tool in _register_tools:
    tool_registry.register_tool(_tool)
