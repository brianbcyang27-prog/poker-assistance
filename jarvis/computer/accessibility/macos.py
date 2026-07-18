"""macOS Accessibility Provider — JARVIS's native eye on macOS.

Uses macOS Accessibility API via AppleScript to inspect UI elements,
find buttons/menus/text fields, and interact with applications.

No dependencies beyond macOS built-ins (osascript, screencapture).
"""

import asyncio
import logging
import time
from typing import Optional

from .base import AccessibilityProvider
from .element import UIElement, ElementType, ElementState

log = logging.getLogger("jarvis.computer.accessibility.macos")


def _parse_elements_from_applescript(raw: str, app: str = "", window: str = "") -> list[UIElement]:
    """Parse AppleScript output into UIElement objects.

    Expects tab-separated lines:
        role<TAB>name<TAB>description<TAB>enabled<TAB>focused<TAB>x<TAB>y<TAB>width<TAB>height
    """
    elements = []
    lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]

    for idx, line in enumerate(lines):
        parts = line.split("\t")
        if len(parts) < 5:
            continue

        role_raw = parts[0].strip() if len(parts) > 0 else ""
        name = parts[1].strip() if len(parts) > 1 else ""
        desc = parts[2].strip() if len(parts) > 2 else ""
        enabled_str = parts[3].strip() if len(parts) > 3 else "true"
        focused_str = parts[4].strip() if len(parts) > 4 else "false"

        x = int(parts[5]) if len(parts) > 5 and parts[5].strip().isdigit() else 0
        y = int(parts[6]) if len(parts) > 6 and parts[6].strip().isdigit() else 0
        w = int(parts[7]) if len(parts) > 7 and parts[7].strip().isdigit() else 0
        h = int(parts[8]) if len(parts) > 8 and parts[8].strip().isdigit() else 0

        # Map AppleScript role to ElementType
        role_map = {
            "AXButton": ElementType.BUTTON,
            "AXMenu": ElementType.MENU,
            "AXMenuItem": ElementType.MENU_ITEM,
            "AXTextField": ElementType.TEXT_FIELD,
            "AXTextArea": ElementType.TEXT_AREA,
            "AXCheckBox": ElementType.CHECKBOX,
            "AXRadioButton": ElementType.RADIO_BUTTON,
            "AXPopUpButton": ElementType.DROPDOWN,
            "AXSlider": ElementType.SLIDER,
            "AXList": ElementType.LIST,
            "AXListItem": ElementType.LIST_ITEM,
            "AXTable": ElementType.TABLE,
            "AXRow": ElementType.TABLE_ROW,
            "AXCell": ElementType.TABLE_CELL,
            "AXTab": ElementType.TAB,
            "AXToolbar": ElementType.TOOLBAR,
            "AXScrollBar": ElementType.SCROLLBAR,
            "AXImage": ElementType.IMAGE,
            "AXLink": ElementType.LINK,
            "AXStaticText": ElementType.STATIC_TEXT,
            "AXGroup": ElementType.GROUP,
            "AXWindow": ElementType.WINDOW,
            "AXSheet": ElementType.SHEET,
            "AXDialog": ElementType.DIALOG,
            "AXApplication": ElementType.UNKNOWN,
        }
        elem_type = role_map.get(role_raw, ElementType.UNKNOWN)

        states = set()
        if enabled_str.lower() in ("true", "1", "yes"):
            states.add(ElementState.ENABLED)
        else:
            states.add(ElementState.DISABLED)
        if focused_str.lower() in ("true", "1", "yes"):
            states.add(ElementState.FOCUSED)

        bounds = {}
        if x or y or w or h:
            bounds = {"x": x, "y": y, "width": w, "height": h}

        element = UIElement(
            id=f"mac_{idx}",
            name=name,
            description=desc,
            role=role_raw,
            type=elem_type,
            states=states,
            bounds=bounds,
            app=app,
            window=window,
            depth=0,
            index=idx,
        )
        elements.append(element)

    return elements


