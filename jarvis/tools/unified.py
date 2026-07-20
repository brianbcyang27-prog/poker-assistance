"""Unified Tool Layer — the only interface agents use (v6.3.0).

The LLM never sees individual managers. Every capability goes through `tool.*`.
Internally routes to the correct manager based on the operation.

Usage:
    from jarvis.tools import tool
    result = await tool.search_web("python async patterns")
"""
import logging
from typing import Any, Dict, List, Optional

from .result import ToolResult, timed

log = logging.getLogger(__name__)


class Tool:
    """Unified interface to all Jarvis capabilities.

    The LLM calls tool.method(). Internally routes to the correct manager.
    """

    def __init__(self):
        self._managers: Dict[str, Any] = {}

    def _get_manager(self, name: str) -> Any:
        """Lazy-load manager by name."""
        if name in self._managers:
            return self._managers[name]
        mgr = self._load_manager(name)
        if mgr is not None:
            self._managers[name] = mgr
        return mgr

    def _load_manager(self, name: str) -> Any:
        """Import and instantiate a manager. Returns None on failure."""
        try:
            if name == "browser":
                from jarvis.browser.manager import BrowserManager
                return BrowserManager()
            elif name == "computer":
                from jarvis.computer.manager import ComputerManager
                return ComputerManager()
            elif name == "accessibility":
                from jarvis.computer.accessibility.manager import AccessibilityManager
                return AccessibilityManager()
            elif name == "vision":
                from jarvis.vision.manager import VisionManager
                return VisionManager()
            elif name == "os":
                from jarvis.os.manager import OSManager
                return OSManager()
            elif name == "memory":
                from jarvis.brain.core.memory import MemoryManager
                return MemoryManager()
            elif name == "engineering":
                from jarvis.engineering.knowledge import EngineeringKnowledgeManager
                return EngineeringKnowledgeManager()
            elif name == "mission":
                from jarvis.mission.manager import MissionManager
                return MissionManager()
            elif name == "project":
                from jarvis.projects import ProjectManager
                return ProjectManager()
            return None
        except Exception as e:
            log.warning("Failed to load manager %s: %s", name, e)
            return None

    # ─── WEB ──────────────────────────────────────────────

    @timed
    async def search_web(self, query: str, source: str = "auto", limit: int = 5) -> ToolResult:
        """Search the web using DuckDuckGo or Brave."""
        br = self._get_manager("browser")
        if not br:
            return ToolResult(ok=False, error="Browser not available", tool="search_web")
        try:
            results = await br.search(query, source=source, limit=limit)
            return ToolResult(ok=True, data=results, tool="search_web")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="search_web")

    @timed
    async def open_url(self, url: str) -> ToolResult:
        """Open a URL in the browser."""
        br = self._get_manager("browser")
        if not br:
            return ToolResult(ok=False, error="Browser not available", tool="open_url")
        try:
            await br.navigate(url)
            return ToolResult(ok=True, data={"url": url}, tool="open_url")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="open_url")

    @timed
    async def fetch_page(self, url: str) -> ToolResult:
        """Fetch page content using httpx."""
        br = self._get_manager("browser")
        if not br:
            return ToolResult(ok=False, error="Browser not available", tool="fetch_page")
        try:
            content = await br.fetch(url)
            return ToolResult(ok=True, data=content, tool="fetch_page")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="fetch_page")

    # ─── BROWSER INTERACTION ──────────────────────────────

    @timed
    async def click(self, selector: str) -> ToolResult:
        """Click an element on the page."""
        br = self._get_manager("browser")
        if not br:
            return ToolResult(ok=False, error="Browser not available", tool="click")
        try:
            await br.click(selector)
            return ToolResult(ok=True, tool="click")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="click")

    @timed
    async def type_text(self, selector: str, text: str) -> ToolResult:
        """Type text into an element."""
        br = self._get_manager("browser")
        if not br:
            return ToolResult(ok=False, error="Browser not available", tool="type_text")
        try:
            await br.type(selector, text)
            return ToolResult(ok=True, tool="type_text")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="type_text")

    @timed
    async def scroll_page(self, direction: str = "down", amount: int = 3) -> ToolResult:
        """Scroll the page up or down."""
        br = self._get_manager("browser")
        if not br:
            return ToolResult(ok=False, error="Browser not available", tool="scroll_page")
        try:
            await br.scroll(direction, amount)
            return ToolResult(ok=True, tool="scroll_page")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="scroll_page")

    @timed
    async def get_page_text(self) -> ToolResult:
        """Get the visible text from the current page."""
        br = self._get_manager("browser")
        if not br:
            return ToolResult(ok=False, error="Browser not available", tool="get_page_text")
        try:
            text = await br.get_text()
            return ToolResult(ok=True, data=text, tool="get_page_text")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="get_page_text")

    # ─── VISION ───────────────────────────────────────────

    @timed
    async def take_screenshot(self, mode: str = "full") -> ToolResult:
        """Take a screenshot of the current screen."""
        vision = self._get_manager("vision")
        if not vision:
            return ToolResult(ok=False, error="Vision not available", tool="take_screenshot")
        try:
            path = await vision.screenshot(mode=mode)
            return ToolResult(ok=True, data={"path": path}, tool="take_screenshot")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="take_screenshot")

    @timed
    async def read_screen(self) -> ToolResult:
        """Read text and elements from the screen using OCR."""
        vision = self._get_manager("vision")
        if not vision:
            return ToolResult(ok=False, error="Vision not available", tool="read_screen")
        try:
            result = await vision.read_screen()
            return ToolResult(ok=True, data=result, tool="read_screen")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="read_screen")

    @timed
    async def find_on_screen(self, query: str) -> ToolResult:
        """Find a visual element on screen matching the query."""
        vision = self._get_manager("vision")
        if not vision:
            return ToolResult(ok=False, error="Vision not available", tool="find_on_screen")
        try:
            result = await vision.find(query)
            return ToolResult(ok=True, data=result, tool="find_on_screen")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="find_on_screen")

    # ─── ACCESSIBILITY ────────────────────────────────────

    @timed
    async def a11y_click(self, query: str, app: Optional[str] = None) -> ToolResult:
        """Click an accessibility element by description."""
        a11y = self._get_manager("accessibility")
        if not a11y:
            return ToolResult(ok=False, error="Accessibility not available", tool="a11y_click")
        try:
            await a11y.click(query, app=app)
            return ToolResult(ok=True, tool="a11y_click")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="a11y_click")

    @timed
    async def a11y_type(self, query: str, text: str, app: Optional[str] = None) -> ToolResult:
        """Type text into an accessibility element."""
        a11y = self._get_manager("accessibility")
        if not a11y:
            return ToolResult(ok=False, error="Accessibility not available", tool="a11y_type")
        try:
            await a11y.type_text(query, text, app=app)
            return ToolResult(ok=True, tool="a11y_type")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="a11y_type")

    @timed
    async def a11y_find(self, query: str, app: Optional[str] = None) -> ToolResult:
        """Find accessibility elements matching a query."""
        a11y = self._get_manager("accessibility")
        if not a11y:
            return ToolResult(ok=False, error="Accessibility not available", tool="a11y_find")
        try:
            result = await a11y.find(query, app=app)
            return ToolResult(ok=True, data=result, tool="a11y_find")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="a11y_find")

    @timed
    async def a11y_summary(self, app: Optional[str] = None) -> ToolResult:
        """Get a summary of the accessibility tree."""
        a11y = self._get_manager("accessibility")
        if not a11y:
            return ToolResult(ok=False, error="Accessibility not available", tool="a11y_summary")
        try:
            result = await a11y.get_summary(app=app)
            return ToolResult(ok=True, data=result, tool="a11y_summary")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="a11y_summary")

    # ─── TERMINAL ─────────────────────────────────────────

    @timed
    async def run_terminal(self, command: str) -> ToolResult:
        """Execute a terminal command."""
        os_mgr = self._get_manager("os")
        if not os_mgr:
            return ToolResult(ok=False, error="OS manager not available", tool="run_terminal")
        try:
            result = await os_mgr.execute(command)
            return ToolResult(ok=True, data=result, tool="run_terminal")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="run_terminal")

    @timed
    async def run_python(self, code: str) -> ToolResult:
        """Run Python code in a sandbox."""
        os_mgr = self._get_manager("os")
        if not os_mgr:
            return ToolResult(ok=False, error="OS manager not available", tool="run_python")
        try:
            result = await os_mgr.run_python(code)
            return ToolResult(ok=True, data=result, tool="run_python")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="run_python")

    # ─── FILE OPERATIONS ──────────────────────────────────

    @timed
    async def read_file(self, path: str) -> ToolResult:
        """Read a file's contents."""
        os_mgr = self._get_manager("os")
        if not os_mgr:
            return ToolResult(ok=False, error="OS manager not available", tool="read_file")
        try:
            content = await os_mgr.read_file(path)
            return ToolResult(ok=True, data=content, tool="read_file")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="read_file")

    @timed
    async def write_file(self, path: str, content: str) -> ToolResult:
        """Write content to a file."""
        os_mgr = self._get_manager("os")
        if not os_mgr:
            return ToolResult(ok=False, error="OS manager not available", tool="write_file")
        try:
            await os_mgr.write_file(path, content)
            return ToolResult(ok=True, tool="write_file")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="write_file")

    @timed
    async def edit_file(self, path: str, old: str, new: str) -> ToolResult:
        """Edit a file by replacing text."""
        os_mgr = self._get_manager("os")
        if not os_mgr:
            return ToolResult(ok=False, error="OS manager not available", tool="edit_file")
        try:
            await os_mgr.edit_file(path, old, new)
            return ToolResult(ok=True, tool="edit_file")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="edit_file")

    @timed
    async def create_folder(self, path: str) -> ToolResult:
        """Create a directory."""
        os_mgr = self._get_manager("os")
        if not os_mgr:
            return ToolResult(ok=False, error="OS manager not available", tool="create_folder")
        try:
            await os_mgr.create_directory(path)
            return ToolResult(ok=True, tool="create_folder")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="create_folder")

    # ─── COMPUTER CONTROL ─────────────────────────────────

    @timed
    async def mouse_click(self, x: int, y: int, button: str = "left") -> ToolResult:
        """Click at screen coordinates."""
        comp = self._get_manager("computer")
        if not comp:
            return ToolResult(ok=False, error="Computer not available", tool="mouse_click")
        try:
            await comp.click(x, y, button=button)
            return ToolResult(ok=True, tool="mouse_click")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="mouse_click")

    @timed
    async def keyboard_type(self, text: str) -> ToolResult:
        """Type text using the keyboard."""
        comp = self._get_manager("computer")
        if not comp:
            return ToolResult(ok=False, error="Computer not available", tool="keyboard_type")
        try:
            await comp.type_text(text)
            return ToolResult(ok=True, tool="keyboard_type")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="keyboard_type")

    @timed
    async def keyboard_hotkey(self, *keys: str) -> ToolResult:
        """Press a keyboard shortcut."""
        comp = self._get_manager("computer")
        if not comp:
            return ToolResult(ok=False, error="Computer not available", tool="keyboard_hotkey")
        try:
            await comp.hotkey(*keys)
            return ToolResult(ok=True, tool="keyboard_hotkey")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="keyboard_hotkey")

    # ─── MEMORY ───────────────────────────────────────────

    @timed
    async def store_memory(self, key: str, value: str, category: str = "general") -> ToolResult:
        """Store a memory."""
        mem = self._get_manager("memory")
        if not mem:
            return ToolResult(ok=False, error="Memory not available", tool="store_memory")
        try:
            await mem.store(key, value, category=category)
            return ToolResult(ok=True, tool="store_memory")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="store_memory")

    @timed
    async def recall_memory(self, query: str, limit: int = 5) -> ToolResult:
        """Recall memories matching a query."""
        mem = self._get_manager("memory")
        if not mem:
            return ToolResult(ok=False, error="Memory not available", tool="recall_memory")
        try:
            results = await mem.recall(query, limit=limit)
            return ToolResult(ok=True, data=results, tool="recall_memory")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="recall_memory")

    # ─── ENGINEERING ──────────────────────────────────────

    @timed
    async def create_cad_model(self, name: str, params: Optional[Dict] = None) -> ToolResult:
        """Create a CAD model."""
        eng = self._get_manager("engineering")
        if not eng:
            return ToolResult(ok=False, error="Engineering not available", tool="create_cad_model")
        try:
            result = eng.create_model(name, **(params or {}))
            return ToolResult(ok=True, data=result, tool="create_cad_model")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="create_cad_model")

    @timed
    async def design_pcb(self, name: str, params: Optional[Dict] = None) -> ToolResult:
        """Create a PCB design project."""
        eng = self._get_manager("engineering")
        if not eng:
            return ToolResult(ok=False, error="Engineering not available", tool="design_pcb")
        try:
            result = eng.create_project(name, **(params or {}))
            return ToolResult(ok=True, data=result, tool="design_pcb")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="design_pcb")

    @timed
    async def recommend_material(self, application: str, **kwargs) -> ToolResult:
        """Recommend a material for an engineering application."""
        eng = self._get_manager("engineering")
        if not eng:
            return ToolResult(ok=False, error="Engineering not available", tool="recommend_material")
        try:
            result = eng.search_materials(application, **kwargs)
            return ToolResult(ok=True, data=result, tool="recommend_material")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="recommend_material")

    # ─── MISSIONS & WORKSPACE ─────────────────────────────

    @timed
    async def create_mission(self, goal: str, priority: int = 5) -> ToolResult:
        """Create a new mission with auto-workspace."""
        mission = self._get_manager("mission")
        if not mission:
            return ToolResult(ok=False, error="Mission manager not available", tool="create_mission")
        try:
            result = await mission.create(goal, priority=priority)
            return ToolResult(ok=True, data=result, tool="create_mission")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="create_mission")

    @timed
    async def resume_mission(self, mission_id: str) -> ToolResult:
        """Resume a paused or completed mission."""
        mission = self._get_manager("mission")
        if not mission:
            return ToolResult(ok=False, error="Mission manager not available", tool="resume_mission")
        try:
            result = await mission.resume(mission_id)
            return ToolResult(ok=True, data=result, tool="resume_mission")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="resume_mission")

    @timed
    async def get_mission_status(self, mission_id: str) -> ToolResult:
        """Get status of a mission."""
        mission = self._get_manager("mission")
        if not mission:
            return ToolResult(ok=False, error="Mission manager not available", tool="get_mission_status")
        try:
            result = await mission.get(mission_id)
            return ToolResult(ok=True, data=result, tool="get_mission_status")
        except Exception as e:
            return ToolResult(ok=False, error=str(e), tool="get_mission_status")

    # ─── LISTING & INTROSPECTION ──────────────────────────

    def list_tools(self) -> List[str]:
        """List all available tool methods."""
        return [
            m for m in dir(self)
            if not m.startswith("_") and callable(getattr(self, m)) and m != "list_tools"
        ]

    def get_tool_info(self, tool_name: str) -> Optional[Dict]:
        """Get metadata about a specific tool."""
        method = getattr(self, tool_name, None)
        if not method or not callable(method):
            return None
        doc = method.__doc__ or ""
        return {
            "name": tool_name,
            "description": doc.strip().split("\n")[0] if doc else "",
            "doc": doc,
        }
