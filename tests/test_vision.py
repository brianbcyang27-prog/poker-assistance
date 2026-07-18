"""Tests for v4.5.0 Vision Core Update.

Tests:
  1. Screenshot capture system
  2. Vision provider base classes
  3. Vision analyzer
  4. Object detector
  5. Grounding engine
  6. Vision memory
  7. VisionManager
  8. ComputerManager vision actions
  9. Multi-perception smart actions
  10. Security/permission integration
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from jarvis.vision.screenshot import ScreenCapture, CapturedScreenshot, ScreenRegion
from jarvis.vision.providers.base import VisionProvider, VisionResult, DetectedObject
from jarvis.vision.analyzer import VisionAnalyzer, ScreenAnalysis
from jarvis.vision.detector import ObjectDetector
from jarvis.vision.grounding import GroundingEngine, GroundedAction
from jarvis.vision.memory import VisionMemory, VisualWorkflow, ScreenshotRecord
from jarvis.vision.manager import VisionManager


# ── Screenshot Tests ────────────────────────────────────────

def test_screenshot_region_creation():
    """Test ScreenRegion dataclass."""
    r = ScreenRegion(x=100, y=200, width=800, height=600)
    assert r.is_valid()
    assert r.to_dict() == {"x": 100, "y": 200, "width": 800, "height": 600}


def test_screenshot_region_invalid():
    """Test invalid ScreenRegion."""
    r = ScreenRegion(x=0, y=0, width=0, height=0)
    assert not r.is_valid()


def test_captured_screenshot_creation():
    """Test CapturedScreenshot dataclass."""
    s = CapturedScreenshot(
        id="ss_001",
        path="/tmp/test.png",
        timestamp=1000.0,
        application="Finder",
        width=1920,
        height=1080,
        file_size=50000,
    )
    d = s.to_dict()
    assert d["id"] == "ss_001"
    assert d["application"] == "Finder"
    assert d["width"] == 1920


def test_screen_capture_init():
    """Test ScreenCapture initialization."""
    capture = ScreenCapture()
    assert capture._dir.endswith("jarvis_screenshots") or "screenshots" in capture._dir


# ── Vision Provider Tests ──────────────────────────────────

def test_detected_object_creation():
    """Test DetectedObject dataclass."""
    obj = DetectedObject(
        type="button",
        name="Export",
        x=500,
        y=200,
        width=80,
        height=30,
        confidence=0.92,
    )
    assert obj.type == "button"
    assert obj.name == "Export"
    assert obj.center() == (500, 200)
    d = obj.to_dict()
    assert d["confidence"] == 0.92


def test_vision_result_creation():
    """Test VisionResult dataclass."""
    result = VisionResult(
        application="Finder",
        screen_description="Finder window showing documents",
        provider="ollama",
        model="qwen2.5-vl",
    )
    assert result.application == "Finder"
    assert result.success is True


def test_vision_result_find_objects():
    """Test finding objects in VisionResult."""
    result = VisionResult(
        objects=[
            DetectedObject(type="button", name="Save", confidence=0.9),
            DetectedObject(type="button", name="Cancel", confidence=0.8),
            DetectedObject(type="menu", name="File", confidence=0.95),
            DetectedObject(type="text_field", name="Search", confidence=0.7),
        ]
    )

    buttons = result.find_objects("button")
    assert len(buttons) == 2

    save = result.find_objects("Save")
    assert len(save) == 1
    assert save[0].name == "Save"

    best = result.find_best_match("Cancel")
    assert best is not None
    assert best.name == "Cancel"


def test_vision_result_no_match():
    """Test no match returns None."""
    result = VisionResult(objects=[])
    assert result.find_best_match("anything") is None


def test_vision_provider_is_abstract():
    """Test that VisionProvider cannot be instantiated."""
    with pytest.raises(TypeError):
        VisionProvider()


# ── Analyzer Tests ──────────────────────────────────────────

def test_screen_analysis_creation():
    """Test ScreenAnalysis dataclass."""
    analysis = ScreenAnalysis(
        application="Finder",
        description="Documents folder",
        objects=[
            DetectedObject(type="button", name="New Folder"),
            DetectedObject(type="button", name="Open"),
            DetectedObject(type="menu", name="File"),
        ],
    )
    assert analysis.application == "Finder"
    assert len(analysis.objects) == 3


def test_screen_analysis_classifies_objects():
    """Test object classification into buttons/menus/fields."""
    analysis = ScreenAnalysis(
        objects=[
            DetectedObject(type="button", name="OK"),
            DetectedObject(type="button", name="Cancel"),
            DetectedObject(type="menu", name="File"),
            DetectedObject(type="text_field", name="Search"),
            DetectedObject(type="text_area", name="Comments"),
        ]
    )
    analysis.buttons = [o for o in analysis.objects if "button" in o.type]
    analysis.menus = [o for o in analysis.objects if "menu" in o.type]
    analysis.text_fields = [o for o in analysis.objects if "text" in o.type]

    assert len(analysis.buttons) == 2
    assert len(analysis.menus) == 1
    assert len(analysis.text_fields) == 2


def test_screen_analysis_to_context():
    """Test LLM context generation."""
    analysis = ScreenAnalysis(
        application="Finder",
        description="Documents folder",
        objects=[DetectedObject(type="button", name="Save")],
        buttons=[DetectedObject(type="button", name="Save")],
    )
    ctx = analysis.to_context()
    assert "Finder" in ctx
    assert "Documents folder" in ctx
    assert "Save" in ctx


def test_screen_analysis_to_dict():
    """Test serialization."""
    analysis = ScreenAnalysis(
        application="Finder",
        description="Test",
        objects=[DetectedObject(type="button", name="OK")],
    )
    d = analysis.to_dict()
    assert d["application"] == "Finder"
    assert d["object_count"] == 1


def test_analyzer_builds_analysis():
    """Test VisionAnalyzer builds ScreenAnalysis from VisionResult."""
    result = VisionResult(
        application="Finder",
        screen_description="A Finder window",
        objects=[
            DetectedObject(type="button", name="OK", confidence=0.9),
            DetectedObject(type="menu_item", name="File", confidence=0.8),
        ],
    )
    analyzer = VisionAnalyzer()
    analysis = analyzer._build_analysis(result)
    assert analysis.application == "Finder"
    assert len(analysis.objects) == 2
    assert len(analysis.buttons) == 1
    assert len(analysis.menus) == 1


# ── Detector Tests ──────────────────────────────────────────

def test_detector_find():
    """Test ObjectDetector.find."""
    result = VisionResult(
        objects=[
            DetectedObject(type="button", name="Export", confidence=0.9),
            DetectedObject(type="button", name="Import", confidence=0.8),
        ]
    )
    detector = ObjectDetector(result)
    found = detector.find("Export")
    assert found is not None
    assert found.name == "Export"


def test_detector_find_all():
    """Test ObjectDetector.find_all."""
    result = VisionResult(
        objects=[
            DetectedObject(type="button", name="OK", confidence=0.9),
            DetectedObject(type="button", name="Cancel", confidence=0.8),
            DetectedObject(type="menu", name="File", confidence=0.95),
        ]
    )
    detector = ObjectDetector(result)
    buttons = detector.find_all(type="button")
    assert len(buttons) == 2


def test_detector_find_buttons():
    """Test ObjectDetector.find_buttons."""
    result = VisionResult(
        objects=[
            DetectedObject(type="button", name="Save", confidence=0.9),
            DetectedObject(type="text_field", name="Search", confidence=0.8),
        ]
    )
    detector = ObjectDetector(result)
    buttons = detector.find_buttons()
    assert len(buttons) == 1
    assert buttons[0].name == "Save"


def test_detector_nearest_to():
    """Test nearest_to finds closest object."""
    result = VisionResult(
        objects=[
            DetectedObject(type="button", name="A", x=100, y=100),
            DetectedObject(type="button", name="B", x=500, y=500),
            DetectedObject(type="button", name="C", x=150, y=150),
        ]
    )
    detector = ObjectDetector(result)
    nearest = detector.nearest_to(120, 120)
    assert nearest.name == "A"


def test_detector_highest_confidence():
    """Test highest_confidence filtering."""
    result = VisionResult(
        objects=[
            DetectedObject(type="button", name="A", confidence=0.9),
            DetectedObject(type="button", name="B", confidence=0.3),
            DetectedObject(type="button", name="C", confidence=0.8),
        ]
    )
    detector = ObjectDetector(result)
    high = detector.highest_confidence(min_confidence=0.5)
    assert len(high) == 2
    assert high[0].confidence >= high[1].confidence


def test_detector_interactive_elements():
    """Test interactive_elements returns buttons, menus, fields."""
    result = VisionResult(
        objects=[
            DetectedObject(type="button", name="OK"),
            DetectedObject(type="text", name="Label"),
            DetectedObject(type="menu", name="File"),
            DetectedObject(type="text_field", name="Search"),
            DetectedObject(type="image", name="Logo"),
        ]
    )
    detector = ObjectDetector(result)
    interactive = detector.interactive_elements()
    assert len(interactive) == 3  # button, menu, text_field


def test_detector_summary():
    """Test detector summary statistics."""
    result = VisionResult(
        objects=[
            DetectedObject(type="button", name="A", confidence=0.9),
            DetectedObject(type="button", name="B", confidence=0.8),
            DetectedObject(type="menu", name="File", confidence=0.95),
        ]
    )
    detector = ObjectDetector(result)
    s = detector.summary()
    assert s["total"] == 3
    assert s["types"]["button"] == 2


# ── Grounding Tests ─────────────────────────────────────────

def test_grounding_click_vision():
    """Test grounding a click via vision detection."""
    engine = GroundingEngine()
    objects = [
        DetectedObject(type="button", name="Export", x=500, y=200, confidence=0.9),
    ]
    action = engine.ground_click("Export", detected_objects=objects)
    assert action.action_type == "click"
    assert action.method == "vision"
    assert action.x == 500
    assert action.y == 200
    assert action.confidence == 0.9


def test_grounding_click_accessibility():
    """Test grounding a click via accessibility element."""
    engine = GroundingEngine()
    mock_element = MagicMock()
    mock_element.name = "Export"
    mock_element.type = "button"
    mock_element.has_bounds.return_value = True
    mock_element.center.return_value = (500, 200)

    action = engine.ground_click("Export", element=mock_element)
    assert action.method == "accessibility"
    assert action.x == 500
    assert action.confidence == 0.95


def test_grounding_click_unknown():
    """Test grounding with no matches."""
    engine = GroundingEngine()
    action = engine.ground_click("NonExistent")
    assert action.method == "unknown"
    assert action.confidence == 0.0


def test_grounding_type_vision():
    """Test grounding a type action via vision."""
    engine = GroundingEngine()
    objects = [
        DetectedObject(type="text_field", name="Search", x=300, y=100, confidence=0.85),
    ]
    action = engine.ground_type("Search", "hello", detected_objects=objects)
    assert action.action_type == "type_into"
    assert action.method == "vision"
    assert action.text == "hello"
    assert action.x == 300


def test_grounding_type_accessibility():
    """Test grounding a type action via accessibility."""
    engine = GroundingEngine()
    mock_element = MagicMock()
    mock_element.name = "Search"
    mock_element.type = "text_field"
    mock_element.center.return_value = (300, 100)

    action = engine.ground_type("Search", "hello", element=mock_element)
    assert action.method == "accessibility"
    assert action.text == "hello"


# ── Vision Memory Tests ─────────────────────────────────────

def test_vision_memory_record_screenshot():
    """Test recording screenshots."""
    memory = VisionMemory()
    screenshot = CapturedScreenshot(id="ss_001", path="/tmp/test.png", application="Finder")
    record = memory.record_screenshot(screenshot)
    assert record.id == "ss_001"
    assert record.application == "Finder"
    assert len(memory.get_recent_screenshots()) == 1


def test_vision_memory_object_cache():
    """Test object location caching."""
    memory = VisionMemory()
    screenshot = CapturedScreenshot(id="ss_001", path="/tmp/test.png", application="Finder")
    analysis = ScreenAnalysis(
        objects=[DetectedObject(type="button", name="Export", x=500, y=200)],
    )
    memory.record_screenshot(screenshot, analysis)

    cached = memory.find_cached_location("Finder", "Export")
    assert cached is not None
    assert cached["x"] == 500
    assert cached["y"] == 200


def test_vision_memory_workflows():
    """Test workflow storage."""
    memory = VisionMemory()
    workflow = VisualWorkflow(
        id="wf_001",
        name="Export Fusion Model",
        application="Fusion 360",
        steps=[
            {"description": "Click File menu", "action": "click", "target": "File"},
            {"description": "Click Export", "action": "click", "target": "Export"},
        ],
    )
    memory.save_workflow(workflow)
    found = memory.get_workflow("wf_001")
    assert found is not None
    assert found.name == "Export Fusion Model"


def test_vision_memory_find_workflows():
    """Test finding workflows by app."""
    memory = VisionMemory()
    memory.save_workflow(VisualWorkflow(id="wf_1", name="Export", application="Fusion 360"))
    memory.save_workflow(VisualWorkflow(id="wf_2", name="Render", application="Blender"))

    results = memory.find_workflows(app="Fusion 360")
    assert len(results) == 1
    assert results[0].name == "Export"


def test_vision_memory_workflow_completion():
    """Test workflow success/fail tracking."""
    memory = VisionMemory()
    wf = VisualWorkflow(id="wf_1", name="Test")
    memory.save_workflow(wf)

    memory.complete_workflow("wf_1", success=True)
    memory.complete_workflow("wf_1", success=True)
    memory.complete_workflow("wf_1", success=False)

    found = memory.get_workflow("wf_1")
    assert found.success_count == 2
    assert found.fail_count == 1
    assert found.success_rate() == 2 / 3


def test_vision_memory_stats():
    """Test memory statistics."""
    memory = VisionMemory()
    screenshot = CapturedScreenshot(id="ss_001", path="/tmp/t.png", application="Finder")
    analysis = ScreenAnalysis(
        objects=[DetectedObject(type="button", name="OK")],
    )
    memory.record_screenshot(screenshot, analysis)
    memory.save_workflow(VisualWorkflow(id="wf_1", name="Test"))

    stats = memory.get_stats()
    assert stats["screenshots"] == 1
    assert stats["workflows"] == 1
    assert "finder" in stats["cached_apps"]


def test_vision_memory_clear():
    """Test clearing memory."""
    memory = VisionMemory()
    memory.record_screenshot(CapturedScreenshot(id="ss_001"))
    memory.save_workflow(VisualWorkflow(id="wf_1"))
    memory.clear()
    assert memory.get_stats()["screenshots"] == 0
    assert memory.get_stats()["workflows"] == 0


# ── VisionManager Tests ─────────────────────────────────────

def test_manager_creation():
    """Test VisionManager creation."""
    manager = VisionManager()
    assert not manager._initialized


@pytest.mark.asyncio
async def test_manager_initialize():
    """Test VisionManager initialization."""
    manager = VisionManager()
    with patch("jarvis.vision.providers.get_vision_provider", return_value=None):
        result = await manager.initialize()
        assert result["ok"]


@pytest.mark.asyncio
async def test_manager_find_object_no_analysis():
    """Test find_object without prior analysis."""
    manager = VisionManager()
    with patch("jarvis.vision.providers.get_vision_provider", return_value=None):
        await manager.initialize()

    # Without provider, analyze returns empty analysis
    obj = await manager.find_object("anything")
    assert obj is None


@pytest.mark.asyncio
async def test_manager_health_check():
    """Test health check without provider."""
    manager = VisionManager()
    result = await manager.health_check()
    assert result["ok"] is False


def test_manager_stats():
    """Test manager statistics."""
    manager = VisionManager()
    stats = manager.get_stats()
    assert "initialized" in stats
    assert "memory" in stats


# ── ComputerManager Vision Actions Tests ────────────────────

@pytest.mark.asyncio
async def test_computer_manager_has_vision_actions():
    """Test ComputerManager registers vision actions."""
    from jarvis.computer.manager import ComputerManager
    manager = ComputerManager()
    actions = [a["name"] for a in manager.get_actions()]

    assert "vision.capture" in actions
    assert "vision.analyze" in actions
    assert "vision.find" in actions
    assert "vision.describe" in actions
    assert "vision.locate" in actions
    assert "vision.click" in actions
    assert "vision.health" in actions
    assert "smart.click" in actions
    assert "smart.type" in actions


@pytest.mark.asyncio
async def test_computer_manager_vision_health():
    """Test vision health action."""
    from jarvis.computer.manager import ComputerManager
    manager = ComputerManager()
    result = await manager._vision_health()
    assert "ok" in result


# ── ActionType Tests ────────────────────────────────────────

def test_action_type_vision():
    """Test VISION action type exists."""
    from jarvis.computer.actions import ActionType
    assert hasattr(ActionType, 'VISION')
    assert ActionType.VISION == "vision"


def test_action_type_accessibility():
    """Test ACCESSIBILITY action type exists."""
    from jarvis.computer.actions import ActionType
    assert hasattr(ActionType, 'ACCESSIBILITY')
    assert ActionType.ACCESSIBILITY == "accessibility"


# ── GroundedAction Tests ────────────────────────────────────

def test_grounded_action_to_dict():
    """Test GroundedAction serialization."""
    action = GroundedAction(
        action_type="click",
        method="vision",
        x=500,
        y=200,
        element_name="Export",
        confidence=0.9,
    )
    d = action.to_dict()
    assert d["action_type"] == "click"
    assert d["method"] == "vision"
    assert d["x"] == 500
    assert d["confidence"] == 0.9


# ── VisualWorkflow Tests ────────────────────────────────────

def test_visual_workflow_to_dict():
    """Test VisualWorkflow serialization."""
    wf = VisualWorkflow(
        id="wf_1",
        name="Test",
        application="Finder",
        steps=[{"action": "click", "target": "OK"}],
    )
    d = wf.to_dict()
    assert d["name"] == "Test"
    assert d["step_count"] == 1


def test_visual_workflow_success_rate():
    """Test workflow success rate calculation."""
    wf = VisualWorkflow(id="wf_1", name="Test")
    wf.success_count = 8
    wf.fail_count = 2
    assert wf.success_rate() == 0.8

    wf_empty = VisualWorkflow(id="wf_2")
    assert wf_empty.success_rate() == 0.0
