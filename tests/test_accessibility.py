"""Tests for v4.4.0 Accessibility Intelligence.

Tests:
  1. UIElement model (creation, matching, clickable/typeable)
  2. AccessibilityTree (add, find, find_elements, stats)
  3. AccessibilityManager (initialization, semantic actions)
  4. ComputerManager semantic actions
  5. Application profiles (registration, lookup)
  6. System workers (application awareness)
  7. macOS provider (structure validation)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from jarvis.computer.accessibility.element import UIElement, ElementType, ElementState
from jarvis.computer.accessibility.tree import AccessibilityTree
from jarvis.computer.accessibility.manager import AccessibilityManager
from jarvis.computer.accessibility.base import AccessibilityProvider
from jarvis.computer.applications.base import ApplicationProfile, ApplicationRegistry, app_registry


# ── UIElement Tests ──────────────────────────────────────────

def test_element_creation():
    """Test creating a UIElement."""
    el = UIElement(
        id="btn_1",
        name="Save",
        role="AXButton",
        type=ElementType.BUTTON,
        states={ElementState.ENABLED},
        bounds={"x": 100, "y": 200, "width": 80, "height": 30},
        app="Finder",
        window="Documents",
    )
    assert el.id == "btn_1"
    assert el.name == "Save"
    assert el.type == ElementType.BUTTON
    assert el.app == "Finder"
    assert el.has_bounds()
    assert el.center() == (140, 215)


def test_element_no_bounds():
    """Test element without bounds."""
    el = UIElement(name="Text", type=ElementType.STATIC_TEXT)
    assert not el.has_bounds()
    assert el.center() is None


def test_element_matches_exact():
    """Test exact name matching."""
    el = UIElement(name="Save", type=ElementType.BUTTON)
    assert el.matches("Save")
    assert not el.matches("Cancel")


def test_element_matches_case_insensitive():
    """Test case-insensitive matching."""
    el = UIElement(name="Export PDF", type=ElementType.BUTTON)
    assert el.matches("export pdf")
    assert el.matches("EXPORT PDF")


def test_element_matches_substring():
    """Test substring matching."""
    el = UIElement(name="Export as PDF", type=ElementType.BUTTON)
    assert el.matches("export")
    assert el.matches("PDF")


def test_element_matches_type():
    """Test type matching."""
    el = UIElement(name="", type=ElementType.BUTTON)
    assert el.matches("button")


def test_element_matches_fuzzy():
    """Test fuzzy matching (spaces removed)."""
    el = UIElement(name="New Folder", type=ElementType.BUTTON)
    assert el.matches("newfolder")


def test_element_is_clickable():
    """Test clickable detection."""
    clickable = UIElement(
        name="OK", type=ElementType.BUTTON,
        states={ElementState.ENABLED},
    )
    assert clickable.is_clickable()

    disabled = UIElement(
        name="OK", type=ElementType.BUTTON,
        states={ElementState.DISABLED},
    )
    assert not disabled.is_clickable()

    text = UIElement(name="Hello", type=ElementType.STATIC_TEXT)
    assert not text.is_clickable()


def test_element_is_typeable():
    """Test typeable detection."""
    field = UIElement(name="Search", type=ElementType.TEXT_FIELD)
    assert field.is_typeable()

    area = UIElement(name="Comments", type=ElementType.TEXT_AREA)
    assert area.is_typeable()

    button = UIElement(name="OK", type=ElementType.BUTTON)
    assert not button.is_typeable()


def test_element_to_dict():
    """Test serialization."""
    el = UIElement(
        id="el_1", name="Close", type=ElementType.BUTTON,
        role="AXButton", states={ElementState.ENABLED},
        bounds={"x": 50, "y": 50, "width": 60, "height": 24},
        app="Finder", window="About",
    )
    d = el.to_dict()
    assert d["id"] == "el_1"
    assert d["name"] == "Close"
    assert d["type"] == ElementType.BUTTON
    assert "enabled" in d["states"]
    assert d["app"] == "Finder"


def test_element_summary():
    """Test summary output."""
    el = UIElement(
        name="OK", type=ElementType.BUTTON,
        bounds={"x": 0, "y": 0, "width": 80, "height": 30},
    )
    s = el.summary()
    assert "button" in s
    assert '"OK"' in s


# ── AccessibilityTree Tests ─────────────────────────────────

def test_tree_add_and_count():
    """Test adding elements and counting."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="OK", type=ElementType.BUTTON))
    tree.add(UIElement(id="2", name="Cancel", type=ElementType.BUTTON))
    tree.add(UIElement(id="3", name="Search", type=ElementType.TEXT_FIELD))
    assert tree.element_count == 3
    assert len(tree) == 3


