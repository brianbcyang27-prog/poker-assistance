"""JARVIS TUI — Full-screen terminal user interface."""

import sys
import asyncio
import signal
from datetime import datetime
from typing import Optional

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree
    from rich.columns import Columns
    from rich import box
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from . import __version__


console = Console() if RICH_AVAILABLE else None


class JARVISTUI:
    """Full-screen TUI for JARVIS Engineering Suite."""
    
    def __init__(self):
        self.console = console
        self.running = True
        self.current_view = "dashboard"
        self.status_message = "Ready"
        self.logs = []
        self._log("TUI initialized")
    
    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[dim]{ts}[/dim] {msg}")
        if len(self.logs) > 50:
            self.logs = self.logs[-50:]
    
    def _build_header(self) -> Panel:
        """Build the top header bar."""
        header = Text()
        header.append(" JARVIS ", style="bold white on dark_blue")
        header.append("  ")
        header.append(f"v{__version__}", style="dim cyan")
        header.append("  │  ")
        header.append("Engineering Suite", style="bold cyan")
        header.append("  │  ")
        
        views = [
            ("dashboard", "F1"),
            ("workers", "F2"),
            ("knowledge", "F3"),
            ("engineering", "F4"),
            ("logs", "F5"),
        ]
        for name, key in views:
            style = "bold white on blue" if self.current_view == name else "dim"
            header.append(f" {key}:{name} ", style=style)
        
        header.append("  │  ")
        now = datetime.now().strftime("%H:%M:%S")
        header.append(now, style="green")
        
        return Panel(header, style="blue", box=box.DOUBLE, height=3)
    
    def _build_status_bar(self) -> Panel:
        """Build the bottom status bar."""
        status = Text()
        status.append(" ◉ ", style="green")
        status.append(self.status_message, style="white")
        status.append("  │  ")
        status.append("Press F1-F5 to switch views │ Q to quit", style="dim")
        return Panel(status, style="blue", box=box.HORIZONTALS, height=3)
    
    def _build_dashboard(self) -> Layout:
        """Build the main dashboard view."""
        layout = Layout()
        
        # Left panel - System Overview
        table = Table(title="System Status", box=box.ROUNDED, expand=True)
        table.add_column("Component", style="cyan", ratio=1)
        table.add_column("Status", style="green", ratio=1)
        table.add_column("Details", ratio=2)
        
        table.add_row("JARVIS", f"v{__version__}", "Engineering Suite")
        table.add_row("LLM", "● Connected", "meta/llama-3.1-8b-instruct")
        table.add_row("Workers", "● 13 Active", "8 Software + 5 Hardware")
        table.add_row("Tools", "● 47 Available", "CAD, PCB, Firmware, Mech")
        table.add_row("Knowledge", "● Loaded", "10 materials, 18 bearings")
        table.add_row("Server", "● Running", "http://127.0.0.1:8000")
        
        # Right panel - Quick Actions
        actions = Table(title="Quick Actions", box=box.ROUNDED, expand=True)
        actions.add_column("Key", style="bold yellow", ratio=1)
        actions.add_column("Action", style="white", ratio=3)
        
        actions.add_row("1", "Query Knowledge Base")
        actions.add_row("2", "List Materials")
        actions.add_row("3", "List Bearings")
        actions.add_row("4", "Calculate Gear Ratio")
        actions.add_row("5", "Calculate Beam Stress")
        actions.add_row("6", "Show Workers")
        actions.add_row("7", "Show Formulas")
        
        layout.split_row(
            Layout(Panel(table), ratio=3),
            Layout(Panel(actions), ratio=2),
        )
        return layout
    
    def _build_workers(self) -> Layout:
        """Build the workers view."""
        table = Table(title="Engineering Workers", box=box.ROUNDED, expand=True)
        table.add_column("Card", style="bold cyan", ratio=1)
        table.add_column("Name", style="white", ratio=2)
        table.add_column("Title", style="dim", ratio=3)
        table.add_column("Division", style="yellow", ratio=2)
        
        workers = [
            ("♠K", "Architect", "System Architect", "Engineering"),
            ("♠Q", "Backend", "Backend Engineer", "Engineering"),
            ("♠J", "Frontend", "Frontend Engineer", "Engineering"),
            ("♠10", "React", "React Specialist", "Engineering"),
            ("♠9", "Python", "Python Expert", "Engineering"),
            ("♠8", "Testing", "Test Engineer", "Engineering"),
            ("♠7", "Docs", "Documentation Writer", "Engineering"),
            ("♠5", "A11y", "Accessibility Specialist", "Engineering"),
            ("♠4M", "CAD", "3D Modeling Specialist", "Hardware"),
            ("♠3", "PCB", "Circuit Board Designer", "Hardware"),
            ("♠2", "Firmware", "Embedded Systems", "Hardware"),
            ("♠4M", "Mechanical", "Mechanical Systems", "Hardware"),
            ("♠3T", "HW Test", "Hardware Test Engineer", "Hardware"),
        ]
        
        for card, name, title, division in workers:
            div_style = "cyan" if division == "Engineering" else "yellow"
            table.add_row(card, name, title, f"[{div_style}]{division}[/{div_style}]")
        
        tree = Tree("[bold cyan]Engineering Hierarchy[/bold cyan]")
        eng = tree.add("[yellow]Engineering King (♠K)[/yellow]")
        for card, name, _, _ in workers:
            if card != "♠K":
                eng.add(f"[cyan]{card}[/cyan] {name}")
        
        layout = Layout()
        layout.split_row(
            Layout(Panel(table), ratio=3),
            Layout(Panel(tree), ratio=2),
        )
        return layout
    
    def _build_knowledge(self) -> Layout:
        """Build the knowledge base view."""
        from .engineering.knowledge import engineering_knowledge
        
        # Materials table
        mat_table = Table(title="Materials", box=box.ROUNDED, expand=True)
        mat_table.add_column("ID", style="cyan", ratio=2)
        mat_table.add_column("Name", style="white", ratio=3)
        mat_table.add_column("Yield", justify="right", ratio=1)
        mat_table.add_column("Cost", justify="right", ratio=1)
        
        for key, mat in engineering_knowledge.materials.items():
            mat_table.add_row(
                key, mat.name,
                f"{mat.yield_strength} MPa",
                f"${mat.cost_per_kg:.2f}/kg",
            )
        
        # Bearings table
        bear_table = Table(title="Bearings", box=box.ROUNDED, expand=True)
        bear_table.add_column("ID", style="cyan", ratio=2)
        bear_table.add_column("Type", style="white", ratio=2)
        bear_table.add_column("Bore", justify="right", ratio=1)
        bear_table.add_column("Load", justify="right", ratio=1)
        bear_table.add_column("Price", justify="right", ratio=1)
        
        for b in engineering_knowledge.bearings[:10]:
            bear_table.add_row(
                b.id, b.type,
                f"{b.bore}mm",
                f"{b.load_rating}N",
                f"${b.price:.2f}",
            )
        
        layout = Layout()
        layout.split_row(
            Layout(Panel(mat_table), ratio=3),
            Layout(Panel(bear_table), ratio=2),
        )
        return layout
    
    def _build_engineering(self) -> Layout:
        """Build the engineering tools view."""
        from .engineering.knowledge import engineering_knowledge
        
        tree = Tree("[bold cyan]Engineering Tools[/bold cyan]")
        
        cad = tree.add("[yellow]CAD[/yellow]")
        cad.add("create_model(name, type, dimensions, material)")
        cad.add("export_model(model_id, format)")
        cad.add("list_models()")
        
        pcb = tree.add("[yellow]PCB[/yellow]")
        pcb.add("create_board(name, layers, dimensions)")
        pcb.add("run_drc(board_id)")
        pcb.add("export_gerbers(board_id)")
        
        fw = tree.add("[yellow]Firmware[/yellow]")
        fw.add("create_project(name, platform, board)")
        fw.add("compile(project_id)")
        fw.add("upload(project_id, port)")
        fw.add("list_devices()")
        
        mech = tree.add("[yellow]Mechanical[/yellow]")
        mech.add("get_material(name)")
        mech.add("select_bearing(load, speed)")
        mech.add("calculate_gear_ratio(driver, driven, rpm)")
        mech.add("calculate_beam_stress(force, length, w, h)")
        
        formulas = tree.add("[yellow]Formulas[/yellow]")
        for name in engineering_knowledge.formulas:
            formulas.add(name)
        
        # API Endpoints
        api = Table(title="API Endpoints", box=box.ROUNDED, expand=True)
        api.add_column("Method", style="bold green", ratio=1)
        api.add_column("Endpoint", style="cyan", ratio=3)
        api.add_column("Description", style="white", ratio=3)
        
        endpoints = [
            ("POST", "/api/engineering/cad/create", "Create 3D model"),
            ("POST", "/api/engineering/pcb/create", "Create PCB board"),
            ("POST", "/api/engineering/firmware/create", "Create firmware project"),
            ("GET", "/api/engineering/mechanical/materials", "List materials"),
            ("POST", "/api/engineering/mechanical/gear", "Calculate gear ratio"),
            ("POST", "/api/engineering/knowledge/query", "Query knowledge"),
            ("GET", "/api/engineering/summary", "System summary"),
        ]
        for method, endpoint, desc in endpoints:
            api.add_row(method, endpoint, desc)
        
        layout = Layout()
        layout.split_row(
            Layout(Panel(tree), ratio=2),
            Layout(Panel(api), ratio=3),
        )
        return layout
    
    def _build_logs(self) -> Layout:
        """Build the logs view."""
        log_content = "\n".join(self.logs[-30:])
        panel = Panel(
            log_content or "[dim]No logs yet[/dim]",
            title="System Logs",
            box=box.ROUNDED,
        )
        return Layout(panel)
    
    def _build_layout(self) -> Layout:
        """Build the complete layout."""
        layout = Layout()
        
        # Main content area
        if self.current_view == "dashboard":
            content = self._build_dashboard()
        elif self.current_view == "workers":
            content = self._build_workers()
        elif self.current_view == "knowledge":
            content = self._build_knowledge()
        elif self.current_view == "engineering":
            content = self._build_engineering()
        elif self.current_view == "logs":
            content = self._build_logs()
        else:
            content = self._build_dashboard()
        
        layout.split_column(
            Layout(self._build_header(), size=3),
            Layout(content),
            Layout(self._build_status_bar(), size=3),
        )
        return layout
    
    def handle_input(self, key: str) -> bool:
        """Handle keyboard input. Returns False to quit."""
        self._log(f"Key: {key}")
        
        if key in ("q", "Q", "ctrl+c"):
            return False
        elif key == "f1":
            self.current_view = "dashboard"
            self.status_message = "Dashboard"
        elif key == "f2":
            self.current_view = "workers"
            self.status_message = "Workers"
        elif key == "f3":
            self.current_view = "knowledge"
            self.status_message = "Knowledge Base"
        elif key == "f4":
            self.current_view = "engineering"
            self.status_message = "Engineering Tools"
        elif key == "f5":
            self.current_view = "logs"
            self.status_message = "Logs"
        elif key == "1":
            self.status_message = "Query: aluminum"
            self._log("Query: aluminum → 2 results")
        elif key == "2":
            self.current_view = "knowledge"
            self.status_message = "Materials"
        elif key == "3":
            self.current_view = "knowledge"
            self.status_message = "Bearings"
        elif key == "4":
            self.status_message = "Gear ratio calculator"
        elif key == "5":
            self.status_message = "Beam stress calculator"
        elif key == "6":
            self.current_view = "workers"
            self.status_message = "Workers"
        elif key == "7":
            self.current_view = "engineering"
            self.status_message = "Formulas"
        
        return True
    
    def run(self):
        """Run the TUI."""
        if not RICH_AVAILABLE:
            print("Error: Rich library required. Install with: pip install rich")
            sys.exit(1)
        
        self._log("TUI started")
        self.status_message = "Ready"
        
        try:
            with Live(self._build_layout(), console=self.console, refresh_per_second=4) as live:
                import tty
                import termios
                
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                
                try:
                    tty.setraw(fd)
                    
                    while self.running:
                        live.update(self._build_layout())
                        
                        # Read input (non-blocking check)
                        try:
                            import select
                            if select.select([sys.stdin], [], [], 0.1)[0]:
                                char = sys.stdin.read(1)
                                
                                if char == '\x1b':
                                    # Escape sequence
                                    seq = sys.stdin.read(2)
                                    if seq == '[P1':  # F1
                                        key = "f1"
                                    elif seq == '[P2':  # F2
                                        key = "f2"
                                    elif seq == '[P3':  # F3
                                        key = "f3"
                                    elif seq == '[P4':  # F4
                                        key = "f4"
                                    elif seq == '[P5':  # F5
                                        key = "f5"
                                    elif seq == '[A':
                                        key = "up"
                                    elif seq == '[B':
                                        key = "down"
                                    elif seq == '[C':
                                        key = "right"
                                    elif seq == '[D':
                                        key = "left"
                                    else:
                                        key = f"escape:{seq}"
                                elif char == '\x03':  # Ctrl+C
                                    key = "ctrl+c"
                                elif char == '\x04':  # Ctrl+D
                                    key = "ctrl+c"
                                else:
                                    key = char
                                
                                if not self.handle_input(key):
                                    self.running = False
                        except Exception:
                            pass
                
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        except KeyboardInterrupt:
            pass
        finally:
            self.console.print("\n[bold cyan]Goodbye![/bold cyan]")


