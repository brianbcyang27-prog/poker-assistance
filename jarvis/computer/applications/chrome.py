"""Chrome — Google Chrome browser profile."""

from .base import ApplicationProfile, app_registry

profile = ApplicationProfile(
    name="Google Chrome",
    bundle_id="com.google.Chrome",
    executable="Google Chrome",
    category="browser",

    common_buttons=[
        "Back", "Forward", "Reload", "Home",
        "New Tab", "New Window", "Bookmarks",
    ],

    common_menus=[
        "Chrome", "File", "Edit", "View", "History", "Bookmarks",
        "Profiles", "Window", "Help",
    ],

    common_shortcuts={
        "new_tab": "Cmd+T",
        "new_window": "Cmd+N",
        "close_tab": "Cmd+W",
        "reopen_tab": "Shift+Cmd+T",
        "address_bar": "Cmd+L",
        "search": "Cmd+F",
        "find_next": "Cmd+G",
        "find_previous": "Shift+Cmd+G",
        "reload": "Cmd+R",
        "hard_reload": "Shift+Cmd+R",
        "developer_tools": "Cmd+Option+I",
        "inspect_element": "Cmd+Option+C",
        "toggle_fullscreen": "Ctrl+Cmd+F",
        "zoom_in": "Cmd+=",
        "zoom_out": "Cmd+-",
        "zoom_reset": "Cmd+0",
        "select_tab_1": "Cmd+1",
        "select_tab_8": "Cmd+8",
        "select_last_tab": "Cmd+9",
        "print": "Cmd+P",
        "save_page": "Cmd+S",
        "show_downloads": "Shift+Cmd+J",
        "toggle_bookmarks": "Shift+Cmd+B",
        "focus_console": "Cmd+Option+J",
        "view_source": "Cmd+U",
    },

    workflows={
        "navigate": ["Click address bar (Cmd+L)", "Type URL", "Press Enter"],
        "search": ["Click address bar (Cmd+L)", "Type search query", "Press Enter"],
        "open_devtools": ["Cmd+Option+I"],
        "inspect_element": ["Right-click element", "Select Inspect"],
        "take_screenshot": ["Cmd+Shift+S (if extension installed)"],
        "clear_cache": ["Shift+Cmd+R", "Open DevTools", "Right-click reload", "Empty Cache and Hard Reload"],
    },

    interaction_notes=(
        "Chrome has tabs at the top, address bar, and extension icons. "
        "The DevTools (Cmd+Option+I) expose the DOM tree, console, network, etc. "
        "For web automation, prefer DevTools over accessibility tree. "
        "Each tab is a separate browsing context. "
        "Extensions may add toolbar buttons and context menu items."
    ),
)

app_registry.register(profile)
