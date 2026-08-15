"""Unified Tool Layer — the only interface workers use (v6.3.0).

Every capability is exposed through one consistent interface.
Internally routes to the correct manager.

Usage:
    from jarvis.tools import tool

    result = await tool.search_web("python async patterns")
    result = await tool.take_screenshot()
    result = await tool.run_terminal("ls -la")
"""

# Import V10 tool modules so their module-level register_tool() calls fire;
# tool_registry stays populated whenever the package is imported.
from . import (
    browser_tools,  # noqa: F401 — side effect: registers browser_* tools
    web_search,  # noqa: F401 — side effect: registers web_search/fetch_page
)
from .result import ToolResult
from .unified import Tool

# Module-level singleton
tool = Tool()

__all__ = ["tool", "Tool", "ToolResult"]