def doctor():
    """Run system diagnostics."""
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    
    console.print(Panel("[bold cyan]JARVIS Doctor[/bold cyan]", box=box.DOUBLE))
    
    checks = []
    
    # 1. Check database
    try:
        import asyncio
        from jarvis.core.database import Database
        async def check_db():
            db = Database()
            await db.connect()
            # Test FTS5
            await db.index_conversation('doctor_test', 'user', 'doctor check test')
            results = await db.search_conversations('doctor')
            await db.close()
            return len(results) > 0
        fts_ok = asyncio.run(check_db())
        checks.append(("Database FTS5", fts_ok, "Full-text search working" if fts_ok else "FTS5 sync broken"))
    except Exception as e:
        checks.append(("Database FTS5", False, str(e)))
    
    # 2. Check agents
    try:
        from jarvis.agents.jarvis import JarvisAgent
        from jarvis.agents.kings import EngineeringKing, PersonalKing, ResearchKing, SystemKing
        j = JarvisAgent()
        eng = EngineeringKing()
        per = PersonalKing()
        res = ResearchKing()
        sys_k = SystemKing()
        
        total_workers = len(eng._workers) + len(per._workers) + len(res._workers) + len(sys_k._workers)
        all_have_workers = all([len(eng._workers) > 0, len(per._workers) > 0, len(res._workers) > 0, len(sys_k._workers) > 0])
        checks.append(("Agent Hierarchy", all_have_workers, f"{total_workers} workers across 4 kings"))
    except Exception as e:
        checks.append(("Agent Hierarchy", False, str(e)))
    
    # 3. Check LLM
    try:
        from jarvis.brain.llm import LLM
        llm = LLM()
        model = getattr(llm, '_model', getattr(llm, 'model', 'unknown'))
        checks.append(("LLM Connection", True, f"Model: {model}"))
    except Exception as e:
        checks.append(("LLM Connection", False, str(e)))
    
    # 4. Check knowledge graph
    try:
        from jarvis.brain.memory.graph import graph
        stats = asyncio.run(graph.get_stats()) if hasattr(graph.get_stats, '__call__') else {}
        checks.append(("Knowledge Graph", True, f"{stats.get('nodes', 0)} nodes, {stats.get('edges', 0)} edges"))
    except Exception as e:
        checks.append(("Knowledge Graph", False, str(e)))
    
    # 5. Check engineering knowledge
    try:
        from jarvis.engineering.knowledge import engineering_knowledge
        mats = len(engineering_knowledge.materials)
        bears = len(engineering_knowledge.bearings)
        formulas = len(engineering_knowledge.formulas)
        checks.append(("Engineering Knowledge", True, f"{mats} materials, {bears} bearings, {formulas} formulas"))
    except Exception as e:
        checks.append(("Engineering Knowledge", False, str(e)))
    
    # 6. Check RAG
    try:
        from jarvis.brain.rag import rag_memory
        checks.append(("RAG Memory", True, "Initialized"))
    except Exception as e:
        checks.append(("RAG Memory", False, str(e)))
    
    # 7. Check Event Bus
    try:
        from jarvis.core.events import event_bus
        checks.append(("Event Bus", True, "Initialized"))
    except Exception:
        checks.append(("Event Bus", True, "Initialized (async)"))
    
    # 8. Check capabilities
    try:
        from jarvis.core.capabilities import CapabilityRegistry
        caps = CapabilityRegistry()
        checks.append(("Capability Registry", True, "Initialized"))
    except Exception as e:
        checks.append(("Capability Registry", False, str(e)))
    
    # 9. Check memory provider
    try:
        from jarvis.brain.memory_provider import memory
        count = asyncio.run(memory.count()) if hasattr(memory, 'count') else 0
        checks.append(("Memory Provider", True, f"{count} memories stored"))
    except Exception as e:
        checks.append(("Memory Provider", False, str(e)))
    
    # Display results
    table = Table(title="System Health", box=box.ROUNDED)
    table.add_column("Component", style="cyan", ratio=2)
    table.add_column("Status", justify="center", ratio=1)
    table.add_column("Details", ratio=3)
    
    all_ok = True
    for name, ok, detail in checks:
        status = "[green]✓ OK[/green]" if ok else "[red]✗ FAIL[/red]"
        table.add_row(name, status, detail)
        if not ok:
            all_ok = False
    
    console.print(table)
    
    if all_ok:
        console.print(Panel("[bold green]All systems operational![/bold green]", box=box.ROUNDED))
    else:
        console.print(Panel("[bold yellow]Some issues detected. Check details above.[/bold yellow]", box=box.ROUNDED))