def test_tree_find_exact():
    """Test finding elements by exact name."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="Save", type=ElementType.BUTTON))
    tree.add(UIElement(id="2", name="Cancel", type=ElementType.BUTTON))

    found = tree.find("Save")
    assert found is not None
    assert found.name == "Save"


def test_tree_find_substring():
    """Test finding elements by substring."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="Export as PDF", type=ElementType.BUTTON))

    found = tree.find("PDF")
    assert found is not None
    assert "PDF" in found.name


def test_tree_find_type():
    """Test finding elements by type."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="", type=ElementType.BUTTON))
    tree.add(UIElement(id="2", name="", type=ElementType.TEXT_FIELD))

    found = tree.find("button")
    assert found is not None
    assert found.type == ElementType.BUTTON


def test_tree_find_not_found():
    """Test finding non-existent element."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="OK", type=ElementType.BUTTON))
    assert tree.find("NonExistent") is None


def test_tree_find_elements_filtered():
    """Test filtered search."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="Save", type=ElementType.BUTTON, app="Finder"))
    tree.add(UIElement(id="2", name="Open", type=ElementType.BUTTON, app="Finder"))
    tree.add(UIElement(id="3", name="Copy", type=ElementType.BUTTON, app="TextEdit"))

    buttons = tree.find_elements(type=ElementType.BUTTON)
    assert len(buttons) == 3

    finder_buttons = tree.find_elements(app="Finder")
    assert len(finder_buttons) == 2


def test_tree_find_elements_clickable_only():
    """Test clickable-only filter."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="OK", type=ElementType.BUTTON,
                       states={ElementState.ENABLED}))
    tree.add(UIElement(id="2", name="Hello", type=ElementType.STATIC_TEXT))
    tree.add(UIElement(id="3", name="Search", type=ElementType.TEXT_FIELD))

    clickable = tree.find_elements(clickable_only=True)
    assert len(clickable) == 1  # only button is clickable (TEXT_FIELD is typeable, not clickable)


def test_tree_get_buttons():
    """Test get_buttons shortcut."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="OK", type=ElementType.BUTTON))
    tree.add(UIElement(id="2", name="Cancel", type=ElementType.BUTTON))
    tree.add(UIElement(id="3", name="Search", type=ElementType.TEXT_FIELD))
    assert len(tree.get_buttons()) == 2


def test_tree_get_text_fields():
    """Test get_text_fields shortcut."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="Search", type=ElementType.TEXT_FIELD))
    tree.add(UIElement(id="2", name="Comments", type=ElementType.TEXT_AREA))
    tree.add(UIElement(id="3", name="OK", type=ElementType.BUTTON))
    assert len(tree.get_text_fields()) == 2


def test_tree_stats():
    """Test tree statistics."""
    tree = AccessibilityTree(app="Finder", window="Documents")
    tree.add(UIElement(id="1", name="OK", type=ElementType.BUTTON))
    tree.add(UIElement(id="2", name="Cancel", type=ElementType.BUTTON))
    tree.add(UIElement(id="3", name="Search", type=ElementType.TEXT_FIELD))

    stats = tree.stats()
    assert stats["total"] == 3
    assert stats["app"] == "Finder"
    assert stats["buttons"] == 2
    assert stats["text_fields"] == 1


def test_tree_to_context():
    """Test LLM context generation."""
    tree = AccessibilityTree(app="Finder", window="Documents")
    tree.add(UIElement(id="1", name="OK", type=ElementType.BUTTON))
    tree.add(UIElement(id="2", name="Search", type=ElementType.TEXT_FIELD))

    ctx = tree.to_context()
    assert "Finder" in ctx
    assert "Documents" in ctx
    assert "BUTTON" in ctx or "button" in ctx


