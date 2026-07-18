"""JARVIS v5.2.0 — Developer CLI.

Provides developer commands for the JARVIS engineering platform.
Requires: Python 3.9.6+, rich.

Usage:
    jarvis <command> [args]

Commands:
    doctor                  System health check
    benchmark               Performance benchmark
    profile <repo_path>     Profile a repository
    graph <repo_path>       Show architecture graph
    memory                  Show memory status
    research <query>        Research a topic
    architecture <repo_path>  Show architecture report
    mission <action> [args] Mission management
    plugins                 Plugin management
    dashboard <repo_path>   Show engineering dashboard
    index <repo_path>       Index a codebase
    scan <repo_path>        Scan for refactoring opportunities
"""

import asyncio
import importlib
import os
import sys
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.tree import Tree
    from rich import box
    from rich.text import Text
    from rich.columns import Columns
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich import print as rprint

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ── Version ──────────────────────────────────────────────────────────

__version__ = "5.2.0"


def _get_console() -> Any:
    """Get or create a Rich Console."""
    if RICH_AVAILABLE:
        return Console()
    return None


def _require_rich() -> None:
    """Raise if rich is not installed."""
    if not RICH_AVAILABLE:
        print("Error: 'rich' is required. Install with: pip install rich", file=sys.stderr)
        sys.exit(1)


# ── Commands ─────────────────────────────────────────────────────────