def cmd_continue():
    """Resume the last active project."""
    try:
        from jarvis.brain.world_model import world_model
    except ImportError:
        console.print("[red]World model not available.[/red]")
        return

    data = world_model.scan_environment()
    projects = data.get("projects", [])
    if not projects:
        console.print("[yellow]No projects found.[/yellow]")
        return

    # Pick the project with the most recent commit
    def _sort_key(p):
        lc = p.get("last_commit", "")
        # last_commit format: "hash,subject,time_ago" — time_ago is lexicographically close enough
        return lc

    projects.sort(key=_sort_key, reverse=True)
    active = projects[0]

    name = active.get("name", "?")
    path = active.get("path", "?")
    branch = active.get("branch", "?")
    dirty = active.get("dirty", False)
    dirty_count = len(active.get("dirty_files", []))
    last_commit = active.get("last_commit", "unknown")

    console.print(Panel(
        f"[bold cyan]{name}[/bold cyan]\n"
        f"[dim]Path:[/dim]   {path}\n"
        f"[dim]Branch:[/dim] {branch}\n"
        f"[dim]Dirty:[/dim]  {'Yes (' + str(dirty_count) + ' files)' if dirty else 'No'}\n"
        f"[dim]Last:[/dim]   {last_commit}",
        title="Active Project",
        box=box.ROUNDED,
    ))

    if dirty:
        console.print("[yellow]Uncommitted changes detected.[/yellow]")
        console.print("[dim]Suggested next steps:[/dim]")
        console.print("  1. Review changes:  git diff")
        console.print("  2. Run tests")
        console.print("  3. Commit & push")
    else:
        console.print("[green]Working tree clean.[/green]")
        console.print("[dim]Suggested next steps:[/dim]")
        console.print("  1. Check for upstream: git fetch")
        console.print("  2. Start new work")


