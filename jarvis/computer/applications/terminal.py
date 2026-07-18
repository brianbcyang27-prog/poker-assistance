"""Terminal — macOS Terminal.app profile."""

from .base import ApplicationProfile, app_registry

profile = ApplicationProfile(
    name="Terminal",
    bundle_id="com.apple.Terminal",
    executable="Terminal",
    category="terminal",

    common_buttons=[
        "New Window", "New Tab", "Close Window", "Close Tab",
    ],

    common_menus=["Shell", "Edit", "View", "Window", "Help"],

    common_shortcuts={
        "new_window": "Cmd+N",
        "new_tab": "Cmd+T",
        "close_tab": "Cmd+W",
        "close_window": "Shift+Cmd+W",
        "select_tab_1": "Cmd+1",
        "select_tab_2": "Cmd+2",
        "select_tab_3": "Cmd+3",
        "clear_screen": "Cmd+K",
        "search": "Cmd+F",
        "split_pane_vertical": "Cmd+D",
        "split_pane_horizontal": "Shift+Cmd+D",
        "toggle_fullscreen": "Cmd+Enter",
    },

    workflows={
        "run_command": ["Type command in active terminal", "Press Enter"],
        "open_new_tab": ["Cmd+T"],
        "navigate_to_directory": ["Type 'cd /path/to/dir'", "Press Enter"],
        "list_files": ["Type 'ls -la'", "Press Enter"],
        "search_output": ["Cmd+F", "Type search term"],
    },

    interaction_notes=(
        "Terminal is a plain text interface — no clickable UI elements beyond the menu bar. "
        "All interaction is via keyboard input to the shell prompt. "
        "JARVIS should type commands directly into the terminal. "
        "Multiple tabs and split panes are available. "
        "Each tab is a separate shell session."
    ),
)

app_registry.register(profile)