class Commands:
    """JARVIS v5.2.0 CLI command implementations.

    All methods are async for consistent execution.
    Uses Rich for all formatted output.
    """

    def __init__(self) -> None:
        _require_rich()
        self.console = _get_console()

    # ── helpers ────────────────────────────────────────────────────

    def _print(self, *args: Any, **kwargs: Any) -> None:
        """Print with Rich if available, else fallback."""
        if self.console:
            self.console.print(*args, **kwargs)
        else:
            print(*args)

    def _panel(self, content: Any, title: str = "", **kwargs: Any) -> None:
        """Print a Rich Panel."""
        self._print(Panel(content, title=title, **kwargs))

    def _table(self, title: str = "", **kwargs: Any) -> Table:
        """Create a Rich Table."""
        if "box" not in kwargs:
            kwargs["box"] = box.ROUNDED
        t = Table(title=title, **kwargs)
        return t

    def _tree(self, label: str = "") -> Tree:
        """Create a Rich Tree."""
        return Tree(label)

    def _elapsed(self, start: float) -> str:
        """Format elapsed time."""
        return f"{time.time() - start:.3f}s"

    # ── 1. doctor ──────────────────────────────────────────────────

    async def doctor(self) -> None:
        """System health check — verify all JARVIS components."""
        self._print(Panel("JARVIS System Health Check", style="bold blue", box=box.DOUBLE))

        table = self._table(title="Health Status", expand=True)
        table.add_column("Component", style="cyan", ratio=1)
        table.add_column("Status", justify="center", ratio=1)
        table.add_column("Details", ratio=3)

        checks = await self._run_health_checks()
        for name, ok, detail in checks:
            status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
            table.add_row(name, status, detail)

        self._print(table)

        passed = sum(1 for _, ok, _ in checks if ok)
        total = len(checks)
        self._print()
        self._panel(
            f"{passed}/{total} checks passed",
            title="Summary",
            style="green" if passed == total else "yellow",
        )

    async def _run_health_checks(self) -> List[Tuple[str, bool, str]]:
        """Run all health checks and return results."""
        checks: List[Tuple[str, bool, str]] = []

        # Python version
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        checks.append(("Python", sys.version_info >= (3, 9), f"{sys.executable} ({py_ver})"))

        # Rich
        checks.append(("Rich", RICH_AVAILABLE, "Installed" if RICH_AVAILABLE else "Missing"))

        # Dependencies
        for pkg in ["openai", "pydantic", "aiohttp", "fastapi", "jinja2"]:
            try:
                mod = importlib.import_module(pkg)
                ver = getattr(mod, "__version__", "unknown")
                checks.append((pkg, True, f"v{ver}"))
            except ImportError:
                checks.append((pkg, False, "Not installed"))

        # Database
        db_path = os.path.join(os.getcwd(), "jarvis.db")
        if os.path.isfile(db_path):
            size = os.path.getsize(db_path)
            checks.append(("Database", True, f"jarvis.db ({size:,} bytes)"))
        else:
            checks.append(("Database", False, "jarvis.db not found in cwd"))

        # Browser (playwright)
        try:
            import playwright.async_api  # noqa: F401
            checks.append(("Browser", True, "Playwright available"))
        except ImportError:
            checks.append(("Browser", False, "Playwright not installed"))

        # LLM (openai)
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            checks.append(("LLM API Key", True, "OPENAI_API_KEY is set"))
        else:
            checks.append(("LLM API Key", False, "OPENAI_API_KEY not set"))

        # .env
        env_path = os.path.join(os.getcwd(), ".env")
        checks.append((".env file", os.path.isfile(env_path), env_path))

        # Git
        try:
            import subprocess
            proc = await asyncio.create_subprocess_exec(
                "git", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            ver = stdout.decode().strip() if proc.returncode == 0 else "not found"
            checks.append(("Git", proc.returncode == 0, ver))
        except Exception:
            checks.append(("Git", False, "Not available"))

        return checks

    # ── 2. benchmark ───────────────────────────────────────────────

    async def benchmark(self) -> None:
        """Performance benchmark — time key JARVIS operations."""
        self._print(Panel("JARVIS Performance Benchmark", style="bold blue", box=box.DOUBLE))

        table = self._table(title="Benchmark Results", expand=True)
        table.add_column("Operation", style="cyan", ratio=2)
        table.add_column("Time", justify="right", style="green", ratio=1)
        table.add_column("Details", ratio=3)

        repo_path = os.getcwd()

        # Repo indexing
        start = time.time()
        try:
            from jarvis.codebase_index import CodebaseIndex
            idx = CodebaseIndex()
            await idx.index(repo_path)
            stats = await idx.get_repo_stats()
            elapsed = self._elapsed(start)
            table.add_row(
                "Repo Indexing",
                elapsed,
                f"{stats.get('total_files', 0)} files, {stats.get('total_symbols', 0)} symbols, {stats.get('total_loc', 0)} LOC",
            )
        except Exception as e:
            table.add_row("Repo Indexing", self._elapsed(start), f"[red]Error: {e}[/red]")

        # Search
        start = time.time()
        try:
            results = await idx.search("main")
            elapsed = self._elapsed(start)
            table.add_row("Search (query='main')", elapsed, f"{len(results)} results")
        except Exception as e:
            table.add_row("Search", self._elapsed(start), f"[red]Error: {e}[/red]")

        # Graph building
        start = time.time()
        try:
            from jarvis.architecture_graph import ArchGraph
            graph = ArchGraph()
            await graph.build(repo_path)
            elapsed = self._elapsed(start)
            table.add_row(
                "Graph Building",
                elapsed,
                f"{len(graph.nodes)} nodes, {len(graph.edges)} edges",
            )
        except Exception as e:
            table.add_row("Graph Building", self._elapsed(start), f"[red]Error: {e}[/red]")

        # Dashboard metrics collection
        start = time.time()
        try:
            from jarvis.dashboard import Dashboard
            dash = Dashboard()
            metrics = await dash.collect(repo_path)
            elapsed = self._elapsed(start)
            table.add_row(
                "Metrics Collection",
                elapsed,
                f"health={metrics.health_score}, architecture={metrics.architecture_score}",
            )
        except Exception as e:
            table.add_row("Metrics Collection", self._elapsed(start), f"[red]Error: {e}[/red]")

        self._print(table)

    # ── 3. profile ─────────────────────────────────────────────────

    async def profile(self, repo_path: str) -> None:
        """Profile a repository — generate ProjectDNA."""
        self._print(Panel(f"Profiling: {repo_path}", style="bold blue", box=box.DOUBLE))

        if not os.path.isdir(repo_path):
            self._print(f"[red]Error: '{repo_path}' is not a directory[/red]")
            return

        start = time.time()
        try:
            from jarvis.repo_intelligence import RepoIntelligence
            ri = RepoIntelligence()
            dna = await ri.analyze(repo_path)
            elapsed = self._elapsed(start)
        except Exception as e:
            self._print(f"[red]Error: {e}[/red]")
            return

        # ProjectDNA summary
        tree = self._tree(f"[bold]{dna.name}[/bold]  [dim]({elapsed})[/dim]")
        tree.add(f"[cyan]Purpose:[/cyan] {dna.purpose}")
        tree.add(f"[cyan]Health:[/cyan] {dna.health_score}/100")
        tree.add(f"[cyan]Risk:[/cyan] {dna.risk_score}/100")
        tree.add(f"[cyan]Debt:[/cyan] {dna.debt_score}/100")

        lang_branch = tree.add("[cyan]Languages:[/cyan]")
        for lang, pct in sorted(dna.languages.items(), key=lambda x: x[1], reverse=True):
            lang_branch.add(f"{lang}: {pct}%")

        if dna.frameworks:
            fw_branch = tree.add("[cyan]Frameworks:[/cyan]")
            for fw in dna.frameworks:
                fw_branch.add(fw)

        tree.add(f"[cyan]Architecture:[/cyan] {dna.architecture_style}")
        tree.add(f"[cyan]Testing:[/cyan] {dna.testing_framework}")
        tree.add(f"[cyan]Deployment:[/cyan] {dna.deployment_method}")
        tree.add(f"[cyan]Doc Quality:[/cyan] {dna.documentation_quality}/100")

        if dna.patterns:
            pat_branch = tree.add("[cyan]Patterns:[/cyan]")
            for p in dna.patterns:
                pat_branch.add(p)

        if dna.ci_cd:
            ci_branch = tree.add("[cyan]CI/CD:[/cyan]")
            for ci in dna.ci_cd:
                ci_branch.add(ci)

        self._print(tree)

        # Coding style detail
        if dna.coding_style:
            cs = dna.coding_style
            if cs is not None:
                self._print()
                style_table = self._table(title="Coding Style")
                style_table.add_column("Metric", style="cyan")
                style_table.add_column("Value", justify="right")
                style_table.add_row("Avg Line Length", str(cs.avg_line_length))
                style_table.add_row("Avg Function Length", str(cs.avg_function_length))
                style_table.add_row("Max Function Length", str(cs.max_function_length))
                style_table.add_row("Naming Convention", cs.naming_convention)
                style_table.add_row("Docstring Coverage", f"{cs.docstring_coverage}%")
                style_table.add_row("Type Hint Coverage", f"{cs.type_hint_coverage}%")
                self._print(style_table)

    # ── 4. graph ───────────────────────────────────────────────────

    async def graph(self, repo_path: str) -> None:
        """Show architecture graph as Mermaid diagram + metrics."""
        self._print(Panel(f"Architecture Graph: {repo_path}", style="bold blue", box=box.DOUBLE))

        if not os.path.isdir(repo_path):
            self._print(f"[red]Error: '{repo_path}' is not a directory[/red]")
            return

        try:
            from jarvis.architecture_graph import ArchGraph
            graph = ArchGraph()
            await graph.build(repo_path)
        except Exception as e:
            self._print(f"[red]Error building graph: {e}[/red]")
            return

        # Metrics
        metrics_table = self._table(title="Graph Metrics")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", justify="right")

        metrics_table.add_row("Nodes", str(len(graph.nodes)))
        metrics_table.add_row("Edges", str(len(graph.edges)))

        # Node type breakdown
        type_counts: Dict[str, int] = Counter(n.type for n in graph.nodes.values())
        for ntype, count in type_counts.most_common():
            metrics_table.add_row(f"  {ntype}", str(count))

        # Edge type breakdown
        edge_type_counts: Dict[str, int] = Counter(e.type for e in graph.edges.values())
        for etype, count in edge_type_counts.most_common():
            metrics_table.add_row(f"  {etype} edges", str(count))

        self._print(metrics_table)

        # Mermaid diagram (truncate for large repos)
        self._print()
        self._print("[bold]Mermaid Diagram:[/bold]")
        self._print("[dim](top-level modules only)[/dim]")

        mermaid_lines = ["```mermaid", "graph TD"]

        # Only show top-level modules to keep diagram readable
        top_nodes = [
            n for n in graph.nodes.values()
            if n.type == "module" and "/" not in n.id
        ][:30]

        for node in top_nodes:
            safe_label = node.label.replace('"', "'")
            mermaid_lines.append(f'  {node.id}["{safe_label}"]')

        # Add edges between top-level modules
        shown_edges: set = set()
        for edge in graph.edges.values():
            src = edge.source.split("/")[0] if "/" in edge.source else edge.source
            tgt = edge.target.split("/")[0] if "/" in edge.target else edge.target
            if src != tgt and (src, tgt) not in shown_edges:
                if any(n.id == src for n in top_nodes) or any(n.id == tgt for n in top_nodes):
                    mermaid_lines.append(f"  {src} --> {tgt}")
                    shown_edges.add((src, tgt))
                if len(shown_edges) >= 40:
                    break

        mermaid_lines.append("```")
        self._print("\n".join(mermaid_lines))

    # ── 5. memory ──────────────────────────────────────────────────

    async def memory(self) -> None:
        """Show memory status — counts, recent entries, stats."""
        self._print(Panel("JARVIS Memory Status", style="bold blue", box=box.DOUBLE))

        # Try to use the database
        db_path = os.path.join(os.getcwd(), "jarvis.db")
        if not os.path.isfile(db_path):
            self._print("[yellow]No jarvis.db found in current directory.[/yellow]")
            self._print("[dim]Memory database stores mission history and learnings.[/dim]")
            return

        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            table = self._table(title="Memory Database", expand=True)
            table.add_column("Table", style="cyan")
            table.add_column("Rows", justify="right")
            table.add_column("Size (bytes)", justify="right")

            total_rows = 0
            for t in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
                    count = cursor.fetchone()[0]
                    total_rows += count
                    table.add_row(t, str(count), "-")
                except Exception:
                    table.add_row(t, "[red]error[/red]", "-")

            self._print(table)
            self._print(f"\n[bold]Total: {len(tables)} tables, {total_rows} rows[/bold]")

            # Show recent entries if possible
            for t in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
                    count = cursor.fetchone()[0]
                    if count > 0:
                        cursor.execute(f"PRAGMA table_info([{t}])")
                        columns = [row[1] for row in cursor.fetchall()]
                        cursor.execute(f"SELECT * FROM [{t}] ORDER BY rowid DESC LIMIT 5")
                        rows = cursor.fetchall()
                        if rows:
                            self._print()
                            recent_table = self._table(title=f"Recent from '{t}' (last 5)")
                            for col in columns[:6]:
                                recent_table.add_column(col, style="cyan", max_width=30)
                            for row in rows:
                                vals = [str(v)[:30] if v is not None else "" for v in row[:6]]
                                recent_table.add_row(*vals)
                            self._print(recent_table)
                            break  # Show only the first populated table
                except Exception:
                    pass

            conn.close()

        except Exception as e:
            self._print(f"[red]Error reading database: {e}[/red]")

        # File stats
        size = os.path.getsize(db_path)
        self._print()
        self._panel(
            f"Path: {db_path}\nSize: {size:,} bytes ({size / 1024:.1f} KB)",
            title="Database Info",
        )

    # ── 6. research ────────────────────────────────────────────────

    async def research(self, query: str) -> None:
        """Research a topic — search GitHub, PyPI, and more."""
        self._print(Panel(f"Researching: {query}", style="bold blue", box=box.DOUBLE))

        try:
            from jarvis.research import ResearchEngine
            engine = ResearchEngine()

            sources = ["github", "pypi"]
            for source in sources:
                self._print(f"\n[bold cyan]Searching {source}...[/bold cyan]")
                start = time.time()
                findings = await engine.search(query, source=source, limit=5)
                elapsed = self._elapsed(start)

                if not findings:
                    self._print(f"  [dim]No results ({elapsed})[/dim]")
                    continue

                table = self._table(title=f"{source.title()} Results", expand=True)
                table.add_column("Title", style="cyan", ratio=2)
                table.add_column("Description", ratio=3)
                table.add_column("Stars", justify="right", style="yellow", ratio=1)
                table.add_column("Relevance", justify="right", style="green", ratio=1)

                for f in findings:
                    stars_str = str(f.stars) if f.stars else "-"
                    rel_pct = f"{f.relevance * 100:.0f}%"
                    desc = f.description[:80] + "..." if len(f.description) > 80 else f.description
                    table.add_row(f.title, desc, stars_str, rel_pct)

                self._print(table)
                self._print(f"[dim]  Found {len(findings)} results in {elapsed}[/dim]")

        except Exception as e:
            self._print(f"[red]Research error: {e}[/red]")

    # ── 7. architecture ────────────────────────────────────────────

    async def architecture(self, repo_path: str) -> None:
        """Show architecture report — metrics + analysis."""
        self._print(Panel(f"Architecture Report: {repo_path}", style="bold blue", box=box.DOUBLE))

        if not os.path.isdir(repo_path):
            self._print(f"[red]Error: '{repo_path}' is not a directory[/red]")
            return

        try:
            from jarvis.dashboard import Dashboard
            from jarvis.repo_intelligence import RepoIntelligence

            dash = Dashboard()
            ri = RepoIntelligence()

            start = time.time()
            metrics, dna = await asyncio.gather(
                dash.collect(repo_path),
                ri.analyze(repo_path),
            )
            elapsed = self._elapsed(start)

            # Overview
            tree = self._tree(f"[bold]{dna.name}[/bold]  [dim]({elapsed})[/dim]")
            tree.add(f"[cyan]Purpose:[/cyan] {dna.purpose}")
            tree.add(f"[cyan]Architecture Style:[/cyan] {dna.architecture_style}")
            tree.add(f"[cyan]Health Score:[/cyan] {metrics.health_score}/100")
            tree.add(f"[cyan]Architecture Score:[/cyan] {metrics.architecture_score}/100")
            self._print(tree)

            # Metrics grid
            self._print()
            scores_table = self._table(title="Quality Metrics", expand=True)
            scores_table.add_column("Metric", style="cyan", ratio=1)
            scores_table.add_column("Score", justify="right", ratio=1)
            scores_table.add_column("Grade", justify="center", ratio=1)

            def _grade(score: float) -> str:
                if score >= 90:
                    return "[green]A[/green]"
                elif score >= 80:
                    return "[green]B[/green]"
                elif score >= 70:
                    return "[yellow]C[/yellow]"
                elif score >= 60:
                    return "[yellow]D[/yellow]"
                return "[red]F[/red]"

            for name, score in [
                ("Health", metrics.health_score),
                ("Test Coverage", metrics.test_coverage),
                ("Security", metrics.security_score),
                ("Performance", metrics.performance_score),
                ("Complexity", metrics.complexity_score),
                ("Duplication", metrics.duplication_score),
                ("Documentation", metrics.documentation_score),
                ("Architecture", metrics.architecture_score),
            ]:
                scores_table.add_row(name, f"{score}/100", _grade(score))

            self._print(scores_table)

            # Code stats
            self._print()
            stats_tree = self._tree("[bold]Codebase Statistics[/bold]")
            stats_tree.add(f"[cyan]Total LOC:[/cyan] {metrics.total_loc:,}")
            stats_tree.add(f"[cyan]Total Files:[/cyan] {metrics.total_files:,}")
            stats_tree.add(f"[cyan]Classes:[/cyan] {metrics.total_classes:,}")
            stats_tree.add(f"[cyan]Functions:[/cyan] {metrics.total_functions:,}")
            stats_tree.add(f"[cyan]Tests:[/cyan] {metrics.total_tests:,}")
            stats_tree.add(f"[cyan]Dead Code:[/cyan] {metrics.dead_code_count:,}")

            if metrics.languages:
                lang_branch = stats_tree.add("[cyan]Languages:[/cyan]")
                for lang, count in sorted(metrics.languages.items(), key=lambda x: x[1], reverse=True):
                    lang_branch.add(f"{lang}: {count} files")

            self._print(stats_tree)

        except Exception as e:
            self._print(f"[red]Error: {e}[/red]")

    # ── 8. mission ─────────────────────────────────────────────────

    async def mission(self, action: str, *args: str) -> None:
        """Mission management — list, status, cancel."""
        self._print(Panel("Mission Management", style="bold blue", box=box.DOUBLE))

        try:
            from jarvis.mission import MissionManager
            manager = MissionManager()
            await manager.load()

            if action == "list":
                await self._mission_list(manager)
            elif action == "status":
                if not args:
                    self._print("[red]Usage: jarvis mission status <mission_id>[/red]")
                    return
                await self._mission_status(manager, args[0])
            elif action == "cancel":
                if not args:
                    self._print("[red]Usage: jarvis mission cancel <mission_id>[/red]")
                    return
                await self._mission_cancel(manager, args[0])
            else:
                self._print(f"[red]Unknown action: {action}[/red]")
                self._print("[dim]Available: list, status, cancel[/dim]")

        except Exception as e:
            self._print(f"[red]Mission error: {e}[/red]")

    async def _mission_list(self, manager: Any) -> None:
        """List active missions."""
        active = await manager.list_active()
        completed = await manager.list_completed()

        all_missions = active + completed
        if not all_missions:
            self._print("[dim]No missions found.[/dim]")
            return

        table = self._table(title="Missions", expand=True)
        table.add_column("ID", style="cyan", ratio=2)
        table.add_column("Status", justify="center", ratio=1)
        table.add_column("Priority", justify="center", ratio=1)
        table.add_column("Request", ratio=3)
        table.add_column("Created", style="dim", ratio=2)

        for m in all_missions:
            status_style = {
                "completed": "green",
                "failed": "red",
                "executing": "yellow",
                "created": "blue",
                "researching": "blue",
                "paused": "dim",
            }.get(str(m.status), "white")

            table.add_row(
                m.id,
                f"[{status_style}]{m.status}[/{status_style}]",
                m.priority,
                m.user_request[:60] + "..." if len(m.user_request) > 60 else m.user_request,
                m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "-",
            )

        self._print(table)
        self._print(f"[dim]{len(active)} active, {len(completed)} completed[/dim]")

    async def _mission_status(self, manager: Any, mission_id: str) -> None:
        """Show mission status."""
        mission = await manager.get(mission_id)
        if not mission:
            self._print(f"[red]Mission '{mission_id}' not found.[/red]")
            return

        tree = self._tree(f"[bold]{mission.id}[/bold]")
        tree.add(f"[cyan]Status:[/cyan] {mission.status}")
        tree.add(f"[cyan]Priority:[/cyan] {mission.priority}")
        tree.add(f"[cyan]Stage:[/cyan] {mission.current_stage}")
        tree.add(f"[cyan]Goal:[/cyan] {mission.goal}")
        tree.add(f"[cyan]Created:[/cyan] {mission.created_at}")

        if mission.started_at:
            tree.add(f"[cyan]Started:[/cyan] {mission.started_at}")
        if mission.completed_at:
            tree.add(f"[cyan]Completed:[/cyan] {mission.completed_at}")

        tree.add(f"[cyan]Research Findings:[/cyan] {len(mission.research_findings)}")
        tree.add(f"[cyan]Tool Candidates:[/cyan] {len(mission.tool_candidates)}")
        tree.add(f"[cyan]Execution Steps:[/cyan] {len(mission.execution_results)}")
        tree.add(f"[cyan]Verification:[/cyan] {len(mission.verification_results)}")
        tree.add(f"[cyan]Review Items:[/cyan] {len(mission.review_items)}")

        if mission.errors:
            err_branch = tree.add("[red]Errors:[/red]")
            for err in mission.errors[-5:]:
                err_branch.add(err)

        self._print(tree)

        # Progress
        progress = await manager.get_progress(mission_id)
        if progress.get("steps_total", 0) > 0:
            self._print()
            pct = progress.get("progress_pct", 0)
            self._print(f"  Progress: {progress.get('steps_done', 0)}/{progress.get('steps_total', 0)} ({pct}%)")

    async def _mission_cancel(self, manager: Any, mission_id: str) -> None:
        """Cancel a mission."""
        mission = await manager.get(mission_id)
        if not mission:
            self._print(f"[red]Mission '{mission_id}' not found.[/red]")
            return

        if str(mission.status) in ("completed", "failed"):
            self._print(f"[yellow]Mission is already {mission.status}.[/yellow]")
            return

        await manager.cancel(mission_id)
        self._print(f"[green]Mission '{mission_id}' cancelled.[/green]")

    # ── 9. plugins ─────────────────────────────────────────────────

    async def plugins(self, action: str = "list", *args: str) -> None:
        """Plugin management — list, info."""
        self._print(Panel("Plugin Management", style="bold blue", box=box.DOUBLE))

        try:
            from jarvis.plugins import PluginManager
            mgr = PluginManager()
            await mgr.discover()

            if action == "list":
                await self._plugin_list(mgr)
            elif action == "info":
                if not args:
                    self._print("[red]Usage: jarvis plugins info <name>[/red]")
                    return
                await self._plugin_info(mgr, args[0])
            else:
                self._print(f"[red]Unknown action: {action}[/red]")
                self._print("[dim]Available: list, info[/dim]")

        except Exception as e:
            self._print(f"[red]Plugin error: {e}[/red]")

    async def _plugin_list(self, mgr: Any) -> None:
        """List discovered plugins."""
        plugins = mgr.list_plugins() if hasattr(mgr, "list_plugins") else []

        if not plugins:
            self._print("[dim]No plugins discovered.[/dim]")
            self._print("[dim]Place plugins in jarvis/plugins/ or ~/.jarvis/plugins/[/dim]")
            return

        table = self._table(title="Discovered Plugins", expand=True)
        table.add_column("Name", style="cyan", ratio=2)
        table.add_column("Type", ratio=1)
        table.add_column("Version", ratio=1)
        table.add_column("Description", ratio=3)
        table.add_column("Status", justify="center", ratio=1)

        for p in plugins:
            table.add_row(
                getattr(p, "name", str(p)),
                getattr(p, "type", "-"),
                getattr(p, "version", "-"),
                getattr(p, "description", "-")[:60],
                "[green]Ready[/green]",
            )

        self._print(table)

    async def _plugin_info(self, mgr: Any, name: str) -> None:
        """Show plugin details."""
        plugin = mgr.get_plugin(name) if hasattr(mgr, "get_plugin") else None
        if not plugin:
            self._print(f"[red]Plugin '{name}' not found.[/red]")
            return

        tree = self._tree(f"[bold]{name}[/bold]")
        for attr in ("name", "type", "version", "description", "author", "url"):
            val = getattr(plugin, attr, None)
            if val is not None:
                tree.add(f"[cyan]{attr.title()}:[/cyan] {val}")

        self._print(tree)

    # ── 10. dashboard ──────────────────────────────────────────────

    async def dashboard(self, repo_path: str) -> None:
        """Show engineering dashboard — all metrics in one view."""
        self._print(Panel(f"Engineering Dashboard: {repo_path}", style="bold blue", box=box.DOUBLE))

        if not os.path.isdir(repo_path):
            self._print(f"[red]Error: '{repo_path}' is not a directory[/red]")
            return

        try:
            from jarvis.dashboard import Dashboard
            dash = Dashboard()
            metrics = await dash.collect(repo_path)
        except Exception as e:
            self._print(f"[red]Error: {e}[/red]")
            return

        # Header
        def _grade(score: float) -> str:
            if score >= 90:
                return "[green]A[/green]"
            elif score >= 80:
                return "[green]B[/green]"
            elif score >= 70:
                return "[yellow]C[/yellow]"
            elif score >= 60:
                return "[yellow]D[/yellow]"
            return "[red]F[/red]"

        self._print(f"\n[bold]{repo_path}[/bold]\n")

        # Scores grid
        scores_table = self._table(title="Quality Scores", expand=True, box=box.SIMPLE_HEAVY)
        scores_table.add_column("Metric", style="cyan", ratio=1)
        scores_table.add_column("Score", justify="right", ratio=1)
        scores_table.add_column("Grade", justify="center", ratio=1)

        scores = [
            ("Health", metrics.health_score),
            ("Architecture", metrics.architecture_score),
            ("Test Coverage", metrics.test_coverage),
            ("Security", metrics.security_score),
            ("Performance", metrics.performance_score),
            ("Complexity", metrics.complexity_score),
            ("Duplication", metrics.duplication_score),
            ("Documentation", metrics.documentation_score),
            ("Technical Debt", metrics.debt_score),
        ]

        for name, score in scores:
            scores_table.add_row(name, f"{score:.1f}", _grade(score))

        self._print(scores_table)

        # Code stats
        self._print()
        stats_table = self._table(title="Codebase Stats", expand=True, box=box.SIMPLE_HEAVY)
        stats_table.add_column("Metric", style="cyan", ratio=1)
        stats_table.add_column("Value", justify="right", ratio=1)

        stats_table.add_row("Total LOC", f"{metrics.total_loc:,}")
        stats_table.add_row("Total Files", f"{metrics.total_files:,}")
        stats_table.add_row("Classes", f"{metrics.total_classes:,}")
        stats_table.add_row("Functions", f"{metrics.total_functions:,}")
        stats_table.add_row("Tests", f"{metrics.total_tests:,}")
        stats_table.add_row("Dead Code", f"{metrics.dead_code_count:,}")
        stats_table.add_row("Unused APIs", f"{metrics.unused_apis:,}")
        stats_table.add_row("Dependency Issues", f"{metrics.dependency_issues:,}")

        self._print(stats_table)

        # Language breakdown
        if metrics.languages:
            self._print()
            lang_table = self._table(title="Languages", expand=True, box=box.SIMPLE_HEAVY)
            lang_table.add_column("Language", style="cyan", ratio=1)
            lang_table.add_column("Files", justify="right", ratio=1)
            lang_table.add_column("Bar", ratio=3)

            max_count = max(metrics.languages.values()) if metrics.languages else 1
            for lang, count in sorted(metrics.languages.items(), key=lambda x: x[1], reverse=True):
                bar_len = int(count / max_count * 30)
                bar = "█" * bar_len
                lang_table.add_row(lang, str(count), f"[green]{bar}[/green]")

            self._print(lang_table)

        # Frameworks
        if metrics.frameworks:
            self._print()
            self._print(f"[bold]Frameworks:[/bold] {', '.join(metrics.frameworks)}")

        # Debt summary
        self._print()
        if metrics.debt_score > 50:
            self._panel(
                f"Debt Score: {metrics.debt_score:.1f}/100\n"
                f"Dead Code: {metrics.dead_code_count} | Unused APIs: {metrics.unused_apis}",
                title="Technical Debt Warning",
                style="red",
            )
        else:
            self._panel(
                f"Debt Score: {metrics.debt_score:.1f}/100 — healthy",
                title="Technical Debt",
                style="green",
            )

    # ── 11. index ──────────────────────────────────────────────────

    async def index(self, repo_path: str) -> None:
        """Index a codebase — build symbol index and print stats."""
        self._print(Panel(f"Indexing: {repo_path}", style="bold blue", box=box.DOUBLE))

        if not os.path.isdir(repo_path):
            self._print(f"[red]Error: '{repo_path}' is not a directory[/red]")
            return

        start = time.time()
        try:
            from jarvis.codebase_index import CodebaseIndex
            idx = CodebaseIndex()

            self._print("[cyan]Building index...[/cyan]")
            await idx.index(repo_path)
            elapsed = self._elapsed(start)

            stats = await idx.get_repo_stats()
        except Exception as e:
            self._print(f"[red]Error: {e}[/red]")
            return

        # Stats tree
        tree = self._tree(f"[bold]Index Complete[/bold]  [dim]({elapsed})[/dim]")
        tree.add(f"[cyan]Repo:[/cyan] {stats.get('repo_path', repo_path)}")
        tree.add(f"[cyan]Total Files:[/cyan] {stats.get('total_files', 0):,}")
        tree.add(f"[cyan]Total Symbols:[/cyan] {stats.get('total_symbols', 0):,}")
        tree.add(f"[cyan]Total LOC:[/cyan] {stats.get('total_loc', 0):,}")
        tree.add(f"[cyan]Complexity:[/cyan] {stats.get('total_complexity', 0):,}")

        # Languages
        lang_counts = stats.get("languages", {})
        if lang_counts:
            lang_branch = tree.add("[cyan]Languages:[/cyan]")
            for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
                lang_branch.add(f"{lang}: {count} files")

        self._print(tree)

        # Top symbols by complexity
        all_symbols = []
        for file_index in idx.repo_index.files.values():
            for sym in file_index.symbols:
                all_symbols.append(sym)

        if all_symbols:
            self._print()
            top_complex = sorted(all_symbols, key=lambda s: s.complexity, reverse=True)[:10]
            table = self._table(title="Top 10 Complex Symbols")
            table.add_column("Symbol", style="cyan", ratio=2)
            table.add_column("Kind", ratio=1)
            table.add_column("File", style="dim", ratio=2)
            table.add_column("Complexity", justify="right", style="yellow", ratio=1)

            for sym in top_complex:
                table.add_row(
                    sym.name,
                    sym.kind,
                    sym.file_path,
                    str(sym.complexity),
                )

            self._print(table)

    # ── 12. scan ───────────────────────────────────────────────────

    async def scan(self, repo_path: str) -> None:
        """Scan for refactoring opportunities — grouped by severity."""
        self._print(Panel(f"Refactoring Scan: {repo_path}", style="bold blue", box=box.DOUBLE))

        if not os.path.isdir(repo_path):
            self._print(f"[red]Error: '{repo_path}' is not a directory[/red]")
            return

        start = time.time()
        try:
            from jarvis.refactoring import RefactoringEngine, Severity
            engine = RefactoringEngine()
            issues = await engine.scan(repo_path)
            elapsed = self._elapsed(start)
        except Exception as e:
            self._print(f"[red]Error: {e}[/red]")
            return

        if not issues:
            self._print("[green]No issues found! Codebase looks clean.[/green]")
            self._print(f"[dim]Scan completed in {elapsed}[/dim]")
            return

        # Group by severity
        by_severity: Dict[str, List[Any]] = {}
        for issue in issues:
            sev = issue.severity.value
            by_severity.setdefault(sev, []).append(issue)

        # Summary
        summary = self._table(title=f"Scan Summary ({elapsed})", box=box.SIMPLE_HEAVY)
        summary.add_column("Severity", style="cyan", ratio=1)
        summary.add_column("Count", justify="right", ratio=1)

        severity_order = ["critical", "high", "medium", "low"]
        for sev in severity_order:
            if sev in by_severity:
                style = {"critical": "red", "high": "red", "medium": "yellow", "low": "dim"}.get(sev, "white")
                summary.add_row(f"[{style}]{sev.upper()}[/{style}]", str(len(by_severity[sev])))

        summary.add_row("[bold]TOTAL[/bold]", f"[bold]{len(issues)}[/bold]")
        self._print(summary)

        # Detailed issues by severity
        for sev in severity_order:
            if sev not in by_severity:
                continue

            style = {"critical": "red", "high": "red", "medium": "yellow", "low": "dim"}.get(sev, "white")
            self._print(f"\n[bold {style}]━━━ {sev.upper()} ({len(by_severity[sev])}) ━━━[/bold {style}]")

            table = self._table(box=box.ROUNDED, expand=True)
            table.add_column("Category", style="cyan", ratio=1)
            table.add_column("File", style="dim", ratio=2)
            table.add_column("Line", justify="right", ratio=1)
            table.add_column("Description", ratio=3)
            table.add_column("Suggestion", ratio=3)

            for issue in by_severity[sev][:20]:  # Limit to 20 per severity
                table.add_row(
                    issue.category.value,
                    os.path.basename(issue.file),
                    str(issue.line),
                    issue.description[:80],
                    issue.suggestion[:60],
                )

            remaining = len(by_severity[sev]) - 20
            if remaining > 0:
                table.add_row("[dim]...", f"[dim]{remaining} more issues", "", "", "")

            self._print(table)

        # Generate proposals summary
        try:
            from jarvis.refactoring import RefactoringEngine
            engine2 = RefactoringEngine()
            proposals = await engine2.generate_proposals(issues)
            if proposals:
                self._print(f"\n[bold]Generated {len(proposals)} refactoring proposals:[/bold]")
                for i, p in enumerate(proposals[:5], 1):
                    risk_style = {"low": "green", "medium": "yellow", "high": "red"}.get(
                        p.risk.value, "white"
                    )
                    self._print(
                        f"  {i}. [cyan]{p.title}[/cyan] "
                        f"({len(p.issues)} issues, risk: [{risk_style}]{p.risk.value}[/{risk_style}])"
                    )
        except Exception:
            pass


# ── CLI Entry Point ──────────────────────────────────────────────────


async def main() -> None:
    """Parse sys.argv and dispatch to the appropriate command."""
    _require_rich()

    args = sys.argv[1:]

    if not args:
        # Show banner
        console = _get_console()
        if console:
            console.print(Panel(
                f"[bold]JARVIS[/bold] [dim]v{__version__}[/dim]\n\n"
                "JARVIS Engineering Suite — Developer CLI\n\n"
                "[dim]Commands:[/dim]\n"
                "  doctor                  System health check\n"
                "  benchmark               Performance benchmark\n"
                "  profile <repo>          Profile a repository\n"
                "  graph <repo>            Architecture graph\n"
                "  memory                  Memory status\n"
                "  research <query>        Research a topic\n"
                "  architecture <repo>     Architecture report\n"
                "  mission <action> [args] Mission management\n"
                "  plugins [action] [name] Plugin management\n"
                "  dashboard <repo>        Engineering dashboard\n"
                "  index <repo>            Index a codebase\n"
                "  scan <repo>             Refactoring scan",
                title=f"JARVIS v{__version__}",
                style="bold blue",
                box=box.DOUBLE,
            ))
        else:
            print(f"JARVIS v{__version__} — Developer CLI")
            print("Run 'jarvis <command>' for help")
        return

    cmd = args[0].lower()
    cmd_args = args[1:]

    commands = Commands()

    dispatch = {
        "doctor": lambda: commands.doctor(),
        "benchmark": lambda: commands.benchmark(),
        "profile": lambda: commands.profile(cmd_args[0] if cmd_args else os.getcwd()),
        "graph": lambda: commands.graph(cmd_args[0] if cmd_args else os.getcwd()),
        "memory": lambda: commands.memory(),
        "research": lambda: commands.research(" ".join(cmd_args) if cmd_args else ""),
        "architecture": lambda: commands.architecture(cmd_args[0] if cmd_args else os.getcwd()),
        "mission": lambda: commands.mission(
            cmd_args[0] if cmd_args else "list",
            *cmd_args[1:],
        ),
        "plugins": lambda: commands.plugins(
            cmd_args[0] if cmd_args else "list",
            *cmd_args[1:],
        ),
        "dashboard": lambda: commands.dashboard(cmd_args[0] if cmd_args else os.getcwd()),
        "index": lambda: commands.index(cmd_args[0] if cmd_args else os.getcwd()),
        "scan": lambda: commands.scan(cmd_args[0] if cmd_args else os.getcwd()),
    }

    if cmd in dispatch:
        await dispatch[cmd]()
    elif cmd in ("-v", "--version", "version"):
        print(f"JARVIS v{__version__}")
    elif cmd in ("-h", "--help", "help"):
        # Re-show banner for help
        args.clear()
        await main()
    else:
        console = _get_console()
        if console:
            console.print(f"[red]Unknown command: {cmd}[/red]\n")
            console.print("[dim]Run 'jarvis' for available commands.[/dim]")
        else:
            print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
