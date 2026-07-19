"""Tool registry — manages JARVIS tool knowledge and recommendations."""
import asyncio
import json
import re
from pathlib import Path
from typing import List, Optional, Dict

from .models import ToolInfo, ToolCapability


_DEFAULT_TOOLS: List[Dict] = [
    {
        "name": "git",
        "category": "version_control",
        "description": "Distributed version control system for tracking code changes",
        "capabilities": [
            {"name": "branching", "description": "Create and manage parallel lines of development", "input_types": ["branch_name"], "output_types": ["branch"]},
            {"name": "merging", "description": "Combine multiple branches of development", "input_types": ["branch"], "output_types": ["merge_result"]},
            {"name": "diffing", "description": "Show changes between commits, branches, or working directory", "input_types": ["ref1", "ref2"], "output_types": ["diff_output"]},
            {"name": "stashing", "description": "Temporarily store modified tracked files", "input_types": ["files"], "output_types": ["stash_entry"]},
            {"name": "rebasing", "description": "Reapply commits on top of another base tip", "input_types": ["base_branch"], "output_types": ["rebased_history"]},
        ],
        "requirements": ["git installed and configured"],
        "common_failures": [
            {"error": "merge conflict", "fix": "Resolve conflicts in marked files, then git add and git commit"},
            {"error": "detached HEAD", "fix": "Create a branch with git checkout -b <branch-name>"},
            {"error": "permission denied", "fix": "Check SSH keys or token authentication"},
        ],
        "examples": ["git status", "git diff", "git log --oneline -10", "git stash", "git rebase main"],
        "check_command": "which git",
        "install_command": "brew install git",
        "version_command": "git --version",
    },
    {
        "name": "python",
        "category": "file_system",
        "description": "Python interpreter for scripting, testing, and application development",
        "capabilities": [
            {"name": "scripting", "description": "Write and execute Python scripts", "input_types": [".py"], "output_types": ["stdout", "exit_code"]},
            {"name": "testing", "description": "Run Python test suites", "input_types": ["test_files"], "output_types": ["test_results"]},
            {"name": "packaging", "description": "Build and distribute Python packages", "input_types": ["pyproject.toml"], "output_types": ["wheel", "sdist"]},
        ],
        "requirements": ["python3 installed", "pip for package management"],
        "common_failures": [
            {"error": "ModuleNotFoundError", "fix": "pip install <module-name>"},
            {"error": "SyntaxError", "fix": "Check Python version compatibility, use correct syntax"},
            {"error": "IndentationError", "fix": "Fix whitespace, use consistent indentation (4 spaces)"},
        ],
        "examples": ["python3 script.py", "python3 -m pytest tests/", "pip install -e ."],
        "check_command": "which python3",
        "install_command": "brew install python",
        "version_command": "python3 --version",
    },
    {
        "name": "node",
        "category": "file_system",
        "description": "Node.js runtime and npm package manager for JavaScript development",
        "capabilities": [
            {"name": "npm", "description": "Package management and script running", "input_types": ["package.json"], "output_types": ["node_modules"]},
            {"name": "build", "description": "Run build scripts and bundlers", "input_types": ["build_config"], "output_types": ["build_output"]},
            {"name": "dev_server", "description": "Start development servers with hot reload", "input_types": ["server_config"], "output_types": ["running_server"]},
        ],
        "requirements": ["node installed", "npm or yarn"],
        "common_failures": [
            {"error": "MODULE_NOT_FOUND", "fix": "Run npm install to install dependencies"},
            {"error": "ERESOLVE", "fix": "Use npm install --legacy-peer-deps or resolve dependency conflict"},
            {"error": "EACCES permission denied", "fix": "Fix npm global directory permissions or use nvm"},
        ],
        "examples": ["npm install", "npm run build", "npm test", "npx create-react-app app"],
        "check_command": "which node",
        "install_command": "brew install node",
        "version_command": "node --version",
    },
    {
        "name": "docker",
        "category": "containerization",
        "description": "Platform for building, shipping, and running containerized applications",
        "capabilities": [
            {"name": "containerization", "description": "Package apps with dependencies into isolated containers", "input_types": ["Dockerfile"], "output_types": ["image", "container"]},
            {"name": "sandboxing", "description": "Run code in isolated environments", "input_types": ["image"], "output_types": ["isolated_process"]},
            {"name": "orchestration", "description": "Manage multi-container applications", "input_types": ["docker-compose.yml"], "output_types": ["stack"]},
        ],
        "requirements": ["docker installed and running"],
        "common_failures": [
            {"error": "Cannot connect to Docker daemon", "fix": "Start Docker Desktop or run sudo systemctl start docker"},
            {"error": "no space left on device", "fix": "Run docker system prune to clean up unused images"},
            {"error": "port already in use", "fix": "Change the port mapping or stop the conflicting container"},
        ],
        "examples": ["docker build -t app .", "docker run -p 8080:8080 app", "docker-compose up"],
        "check_command": "which docker",
        "install_command": "brew install --cask docker",
        "version_command": "docker --version",
    },
    {
        "name": "vscode",
        "category": "file_system",
        "description": "Visual Studio Code editor for code editing and debugging",
        "capabilities": [
            {"name": "editing", "description": "Code editing with IntelliSense and multi-cursor", "input_types": ["source_files"], "output_types": ["modified_files"]},
            {"name": "debugging", "description": "Built-in debugger for multiple languages", "input_types": ["source_files", "launch_config"], "output_types": ["debug_session"]},
            {"name": "extensions", "description": "Extensible plugin ecosystem", "input_types": ["extension_id"], "output_types": ["enhanced_features"]},
        ],
        "requirements": ["vscode installed", "code CLI available"],
        "common_failures": [
            {"error": "extension not found", "fix": "Search marketplace or install with code --install-extension <ext>"},
            {"error": "debugger not working", "fix": "Check launch.json configuration and ensure correct runtime is installed"},
        ],
        "examples": ["code .", "code --install-extension ms-python.python", "code --diff file1 file2"],
        "check_command": "which code",
        "install_command": "brew install --cask visual-studio-code",
        "version_command": "code --version",
    },
    {
        "name": "playwright",
        "category": "browser",
        "description": "Browser automation framework for testing and web interaction",
        "capabilities": [
            {"name": "browser_automation", "description": "Control browser for web interaction and testing", "input_types": ["url", "selectors"], "output_types": ["page_state", "screenshots"]},
            {"name": "e2e_testing", "description": "End-to-end testing with assertions", "input_types": ["test_specs"], "output_types": ["test_results"]},
            {"name": "web_scraping", "description": "Extract data from web pages", "input_types": ["url", "selectors"], "output_types": ["structured_data"]},
        ],
        "requirements": ["playwright installed", "browser binaries"],
        "common_failures": [
            {"error": "browser not found", "fix": "Run npx playwright install to download browser binaries"},
            {"error": "element not visible", "fix": "Wait for element with page.waitForSelector or increase timeout"},
            {"error": "navigation timeout", "fix": "Increase timeout or check network connectivity"},
        ],
        "examples": ["npx playwright test", "npx playwright codegen", "npx playwright screenshot url"],
        "check_command": "which npx && npx playwright --version",
        "install_command": "npm install -D @playwright/test",
        "version_command": "npx playwright --version",
    },
    {
        "name": "fusion360",
        "category": "cad",
        "description": "Cloud-based 3D CAD, CAM, CAE, and PCB design tool",
        "capabilities": [
            {"name": "3d_modeling", "description": "Parametric and freeform 3D modeling", "input_types": ["sketches", "dimensions"], "output_types": ["3d_bodies", "assemblies"]},
            {"name": "assemblies", "description": "Multi-component assembly design and motion study", "input_types": ["components"], "output_types": ["assembly"]},
            {"name": "simulation", "description": "Stress, thermal, and motion simulation", "input_types": ["model", "loads"], "output_types": ["simulation_results"]},
        ],
        "requirements": ["Fusion 360 installed", "Autodesk account"],
        "common_failures": [
            {"error": "license not found", "fix": "Sign in with Autodesk account and verify license status"},
            {"error": "model won't export", "fix": "Check export format compatibility and try alternative formats"},
        ],
        "examples": ["Export as STEP", "Create assembly", "Run stress analysis"],
        "check_command": "ls /Applications/Autodesk/Autodesk\\ Fusion\\ 360",
        "install_command": "Download from autodesk.com",
        "version_command": "N/A (cloud-based)",
    },
    {
        "name": "kicad",
        "category": "pcb",
        "description": "Open-source electronics design automation suite",
        "capabilities": [
            {"name": "schematic", "description": "Electronic schematic capture", "input_types": ["components"], "output_types": ["schematic"]},
            {"name": "pcb_layout", "description": "PCB layout and routing", "input_types": ["schematic"], "output_types": ["pcb_layout"]},
            {"name": "gerber_export", "description": "Manufacturing output generation", "input_types": ["pcb_layout"], "output_types": ["gerber_files"]},
        ],
        "requirements": ["KiCad installed"],
        "common_failures": [
            {"error": "lib not found", "fix": "Configure library paths in Preferences > Configure Paths"},
            {"error": "DRC errors", "fix": "Review design rule violations and adjust trace widths or clearances"},
        ],
        "examples": ["Open schematic editor", "Run ERC", "Generate Gerber files"],
        "check_command": "which kicad-cli",
        "install_command": "brew install --cask kicad",
        "version_command": "kicad-cli --version",
    },
    {
        "name": "arduino",
        "category": "firmware",
        "description": "Arduino IDE for embedded firmware development",
        "capabilities": [
            {"name": "firmware_dev", "description": "Write and upload firmware to Arduino boards", "input_types": [".ino"], "output_types": ["compiled_binary"]},
            {"name": "serial_monitor", "description": "Monitor serial communication from boards", "input_types": ["serial_port"], "output_types": ["serial_output"]},
            {"name": "library_management", "description": "Manage Arduino libraries", "input_types": ["library_name"], "output_types": ["installed_library"]},
        ],
        "requirements": ["Arduino IDE installed", "board connected via USB"],
        "common_failures": [
            {"error": "board not found", "fix": "Check USB connection and select correct board/port in Tools menu"},
            {"error": "library not found", "fix": "Install library via Library Manager (Sketch > Include Library)"},
            {"error": "upload failed", "fix": "Hold reset button during upload, check baud rate"},
        ],
        "examples": ["Upload blink sketch", "Open serial monitor", "Install Adafruit library"],
        "check_command": "which arduino-cli",
        "install_command": "brew install arduino-cli",
        "version_command": "arduino-cli version",
    },
    {
        "name": "blender",
        "category": "rendering",
        "description": "Open-source 3D creation suite for modeling, animation, and rendering",
        "capabilities": [
            {"name": "3d_rendering", "description": "Photorealistic and real-time rendering", "input_types": ["scene"], "output_types": ["image", "video"]},
            {"name": "animation", "description": "Character and object animation", "input_types": ["keyframes"], "output_types": ["animated_scene"]},
            {"name": "modeling", "description": "Polygon, curve, and sculpt modeling", "input_types": ["primitives"], "output_types": ["3d_mesh"]},
        ],
        "requirements": ["Blender installed"],
        "common_failures": [
            {"error": "addon not found", "fix": "Enable addon in Preferences > Add-ons or install from .zip"},
            {"error": "render error", "fix": "Check GPU drivers, switch to CPU render if needed"},
        ],
        "examples": ["blender --background --python script.py", "Render animation", "Install addon"],
        "check_command": "which blender",
        "install_command": "brew install --cask blender",
        "version_command": "blender --version",
    },
    {
        "name": "sqlite",
        "category": "database",
        "description": "Lightweight embedded SQL database",
        "capabilities": [
            {"name": "query", "description": "Execute SQL queries", "input_types": ["sql"], "output_types": ["query_results"]},
            {"name": "schema_management", "description": "Create and modify database schemas", "input_types": ["ddl"], "output_types": ["schema_changes"]},
            {"name": "backup", "description": "Database backup and restore", "input_types": ["database_path"], "output_types": ["backup_file"]},
        ],
        "requirements": ["sqlite3 installed"],
        "common_failures": [
            {"error": "database locked", "fix": "Ensure no other process is writing, use WAL mode"},
            {"error": "no such table", "fix": "Check table name and database path"},
        ],
        "examples": ["sqlite3 database.db", ".schema", "SELECT * FROM table LIMIT 10"],
        "check_command": "which sqlite3",
        "install_command": "Pre-installed on macOS",
        "version_command": "sqlite3 --version",
    },
    {
        "name": "curl",
        "category": "communication",
        "description": "Command-line tool for transferring data with URLs",
        "capabilities": [
            {"name": "http_requests", "description": "Make HTTP/HTTPS requests", "input_types": ["url", "method"], "output_types": ["response"]},
            {"name": "file_transfer", "description": "Upload and download files", "input_types": ["url", "file"], "output_types": ["transfer_result"]},
        ],
        "requirements": ["curl installed"],
        "common_failures": [
            {"error": "SSL certificate problem", "fix": "Update CA certificates or use --insecure for testing"},
            {"error": "connection refused", "fix": "Check URL, port, and server availability"},
        ],
        "examples": ["curl -X GET https://api.example.com", "curl -X POST -d '{}' url"],
        "check_command": "which curl",
        "install_command": "Pre-installed on macOS",
        "version_command": "curl --version",
    },
    {
        "name": "pytest",
        "category": "testing",
        "description": "Python testing framework with powerful fixtures and assertions",
        "capabilities": [
            {"name": "unit_testing", "description": "Run unit tests with assertions", "input_types": ["test_files"], "output_types": ["test_results"]},
            {"name": "fixtures", "description": "Reusable test setup and teardown", "input_types": ["fixture_defs"], "output_types": ["fixture_instances"]},
            {"name": "coverage", "description": "Measure code coverage", "input_types": ["source"], "output_types": ["coverage_report"]},
        ],
        "requirements": ["pytest installed"],
        "common_failures": [
            {"error": "no tests collected", "fix": "Check test file naming (test_*.py) and function naming (test_*)"},
            {"error": "fixture not found", "fix": "Ensure fixture is in conftest.py or imported"},
        ],
        "examples": ["pytest tests/", "pytest -v --tb=short", "pytest --cov=src"],
        "check_command": "which pytest",
        "install_command": "pip install pytest",
        "version_command": "pytest --version",
    },
    {
        "name": "eslint",
        "category": "testing",
        "description": "JavaScript/TypeScript linting tool for code quality",
        "capabilities": [
            {"name": "linting", "description": "Detect and report code quality issues", "input_types": ["js/ts_files"], "output_types": ["lint_report"]},
            {"name": "auto_fix", "description": "Automatically fix linting issues", "input_types": ["js/ts_files"], "output_types": ["fixed_files"]},
        ],
        "requirements": ["eslint installed", "eslint config file"],
        "common_failures": [
            {"error": "config not found", "fix": "Create .eslintrc.json or run eslint --init"},
            {"error": "parser error", "fix": "Install correct parser plugin for TypeScript or JSX"},
        ],
        "examples": ["eslint src/", "eslint --fix src/", "eslint --config custom.json src/"],
        "check_command": "which eslint",
        "install_command": "npm install -g eslint",
        "version_command": "eslint --version",
    },
    {
        "name": "black",
        "category": "testing",
        "description": "Opinionated Python code formatter",
        "capabilities": [
            {"name": "formatting", "description": "Auto-format Python code to consistent style", "input_types": [".py"], "output_types": ["formatted_.py"]},
            {"name": "check", "description": "Check if files need formatting without modifying", "input_types": [".py"], "output_types": ["check_result"]},
        ],
        "requirements": ["black installed"],
        "common_failures": [
            {"error": "invalid syntax", "fix": "Fix syntax errors before formatting"},
            {"error": "can't parse", "fix": "Check for Python version compatibility issues"},
        ],
        "examples": ["black src/", "black --check src/", "black --line-length 100 src/"],
        "check_command": "which black",
        "install_command": "pip install black",
        "version_command": "black --version",
    },
]


