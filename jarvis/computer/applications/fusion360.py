"""Fusion 360 — Autodesk Fusion 360 CAD profile."""

from .base import ApplicationProfile, app_registry

profile = ApplicationProfile(
    name="Fusion 360",
    bundle_id="com.autodesk.fusion360",
    executable="Fusion 360",
    category="cad",

    common_buttons=[
        "New Design", "Open", "Save", "Undo", "Redo",
        "Extrude", "Revolve", "Fillet", "Chamfer",
        "Sketch", "Construct", "Inspect", "Insert",
        "Make", "Automate", "Drawing",
    ],

    common_menus=[
        "File", "Edit", "View", "Solid", "Surface", "Mesh",
        "Sketch", "Construct", "Inspect", "Insert", "Make",
    ],

    common_shortcuts={
        "undo": "Cmd+Z",
        "redo": "Shift+Cmd+Z",
        "save": "Cmd+S",
        "orbit": "Shift+Middle Mouse",
        "pan": "Middle Mouse",
        "zoom": "Scroll Wheel",
        "fit_all": "Home",
        "look_at": "Ctrl+Shift+L",
        "last_command": "Enter",
        "repeat_last": "Enter",
        "new_sketch": "Shift+S",
        "extrude": "E",
        "move": "M",
        "rectangle": "R",
        "circle": "C",
        "line": "L",
        "trim": "T",
        "offset": "O",
        "finish_sketch": "Q",
        "toggle_construction": "X",
    },

    workflows={
        "new_design": ["File menu", "New Design"],
        "save_design": ["Cmd+S"],
        "export_step": ["File menu", "Export", "Select STEP format"],
        "export_stl": ["File menu", "Export", "Select STL format"],
        "create_sketch": ["Press Shift+S or click Sketch button", "Select plane"],
        "extrude": ["Select sketch profile", "Press E", "Enter distance", "Press Enter"],
        "fillet": ["Select edges", "Press the Fillet button", "Enter radius"],
        "measure": ["Inspect menu", "Measure", "Select entity"],
        "take_screenshot": ["View menu", "Capture Image"],
    },

    interaction_notes=(
        "Fusion 360 has a ribbon toolbar at the top with context-sensitive tools. "
        "The timeline at the bottom shows the design history. "
        "The browser tree on the left shows components, bodies, sketches. "
        "Navigation: orbit (Shift+middle mouse), pan (middle mouse), zoom (scroll). "
        "The canvas is the main 3D viewport. "
        "Keyboard shortcuts are essential for efficient use."
    ),
)

app_registry.register(profile)
