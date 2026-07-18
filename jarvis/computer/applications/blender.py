"""Blender — 3D creation suite profile."""

from .base import ApplicationProfile, app_registry

profile = ApplicationProfile(
    name="Blender",
    bundle_id="org.blenderfoundation.blender",
    executable="Blender",
    category="3d_editor",

    common_buttons=[
        "Add", "Object", "Mesh", "Curve", "Surface",
        "Render", "Play", "Stop", "Pause",
    ],

    common_menus=[
        "File", "Edit", "Render", "Window", "Help",
    ],

    common_shortcuts={
        "undo": "Cmd+Z",
        "redo": "Shift+Cmd+Z",
        "save": "Cmd+S",
        "save_as": "Shift+Cmd+S",
        "new_file": "Cmd+N",
        "open_file": "Cmd+O",
        "quit": "Cmd+Q",
        "toggle_object_mode": "Tab",
        "add_mesh_cube": "Shift+A → Mesh → Cube",
        "add_mesh_sphere": "Shift+A → Mesh → UV Sphere",
        "grab_move": "G",
        "rotate": "R",
        "scale": "S",
        "delete": "X",
        "duplicate": "Shift+D",
        "edit_mode": "Tab",
        "object_mode": "Tab",
        "toggle_xray": "Alt+Z",
        "frame_all": "Home",
        "render_image": "F12",
        "render_animation": "Ctrl+F12",
        "view_persp_ortho": "Numpad 5",
        "view_front": "Numpad 1",
        "view_right": "Numpad 3",
        "view_top": "Numpad 7",
        "toggle_sidebar": "N",
        "toggle_properties": "Ctrl+Alt+P",  # varies by version
        "circle_select": "C",
        "box_select": "B",
        "knife_tool": "K",
        "loop_cut": "Ctrl+R",
        "extrude": "E",
        "inset": "I",
        "bevel": "Ctrl+B",
        "merge": "M",
        "shade_smooth": "Right-click → Shade Smooth",
    },

    workflows={
        "new_scene": ["File menu", "New", "General"],
        "save_file": ["Cmd+S"],
        "export_obj": ["File menu", "Export", "Wavefront (.obj)"],
        "export_gltf": ["File menu", "Export", "glTF 2.0 (.glb/.gltf)"],
        "export_stl": ["File menu", "Export", "STL (.stl)"],
        "add_cube": ["Shift+A", "Mesh", "Cube"],
        "add_light": ["Shift+A", "Light", "Point"],
        "add_camera": ["Shift+A", "Camera"],
        "render_frame": ["F12"],
        "toggle_rendered_view": ["Z", "Rendered"],
        "set_origin": ["Right-click", "Set Origin"],
        "parent_object": ["Select child", "Shift+Select parent", "Ctrl+P"],
    },

    interaction_notes=(
        "Blender has a highly customizable UI with multiple editors. "
        "The 3D Viewport is the main workspace. "
        "Properties panel (right side) shows context-sensitive settings. "
        "Outliner (top right) shows the scene hierarchy. "
        "Timeline (bottom) for animation. "
        "Blender uses a non-standard UI toolkit (not native macOS) — "
        "accessibility tree may be limited. Use keyboard shortcuts when possible."
    ),
)

app_registry.register(profile)
