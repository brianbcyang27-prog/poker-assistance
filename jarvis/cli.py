"""JARVIS CLI - Command line interface."""

import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

from .core.config import get_config
from .core.database import get_db
from .agents.jarvis import JarvisAgent
from .agents.kings import EngineeringKing, PersonalKing, ResearchKing, SystemKing
from .agents.workers import (
    ArchitectWorker, BackendWorker, FrontendWorker,
    ReactWorker, PythonWorker, TestingWorker, DocsWorker, A11yWorker,
    CalendarWorker, EmailWorker, TasksWorker, SchedulingWorker,
    WebResearchWorker, DocumentationWorker, FactCheckWorker,
    FilesWorker, TerminalWorker, ApplicationsWorker,
)

console = Console()


def initialize_agents() -> JarvisAgent:
    """Initialize the JARVIS agent hierarchy."""
    jarvis = JarvisAgent()
    
    # Create Kings
    eng_king = EngineeringKing()
    personal_king = PersonalKing()
    research_king = ResearchKing()
    system_king = SystemKing()
    
    # Register Kings
    jarvis.register_king(eng_king)
    jarvis.register_king(personal_king)
    jarvis.register_king(research_king)
    jarvis.register_king(system_king)
    
    # Register Engineering workers
    eng_king.register_worker(ArchitectWorker())
    eng_king.register_worker(BackendWorker())
    eng_king.register_worker(FrontendWorker())
    eng_king.register_worker(ReactWorker())
    eng_king.register_worker(PythonWorker())
    eng_king.register_worker(TestingWorker())
    eng_king.register_worker(DocsWorker())
    eng_king.register_worker(A11yWorker())
    
    # Register Personal workers
    personal_king.register_worker(CalendarWorker())
    personal_king.register_worker(EmailWorker())
    personal_king.register_worker(TasksWorker())
    personal_king.register_worker(SchedulingWorker())
    
    # Register Research workers
    research_king.register_worker(WebResearchWorker())
    research_king.register_worker(DocumentationWorker())
    research_king.register_worker(FactCheckWorker())
    
    # Register System workers
    system_king.register_worker(FilesWorker())
    system_king.register_worker(TerminalWorker())
    system_king.register_worker(ApplicationsWorker())
    
    return jarvis


async def main():
    """Run JARVIS CLI."""
    console.print(Panel.fit(
        "[bold cyan]JARVIS[/bold cyan] - Multi-Agent AI Operating System\n"
        "[dim]Type 'quit' to exit, 'status' to see agent hierarchy[/dim]",
        border_style="cyan"
    ))
    
    # Initialize
    config = get_config()
    db = await get_db()
    jarvis = initialize_agents()
    
    console.print("\n[green]System initialized.[/green]\n")
    
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            
            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]Goodbye.[/dim]")
                break
            
            if user_input.lower() == "status":
                status = jarvis.get_status()
                console.print(Panel(
                    f"[bold]JARVIS[/bold]: {status['state']}\n\n"
                    + "\n".join(
                        f"[bold]{k}[/bold]: {v['state']}"
                        for k, v in status['kings'].items()
                    ),
                    title="Agent Status",
                    border_style="cyan"
                ))
                continue
            
            if not user_input.strip():
                continue
            
            # Process through JARVIS
            console.print("\n[dim]Processing...[/dim]")
            
            response = await jarvis.process_user_request(user_input)
            
            console.print()
            console.print(Panel(
                Markdown(response),
                title="[bold cyan]JARVIS[/bold cyan]",
                border_style="cyan"
            ))
            console.print()
        
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye.[/dim]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")


def main_cli():
    """Entry point for CLI."""
    asyncio.run(main())


if __name__ == "__main__":
    main_cli()
