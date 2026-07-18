"""Tests for JARVIS OS Integration (v5.0.0)."""

import pytest
import asyncio
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.os.notifications import NotificationManager
from jarvis.os.clipboard import ClipboardManager, ClipboardEntry
from jarvis.os.hotkeys import HotkeyManager
from jarvis.os.menubar import MenuBarManager
from jarvis.os.watcher import FileWatcher
from jarvis.os.manager import OSManager
from jarvis.computer.actions import ActionType
from jarvis.computer.manager import ComputerManager


# ── NotificationManager Tests ────────────────────────────

class TestNotificationManager:
    def setup_method(self):
        self.nm = NotificationManager()

    def test_init(self):
        assert self.nm.is_enabled
        assert len(self.nm.history) == 0

    def test_enable_disable(self):
        self.nm.disable()
        assert not self.nm.is_enabled
        self.nm.enable()
        assert self.nm.is_enabled

    def test_get_history_empty(self):
        history = self.nm.get_history()
        assert history == []

    def test_get_history_limit(self):
        from jarvis.os.notifications import Notification
        from datetime import datetime
        for i in range(15):
            self.nm.history.append(Notification(title=f"Test {i}", message=f"Message {i}"))
        history = self.nm.get_history(limit=5)
        assert len(history) == 5
        assert history[0]["title"] == "Test 10"

    def test_escape(self):
        assert self.nm._escape('hello "world"') == 'hello \\"world\\"'
        assert self.nm._escape('path\\to\\file') == 'path\\\\to\\\\file'


# ── ClipboardManager Tests ───────────────────────────────

class TestClipboardManager:
    def setup_method(self):
        self.cm = ClipboardManager()

    def test_init(self):
        assert not self.cm.is_monitoring
        assert len(self.cm.history) == 0

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        ok = await self.cm.set_content("Hello JARVIS")
        assert ok
        content = await self.cm.get_content()
        assert content == "Hello JARVIS"

    @pytest.mark.asyncio
    async def test_clear(self):
        await self.cm.set_content("To be cleared")
        ok = await self.cm.clear()
        assert ok

    def test_monitoring_start_stop(self):
        self.cm.start_monitoring(interval=0.5)
        assert self.cm.is_monitoring
        self.cm.stop_monitoring()
        assert not self.cm.is_monitoring

    def test_on_change_callback(self):
        called = []
        self.cm.on_change(lambda e: called.append(e))
        assert len(called) == 0  # No callback yet

    def test_history_tracking(self):
        from jarvis.os.clipboard import ClipboardEntry
        from datetime import datetime
        for i in range(5):
            self.cm.history.append(ClipboardEntry(content=f"item {i}", content_type="text"))
        history = self.cm.get_history(limit=3)
        assert len(history) == 3
        assert history[0]["content"] == "item 2"


# ── HotkeyManager Tests ──────────────────────────────────

class TestHotkeyManager:
    def setup_method(self):
        self.hm = HotkeyManager()

    def test_register(self):
        ok = self.hm.register("cmd+shift+j", "open_jarvis", "Open JARVIS")
        assert ok
        assert "open_jarvis" in self.hm.hotkeys

    def test_unregister(self):
        self.hm.register("cmd+j", "test_action")
        ok = self.hm.unregister("test_action")
        assert ok
        assert "test_action" not in self.hm.hotkeys

    def test_enable_disable(self):
        self.hm.register("cmd+j", "test_action")
        self.hm.disable("test_action")
        assert not self.hm.hotkeys["test_action"].enabled
        self.hm.enable("test_action")
        assert self.hm.hotkeys["test_action"].enabled

    def test_get_registered(self):
        self.hm.register("cmd+j", "test_action", "Test")
        registered = self.hm.get_registered()
        assert len(registered) == 1
        assert registered[0]["action"] == "test_action"

    def test_listening_start_stop(self):
        self.hm.start_listening()
        assert self.hm.is_listening
        self.hm.stop_listening()
        assert not self.hm.is_listening


