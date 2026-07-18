"""Finder — macOS file manager profile."""

from .base import ApplicationProfile, app_registry

profile = ApplicationProfile(
    name="Finder",
    bundle_id="com.apple.finder",
    executable="Finder",
    category="file_manager",

    common_buttons=[
        "New Folder", "Open", "Get Info", "Rename", "Move to Trash",
        "AirDrop", "Share", "Tags",
    ],

    common_menus=["File", "Edit", "View", "Go", "Window", "Help"],

    common_shortcuts={
        "new_folder": "Shift+Cmd+N",
        "get_info": "Cmd+I",
        "duplicate": "Cmd+D",
        "rename": "Enter",
        "select_all": "Cmd+A",
        "copy": "Cmd+C",
        "paste": "Cmd+V",
        "move_to_trash": "Cmd+Backspace",
        "new_window": "Cmd+N",
        "show_package_contents": "Cmd+Down",
        "go_to_folder": "Shift+Cmd+G",
        "quick_look": "Space",
    },

    workflows={
        "open_file": ["Double-click the file"],
        "new_folder": ["File menu", "New Folder"],
        "rename_file": ["Select file", "Press Enter", "Type new name", "Press Enter"],
        "delete_file": ["Select file", "Cmd+Backspace"],
        "get_info": ["Select file", "Cmd+I"],
        "show_hidden_files": ["Cmd+Shift+."],
        "go_to_folder": ["Shift+Cmd+G", "Type path", "Press Enter"],
    },

    interaction_notes=(
        "Finder uses a sidebar for quick access (Favorites, Locations, Tags). "
        "Files are shown in icon/list/column/gallery view. "
        "The path bar at the bottom shows the full path. "
        "To access hidden files, press Cmd+Shift+."
    ),
)

app_registry.register(profile)