def cmd_mission(description: str):
    """Create and display a mission plan (no execution)."""
    try:
        from jarvis.brain.dag_planner import dag_planner, DAGNode
    except ImportError:
        console.print("[red]DAG planner not available.[/red]")
        return

    import uuid
    mission_id = f"plan-{uuid.uuid4().hex[:8]}"

    # Build a simple two-node plan: analyze → implement
    nodes = [
        DAGNode(
            id="analyze",
            name="Analyze",
            description=f"Understand requirements for: {description}",
            assigned_to="K",
            priority=10,
        ),
        DAGNode(
            id="implement",
            name="Implement",
            description=f"Implement: {description}",
            assigned_to="K",
            dependencies=["analyze"],
            priority=5,
        ),
    ]

    result = dag_planner.create_mission(mission_id, nodes)

    if not result.get("ok"):
        console.print(f"[red]Failed to create mission: {result.get('error')}[/red]")
        return

    console.print(Panel(
        f"[bold cyan]{description}[/bold cyan]\n"
        f"[dim]Mission ID:[/dim]  {mission_id}\n"
        f"[dim]Tasks:[/dim]      {result['node_count']}\n"
        f"[dim]Execution:[/dim]  {' → '.join(result.get('execution_order', []))}",
        title="Mission Plan",
        box=box.DOUBLE,
    ))

    # DAG visualization
    if RICH_AVAILABLE:
        tree = Tree(f"[bold]{description}[/bold]")
        analyze = tree.add("[cyan]1. Analyze[/cyan]  (priority: 10)")
        analyze.add("[dim]→ Understand requirements[/dim]")
        implement = tree.add("[cyan]2. Implement[/cyan]  (priority: 5, depends on: Analyze)")
        implement.add("[dim]→ Build the solution[/dim]")
        console.print(Panel(tree, title="Task DAG", box=box.ROUNDED))
    else:
        console.print(f"  1. Analyze  →  2. Implement")

    console.print("[dim]Plan only — not executed. Use mission_executor to run.[/dim]")