# ── MenuBarManager Tests ─────────────────────────────────

class TestMenuBarManager:
    def setup_method(self):
        self.mm = MenuBarManager()

    @pytest.mark.asyncio
    async def test_add_item(self):
        ok = await self.mm.add_item("status", "JARVIS", tooltip="JARVIS Status")
        assert ok
        assert "status" in self.mm.items

    @pytest.mark.asyncio
    async def test_update_item(self):
        await self.mm.add_item("status", "JARVIS")
        ok = await self.mm.update_item("status", "JARVIS ✓", tooltip="Online")
        assert ok
        assert self.mm.items["status"].title == "JARVIS ✓"

    @pytest.mark.asyncio
    async def test_remove_item(self):
        await self.mm.add_item("status", "JARVIS")
        ok = await self.mm.remove_item("status")
        assert ok
        assert "status" not in self.mm.items

    def test_get_items(self):
        items = self.mm.get_items()
        assert isinstance(items, list)


# ── FileWatcher Tests ────────────────────────────────────

class TestFileWatcher:
    def setup_method(self):
        self.fw = FileWatcher()

    @pytest.mark.asyncio
    async def test_watch_directory(self):
        ok = await self.fw.watch("/tmp", key="tmp")
        assert ok
        assert "tmp" in self.fw.watchers

    @pytest.mark.asyncio
    async def test_unwatch_directory(self):
        await self.fw.watch("/tmp", key="tmp")
        ok = await self.fw.unwatch("tmp")
        assert ok
        assert "tmp" not in self.fw.watchers

    def test_get_watched(self):
        watched = self.fw.get_watched()
        assert isinstance(watched, list)

    def test_monitoring_start_stop(self):
        self.fw.start_monitoring(interval=0.5)
        assert self.fw.is_monitoring
        self.fw.stop_monitoring()
        assert not self.fw.is_monitoring

    def test_events_empty(self):
        events = self.fw.get_events()
        assert events == []


# ── OSManager Tests ──────────────────────────────────────

class TestOSManager:
    def setup_method(self):
        self.os = OSManager()

    @pytest.mark.asyncio
    async def test_initialize(self):
        ok = await self.os.initialize()
        assert ok
        assert self.os._initialized

    @pytest.mark.asyncio
    async def test_shutdown(self):
        await self.os.initialize()
        await self.os.shutdown()
        assert not self.os._initialized

    @pytest.mark.asyncio
    async def test_system_info(self):
        info = await self.os.get_system_info()
        assert "platform" in info
        assert "python_version" in info
        assert "pid" in info

    def test_status(self):
        status = self.os.get_status()
        assert "initialized" in status
        assert "notifications_enabled" in status
        assert "clipboard_monitoring" in status
        assert "hotkeys_registered" in status

    def test_hotkey_operations(self):
        ok = self.os.hotkey_register("cmd+j", "test", "Test hotkey")
        assert ok
        registered = self.os.hotkey_list()
        assert len(registered) == 1
        ok = self.os.hotkey_unregister("test")
        assert ok

    def test_menubar_operations(self):
        items = self.os.menubar_list()
        assert isinstance(items, list)

    def test_watcher_operations(self):
        watched = self.os.watched_directories()
        assert isinstance(watched, list)

    def test_file_events(self):
        events = self.os.file_events()
        assert isinstance(events, list)


# ── ActionType Tests ─────────────────────────────────────

class TestActionTypeOS:
    def test_os_action_type_exists(self):
        assert ActionType.OS == "os"

    def test_action_type_from_name(self):
        cm = ComputerManager()
        assert cm._action_type_from_name("os.notify") == "os"
        assert cm._action_type_from_name("os.clipboard_read") == "os"
        assert cm._action_type_from_name("os.system_info") == "os"