def test_tree_find_all():
    """Test find_all returns multiple matches."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="Save", type=ElementType.BUTTON))
    tree.add(UIElement(id="2", name="Save As", type=ElementType.BUTTON))
    tree.add(UIElement(id="3", name="Cancel", type=ElementType.BUTTON))

    results = tree.find_all("Save")
    assert len(results) == 2


def test_tree_iter():
    """Test iteration over tree."""
    tree = AccessibilityTree()
    tree.add(UIElement(id="1", name="A"))
    tree.add(UIElement(id="2", name="B"))
    names = [el.name for el in tree]
    assert names == ["A", "B"]


# ── Application Profiles Tests ──────────────────────────────

def test_app_profile_creation():
    """Test creating an application profile."""
    profile = ApplicationProfile(
        name="TestApp",
        bundle_id="com.test.app",
        executable="TestApp",
        category="editor",
        common_buttons=["Save", "Open"],
        common_shortcuts={"save": "Cmd+S"},
    )
    assert profile.name == "TestApp"
    assert profile.category == "editor"
    assert "Save" in profile.common_buttons


def test_app_profile_describe():
    """Test profile description generation."""
    profile = ApplicationProfile(
        name="Finder",
        category="file_manager",
        common_buttons=["New Folder", "Open"],
        common_shortcuts={"new_folder": "Shift+Cmd+N"},
    )
    desc = profile.describe()
    assert "Finder" in desc
    assert "file_manager" in desc
    assert "New Folder" in desc


def test_app_registry_register_and_get():
    """Test registering and retrieving profiles."""
    registry = ApplicationRegistry()
    profile = ApplicationProfile(name="MyApp", executable="MyApp")
    registry.register(profile)

    found = registry.get("myapp")
    assert found is not None
    assert found.name == "MyApp"


def test_app_registry_case_insensitive():
    """Test case-insensitive lookup."""
    registry = ApplicationRegistry()
    registry.register(ApplicationProfile(name="Finder", executable="Finder"))

    assert registry.get("finder") is not None
    assert registry.get("FINDER") is not None


def test_app_registry_list():
    """Test listing registered apps."""
    registry = ApplicationRegistry()
    registry.register(ApplicationProfile(name="Alpha", executable="Alpha"))
    registry.register(ApplicationProfile(name="Beta", executable="Beta"))

    apps = registry.list_apps()
    assert "alpha" in apps
    assert "beta" in apps


def test_app_registry_find_by_bundle():
    """Test finding by bundle ID."""
    registry = ApplicationRegistry()
    registry.register(ApplicationProfile(
        name="Finder", bundle_id="com.apple.finder",
    ))

    found = registry.find_by_bundle("com.apple.finder")
    assert found is not None
    assert found.name == "Finder"


def test_app_registry_find_by_executable():
    """Test finding by executable name."""
    registry = ApplicationRegistry()
    registry.register(ApplicationProfile(
        name="Chrome", executable="Google Chrome",
    ))

    found = registry.find_by_executable("Google Chrome")
    assert found is not None


def test_builtin_profiles_registered():
    """Test that built-in profiles are auto-registered."""
    # Import the profiles module to trigger registration
    from jarvis.computer.applications import finder, terminal, vscode, chrome, fusion360, blender

    assert app_registry.get("Finder") is not None
    assert app_registry.get("Terminal") is not None
    assert app_registry.get("Code") is not None
    assert app_registry.get("Google Chrome") is not None
    assert app_registry.get("Fusion 360") is not None
    assert app_registry.get("Blender") is not None


# ── AccessibilityManager Tests ──────────────────────────────

def test_manager_initialization():
    """Test manager can be created."""
    manager = AccessibilityManager()
    assert not manager._initialized


@pytest.mark.asyncio
async def test_manager_init_macos():
    """Test manager initializes on macOS."""
    manager = AccessibilityManager()
    with patch("sys.platform", "darwin"):
        result = await manager.initialize()
        assert result["ok"]
        assert result["platform"] == "macos"
        assert manager._initialized


@pytest.mark.asyncio
async def test_manager_not_initialized_error():
    """Test calling methods before initialization raises error."""
    manager = AccessibilityManager()
    with pytest.raises(RuntimeError, match="not initialized"):
        await manager.get_tree()


@pytest.mark.asyncio
async def test_manager_double_init():
    """Test double initialization is idempotent."""
    manager = AccessibilityManager()
    with patch("sys.platform", "darwin"):
        await manager.initialize()
        result = await manager.initialize()
        assert result["ok"]


@pytest.mark.asyncio
async def test_manager_find_element():
    """Test finding element through manager."""
    manager = AccessibilityManager()
    with patch("sys.platform", "darwin"):
        await manager.initialize()

        # Mock the provider
        mock_elements = [
            UIElement(id="1", name="Save", type=ElementType.BUTTON),
            UIElement(id="2", name="Cancel", type=ElementType.BUTTON),
        ]
        manager._provider.get_elements = AsyncMock(return_value=mock_elements)
        manager._provider.get_active_window = AsyncMock(return_value={"app": "Finder", "title": "Test"})

        # Force cache refresh
        manager._last_tree = None
        element = await manager.find("Save")
        assert element is not None
        assert element.name == "Save"


@pytest.mark.asyncio
async def test_manager_click_element():
    """Test clicking element through manager."""
    manager = AccessibilityManager()
    with patch("sys.platform", "darwin"):
        await manager.initialize()

        element = UIElement(
            id="1", name="OK", type=ElementType.BUTTON,
            bounds={"x": 100, "y": 200, "width": 80, "height": 30},
        )
        manager._provider.get_elements = AsyncMock(return_value=[element])
        manager._provider.get_active_window = AsyncMock(return_value={"app": "Finder", "title": "Test"})
        manager._provider.click_element = AsyncMock(return_value={"ok": True})

        manager._last_tree = None
        result = await manager.click("OK")
        assert result["ok"]
        assert result["element"] == "OK"


@pytest.mark.asyncio
async def test_manager_click_not_found():
    """Test clicking non-existent element returns error."""
    manager = AccessibilityManager()
    with patch("sys.platform", "darwin"):
        await manager.initialize()

        manager._provider.get_elements = AsyncMock(return_value=[])
        manager._provider.get_active_window = AsyncMock(return_value={"app": "Finder", "title": "Test"})

        manager._last_tree = None
        result = await manager.click("NonExistent")
        assert not result["ok"]
        assert "No element found" in result["error"]


@pytest.mark.asyncio
async def test_manager_type_into():
    """Test typing into element through manager."""
    manager = AccessibilityManager()
    with patch("sys.platform", "darwin"):
        await manager.initialize()

        field = UIElement(
            id="1", name="Search", type=ElementType.TEXT_FIELD,
            bounds={"x": 50, "y": 50, "width": 200, "height": 24},
        )
        manager._provider.get_elements = AsyncMock(return_value=[field])
        manager._provider.get_active_window = AsyncMock(return_value={"app": "Finder", "title": "Test"})
        manager._provider.type_text = AsyncMock(return_value={"ok": True})

        manager._last_tree = None
        result = await manager.type_into("Search", "hello world")
        assert result["ok"]
        assert result["element"] == "Search"


@pytest.mark.asyncio
async def test_manager_type_into_non_typeable():
    """Test typing into non-typeable element returns error."""
    manager = AccessibilityManager()
    with patch("sys.platform", "darwin"):
        await manager.initialize()

        button = UIElement(id="1", name="OK", type=ElementType.BUTTON)
        manager._provider.get_elements = AsyncMock(return_value=[button])
        manager._provider.get_active_window = AsyncMock(return_value={"app": "Finder", "title": "Test"})

        manager._last_tree = None
        result = await manager.type_into("OK", "hello")
        assert not result["ok"]
        assert "not a text field" in result["error"]


# ── AccessibilityProvider Abstract Tests ────────────────────

def test_provider_is_abstract():
    """Test that AccessibilityProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AccessibilityProvider()


# ── Integration: ComputerManager Semantic Actions ──────────

@pytest.mark.asyncio
async def test_computer_manager_has_accessibility_actions():
    """Test that ComputerManager registers accessibility actions."""
    from jarvis.computer.manager import ComputerManager
    manager = ComputerManager()
    actions = [a["name"] for a in manager.get_actions()]

    assert "accessibility.tree" in actions
    assert "accessibility.find" in actions
    assert "accessibility.click" in actions
    assert "accessibility.type_into" in actions
    assert "accessibility.activate" in actions
    assert "accessibility.apps" in actions
    assert "accessibility.summary" in actions