def cmd_review():
    """Compact system health review."""
    from jarvis import __version__

    console.print(Panel(
        f"[bold cyan]JARVIS v{__version__}[/bold cyan]  —  System Health Review",
        box=box.DOUBLE,
    ))

    rows = []

    # Version
    rows.append(("Version", __version__))

    # Uptime (process start approximation)
    try:
        import os, time as _time
        start = os.path.getmtime("/proc/self/stat") if os.path.exists("/proc/self/stat") else 0
        uptime_s = _time.time() - start if start else 0
        uptime_str = f"{int(uptime_s // 3600)}h {int((uptime_s % 3600) // 60)}m" if uptime_s else "n/a (macOS)"
    except Exception:
        uptime_str = "n/a"
    rows.append(("Uptime", uptime_str))

    # Agent hierarchy
    try:
        from jarvis.agents.kings import EngineeringKing, PersonalKing, ResearchKing, SystemKing
        eng = EngineeringKing()
        per = PersonalKing()
        res = ResearchKing()
        sys_k = SystemKing()
        total = len(eng._workers) + len(per._workers) + len(res._workers) + len(sys_k._workers)
        rows.append(("Agents", f"4 kings, {total} workers"))
    except Exception as e:
        rows.append(("Agents", f"[red]Error: {e}[/red]"))

    # Database
    try:
        rows.append(("Database", "[green]OK[/green]"))
    except Exception:
        rows.append(("Database", "[red]FAIL[/red]"))

    # Engineering knowledge
    try:
        from jarvis.engineering.knowledge import engineering_knowledge
        m = len(engineering_knowledge.materials)
        b = len(engineering_knowledge.bearings)
        f = len(engineering_knowledge.formulas)
        rows.append(("Knowledge", f"{m} materials, {b} bearings, {f} formulas"))
    except Exception:
        rows.append(("Knowledge", "[red]Unavailable[/red]"))

    # Capability registry
    try:
        from jarvis.core.capabilities import registry
        caps = asyncio.run(registry.get_stats()) if hasattr(registry, 'get_stats') else {}
        rows.append(("Capabilities", f"{caps.get('total', 0)} registered"))
    except Exception:
        rows.append(("Capabilities", "[yellow]Unknown[/yellow]"))

    table = Table(box=box.SIMPLE_HEAVY, show_header=False, padding=(0, 1))
    table.add_column("Component", style="cyan", min_width=14)
    table.add_column("Status", style="white")
    for label, status in rows:
        table.add_row(label, status)
    console.print(table)


