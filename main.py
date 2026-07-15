#!/usr/bin/env python3
"""JARVIS - Personal AI Assistant

An Iron Man style personal AI assistant for managing software projects.
"""

import sys
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table

from jarvis.config import get_config
from jarvis.brain.llm import LLM
from jarvis.tasks.manager import TaskManager, TaskStatus
from jarvis.agents.opencode import OpenCodeAgent
from jarvis.safety.validator import SafetyValidator
from jarvis.memory.database import MemoryDatabase
from jarvis.voice.whisper import SpeechToText
from jarvis.voice.tts import TextToSpeech


console = Console()


class Jarvis:
    """Main JARVIS assistant class."""
    
    def __init__(self):
        self.config = get_config()
        self.llm = LLM()
        self.task_manager = TaskManager()
        self.opencode = OpenCodeAgent()
        self.safety = SafetyValidator()
        self.memory = MemoryDatabase()
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.running = False
        self.session_id = str(uuid.uuid4())[:8]
        self.voice_mode = False
    
    def start(self):
        """Start JARVIS."""
        self.running = True
        self._load_preferences()
        self._show_welcome()
        self._main_loop()
    
    def _load_preferences(self):
        """Load user preferences from memory."""
        name = self.memory.get_preference("user_name", "Brian")
        self.user_name = name
    
    def _show_welcome(self):
        """Display welcome message."""
        voice_status = "✓ Enabled" if self.stt.is_available() else "✗ Disabled"
        tts_status = "✓ Enabled" if self.tts.is_available() else "✗ Disabled"
        backend = "NVIDIA" if self.llm.use_nvidia else "Ollama"
        
        welcome = f"""
# 🤖 JARVIS Online

**Personal AI Assistant v2.0**

Hello, {self.user_name}. I'm JARVIS, your AI assistant.

**Status:**
- LLM Backend: {backend}
- Voice Input: {voice_status}
- Voice Output: {tts_status}

**Commands:**
- Type any request to get help
- `plan <request>` - Create a task plan
- `tasks` - Show active tasks
- `history` - Show completed tasks
- `voice` - Toggle voice mode
- `voice on/off` - Enable/disable voice
- `memory` - Show stored memories
- `remember <key> <value>` - Store a preference
- `projects` - Show known projects
- `learn <project> <path>` - Learn about a project
- `switch ollama` - Switch to local Ollama
- `switch nvidia` - Switch to NVIDIA API
- `clear` - Clear conversation history
- `exit` or `quit` - Exit JARVIS

**Example:**
> Prepare BlockFlow v2.1 release
> Create a new React component
> Fix the bug in the login module
"""
        console.print(Panel(Markdown(welcome), title="[bold blue]JARVIS[/bold blue]"))
    
    def _main_loop(self):
        """Main conversation loop."""
        while self.running:
            try:
                if self.voice_mode and self.stt.is_available():
                    console.print("\n[bold cyan]🎤 Listening...[/bold cyan]")
                    user_input = self.stt.transcribe_microphone(duration=5)
                    if user_input:
                        console.print(f"[bold cyan]You:[/bold cyan] {user_input}")
                    else:
                        continue
                else:
                    user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ('exit', 'quit', 'q'):
                    self._exit()
                    break
                
                if user_input.lower() == 'clear':
                    self.llm.clear_history()
                    console.print("[dim]History cleared.[/dim]")
                    continue
                
                if user_input.lower() == 'tasks':
                    self._show_active_tasks()
                    continue
                
                if user_input.lower() == 'history':
                    self._show_completed_tasks()
                    continue
                
                if user_input.lower() == 'voice':
                    self.voice_mode = not self.voice_mode
                    status = "enabled" if self.voice_mode else "disabled"
                    console.print(f"[dim]Voice mode {status}.[/dim]")
                    continue
                
                if user_input.lower().startswith('voice '):
                    mode = user_input[6:].strip().lower()
                    if mode == 'on':
                        self.voice_mode = True
                        console.print("[dim]Voice mode enabled.[/dim]")
                    elif mode == 'off':
                        self.voice_mode = False
                        console.print("[dim]Voice mode disabled.[/dim]")
                    continue
                
                if user_input.lower() == 'memory':
                    self._show_memory()
                    continue
                
                if user_input.lower().startswith('remember '):
                    parts = user_input[9:].strip().split(' ', 1)
                    if len(parts) == 2:
                        key, value = parts
                        self.memory.set_preference(key, value)
                        console.print(f"[dim]Remembered: {key} = {value}[/dim]")
                    else:
                        console.print("[dim]Usage: remember <key> <value>[/dim]")
                    continue
                
                if user_input.lower() == 'projects':
                    self._show_projects()
                    continue
                
                if user_input.lower().startswith('learn '):
                    parts = user_input[6:].strip().split(' ', 1)
                    if len(parts) == 2:
                        name, path = parts
                        self.memory.add_project(name, path)
                        console.print(f"[dim]Learned project: {name} at {path}[/dim]")
                    else:
                        console.print("[dim]Usage: learn <project_name> <path>[/dim]")
                    continue
                
                if user_input.lower() == 'switch ollama':
                    try:
                        self.llm.switch_to_ollama()
                        console.print("[dim]Switched to Ollama backend.[/dim]")
                    except RuntimeError as e:
                        console.print(f"[red]{e}[/red]")
                    continue
                
                if user_input.lower() == 'switch nvidia':
                    self.llm.switch_to_nvidia()
                    console.print("[dim]Switched to NVIDIA backend.[/dim]")
                    continue
                
                if user_input.lower().startswith('plan '):
                    request = user_input[5:].strip()
                    self._create_and_execute_plan(request)
                    continue
                
                self._handle_message(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[dim]Use 'exit' to quit JARVIS.[/dim]")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
    
    def _handle_message(self, message: str):
        """Handle a user message."""
        needs_confirmation, reason = self.safety.requires_confirmation(message)
        
        if needs_confirmation:
            if not self.safety.get_confirmation(message, reason):
                console.print("[dim]Action cancelled.[/dim]")
                return
        
        console.print("\n[bold yellow]Processing...[/bold yellow]")
        
        response = self.llm.chat(message)
        
        console.print("\n[bold green]JARVIS[/bold green]")
        console.print(Markdown(response))
        
        if self.tts.is_available():
            clean_response = response.replace('#', '').replace('*', '').replace('`', '')
            self.tts.speak(clean_response)
        
        self.memory.save_conversation(self.session_id, "user", message)
        self.memory.save_conversation(self.session_id, "assistant", response)
    
    def _create_and_execute_plan(self, request: str):
        """Create and execute a task plan."""
        console.print("\n[bold yellow]Analyzing request...[/bold yellow]")
        
        llm_response = self.llm.plan_task(request)
        
        if llm_response.get("parse_error"):
            console.print(f"[red]Failed to parse plan: {llm_response.get('raw_response', 'Unknown error')}[/red]")
            return
        
        plan = self.task_manager.create_plan_from_llm(request, llm_response)
        
        console.print("\n[bold green]Task Plan Created:[/bold green]")
        console.print(self.task_manager.format_plan(plan))
        
        console.print("\n[bold yellow]Execute this plan?[/bold yellow]")
        console.print("  [y] Yes - Execute all tasks")
        console.print("  [n] No - Cancel")
        console.print("  [e] Edit - Modify tasks before execution")
        
        choice = Prompt.ask("Choice", choices=['y', 'n', 'e'], default='y')
        
        if choice == 'n':
            console.print("[dim]Plan cancelled.[/dim]")
            return
        
        if choice == 'e':
            console.print("[dim]Edit mode coming soon. Using current plan.[/dim]")
        
        self._execute_plan(plan.id)
    
    def _execute_plan(self, plan_id: str):
        """Execute all tasks in a plan."""
        plan = self.task_manager.active_plans.get(plan_id)
        if not plan:
            console.print("[red]Plan not found.[/red]")
            return
        
        console.print(f"\n[bold cyan]Executing Plan: {plan.id}[/bold cyan]")
        
        while True:
            ready_tasks = self.task_manager.get_next_tasks(plan_id)
            
            if not ready_tasks:
                break
            
            for task in ready_tasks:
                console.print(f"\n[bold yellow]Executing: {task.name}[/bold yellow]")
                
                needs_confirmation, reason = self.safety.validate_task(
                    f"{task.description} (Agent: {task.agent})"
                )
                
                if needs_confirmation:
                    if not self.safety.get_confirmation(task.description, reason):
                        self.task_manager.update_task_status(
                            plan_id, task.id, TaskStatus.FAILED,
                            error="Cancelled by user"
                        )
                        continue
                
                self.task_manager.update_task_status(
                    plan_id, task.id, TaskStatus.IN_PROGRESS
                )
                
                if task.agent == "opencode":
                    result = self.opencode.execute_task(task)
                    
                    if result["success"]:
                        self.task_manager.update_task_status(
                            plan_id, task.id, TaskStatus.COMPLETED,
                            result=result["output"]
                        )
                        console.print(f"[green]✓ {task.name} completed[/green]")
                    else:
                        self.task_manager.update_task_status(
                            plan_id, task.id, TaskStatus.FAILED,
                            error=result["error"]
                        )
                        console.print(f"[red]✗ {task.name} failed: {result['error']}[/red]")
                
                console.print(self.task_manager.format_plan(plan))
        
        tasks_data = [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status.value,
            }
            for t in plan.tasks
        ]
        self.memory.save_task_history(
            plan_id=plan.id,
            user_request=plan.user_request,
            summary=plan.summary,
            tasks=tasks_data,
        )
        
        if plan.completed_at:
            console.print(f"\n[bold green]Plan {plan.id} completed![/bold green]")
        else:
            console.print(f"\n[bold yellow]Plan {plan.id} paused - waiting for dependencies[/bold yellow]")
    
    def _show_active_tasks(self):
        """Display active task plans."""
        if not self.task_manager.active_plans:
            console.print("[dim]No active task plans.[/dim]")
            return
        
        table = Table(title="Active Task Plans")
        table.add_column("ID", style="cyan")
        table.add_column("Request", style="white")
        table.add_column("Tasks", style="green")
        table.add_column("Progress", style="yellow")
        
        for plan_id, plan in self.task_manager.active_plans.items():
            completed = sum(
                1 for t in plan.tasks
                if t.status == TaskStatus.COMPLETED
            )
            total = len(plan.tasks)
            
            table.add_row(
                plan_id,
                plan.user_request[:50] + "..." if len(plan.user_request) > 50 else plan.user_request,
                str(total),
                f"{completed}/{total}"
            )
        
        console.print(table)
    
    def _show_completed_tasks(self):
        """Display completed task plans."""
        if not self.task_manager.completed_plans:
            console.print("[dim]No completed task plans.[/dim]")
            return
        
        table = Table(title="Completed Task Plans")
        table.add_column("ID", style="cyan")
        table.add_column("Request", style="white")
        table.add_column("Tasks", style="green")
        table.add_column("Completed", style="yellow")
        
        for plan in self.task_manager.completed_plans:
            completed = sum(
                1 for t in plan.tasks
                if t.status == TaskStatus.COMPLETED
            )
            
            table.add_row(
                plan.id,
                plan.user_request[:50] + "..." if len(plan.user_request) > 50 else plan.user_request,
                str(len(plan.tasks)),
                str(completed),
            )
        
        console.print(table)
    
    def _show_memory(self):
        """Display stored memories."""
        prefs = self.memory.get_all_preferences()
        projects = self.memory.get_all_projects()
        decisions = self.memory.get_decisions(limit=5)
        
        if prefs:
            console.print("\n[bold]User Preferences:[/bold]")
            for key, value in prefs.items():
                console.print(f"  {key}: {value}")
        
        if projects:
            console.print("\n[bold]Known Projects:[/bold]")
            for proj in projects:
                console.print(f"  {proj['name']}: {proj['path']}")
        
        if decisions:
            console.print("\n[bold]Recent Decisions:[/bold]")
            for dec in decisions:
                console.print(f"  [{dec['topic']}] {dec['decision']}")
        
        if not prefs and not projects and not decisions:
            console.print("[dim]No memories stored yet.[/dim]")
    
    def _show_projects(self):
        """Display known projects."""
        projects = self.memory.get_all_projects()
        
        if not projects:
            console.print("[dim]No projects learned yet. Use 'learn <name> <path>' to add one.[/dim]")
            return
        
        table = Table(title="Known Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Path", style="white")
        table.add_column("Language", style="green")
        table.add_column("Updated", style="yellow")
        
        for proj in projects:
            table.add_row(
                proj["name"],
                proj["path"],
                proj.get("language", "Unknown"),
                proj.get("updated_at", "Unknown"),
            )
        
        console.print(table)
    
    def _exit(self):
        """Exit JARVIS."""
        console.print(f"\n[bold blue]JARVIS[/bold blue]: Goodbye, {self.user_name}. Shutting down.")
        self.running = False


def main():
    """Main entry point."""
    try:
        jarvis = Jarvis()
        jarvis.start()
    except KeyboardInterrupt:
        console.print("\n[dim]JARVIS terminated.[/dim]")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()