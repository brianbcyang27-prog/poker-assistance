"""VS Code — Visual Studio Code profile."""

from .base import ApplicationProfile, app_registry

profile = ApplicationProfile(
    name="Code",
    bundle_id="com.microsoft.VSCode",
    executable="Code",
    category="editor",

    common_buttons=[
        "Explorer", "Search", "Source Control", "Run", "Extensions",
        "Close", "Minimize", "Maximize",
    ],

    common_menus=[
        "File", "Edit", "Selection", "View", "Go", "Run", "Terminal", "Help",
    ],

    common_shortcuts={
        "command_palette": "Shift+Cmd+P",
        "quick_open": "Cmd+P",
        "save": "Cmd+S",
        "save_all": "Shift+Cmd+S",
        "new_file": "Cmd+N",
        "open_file": "Cmd+O",
        "toggle_terminal": "Ctrl+`",
        "toggle_sidebar": "Cmd+B",
        "find_in_files": "Shift+Cmd+F",
        "replace_in_files": "Shift+Cmd+H",
        "go_to_line": "Ctrl+G",
        "format_document": "Shift+Option+F",
        "toggle_comments": "Cmd+/",
        "duplicate_line": "Shift+Option+Down",
        "delete_line": "Shift+Cmd+K",
        "multi_cursor": "Cmd+D",
        "rename_symbol": "F2",
        "go_to_definition": "F12",
        "peek_definition": "Option+F12",
        "show_problems": "Shift+Cmd+M",
        "toggle_focus_editor": "Cmd+1",
        "toggle_focus_terminal": "Ctrl+`",
    },

    workflows={
        "open_file": ["Cmd+P", "Type filename", "Press Enter"],
        "open_folder": ["Cmd+O", "Select folder in dialog"],
        "run_code": ["Press the Run button or F5"],
        "debug": ["Press F5 to start debugging"],
        "search_and_replace": ["Shift+Cmd+H", "Enter search", "Enter replace"],
        "format_code": ["Shift+Option+F"],
        "rename_symbol": ["Place cursor on symbol", "Press F2", "Type new name", "Press Enter"],
        "open_terminal": ["Ctrl+`"],
        "git_commit": ["Source Control panel", "Type message", "Cmd+Enter to commit"],
    },

    interaction_notes=(
        "VS Code has a rich UI: Activity Bar (left), Editor (center), Panel (bottom), "
        "Status Bar (bottom). The Command Palette (Shift+Cmd+P) gives access to all commands. "
        "The Explorer sidebar shows files and folders. "
        "Extensions can add new panels and commands. "
        "The integrated terminal is in the bottom panel."
    ),
)

app_registry.register(profile)