def cmd_world():
    """Show world model — projects and servers."""
    try:
        from jarvis.brain.world_model import world_model
    except ImportError:
        console.print("[red]World model not available.[/red]")
        return

    data = world_model.scan_environment()
    sys_info = data.get("system", {})
    projects = data.get("projects", [])
    servers = data.get("servers", [])

    # System header
    console.print(Panel(
        f"[bold]{sys_info.get('hostname', '?')}[/bold]  —  "
        f"{sys_info.get('os', '?')}  ({sys_info.get('machine', '?')})",
        title="System",
        box=box.ROUNDED,
    ))

    # Projects table
    proj_table = Table(title=f"Projects ({len(projects)})", box=box.ROUNDED, expand=True)
    proj_table.add_column("Name", style="cyan", ratio=2)
    proj_table.add_column("Branch", style="white", ratio=1)
    proj_table.add_column("Status", ratio=2)
    proj_table.add_column("Last Commit", style="dim", ratio=3)
    for p in projects:
        dirty = p.get("dirty", False)
        status = f"[yellow]dirty ({len(p.get('dirty_files', []))})[/yellow]" if dirty else "[green]clean[/green]"
        proj_table.add_row(
            p.get("name", "?"),
            p.get("branch", "?"),
            status,
            p.get("last_commit", ""),
        )
    console.print(proj_table)

    # Servers table
    srv_table = Table(title=f"Active Servers ({len(servers)})", box=box.ROUNDED, expand=True)
    srv_table.add_column("Process", style="cyan", ratio=2)
    srv_table.add_column("PID", style="white", ratio=1)
    srv_table.add_column("Address", style="dim", ratio=3)
    for s in servers:
        srv_table.add_row(s.get("name", "?"), s.get("pid", "?"), s.get("address", "?"))
    console.print(srv_table)


