"""Tool Executor — bridge between agents and real-world capabilities.

Workers call tools.execute(action, **params) to:
- Control the computer (mouse, keyboard, screen, browser)
- Search the web
- Control Arduino/ESP32 devices on WiFi
- Execute shell commands

This is what makes agents DO things instead of just thinking about them.
"""

from typing import Optional, Any
import asyncio


class ToolExecutor:
    """Unified tool interface for agents.
    
    Usage in a worker:
        tools = ToolExecutor()
        result = await tools.execute("screen_capture")
        result = await tools.execute("web_search", query="python async")
        result = await tools.execute("arduino_list_devices")
        result = await tools.execute("arduino_command", device_id="esp32_01", command="ledon")
    """
    
    def __init__(self):
        self._computer = None
        self._browser = None
        self._mouse = None
        self._screen = None
        self._search = None
        self._arduino = None
    
    @property
    def computer(self):
        if self._computer is None:
            from ..computer.controller import controller
            self._computer = controller
        return self._computer
    
    @property
    def browser(self):
        if self._browser is None:
            from ..computer.browser import browser
            self._browser = browser
        return self._browser
    
    @property
    def mouse(self):
        if self._mouse is None:
            from ..computer.mouse import mouse
            self._mouse = mouse
        return self._mouse
    
    @property
    def screen(self):
        if self._screen is None:
            from ..computer.screen import screen
            self._screen = screen
        return self._screen
    
    @property
    def search(self):
        if self._search is None:
            from ..computer.search import web_search
            self._search = web_search
        return self._search
    
    @property
    def arduino(self):
        if self._arduino is None:
            from ..iot.manager import device_manager
            self._arduino = device_manager
        return self._arduino
    
    async def execute(self, action: str, **params) -> dict:
        """Execute a tool action and return structured result.
        
        Actions:
            # Computer control
            screen_capture        - Take screenshot
            screen_capture_region - Take region screenshot (x, y, w, h)
            screen_list_windows   - List open windows
            screen_active_window  - Get active window info
            screen_open_app       - Open an application (app_name)
            screen_open_url       - Open URL in browser (url)
            
            mouse_click           - Click at position (x, y)
            mouse_move            - Move cursor (x, y)
            mouse_type            - Type text (text)
            mouse_hotkey          - Press hotkey combo (keys: list)
            mouse_scroll          - Scroll (amount)
            
            browser_navigate      - Go to URL (url)
            browser_click         - Click element (selector)
            browser_fill          - Fill input (selector, text)
            browser_screenshot    - Screenshot current page
            browser_text          - Get page text
            browser_press_key     - Press key (key)
            browser_evaluate      - Run JS code (code)
            browser_scroll        - Scroll page
            
            web_search            - Search DuckDuckGo (query)
            web_fetch             - Fetch URL content (url)
            
            # IoT / Arduino control
            arduino_list_devices  - List connected ESP32 devices
            arduino_send          - Send command to device (device_id, command, payload)
            arduino_read          - Read sensor from device (device_id, sensor)
            arduino_status        - Get device status (device_id)
            
            # System
            shell_execute         - Run shell command (command)
            task_complete         - Signal task completion (summary)
        """
        try:
            return await self._dispatch(action, **params)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action,
            }
    
    async def _dispatch(self, action: str, **params) -> dict:
        """Dispatch to the right handler."""
        
        # --- Project Memory ---
        if action == "register_project":
            from ..brain.project_memory import project_memory
            project = await project_memory.register_project(
                name=params["name"],
                path=params["path"],
                description=params.get("description", ""),
                language=params.get("language", ""),
                server_command=params.get("server_command", ""),
                server_port=params.get("server_port", 0),
                url=params.get("url", ""),
                ai_tool_command=params.get("ai_tool_command", ""),
                ai_tool_name=params.get("ai_tool_name", ""),
                context=params.get("context", {}),
            )
            return {"success": True, "project": project}
        
        elif action == "list_projects":
            from ..brain.project_memory import project_memory
            projects = await project_memory.list_projects(
                status=params.get("status"),
            )
            return {"success": True, "projects": projects}
        
        elif action == "get_active_project":
            from ..brain.project_memory import project_memory
            project = await project_memory.get_active_project()
            if project:
                return {"success": True, "project": project}
            return {"success": False, "error": "No active project"}
        
        elif action == "record_activity":
            from ..brain.project_memory import project_memory
            await project_memory.record_activity(params["name"])
            return {"success": True}
        
        elif action == "resume_project":
            from ..brain.project_memory import project_memory
            name = params.get("name")
            if name:
                project = await project_memory.get_project(name)
            else:
                project = await project_memory.get_active_project()
            if not project:
                return {"success": False, "error": "No project found"}
            
            await project_memory.record_activity(project["name"])
            
            # Build and execute resume script
            script = project_memory.build_resume_script(project)
            if script:
                # Write script to temp file and execute
                import tempfile
                with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
                    f.write(script)
                    f.flush()
                    script_path = f.name
                
                # Execute asynchronously in background
                proc = await asyncio.create_subprocess_shell(
                    f"chmod +x {script_path} && bash {script_path}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                # Don't wait — let it run in background
            
            commands = project_memory.build_resume_commands(project)
            return {
                "success": True,
                "project": project["name"],
                "windows": [c["title"] for c in commands],
                "script": script,
            }
        
        elif action == "open_terminal":
            # Open a new Terminal window with a command
            command = params["command"]
            title = params.get("title", "JARVIS")
            escaped_cmd = command.replace('"', '\\"')
            escaped_title = title.replace('"', '\\"')
            
            apple_script = (
                f'tell application "Terminal"\n'
                f'  activate\n'
                f'  do script "{escaped_cmd}"\n'
                f'  set custom title of front window to "{escaped_title}"\n'
                f'end tell'
            )
            proc = await asyncio.create_subprocess_shell(
                f"osascript -e '{apple_script}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return {"success": proc.returncode == 0, "title": title}
        
        # --- Screen ---
        if action == "screen_capture":
            path = self.screen.capture()
            return {"success": True, "path": path}
        
        elif action == "screen_capture_region":
            path = self.screen.capture(
                region=(params["x"], params["y"], params["w"], params["h"])
            )
            return {"success": True, "path": path}
        
        elif action == "screen_list_windows":
            windows = self.screen.list_windows()
            return {"success": True, "windows": windows}
        
        elif action == "screen_active_window":
            info = self.screen.get_active_window()
            return {"success": True, "window": info}
        
        elif action == "screen_open_app":
            self.screen.open_app(params["app_name"])
            return {"success": True}
        
        elif action == "screen_open_url":
            self.screen.open_url(params["url"])
            return {"success": True}
        
        # --- Mouse / Keyboard ---
        elif action == "mouse_click":
            self.mouse.click(params["x"], params["y"])
            return {"success": True}
        
        elif action == "mouse_move":
            self.mouse.move(params["x"], params["y"])
            return {"success": True}
        
        elif action == "mouse_type":
            self.mouse.type_text(params["text"])
            return {"success": True}
        
        elif action == "mouse_hotkey":
            self.mouse.hotkey(*params["keys"])
            return {"success": True}
        
        elif action == "mouse_scroll":
            self.mouse.scroll(params["amount"])
            return {"success": True}
        
        # --- Browser ---
        elif action == "browser_navigate":
            await self.browser.navigate(params["url"])
            return {"success": True}
        
        elif action == "browser_click":
            await self.browser.click(params["selector"])
            return {"success": True}
        
        elif action == "browser_fill":
            await self.browser.fill(params["selector"], params["text"])
            return {"success": True}
        
        elif action == "browser_screenshot":
            path = await self.browser.screenshot()
            return {"success": True, "path": path}
        
        elif action == "browser_text":
            text = await self.browser.get_text()
            return {"success": True, "text": text}
        
        elif action == "browser_press_key":
            await self.browser.press_key(params["key"])
            return {"success": True}
        
        elif action == "browser_evaluate":
            result = await self.browser.evaluate(params["code"])
            return {"success": True, "result": result}
        
        elif action == "browser_scroll":
            await self.browser.scroll(params.get("amount", 3))
            return {"success": True}
        
        # --- Web Search ---
        elif action == "web_search":
            results = await self.search.search(params["query"])
            return {"success": True, "results": results}
        
        elif action == "web_fetch":
            text = await self.search.fetch_url(params["url"])
            return {"success": True, "text": text}
        
        # --- IoT / Arduino ---
        elif action == "arduino_list_devices":
            devices = self.arduino.list_devices()
            return {"success": True, "devices": devices}
        
        elif action == "arduino_send":
            result = await self.arduino.send_command(
                params["device_id"],
                params["command"],
                params.get("payload", {}),
            )
            return {"success": True, "result": result}
        
        elif action == "arduino_read":
            result = await self.arduino.read_sensor(
                params["device_id"],
                params["sensor"],
            )
            return {"success": True, "result": result}
        
        elif action == "arduino_status":
            status = self.arduino.get_status(params["device_id"])
            return {"success": True, "status": status}
        
        # --- Engineering ---
        elif action == "engineering_cad_create":
            from ..engineering.cad.base import CADProvider
            cad = CADProvider()
            model_id = await cad.create_model(
                name=params["name"],
                model_type=params.get("type", "part"),
                dimensions=params.get("dimensions", {}),
                material=params.get("material"),
            )
            return {"success": True, "model_id": model_id}
        
        elif action == "engineering_cad_export":
            from ..engineering.cad.base import CADProvider
            cad = CADProvider()
            path = await cad.export_model(
                model_id=params["model_id"],
                format=params["format"],
                path=params.get("path"),
            )
            return {"success": True, "path": path}
        
        elif action == "engineering_pcb_create":
            from ..engineering.pcb.base import PCBProvider
            pcb = PCBProvider()
            board_id = await pcb.create_board(
                name=params["name"],
                layers=params.get("layers", 2),
                dimensions=params.get("dimensions", {}),
            )
            return {"success": True, "board_id": board_id}
        
        elif action == "engineering_pcb_drc":
            from ..engineering.pcb.base import PCBProvider
            pcb = PCBProvider()
            results = await pcb.run_drc(board_id=params["board_id"])
            return {"success": True, "results": results}
        
        elif action == "engineering_pcb_export":
            from ..engineering.pcb.base import PCBProvider
            pcb = PCBProvider()
            path = await pcb.export_gerbers(
                board_id=params["board_id"],
                path=params.get("path"),
            )
            return {"success": True, "path": path}
        
        elif action == "engineering_firmware_create":
            from ..engineering.embedded.base import EmbeddedProvider
            embedded = EmbeddedProvider()
            project_id = await embedded.create_project(
                name=params["name"],
                platform=params["platform"],
                board=params.get("board"),
            )
            return {"success": True, "project_id": project_id}
        
        elif action == "engineering_firmware_compile":
            from ..engineering.embedded.base import EmbeddedProvider
            embedded = EmbeddedProvider()
            result = await embedded.compile(
                project_id=params["project_id"],
                config=params.get("config", "release"),
            )
            return {"success": True, "result": result}
        
        elif action == "engineering_firmware_upload":
            from ..engineering.embedded.base import EmbeddedProvider
            embedded = EmbeddedProvider()
            result = await embedded.upload(
                project_id=params["project_id"],
                port=params.get("port"),
            )
            return {"success": True, "result": result}
        
        elif action == "engineering_firmware_devices":
            from ..engineering.embedded.base import EmbeddedProvider
            embedded = EmbeddedProvider()
            devices = await embedded.list_devices()
            return {"success": True, "devices": devices}
        
        elif action == "engineering_mechanical_material":
            from ..engineering.mechanical.base import MechanicalProvider
            mech = MechanicalProvider()
            material = mech.get_material(params["material"])
            return {"success": True, "material": material}
        
        elif action == "engineering_mechanical_stress":
            from ..engineering.mechanical.base import MechanicalProvider
            mech = MechanicalProvider()
            result = mech.calculate_beam_stress(
                force=params["force"],
                distance=params["distance"],
                width=params["width"],
                height=params["height"],
            )
            return {"success": True, "result": result}
        
        elif action == "engineering_mechanical_bearing":
            from ..engineering.mechanical.base import MechanicalProvider
            mech = MechanicalProvider()
            bearing = mech.select_bearing(
                load=params["load"],
                speed_rpm=params["speed_rpm"],
                life_hours=params.get("life_hours", 1000),
            )
            return {"success": True, "bearing": bearing}
        
        elif action == "engineering_mechanical_gear":
            from ..engineering.mechanical.base import MechanicalProvider
            mech = MechanicalProvider()
            gear = mech.calculate_gear_ratio(
                driver_teeth=params["driver_teeth"],
                driven_teeth=params["driven_teeth"],
                input_rpm=params["input_rpm"],
            )
            return {"success": True, "gear": gear}
        
        elif action == "engineering_knowledge":
            from ..engineering.knowledge import engineering_knowledge
            result = engineering_knowledge.query(
                query=params["query"],
                category=params.get("category"),
            )
            return {"success": True, "result": result}
        
        # --- System ---
        elif action == "shell_execute":
            proc = await asyncio.create_subprocess_shell(
                params["command"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "returncode": proc.returncode,
            }
        
        elif action == "task_complete":
            return {"success": True, "summary": params.get("summary", "Task complete")}
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def list_actions(self) -> list[str]:
        """List all available tool actions."""
        return [
            # Project Memory
            "register_project", "list_projects", "get_active_project",
            "record_activity", "resume_project", "open_terminal",
            # Screen
            "screen_capture", "screen_capture_region", "screen_list_windows",
            "screen_active_window", "screen_open_app", "screen_open_url",
            # Mouse/Keyboard
            "mouse_click", "mouse_move", "mouse_type", "mouse_hotkey", "mouse_scroll",
            # Browser
            "browser_navigate", "browser_click", "browser_fill", "browser_screenshot",
            "browser_text", "browser_press_key", "browser_evaluate", "browser_scroll",
            # Web
            "web_search", "web_fetch",
            # IoT
            "arduino_list_devices", "arduino_send", "arduino_read", "arduino_status",
            # Engineering - CAD
            "engineering_cad_create", "engineering_cad_export",
            # Engineering - PCB
            "engineering_pcb_create", "engineering_pcb_drc", "engineering_pcb_export",
            # Engineering - Embedded
            "engineering_firmware_create", "engineering_firmware_compile",
            "engineering_firmware_upload", "engineering_firmware_devices",
            # Engineering - Mechanical
            "engineering_mechanical_material", "engineering_mechanical_stress",
            "engineering_mechanical_bearing", "engineering_mechanical_gear",
            # Engineering - Knowledge
            "engineering_knowledge",
            # System
            "shell_execute", "task_complete",
        ]


# Singleton
tools = ToolExecutor()
