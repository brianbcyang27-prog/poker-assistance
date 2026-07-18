"""Browser state tracking.

Maintains real-time state of the browser session:
- Current URL and title
- Navigation history
- Open tabs
- Active elements
- Download state
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class BrowserStatus(str, Enum):
    """Current browser operating status."""
    IDLE = "idle"
    NAVIGATING = "Navigating"
    LOADING = "Loading"
    BROWSING = "Browsing"
    EXTRACTING = "Extracting"
    DOWNLOADING = "Downloading"
    FILLING_FORM = "Filling form"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class TabInfo:
    """Information about a single browser tab."""
    id: str = ""
    url: str = ""
    title: str = ""
    is_active: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "is_active": self.is_active,
        }


@dataclass
class NavigationEntry:
    """A single entry in the navigation history."""
    url: str = ""
    title: str = ""
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


@dataclass
class BrowserState:
    """Complete real-time state of the browser.

    Updated by the BrowserManager on every action.
    Read by the UI for live status display.
    """
    status: str = BrowserStatus.IDLE
    current_url: str = ""
    current_title: str = ""
    tabs: list[TabInfo] = None
    history: list[NavigationEntry] = None
    active_element: Optional[str] = None
    error: Optional[str] = None
    last_action: str = ""
    last_action_time: float = 0.0
    progress: float = 0.0  # 0-1 for multi-step operations
    agent: str = ""  # which worker is using the browser
    task_summary: str = ""

    def __post_init__(self):
        if self.tabs is None:
            self.tabs = []
        if self.history is None:
            self.history = []
        self._active_tab_id = ""
        self._current_action = ""
        self._navigation_history: list[NavigationEntry] = []
        self._last_activity: float = 0.0
        self._last_error: str = ""
        self._tab_count: int = 0

    @property
    def tab_count(self) -> int:
        return len(self.tabs)

    @property
    def active_tab_id(self) -> str:
        return self._active_tab_id

    @property
    def current_action(self) -> str:
        return self._current_action or self.last_action

    @property
    def navigation_history(self) -> list[NavigationEntry]:
        return self.history

    @property
    def last_activity(self) -> float:
        return self._last_activity or self.last_action_time

    @property
    def last_error(self) -> str:
        return self._last_error or (self.error or "")

    def add_tab(self, tab: TabInfo):
        self.tabs.append(tab)
        self._tab_count = len(self.tabs)

    def set_active_tab(self, tab_id: str):
        self._active_tab_id = tab_id
        for t in self.tabs:
            t.is_active = (t.id == tab_id)

    def remove_tab(self, tab_id: str):
        self.tabs = [t for t in self.tabs if t.id != tab_id]
        self._tab_count = len(self.tabs)

    def update_navigation(self, url: str, title: str = "", duration_ms: float = 0):
        """Record a navigation event."""
        self.current_url = url
        self.current_title = title
        self.status = BrowserStatus.BROWSING
        self.last_action = f"navigate:{url}"
        self._current_action = self.last_action
        self.last_action_time = time.time()
        self._last_activity = self.last_action_time
        self._navigation_history.append(NavigationEntry(
            url=url, title=title, duration_ms=duration_ms,
        ))
        entry = self._navigation_history[-1]
        self.history.append(entry)
        # Keep last 50 entries
        if len(self.history) > 50:
            self.history = self.history[-50:]
        if len(self._navigation_history) > 50:
            self._navigation_history = self._navigation_history[-50:]

    def update_status(self, status: str, detail: str = ""):
        """Update the current status."""
        self.status = status
        if detail:
            self.last_action = detail
            self._current_action = detail
        self.last_action_time = time.time()
        self._last_activity = self.last_action_time

    def set_error(self, error: str):
        """Record an error."""
        self.error = error
        self._last_error = error
        self.status = BrowserStatus.ERROR

    def clear_error(self):
        """Clear the error state."""
        self.error = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "current_url": self.current_url,
            "current_title": self.current_title,
            "tab_count": len(self.tabs),
            "tabs": [t.to_dict() for t in self.tabs[:10]],
            "history_length": len(self.history),
            "last_history": [h.to_dict() for h in self.history[-5:]],
            "active_element": self.active_element,
            "error": self.error,
            "last_action": self.last_action,
            "progress": self.progress,
            "agent": self.agent,
            "task_summary": self.task_summary,
        }

    def to_status_string(self) -> str:
        """Compact status for UI display."""
        status_icon = {
            BrowserStatus.IDLE: "○",
            BrowserStatus.NAVIGATING: "↻",
            BrowserStatus.LOADING: "⟳",
            BrowserStatus.BROWSING: "◉",
            BrowserStatus.EXTRACTING: "📋",
            BrowserStatus.DOWNLOADING: "⬇",
            BrowserStatus.FILLING_FORM: "✎",
            BrowserStatus.ERROR: "✗",
            BrowserStatus.CLOSED: "–",
        }.get(self.status, "?")

        parts = [f"{status_icon} {self.status}"]
        if self.current_url:
            from urllib.parse import urlparse
            domain = urlparse(self.current_url).netloc
            parts.append(f"  {domain}")
        if self.agent:
            parts.append(f"  Agent: {self.agent}")
        if self.task_summary:
            parts.append(f"  Task: {self.task_summary}")
        if self.error:
            parts.append(f"  Error: {self.error}")
        return "\n".join(parts)
