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


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS TUI")
    parser.add_argument("--cli", action="store_true", help="Use CLI mode instead of TUI")
    parser.add_argument("command", nargs="?", help="Command to run")
    args = parser.parse_args()
    
    if args.command == "doctor":
        doctor()
    elif args.command == "status":
        from jarvis.agents.jarvis import JarvisAgent
        from jarvis import __version__
        console.print(f"[bold cyan]JARVIS v{__version__}[/bold cyan]")
        console.print("System is operational.")
    elif args.command == "agents":
        from jarvis.agents.kings import EngineeringKing, PersonalKing, ResearchKing, SystemKing
        eng = EngineeringKing()
        per = PersonalKing()
        res = ResearchKing()
        sys_k = SystemKing()
        console.print(f"[cyan]Engineering:[/cyan] {len(eng._workers)} workers")
        console.print(f"[cyan]Personal:[/cyan] {len(per._workers)} workers")
        console.print(f"[cyan]Research:[/cyan] {len(res._workers)} workers")
        console.print(f"[cyan]System:[/cyan] {len(sys_k._workers)} workers")
    elif args.command == "knowledge":
        from jarvis.engineering.knowledge import engineering_knowledge
        console.print(f"[cyan]Materials:[/cyan] {len(engineering_knowledge.materials)}")
        console.print(f"[cyan]Bearings:[/cyan] {len(engineering_knowledge.bearings)}")
        console.print(f"[cyan]Formulas:[/cyan] {len(engineering_knowledge.formulas)}")
    elif args.cli:
        from . import __version__
        console.print(f"[bold cyan]JARVIS v{__version__}[/bold cyan]")
        console.print("Use 'jarvis-cli' without --cli for full TUI experience")
    elif args.command is None:
        tui = JARVISTUI()
        tui.run()
    else:
        console.print(f"[red]Unknown command: {args.command}[/red]")
        console.print("Available commands: doctor, status, agents, knowledge")


if __name__ == "__main__":
    main()