class ToolRegistry:
    """Registry of available tools with smart recommendations."""

    def __init__(self, store_path: str = "memory_store/tools.json") -> None:
        self._store_path = Path(store_path)
        self._tools: Dict[str, ToolInfo] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        if not self._loaded:
            await self._load()
            self._loaded = True

    async def _load(self) -> None:
        self._tools.clear()
        self._category_index.clear()

        for d in _DEFAULT_TOOLS:
            caps = [ToolCapability(**c) for c in d.pop("capabilities", [])]
            ti = ToolInfo(**d, capabilities=caps)
            self._tools[ti.name] = ti
            self._category_index.setdefault(ti.category, []).append(ti.name)

        if self._store_path.exists():
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, td in data.items():
                    caps = [ToolCapability(**c) for c in td.pop("capabilities", [])]
                    self._tools[name] = ToolInfo(**td, capabilities=caps)
                    cat = td.get("category", "file_system")
                    if name not in self._category_index.get(cat, []):
                        self._category_index.setdefault(cat, []).append(name)
            except Exception:
                pass

    async def save(self) -> None:
        await self._ensure_loaded()
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for name, t in self._tools.items():
            data[name] = t.to_dict()
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def get(self, tool_name: str) -> Optional[ToolInfo]:
        await self._ensure_loaded()
        return self._tools.get(tool_name)

    async def get_by_category(self, category: str) -> List[ToolInfo]:
        await self._ensure_loaded()
        names = self._category_index.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    async def get_all(self) -> List[ToolInfo]:
        await self._ensure_loaded()
        return list(self._tools.values())

    async def search(self, query: str) -> List[ToolInfo]:
        await self._ensure_loaded()
        q = query.lower()
        results: List[ToolInfo] = []
        for t in self._tools.values():
            if q in t.name.lower() or q in t.description.lower():
                results.append(t)
                continue
            for cap in t.capabilities:
                if q in cap.name.lower() or q in cap.description.lower():
                    results.append(t)
                    break
        return results

    async def check_availability(self, tool_name: str) -> Dict:
        await self._ensure_loaded()
        t = self._tools.get(tool_name)
        if not t:
            return {"tool": tool_name, "available": False, "error": "not in registry"}

        result: Dict = {"tool": tool_name, "available": False, "version": ""}
        if t.check_command:
            try:
                proc = await asyncio.create_subprocess_shell(
                    t.check_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                result["available"] = proc.returncode == 0
            except Exception:
                result["available"] = False

        if result["available"] and t.version_command:
            try:
                proc = await asyncio.create_subprocess_shell(
                    t.version_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                result["version"] = stdout.decode().strip().split("\n")[0]
            except Exception:
                pass

        t.available = result["available"]
        t.version = result["version"]
        return result

    async def check_all_availability(self) -> Dict[str, bool]:
        await self._ensure_loaded()
        results: Dict[str, bool] = {}
        for name in self._tools:
            info = await self.check_availability(name)
            results[name] = info["available"]
        return results

    async def get_for_task(self, task_description: str) -> List[ToolInfo]:
        await self._ensure_loaded()
        task_lower = task_description.lower()

        keyword_map: Dict[str, List[str]] = {
            "git": ["version control", "commit", "branch", "merge", "diff", "history", "revert", "clone", "git"],
            "python": ["python", "script", "pip", "virtualenv", "pylint", "type hint"],
            "node": ["javascript", "typescript", "npm", "yarn", "package.json", "node"],
            "docker": ["container", "docker", "image", "compose", "sandbox", "isolate"],
            "vscode": ["editor", "ide", "debug", "intellisense", "vscode"],
            "playwright": ["browser", "automate", "web scraping", "e2e test", "playwright", "screenshot"],
            "fusion360": ["cad", "3d model", "assembly", "simulate", "fusion", "parametric"],
            "kicad": ["pcb", "schematic", "circuit", "electronics", "gerber", "kicad"],
            "arduino": ["firmware", "embedded", "microcontroller", "iot", "arduino", "serial"],
            "blender": ["render", "3d render", "animation", "blender", "mesh"],
            "sqlite": ["database", "sql", "query", "sqlite", "table", "schema"],
            "curl": ["http request", "api call", "fetch", "curl", "rest api"],
            "pytest": ["test", "assert", "fixture", "mock", "coverage", "pytest"],
            "eslint": ["lint", "code style", "eslint", "js lint", "ts lint"],
            "black": ["format", "python format", "black", "code style python"],
        }

        scores: Dict[str, float] = {}
        for tool_name, keywords in keyword_map.items():
            if tool_name not in self._tools:
                continue
            score = 0.0
            for kw in keywords:
                if kw in task_lower:
                    score += 1.0
            if score > 0:
                scores[tool_name] = score

        if not scores:
            return list(self._tools.values())

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [self._tools[name] for name, _ in ranked if name in self._tools]

    async def get_common_fixes(self, error_type: str) -> List[Dict]:
        await self._ensure_loaded()
        fixes: List[Dict] = []
        et = error_type.lower()
        for t in self._tools.values():
            for cf in t.common_failures:
                if et in cf.get("error", "").lower() or et in cf.get("fix", "").lower():
                    fixes.append({"tool": t.name, "error": cf["error"], "fix": cf["fix"]})
        return fixes

    async def register(self, tool_info: ToolInfo) -> ToolInfo:
        await self._ensure_loaded()
        self._tools[tool_info.name] = tool_info
        self._category_index.setdefault(tool_info.category, []).append(tool_info.name)
        return tool_info