class MacOSAccessibilityProvider(AccessibilityProvider):
    """macOS Accessibility API provider via AppleScript.

    Requires System Preferences → Privacy → Accessibility permission
    for Terminal/Python.

    Provides:
      - Window listing and inspection
      - UI element discovery via AppleScript
      - Element interaction (click, type)
      - Application activation
    """

    def __init__(self):
        self._initialized = False

    async def _run_applescript(self, script: str) -> str:
        """Run an AppleScript and return stdout."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode != 0:
                err = stderr.decode().strip()
                log.warning("AppleScript error: %s", err)
                return ""
            return stdout.decode().strip()
        except asyncio.TimeoutError:
            log.warning("AppleScript timed out")
            return ""
        except FileNotFoundError:
            log.warning("osascript not found — not on macOS")
            return ""
        except Exception as e:
            log.warning("AppleScript failed: %s", e)
            return ""

    async def get_windows(self) -> list[dict]:
        """Get all visible windows via AppleScript."""
        script = """
        tell application "System Events"
            set windowList to {}
            set procList to every process whose visible is true
            repeat with proc in procList
                set procName to name of proc
                set procPID to unix id of proc
                try
                    set procWindows to every window of proc
                    repeat with win in procWindows
                        set winTitle to name of win
                        set end of windowList to procName & "\t" & winTitle & "\t" & (procPID as text)
                    end repeat
                end try
            end repeat
            set AppleScript's text item delimiters to "\n"
            return windowList as string
        end tell
        """
        raw = await self._run_applescript(script)
        if not raw:
            return []

        windows = []
        for line in raw.split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3:
                windows.append({
                    "app": parts[0].strip(),
                    "title": parts[1].strip(),
                    "pid": int(parts[2].strip()) if parts[2].strip().isdigit() else 0,
                    "focused": False,
                })

        # Mark the frontmost window as focused
        if windows:
            windows[0]["focused"] = True

        return windows

    async def get_active_window(self) -> Optional[dict]:
        """Get the currently focused window."""
        script = """
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            set appName to name of frontApp
            set appPID to unix id of frontApp
            try
                set frontWindow to first window of frontApp
                set winTitle to name of frontWindow
                return appName & "\t" & winTitle & "\t" & (appPID as text)
            on error
                return appName & "\t\t" & (appPID as text)
            end try
        end tell
        """
        raw = await self._run_applescript(script)
        if not raw:
            return None

        parts = raw.split("\t")
        if len(parts) >= 2:
            return {
                "app": parts[0].strip(),
                "title": parts[1].strip(),
                "pid": int(parts[2].strip()) if len(parts) > 2 and parts[2].strip().isdigit() else 0,
            }
        return None

    async def get_elements(self, window_title: str = "") -> list[UIElement]:
        """Get UI elements from the active (or specified) window."""
        active = await self.get_active_window()
        if not active:
            return []

        app_name = active["app"]
        win_title = window_title or active["title"]

        # Get elements via AppleScript accessibility inspection
        script = f'''
        tell application "System Events"
            set proc to first process whose name is "{app_name}"
            set targetWindow to missing value
            try
                if "{win_title}" is "" then
                    set targetWindow to first window of proc whose subrole is "AXStandardWindow"
                else
                    set targetWindow to first window of proc whose name is "{win_title}"
                end if
            on error
                try
                    set targetWindow to first window of proc
                on error
                    return ""
                end try
            end try

            set elemList to {{}}
            set allElements to every UI element of targetWindow
            repeat with elem in allElements
                try
                    set elemRole to role of elem
                    set elemName to ""
                    try
                        set elemName to name of elem
                    end try
                    set elemDesc to ""
                    try
                        set elemDesc to description of elem
                    end try
                    set elemEnabled to "true"
                    try
                        if not (enabled of elem) then set elemEnabled to "false"
                    end try
                    set elemFocused to "false"
                    try
                        if focused of elem then set elemFocused to "true"
                    end try
                    set elemPos to ""
                    try
                        set pos to position of elem
                        set elemPos to (item 1 of pos as text) & "\t" & (item 2 of pos as text)
                    end try
                    set elemSize to ""
                    try
                        set sz to size of elem
                        set elemSize to (item 1 of sz as text) & "\t" & (item 2 of sz as text)
                    end try

                    set posParts to ""
                    if elemPos is not "" and elemSize is not "" then
                        set posParts to elemPos & "\t" & elemSize
                    else
                        set posParts to "0\t0\t0\t0"
                    end if

                    set end of elemList to elemRole & "\t" & elemName & "\t" & elemDesc & "\t" & elemEnabled & "\t" & elemFocused & "\t" & posParts
                end try
            end repeat
            set AppleScript's text item delimiters to "\n"
            return elemList as string
        end tell
        '''
        raw = await self._run_applescript(script)
        return _parse_elements_from_applescript(raw, app=app_name, window=win_title)

    async def find_element(
        self,
        name: str = "",
        role: str = "",
        app: str = "",
    ) -> Optional[UIElement]:
        """Find a specific UI element by name and/or role."""
        elements = await self.get_elements()
        for el in elements:
            name_match = not name or el.matches(name)
            role_match = not role or role.lower() in el.role.lower() or role.lower() == el.type.lower()
            app_match = not app or el.app.lower() == app.lower()
            if name_match and role_match and app_match:
                return el
        return None

    async def click_element(self, element: UIElement) -> dict:
        """Click on a UI element using its bounds."""
        if not element.has_bounds():
            return {"ok": False, "error": "Element has no bounds — cannot click"}

        center = element.center()
        if not center:
            return {"ok": False, "error": "Cannot calculate element center"}

        x, y = center
        script = f'''
        tell application "System Events"
            set proc to first process whose name is "{element.app}"
            click at {{{x}, {y}}}
        end tell
        '''
        raw = await self._run_applescript(script)
        return {"ok": True, "x": x, "y": y, "element": element.name}

    async def type_text(self, element: UIElement, text: str) -> dict:
        """Type text into a UI element."""
        # Focus the element first via click, then type
        if element.has_bounds():
            await self.click_element(element)
            await asyncio.sleep(0.1)

        # Use keystroke to type text
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        script = f'''
        tell application "System Events"
            keystroke "{escaped}"
        end tell
        '''
        await self._run_applescript(script)
        return {"ok": True, "text": text, "element": element.name}

    async def get_tree(self, window_title: str = "") -> dict:
        """Get the full accessibility tree for a window."""
        elements = await self.get_elements(window_title)
        active = await self.get_active_window()
        app = active["app"] if active else ""
        win = window_title or (active["title"] if active else "")
        from .tree import AccessibilityTree
        tree = AccessibilityTree(elements, app=app, window=win)
        return tree.to_dict()

    async def activate_app(self, app_name: str) -> dict:
        """Bring an application to the foreground."""
        script = f'''
        tell application "{app_name}"
            activate
        end tell
        '''
        await self._run_applescript(script)
        await asyncio.sleep(0.3)
        return {"ok": True, "app": app_name}

    async def get_applications(self) -> list[str]:
        """Get list of running application names."""
        script = """
        tell application "System Events"
            set procList to every process whose visible is true
            set nameList to {{}}
            repeat with proc in procList
                set end of nameList to name of proc
            end repeat
            set AppleScript's text item delimiters to "\n"
            return nameList as string
        end tell
        """
        raw = await self._run_applescript(script)
        if not raw:
            return []
        return [name.strip() for name in raw.split("\n") if name.strip()]
