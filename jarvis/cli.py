"""JARVIS Developer CLI — beautiful terminal interface for system management."""

import sys
import asyncio
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, Confirm
    from rich.tree import Tree
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from . import __version__


console = Console() if RICH_AVAILABLE else None


def print(message: str, *args, **kwargs):
    if console:
        console.print(message, *args, **kwargs)
    else:
        print(message, *args, **kwargs)


class JARVISCLI:
    """JARVIS Developer CLI with Rich interface."""
    
    def __init__(self):
        self.console = console
    
    def show_banner(self):
        """Display the JARVIS CLI banner."""
        banner = f"""
[bold cyan]
    ╦═╗╔═╗╔═╗╦    ╦╔═╗  ╔═╗╔═╗╔╦╗╔═╗╔╦╗╔═╗╔╦╗
    ╠╦╝║ ║║ ║║    ║║ ╦  ╠═╣║ ║║║║║╣ ║║║║╣ ║║
    ╩╚═╚═╝╚═╝╩═╝╩╝╚═╝  ╩ ╩╚═╝╩ ╩╚═╝╩ ╩╚═╝╩ ╩[/bold cyan]
    
[dim]    Engineering Suite v{__version__}[/dim]
[dim]    Type 'help' for commands, 'exit' to quit[/dim]
"""
        if self.console:
            self.console.print(banner)
        else:
            print(banner)
    
    def show_help(self):
        """Display available commands."""
        table = Table(title="Available Commands", box=box.ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        
        commands = [
            ("status", "Show system status"),
            ("workers", "List all workers"),
            ("king <division>", "Show king details (software/engineering/protocol/personal)"),
            ("tools", "List available tools"),
            ("knowledge query", "Query engineering knowledge base"),
            ("materials", "List available materials"),
            ("bearings", "List available bearings"),
            ("formula <name>", "Show engineering formula"),
            ("project <name>", "Create new engineering project"),
            ("cad", "CAD operations menu"),
            ("pcb", "PCB operations menu"),
            ("firmware", "Firmware operations menu"),
            ("test", "Hardware test operations"),
            ("export", "Export/compile operations"),
            ("help", "Show this help message"),
            ("exit", "Exit CLI"),
        ]
        
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        
        print(table)
    
    def show_status(self):
        """Show system status."""
        from .core.config import get_config
        config = get_config()
        
        table = Table(title="System Status", box=box.ROUNDED)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        # Version
        table.add_row("JARVIS", f"v{__version__}", "Engineering Suite")
        
        # Model
        table.add_row("LLM", "Connected", config.nvidia_model)
        
        # Workspace
        table.add_row("Workspace", "Active", str(config.workspace_path))
        
        # Workers
        table.add_row("Workers", "14", "8 Software + 6 Hardware")
        
        # Tools
        tools = self._get_tool_count()
        table.add_row("Tools", str(tools), "Available actions")
        
        print(table)
    
    def show_workers(self):
        """Show all workers with their cards."""
        table = Table(title="Agent Workers", box=box.ROUNDED)
        table.add_column("Card", style="cyan bold")
        table.add_column("Name", style="white")
        table.add_column("Title", style="dim")
        table.add_column("Division", style="yellow")
        
        # Software workers
        software = [
            ("♠K", "Architect", "System Architect", "Engineering"),
            ("♠Q", "Backend", "Backend Engineer", "Engineering"),
            ("♠J", "Frontend", "Frontend Engineer", "Engineering"),
            ("♠10", "React", "React Specialist", "Engineering"),
            ("♠9", "Python", "Python Expert", "Engineering"),
            ("♠8", "Testing", "Test Engineer", "Engineering"),
            ("♠7", "Docs", "Documentation Writer", "Engineering"),
            ("♠5", "A11y", "Accessibility Specialist", "Engineering"),
        ]
        
        # Hardware workers
        hardware = [
            ("♠4M", "Mechanical", "CAD/3D Modeling", "Hardware"),
            ("♠3", "PCB", "Circuit Board Designer", "Hardware"),
            ("♠2", "Firmware", "Embedded Systems", "Hardware"),
            ("♠4M", "Mechanical", "Mechanical Systems", "Hardware"),
            ("♠3T", "HW Test", "Hardware Test Engineer", "Hardware"),
        ]
        
        for card, name, title, division in software:
            table.add_row(card, name, title, division)
        
        print(table)
    
    def show_tools(self):
        """Show available engineering tools."""
        tree = Tree("[bold cyan]Engineering Tools[/bold cyan]")
        
        cad = tree.add("[yellow]CAD[/yellow]")
        cad.add("create_model(name, type, dimensions, material)")
        cad.add("add_feature(model_id, feature_type, params)")
        cad.add("export_model(model_id, format, path)")
        cad.add("list_models()")
        cad.add("get_model(model_id)")
        cad.add("measure_distance(model_id, point1, point2)")
        
        pcb = tree.add("[yellow]PCB[/yellow]")
        pcb.add("create_board(name, layers, dimensions)")
        pcb.add("add_component(board_id, component)")
        pcb.add("connect(board_id, net_name, pads)")
        pcb.add("route_board(board_id)")
        pcb.add("run_drc(board_id)")
        pcb.add("export_gerbers(board_id, path)")
        pcb.add("generate_bom(board_id)")
        
        firmware = tree.add("[yellow]Firmware[/yellow]")
        firmware.add("create_project(name, platform, board)")
        firmware.add("add_file(project_id, filename, content)")
        firmware.add("compile(project_id, config)")
        firmware.add("upload(project_id, port)")
        firmware.add("list_devices()")
        firmware.add("monitor(port, baud_rate)")
        
        mechanical = tree.add("[yellow]Mechanical[/yellow]")
        mechanical.add("get_material(name)")
        mechanical.add("list_materials()")
        mechanical.add("select_bearing(load, speed, bore)")
        mechanical.add("calculate_gear_ratio(driver, driven, rpm)")
        mechanical.add("calculate_beam_stress(force, length, width, height)")
        
        knowledge = tree.add("[yellow]Knowledge[/yellow]")
        knowledge.add("query(query, category)")
        knowledge.add("get_formula(name)")
        knowledge.add("recommend_material(requirements)")
        
        print(tree)
    
    def show_materials(self):
        """Show available materials."""
        from .engineering.knowledge import engineering_knowledge
        
        table = Table(title="Engineering Materials", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Yield (MPa)", justify="right")
        table.add_column("Cost ($/kg)", justify="right")
        table.add_column("Uses")
        
        for key, mat in engineering_knowledge.materials.items():
            table.add_row(
                key,
                mat.name,
                f"{mat.yield_strength}",
                f"{mat.cost_per_kg:.2f}",
                ", ".join(mat.common_uses[:2]),
            )
        
        print(table)
    
    def show_bearings(self):
        """Show available bearings."""
        from .engineering.knowledge import engineering_knowledge
        
        table = Table(title="Bearing Catalog", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Bore (mm)", justify="right")
        table.add_column("OD (mm)", justify="right")
        table.add_column("Load (N)", justify="right")
        table.add_column("Speed (RPM)", justify="right")
        table.add_column("Price", justify="right")
        
        for b in engineering_knowledge.bearings:
            table.add_row(
                b.id,
                b.type,
                f"{b.bore}",
                f"{b.od}",
                f"{b.load_rating}",
                f"{b.speed_limit}",
                f"${b.price:.2f}",
            )
        
        print(table)
    
    def show_formula(self, name: str):
        """Show engineering formula."""
        from .engineering.knowledge import engineering_knowledge
        
        formula = engineering_knowledge.formulas.get(name)
        if formula:
            panel = Panel(
                f"[bold]{formula['name']}[/bold]\n\n"
                f"[cyan]{formula['formula']}[/cyan]\n\n"
                f"[yellow]Variables:[/yellow]\n" +
                "\n".join(f"  {k}: {v}" for k, v in formula["variables"].items()),
                title=f"Formula: {name}",
                box=box.ROUNDED,
            )
            print(panel)
        else:
            print(f"[red]Formula '{name}' not found[/red]")
            print("Available:", ", ".join(engineering_knowledge.formulas.keys()))
    
    def query_knowledge(self, query: str, category: str = None):
        """Query the engineering knowledge base."""
        from .engineering.knowledge import engineering_knowledge
        from rich.json import JSON
        import json
        
        result = engineering_knowledge.query(query, category)
        print(JSON(json.dumps(result, indent=2)))
    
    def show_cad_menu(self):
        """Show CAD operations menu."""
        table = Table(title="CAD Operations", box=box.ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        
        table.add_row("create", "Create new 3D model")
        table.add_row("export", "Export model to STL/STEP/OBJ")
        table.add_row("list", "List all models")
        table.add_row("measure", "Measure distance between points")
        
        print(table)
    
    def show_pcb_menu(self):
        """Show PCB operations menu."""
        table = Table(title="PCB Operations", box=box.ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        
        table.add_row("create", "Create new PCB board")
        table.add_row("route", "Route traces")
        table.add_row("drc", "Run design rule check")
        table.add_row("gerber", "Export Gerber files")
        table.add_row("bom", "Generate bill of materials")
        
        print(table)
    
    def show_firmware_menu(self):
        """Show firmware operations menu."""
        table = Table(title="Firmware Operations", box=box.ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        
        table.add_row("create", "Create new firmware project")
        table.add_row("compile", "Compile project")
        table.add_row("upload", "Upload to device")
        table.add_row("devices", "List connected devices")
        table.add_row("monitor", "Monitor serial port")
        
        print(table)
    
    def _get_tool_count(self) -> int:
        """Get count of available tools."""
        from .agents.tools import tools
        return len(tools.list_actions())
    
    def interactive(self):
        """Run interactive CLI."""
        self.show_banner()
        
        while True:
            try:
                if self.console:
                    user_input = self.console.input("[bold cyan]jarvis>[/bold cyan] ")
                else:
                    user_input = input("jarvis> ")
                
                if not user_input.strip():
                    continue
                
                parts = user_input.strip().split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd in ("exit", "quit", "q"):
                    print("[yellow]Goodbye![/yellow]")
                    break
                elif cmd == "help":
                    self.show_help()
                elif cmd == "status":
                    self.show_status()
                elif cmd == "workers":
                    self.show_workers()
                elif cmd == "tools":
                    self.show_tools()
                elif cmd == "materials":
                    self.show_materials()
                elif cmd == "bearings":
                    self.show_bearings()
                elif cmd == "formula":
                    if args:
                        self.show_formula(args.strip())
                    else:
                        print("[red]Usage: formula <name>[/red]")
                elif cmd in ("query", "knowledge"):
                    if args:
                        self.query_knowledge(args.strip())
                    else:
                        print("[red]Usage: query <search term>[/red]")
                elif cmd == "cad":
                    self.show_cad_menu()
                elif cmd == "pcb":
                    self.show_pcb_menu()
                elif cmd == "firmware":
                    self.show_firmware_menu()
                elif cmd == "king":
                    if args:
                        print(f"[yellow]King details for {args} coming soon...[/yellow]")
                    else:
                        print("[red]Usage: king <division>[/red]")
                elif cmd == "project":
                    if args:
                        print(f"[yellow]Creating project '{args}'...[/yellow]")
                        print("[dim]Use the web interface for full project creation[/dim]")
                    else:
                        print("[red]Usage: project <name>[/red]")
                elif cmd == "export":
                    print("[yellow]Export operations coming soon...[/yellow]")
                elif cmd == "test":
                    print("[yellow]Hardware test operations coming soon...[/yellow]")
                else:
                    print(f"[red]Unknown command: {cmd}[/red]")
                    print("[dim]Type 'help' for available commands[/dim]")
            
            except KeyboardInterrupt:
                print("\n[yellow]Use 'exit' to quit[/yellow]")
            except EOFError:
                break
            except Exception as e:
                print(f"[red]Error: {e}[/red]")


def main():
    """CLI entry point."""
    cli = JARVISCLI()
    
    if len(sys.argv) > 1:
        # Command-line arguments
        cmd = sys.argv[1]
        args = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        
        if cmd == "status":
            cli.show_status()
        elif cmd == "workers":
            cli.show_workers()
        elif cmd == "tools":
            cli.show_tools()
        elif cmd == "materials":
            cli.show_materials()
        elif cmd == "bearings":
            cli.show_bearings()
        elif cmd == "formula" and args:
            cli.show_formula(args)
        elif cmd in ("query", "knowledge") and args:
            cli.query_knowledge(args)
        elif cmd == "help":
            cli.show_help()
        else:
            cli.show_banner()
            cli.show_help()
    else:
        # Interactive mode
        cli.interactive()


if __name__ == "__main__":
    main()
