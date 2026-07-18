"""File System Watcher — Monitor directories for changes."""

import asyncio
import os
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import threading
import time


@dataclass
class FileEvent:
    """A file system event."""
    path: str
    event_type: str  # created, modified, deleted, moved
    is_directory: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


class FileWatcher:
    """Monitor directories for file system changes using FSEvents."""
    
    def __init__(self):
        self.watchers: Dict[str, Dict[str, Any]] = {}
        self.events: List[FileEvent] = []
        self.max_events = 100
        self._callbacks: Dict[str, List[Callable]] = {}
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._snapshots: Dict[str, Dict[str, float]] = {}
    
    async def watch(
        self,
        path: str,
        key: Optional[str] = None,
        recursive: bool = True,
        patterns: Optional[List[str]] = None,
    ) -> bool:
        """Start watching a directory."""
        watch_key = key or path
        
        self.watchers[watch_key] = {
            "path": path,
            "recursive": recursive,
            "patterns": patterns or [],
            "created_at": datetime.now(),
        }
        
        # Take initial snapshot
        self._snapshots[watch_key] = self._snapshot_dir(path, recursive)
        
        return True
    
    async def unwatch(self, key: str) -> bool:
        """Stop watching a directory."""
        if key in self.watchers:
            del self.watchers[key]
            self._snapshots.pop(key, None)
            return True
        return False
    
    def on_event(self, key: str, callback: Callable):
        """Register a callback for file events."""
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)
    
    def start_monitoring(self, interval: float = 2.0):
        """Start monitoring for file changes."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True,
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring for file changes."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None
    
    def _snapshot_dir(self, path: str, recursive: bool) -> Dict[str, float]:
        """Take a snapshot of directory contents (path -> mtime)."""
        snapshot = {}
        try:
            if recursive:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        filepath = os.path.join(root, f)
                        try:
                            snapshot[filepath] = os.path.getmtime(filepath)
                        except OSError:
                            pass
            else:
                for entry in os.scandir(path):
                    if entry.is_file():
                        try:
                            snapshot[entry.path] = entry.stat().st_mtime
                        except OSError:
                            pass
        except OSError:
            pass
        return snapshot
    
    def _monitor_loop(self, interval: float):
        """Background loop to detect file changes."""
        while self._monitoring:
            for key, watcher in list(self.watchers.items()):
                path = watcher["path"]
                recursive = watcher["recursive"]
                patterns = watcher["patterns"]
                
                new_snapshot = self._snapshot_dir(path, recursive)
                old_snapshot = self._snapshots.get(key, {})
                
                # Detect new and modified files
                for filepath, mtime in new_snapshot.items():
                    if filepath not in old_snapshot:
                        event = FileEvent(
                            path=filepath,
                            event_type="created",
                            is_directory=os.path.isdir(filepath),
                        )
                        self._emit_event(key, event)
                    elif mtime > old_snapshot[filepath]:
                        event = FileEvent(
                            path=filepath,
                            event_type="modified",
                            is_directory=os.path.isdir(filepath),
                        )
                        self._emit_event(key, event)
                
                # Detect deleted files
                for filepath in old_snapshot:
                    if filepath not in new_snapshot:
                        event = FileEvent(
                            path=filepath,
                            event_type="deleted",
                            is_directory=os.path.isdir(filepath),
                        )
                        self._emit_event(key, event)
                
                self._snapshots[key] = new_snapshot
            
            time.sleep(interval)
    
    def _emit_event(self, key: str, event: FileEvent):
        """Emit a file event to callbacks."""
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        for cb in self._callbacks.get(key, []):
            try:
                cb(event)
            except Exception:
                pass
    
    def get_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent file events."""
        return [
            {
                "path": e.path,
                "event_type": e.event_type,
                "is_directory": e.is_directory,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in self.events[-limit:]
        ]
    
    def get_watched(self) -> List[Dict[str, Any]]:
        """Get all watched directories."""
        return [
            {
                "key": k,
                "path": v["path"],
                "recursive": v["recursive"],
                "patterns": v["patterns"],
            }
            for k, v in self.watchers.items()
        ]
    
    @property
    def is_monitoring(self) -> bool:
        return self._monitoring
