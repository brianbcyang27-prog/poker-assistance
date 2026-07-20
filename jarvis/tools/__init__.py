"""Unified Tool Layer — the only interface workers use (v6.3.0).

Every capability is exposed through one consistent interface.
Internally routes to the correct manager.

Usage:
    from jarvis.tools import tool

    result = await tool.search_web("python async patterns")
    result = await tool.take_screenshot()
    result = await tool.run_terminal("ls -la")
"""

from .result import ToolResult
from .unified import Tool

# Module-level singleton
tool = Tool()

__all__ = ["tool", "Tool", "ToolResult"]
