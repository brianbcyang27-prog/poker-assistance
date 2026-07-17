"""Project Memory — JARVIS remembers what you're working on.

When you say "I'm home, let's proceed with my project", JARVIS knows:
- Which project (most recently active)
- Where the code lives
- How to start the dev server
- What URL to open
- What AI tool to launch alongside

All context is persisted in SQLite and survives restarts.
"""

import json
import subprocess
import asyncio
from datetime import datetime
from typing import Optional
from pathlib import Path

from ..core.config import get_config


class ProjectMemory:
    """Manages project registry with activity tracking and auto-resume."""

    def __init__(self):
        self._config = get_config()

    async def _db(self):
        from ..core.database import get_db
        return await get_db()

    async def ensure_schema(self):
        """Add columns to projects table if they don't exist."""
        db = await self._db()
        # Try adding new columns (idempotent)
        for col, default in [
            ("active", "1"),
            ("last_worked_on", "NULL"),
            ("server_command", "''"),
            ("server_port", "0"),
            ("url", "''"),
            ("ai_tool_command", "''"),
            ("ai_tool_name", "''"),
            ("context", "'{}'"),
            ("status", "'active'"),
        ]:
            try:
                await db._db.execute(
                    f"ALTER TABLE projects ADD COLUMN {col} DEFAULT {default}"
                )
            except Exception:
                pass  # Column already exists
        await db._db.commit()

    async def register_project(
        self,
        name: str,
        path: str,
        description: str = "",
        language: str = "",
        server_command: str = "",
        server_port: int = 0,
        url: str = "",
        ai_tool_command: str = "",
        ai_tool_name: str = "",
        context: dict = None,
    ) -> dict:
        """Register or update a project."""
        await self.ensure_schema()
        db = await self._db()
        now = datetime.now().isoformat()

        await db._db.execute(
            """INSERT OR REPLACE INTO projects 
               (name, path, description, language, 
                active, last_worked_on, server_command, server_port,
                url, ai_tool_command, ai_tool_name, context, status,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 'active',
                       COALESCE((SELECT created_at FROM projects WHERE name = ?), ?),
                       ?)""",
            (
                name, path, description, language,
                now, server_command, server_port,
                url, ai_tool_command, ai_tool_name,
                json.dumps(context or {}),
                name, now, now,
            ),
        )
        await db._db.commit()
        return await self.get_project(name)

    async def get_project(self, name: str) -> Optional[dict]:
        await self.ensure_schema()
        db = await self._db()
        cursor = await db._db.execute(
            "SELECT * FROM projects WHERE name = ?", (name,)
        )
        row = await cursor.fetchone()
        if row:
            d = dict(row)
            if isinstance(d.get("context"), str):
                d["context"] = json.loads(d["context"])
            return d
        return None

    async def get_active_project(self) -> Optional[dict]:
        """Get the most recently worked on project."""
        await self.ensure_schema()
        db = await self._db()
        cursor = await db._db.execute(
            """SELECT * FROM projects 
               WHERE status = 'active' 
               ORDER BY last_worked_on DESC LIMIT 1"""
        )
        row = await cursor.fetchone()
        if row:
            d = dict(row)
            if isinstance(d.get("context"), str):
                d["context"] = json.loads(d["context"])
            return d
        return None

    async def record_activity(self, name: str):
        """Touch last_worked_on timestamp."""
        await self.ensure_schema()
        db = await self._db()
        now = datetime.now().isoformat()
        await db._db.execute(
            "UPDATE projects SET last_worked_on = ?, updated_at = ? WHERE name = ?",
            (now, now, name),
        )
        await db._db.commit()

    async def list_projects(self, status: Optional[str] = None) -> list[dict]:
        await self.ensure_schema()
        db = await self._db()
        if status:
            cursor = await db._db.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY last_worked_on DESC",
                (status,),
            )
        else:
            cursor = await db._db.execute(
                "SELECT * FROM projects ORDER BY last_worked_on DESC"
            )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("context"), str):
                d["context"] = json.loads(d["context"])
            result.append(d)
        return result

    async def delete_project(self, name: str) -> bool:
        await self.ensure_schema()
        db = await self._db()
        cursor = await db._db.execute(
            "DELETE FROM projects WHERE name = ?", (name,)
        )
        await db._db.commit()
        return cursor.rowcount > 0

    def build_resume_commands(self, project: dict) -> list[dict]:
        """Build shell commands to resume a project's environment.
        
        Server terminal: just opens in the project directory (user runs server manually).
        AI tool: launches directly.
        Browser: opens the URL.
        
        Returns a list of window descriptors:
        [{"title": "...", "command": "...", "dir": "..."}]
        """
        commands = []
        project_dir = project.get("path", "")

        # 1. Dev server terminal — just cd into the directory
        server_cmd = project.get("server_command", "")
        if server_cmd:
            commands.append({
                "title": f"Dev Server — {project['name']}",
                "command": f"cd {project_dir}",
                "dir": project_dir,
                "type": "server",
                "hint": server_cmd,  # Tell the user what to run
            })

        # 2. AI tool terminal
        ai_cmd = project.get("ai_tool_command", "")
        if ai_cmd:
            commands.append({
                "title": f"AI Tool — {project.get('ai_tool_name', 'AI')}",
                "command": ai_cmd,
                "dir": project_dir,
                "type": "ai_tool",
            })

        # 3. Browser URL
        url = project.get("url", "")
        if url:
            commands.append({
                "title": f"Browser — {project['name']}",
                "command": f"open {url}",
                "dir": project_dir,
                "type": "browser",
            })

        return commands

    def build_resume_script(self, project: dict) -> str:
        """Build a shell script that opens all project windows on macOS.
        
        Server terminal: opens in project dir with a hint comment.
        AI tool: launches directly.
        Browser: opens the URL.
        """
        commands = self.build_resume_commands(project)
        if not commands:
            return ""

        lines = ['#!/bin/bash', f'# Auto-generated by JARVIS to resume {project["name"]}', '']

        for i, cmd in enumerate(commands):
            title = cmd["title"]
            shell_cmd = cmd["command"]

            if cmd["type"] == "browser":
                lines.append(f'# Open browser')
                lines.append(f'{shell_cmd}')
                lines.append('')
            elif cmd["type"] == "server":
                # Open terminal in project dir with hint
                hint = cmd.get("hint", "")
                escaped_cmd = shell_cmd.replace('"', '\\"')
                escaped_title = title.replace('"', '\\"')
                escaped_hint = hint.replace('"', '\\"')
                lines.append(f'# Window {i + 1}: {title} (run manually)')
                lines.append(f'osascript -e \'tell application "Terminal"')
                lines.append(f'  activate')
                lines.append(f'  do script "{escaped_cmd}"')
                lines.append(f'  set custom title of front window to "{escaped_title}"')
                lines.append(f'  display dialog "Run: {escaped_hint}" with title "{escaped_title}" buttons {{"OK"}} default button "OK"')
                lines.append(f'end tell\'')
                lines.append('')
            else:
                # AI tool — launch directly
                escaped_cmd = shell_cmd.replace('"', '\\"')
                escaped_title = title.replace('"', '\\"')
                lines.append(f'# Window {i + 1}: {title}')
                lines.append(f'osascript -e \'tell application "Terminal"')
                lines.append(f'  activate')
                lines.append(f'  do script "{escaped_cmd}"')
                lines.append(f'  set custom title of front window to "{escaped_title}"')
                lines.append(f'end tell\'')
                lines.append('')

        return "\n".join(lines)


# Singleton
project_memory = ProjectMemory()
