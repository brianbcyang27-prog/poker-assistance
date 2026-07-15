import sqlite3
import json
from datetime import datetime
from typing import Optional
from pathlib import Path

from ..config import get_config


class MemoryDatabase:
    """SQLite-based persistent memory storage."""
    
    def __init__(self):
        config = get_config()
        self.db_path = config.memory_db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    path TEXT,
                    description TEXT,
                    language TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT,
                    user_request TEXT,
                    summary TEXT,
                    tasks_json TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS important_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    decision TEXT,
                    reason TEXT,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def set_preference(self, key: str, value: str):
        """Set a user preference."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, datetime.now().isoformat())
            )
            conn.commit()
    
    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a user preference."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else default
    
    def get_all_preferences(self) -> dict:
        """Get all user preferences."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_preferences")
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def add_project(self, name: str, path: str, description: str = "", language: str = ""):
        """Add or update a project."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO projects (name, path, description, language, updated_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                (name, path, description, language, datetime.now().isoformat())
            )
            conn.commit()
    
    def get_project(self, name: str) -> Optional[dict]:
        """Get project information."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "path": row[2],
                    "description": row[3],
                    "language": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                }
            return None
    
    def get_all_projects(self) -> list[dict]:
        """Get all projects."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "path": row[2],
                    "description": row[3],
                    "language": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                }
                for row in cursor.fetchall()
            ]
    
    def save_task_history(
        self,
        plan_id: str,
        user_request: str,
        summary: str,
        tasks: list[dict],
        status: str = "completed",
    ):
        """Save task history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO task_history (plan_id, user_request, summary, tasks_json, status, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (plan_id, user_request, summary, json.dumps(tasks), status, datetime.now().isoformat())
            )
            conn.commit()
    
    def get_task_history(self, limit: int = 10) -> list[dict]:
        """Get recent task history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM task_history ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [
                {
                    "id": row[0],
                    "plan_id": row[1],
                    "user_request": row[2],
                    "summary": row[3],
                    "tasks": json.loads(row[4]),
                    "status": row[5],
                    "created_at": row[6],
                    "completed_at": row[7],
                }
                for row in cursor.fetchall()
            ]
    
    def save_conversation(self, session_id: str, role: str, content: str):
        """Save a conversation message."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            conn.commit()
    
    def get_conversation(self, session_id: str, limit: int = 50) -> list[dict]:
        """Get conversation history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
            return [
                {"role": row[0], "content": row[1], "timestamp": row[2]}
                for row in reversed(cursor.fetchall())
            ]
    
    def save_decision(self, topic: str, decision: str, reason: str, context: str = ""):
        """Save an important decision."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO important_decisions (topic, decision, reason, context) VALUES (?, ?, ?, ?)",
                (topic, decision, reason, context)
            )
            conn.commit()
    
    def get_decisions(self, topic: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Get important decisions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if topic:
                cursor.execute(
                    "SELECT * FROM important_decisions WHERE topic = ? ORDER BY created_at DESC LIMIT ?",
                    (topic, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM important_decisions ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            return [
                {
                    "id": row[0],
                    "topic": row[1],
                    "decision": row[2],
                    "reason": row[3],
                    "context": row[4],
                    "created_at": row[5],
                }
                for row in cursor.fetchall()
            ]