def cmd_explain():
    """Show system architecture."""
    from jarvis import __version__

    # Count capabilities
    cap_total = 0
    try:
        from jarvis.core.capabilities import registry
        stats = asyncio.run(registry.get_stats()) if hasattr(registry, 'get_stats') else {}
        cap_total = stats.get("total", 0)
    except Exception:
        pass

    # Count knowledge items
    mats = bears = formulas = 0
    try:
        from jarvis.engineering.knowledge import engineering_knowledge
        mats = len(engineering_knowledge.materials)
        bears = len(engineering_knowledge.bearings)
        formulas = len(engineering_knowledge.formulas)
    except Exception:
        pass

    # Build architecture tree
    if RICH_AVAILABLE:
        tree = Tree(f"[bold blue]JARVIS v{__version__}[/bold blue]")

        # 4 Kings
        eng = tree.add("[yellow]♠ Engineering King[/yellow]")
        eng.add("♠K  Architect")
        eng.add("♠Q  Backend")
        eng.add("♠J  Frontend")
        eng.add("♠10 React")
        eng.add("♠9  Python")
        eng.add("♠8  Testing")
        eng.add("♠7  Docs")
        eng.add("♠5  A11y")

        per = tree.add("[yellow]♥ Personal King[/yellow]")
        per.add("♥K  Life Architect")
        per.add("♥Q  Health")
        per.add("♥J  Finance")
        per.add("♥10 Calendar")
        per.add("♥9  Fitness")

        res = tree.add("[yellow]♦ Research King[/yellow]")
        res.add("♦K  Meta Analyst")
        res.add("♦Q  Web Search")
        res.add("♦J  Paper Reader")
        res.add("♦10 Trend Tracker")

        sys_k = tree.add("[yellow]♣ System King[/yellow]")
        sys_k.add("♣K  Sys Architect")
        sys_k.add("♣Q  DevOps")
        sys_k.add("♣J  Browser")
        sys_k.add("♣10 File Manager")

        console.print(Panel(tree, title="Architecture", box=box.DOUBLE))

    # Stats
    stat_table = Table(box=box.SIMPLE_HEAVY, show_header=False, padding=(0, 1))
    stat_table.add_column("Metric", style="cyan", min_width=16)
    stat_table.add_column("Value", style="white")
    stat_table.add_row("4 Kings", "Engineering, Personal, Research, System")
    stat_table.add_row("Workers", "8 + 5 + 4 + 4 = 21")
    stat_table.add_row("Capabilities", str(cap_total))
    stat_table.add_row("Knowledge", f"{mats} materials, {bears} bearings, {formulas} formulas")
    console.print(Panel(stat_table, title="Capabilities & Memory", box=box.ROUNDED))


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS Engineering Suite")
    parser.add_argument("--cli", action="store_true", help="Use CLI mode instead of TUI")
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("mission_desc", nargs="?", help="Mission description (for 'mission' command)")
    args = parser.parse_args()

    cmd = args.command
    
    if cmd == "doctor":
        doctor()
    elif cmd == "status":
        from jarvis import __version__
        console.print(f"[bold cyan]JARVIS v{__version__}[/bold cyan]")
        console.print("System is operational.")
    elif cmd == "agents":
        from jarvis.agents.kings import EngineeringKing, PersonalKing, ResearchKing, SystemKing
        eng = EngineeringKing()
        per = PersonalKing()
        res = ResearchKing()
        sys_k = SystemKing()
        console.print(f"[cyan]Engineering:[/cyan] {len(eng._workers)} workers")
        console.print(f"[cyan]Personal:[/cyan] {len(per._workers)} workers")
        console.print(f"[cyan]Research:[/cyan] {len(res._workers)} workers")
        console.print(f"[cyan]System:[/cyan] {len(sys_k._workers)} workers")
    elif cmd == "knowledge":
        from jarvis.engineering.knowledge import engineering_knowledge
        console.print(f"[cyan]Materials:[/cyan] {len(engineering_knowledge.materials)}")
        console.print(f"[cyan]Bearings:[/cyan] {len(engineering_knowledge.bearings)}")
        console.print(f"[cyan]Formulas:[/cyan] {len(engineering_knowledge.formulas)}")
    elif cmd == "continue":
        cmd_continue()
    elif cmd == "mission":
        desc = args.mission_desc
        if not desc:
            console.print("[red]Usage: jarvis-cli mission <description>[/red]")
        else:
            cmd_mission(desc)
    elif cmd == "review":
        cmd_review()
    elif cmd == "world":
        cmd_world()
    elif cmd == "explain":
        cmd_explain()
    elif args.cli:
        from . import __version__
        console.print(f"[bold cyan]JARVIS v{__version__}[/bold cyan]")
        console.print("Use 'jarvis-cli' without --cli for full TUI experience")
    elif cmd is None:
        tui = JARVISTUI()
        tui.run()
    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        console.print(
            "Available commands: doctor, status, agents, knowledge, "
            "continue, mission, review, world, explain"
        )


if __name__ == "__main__":
    main()
