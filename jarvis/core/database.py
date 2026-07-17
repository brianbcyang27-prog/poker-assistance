"""Unified async SQLite database for JARVIS."""

import aiosqlite
from typing import Optional
from pathlib import Path
from datetime import datetime
import json

from .config import get_config


class Database:
    """Async SQLite database with WAL mode."""
    
    def __init__(self):
        self._db: Optional[aiosqlite.Connection] = None
        self._config = get_config()
    
    async def connect(self):
        """Connect to the database."""
        self._db = await aiosqlite.connect(str(self._config.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._init_schema()
    
    async def close(self):
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None
    
    async def _init_schema(self):
        """Initialize database schema."""
        await self._db.executescript("""
            -- Preferences
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Projects
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                description TEXT DEFAULT '',
                language TEXT DEFAULT 'unknown',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Conversations
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Agent Messages
            CREATE TABLE IF NOT EXISTS agent_messages (
                id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                task_id TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                confidence REAL DEFAULT 0.0,
                issues TEXT DEFAULT '[]',
                result TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Workspaces
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                owner TEXT NOT NULL,
                status TEXT DEFAULT 'planning',
                progress REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            
            -- Tasks
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                assigned_to TEXT NOT NULL,
                status TEXT DEFAULT 'idle',
                priority INTEGER DEFAULT 5,
                dependencies TEXT DEFAULT '[]',
                result TEXT,
                confidence REAL DEFAULT 0.0,
                issues TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
            );
            
            -- Task History
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT NOT NULL,
                user_request TEXT NOT NULL,
                summary TEXT,
                tasks_json TEXT,
                workspace_id TEXT,
                owner TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Voice Samples
            CREATE TABLE IF NOT EXISTS voice_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Important Decisions
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Agent States (for persistence across restarts)
            CREATE TABLE IF NOT EXISTS agent_states (
                card_id TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'idle',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- LLM Conversation Context (for multi-turn persistence)
            CREATE TABLE IF NOT EXISTS llm_context (
                session_id TEXT PRIMARY KEY,
                context_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self._db.commit()
        
        # Upgrade projects table — add columns if missing (idempotent)
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
                await self._db.execute(
                    f"ALTER TABLE projects ADD COLUMN {col} DEFAULT {default}"
                )
            except Exception:
                pass  # Column already exists
        await self._db.commit()
    
    # Preferences
    async def set_preference(self, key: str, value: str):
        await self._db.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, datetime.now().isoformat())
        )
        await self._db.commit()
    
    async def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        cursor = await self._db.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else default
    
    async def get_all_preferences(self) -> dict:
        cursor = await self._db.execute("SELECT key, value FROM preferences")
        rows = await cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}
    
    # Projects
    async def add_project(self, name: str, path: str, description: str = "", language: str = ""):
        await self._db.execute(
            """INSERT OR REPLACE INTO projects (name, path, description, language, updated_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (name, path, description, language, datetime.now().isoformat())
        )
        await self._db.commit()
    
    async def get_project(self, name: str) -> Optional[dict]:
        cursor = await self._db.execute("SELECT * FROM projects WHERE name = ?", (name,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    async def get_all_projects(self) -> list[dict]:
        cursor = await self._db.execute("SELECT * FROM projects ORDER BY updated_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    # Conversations
    async def save_conversation(self, session_id: str, role: str, content: str):
        await self._db.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        await self._db.commit()
    
    async def get_conversation(self, session_id: str, limit: int = 50) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in reversed(rows)]
    
    async def get_all_sessions(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get all conversation sessions with first user message as preview."""
        cursor = await self._db.execute(
            """SELECT session_id, 
                      MIN(timestamp) as started_at,
                      MAX(timestamp) as last_at,
                      COUNT(*) as message_count
               FROM conversations 
               GROUP BY session_id 
               ORDER BY last_at DESC 
               LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        sessions = []
        for row in await cursor.fetchall():
            d = dict(row)
            # Get first user message as preview
            preview_cursor = await self._db.execute(
                "SELECT content FROM conversations WHERE session_id = ? AND role = 'user' ORDER BY id LIMIT 1",
                (d["session_id"],)
            )
            preview_row = await preview_cursor.fetchone()
            d["preview"] = preview_row["content"][:100] if preview_row else ""
            sessions.append(d)
        return sessions
    
    async def get_session_count(self) -> int:
        cursor = await self._db.execute("SELECT COUNT(DISTINCT session_id) as count FROM conversations")
        row = await cursor.fetchone()
        return row["count"]
    
    # Agent Messages
    async def save_agent_message(self, message: dict):
        await self._db.execute(
            """INSERT OR REPLACE INTO agent_messages 
               (id, sender, receiver, task_id, content, status, confidence, issues, result, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message["id"], message["sender"], message["receiver"],
                message["task_id"], message["content"], message["status"],
                message["confidence"], json.dumps(message.get("issues", [])),
                json.dumps(message.get("result")), message["timestamp"]
            )
        )
        await self._db.commit()
    
    async def get_agent_messages(self, task_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        if task_id:
            cursor = await self._db.execute(
                "SELECT * FROM agent_messages WHERE task_id = ? ORDER BY timestamp DESC LIMIT ?",
                (task_id, limit)
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM agent_messages ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    # Workspaces
    async def save_workspace(self, workspace: dict):
        await self._db.execute(
            """INSERT OR REPLACE INTO workspaces 
               (id, goal, owner, status, progress, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                workspace["id"], workspace["goal"], workspace["owner"],
                workspace["status"], workspace["progress"],
                workspace.get("created_at", datetime.now().isoformat()),
                workspace.get("completed_at")
            )
        )
        await self._db.commit()
    
    async def get_workspace(self, workspace_id: str) -> Optional[dict]:
        cursor = await self._db.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    async def get_all_workspaces(self, status: Optional[str] = None) -> list[dict]:
        if status:
            cursor = await self._db.execute(
                "SELECT * FROM workspaces WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            cursor = await self._db.execute("SELECT * FROM workspaces ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    # Tasks
    async def save_task(self, task: dict, workspace_id: str):
        await self._db.execute(
            """INSERT OR REPLACE INTO tasks 
               (id, workspace_id, name, description, assigned_to, status, priority, 
                dependencies, result, confidence, issues, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task["id"], workspace_id, task["name"], task["description"],
                task["assigned_to"], task["status"], task["priority"],
                json.dumps(task.get("dependencies", [])),
                task.get("result"), task.get("confidence", 0.0),
                json.dumps(task.get("issues", [])),
                task.get("created_at", datetime.now().isoformat()),
                task.get("completed_at")
            )
        )
        await self._db.commit()
    
    async def get_workspace_tasks(self, workspace_id: str) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM tasks WHERE workspace_id = ? ORDER BY created_at",
            (workspace_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    # Decisions
    async def save_decision(self, topic: str, decision: str, reason: str = "", context: str = ""):
        await self._db.execute(
            "INSERT INTO decisions (topic, decision, reason, context) VALUES (?, ?, ?, ?)",
            (topic, decision, reason, context)
        )
        await self._db.commit()
    
    async def get_decisions(self, topic: Optional[str] = None, limit: int = 10) -> list[dict]:
        if topic:
            cursor = await self._db.execute(
                "SELECT * FROM decisions WHERE topic = ? ORDER BY created_at DESC LIMIT ?",
                (topic, limit)
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    # Agent States (persistence across restarts)
    async def save_agent_state(self, card_id: str, state: str):
        await self._db.execute(
            "INSERT OR REPLACE INTO agent_states (card_id, state, updated_at) VALUES (?, ?, ?)",
            (card_id, state, datetime.now().isoformat())
        )
        await self._db.commit()
    
    async def get_agent_states(self) -> dict[str, str]:
        cursor = await self._db.execute("SELECT card_id, state FROM agent_states")
        rows = await cursor.fetchall()
        return {row["card_id"]: row["state"] for row in rows}
    
    async def get_agent_state(self, card_id: str) -> Optional[str]:
        cursor = await self._db.execute("SELECT state FROM agent_states WHERE card_id = ?", (card_id,))
        row = await cursor.fetchone()
        return row["state"] if row else None
    
    # LLM Conversation Context (for multi-turn persistence)
    async def save_llm_context(self, session_id: str, context: list[dict]):
        await self._db.execute(
            "INSERT OR REPLACE INTO llm_context (session_id, context_json, updated_at) VALUES (?, ?, ?)",
            (session_id, json.dumps(context), datetime.now().isoformat())
        )
        await self._db.commit()
    
    async def get_llm_context(self, session_id: str) -> Optional[list[dict]]:
        cursor = await self._db.execute(
            "SELECT context_json FROM llm_context WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["context_json"])
        return None
    
    # Task History (for history page and replay)
    async def save_task_history(self, history: dict):
        await self._db.execute(
            """INSERT INTO task_history 
               (plan_id, user_request, summary, tasks_json, workspace_id, owner, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                history["plan_id"],
                history["user_request"],
                history.get("summary", ""),
                json.dumps(history.get("tasks", [])),
                history.get("workspace_id"),
                history.get("owner"),
                history.get("duration_ms"),
            )
        )
        await self._db.commit()
    
    async def get_task_history(self, limit: int = 20, offset: int = 0) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM task_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["tasks"] = json.loads(d.get("tasks_json", "[]"))
            del d["tasks_json"]
            result.append(d)
        return result
    
    async def get_task_history_count(self) -> int:
        cursor = await self._db.execute("SELECT COUNT(*) as count FROM task_history")
        row = await cursor.fetchone()
        return row["count"]
    
    async def get_task_history_by_id(self, plan_id: str) -> Optional[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM task_history WHERE plan_id = ?", (plan_id,)
        )
        row = await cursor.fetchone()
        if row:
            d = dict(row)
            d["tasks"] = json.loads(d.get("tasks_json", "[]"))
            del d["tasks_json"]
            return d
        return None


# Singleton instance
_db: Optional[Database] = None


async def get_db() -> Database:
    """Get or create the global database instance."""
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
    return _db
