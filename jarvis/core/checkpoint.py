"""Checkpoint system for JARVIS v8.0.0.

Provides undo/restore capability for:
- File changes (before/after snapshots)
- Mission steps (rollback to previous state)
- Workspace state (save/restore)
"""

import json
import time
import shutil
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("jarvis.checkpoint")


@dataclass
class Checkpoint:
    """A single checkpoint entry."""
    id: str
    timestamp: float
    type: str  # "file", "mission", "workspace"
    description: str
    data: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class CheckpointManager:
    """Manages checkpoints for undo/restore operations."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self._storage_dir = storage_dir or Path.home() / ".jarvis" / "checkpoints"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._storage_dir / "index.json"
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._load_index()
    
    def _load_index(self):
        """Load checkpoint index from disk."""
        try:
            if self._index_path.exists():
                data = json.loads(self._index_path.read_text())
                for entry in data.get("checkpoints", []):
                    cp = Checkpoint(**entry)
                    self._checkpoints[cp.id] = cp
        except Exception as e:
            logger.warning("Failed to load checkpoint index: %s", e)
    
    def _save_index(self):
        """Save checkpoint index to disk."""
        try:
            data = {
                "checkpoints": [cp.to_dict() for cp in self._checkpoints.values()]
            }
            self._index_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to save checkpoint index: %s", e)
    
    def create_file_checkpoint(
        self,
        file_path: str,
        description: str = "",
        parent_id: Optional[str] = None,
    ) -> Optional[Checkpoint]:
        """Create a checkpoint before modifying a file."""
        path = Path(file_path)
        if not path.exists():
            return None
        
        cp_id = f"file_{int(time.time() * 1000)}"
        snapshot_path = self._storage_dir / f"{cp_id}_{path.name}"
        
        try:
            shutil.copy2(path, snapshot_path)
            cp = Checkpoint(
                id=cp_id,
                timestamp=time.time(),
                type="file",
                description=description or f"Snapshot of {path.name}",
                data={
                    "original_path": str(path),
                    "snapshot_path": str(snapshot_path),
                    "size": path.stat().st_size,
                },
                parent_id=parent_id,
            )
            self._checkpoints[cp_id] = cp
            self._save_index()
            logger.info("Created file checkpoint: %s for %s", cp_id, file_path)
            return cp
        except Exception as e:
            logger.error("Failed to create file checkpoint: %s", e)
            return None
    
    def restore_file_checkpoint(self, cp_id: str) -> bool:
        """Restore a file from checkpoint."""
        cp = self._checkpoints.get(cp_id)
        if not cp or cp.type != "file":
            return False
        
        snapshot_path = Path(cp.data["snapshot_path"])
        original_path = Path(cp.data["original_path"])
        
        if not snapshot_path.exists():
            logger.error("Snapshot not found: %s", snapshot_path)
            return False
        
        try:
            shutil.copy2(snapshot_path, original_path)
            logger.info("Restored file from checkpoint: %s", cp_id)
            return True
        except Exception as e:
            logger.error("Failed to restore file checkpoint: %s", e)
            return False
    
    def create_mission_checkpoint(
        self,
        mission_id: str,
        state: Dict[str, Any],
        description: str = "",
        parent_id: Optional[str] = None,
    ) -> Checkpoint:
        """Create a checkpoint for mission state."""
        cp_id = f"mission_{int(time.time() * 1000)}"
        cp = Checkpoint(
            id=cp_id,
            timestamp=time.time(),
            type="mission",
            description=description or f"Mission {mission_id} state",
            data={
                "mission_id": mission_id,
                "state": state,
            },
            parent_id=parent_id,
        )
        self._checkpoints[cp_id] = cp
        self._save_index()
        logger.info("Created mission checkpoint: %s for mission %s", cp_id, mission_id)
        return cp
    
    def restore_mission_checkpoint(self, cp_id: str) -> Optional[Dict[str, Any]]:
        """Restore mission state from checkpoint. Returns the saved state."""
        cp = self._checkpoints.get(cp_id)
        if not cp or cp.type != "mission":
            return None
        return cp.data.get("state")
    
    def list_checkpoints(
        self,
        type_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Checkpoint]:
        """List checkpoints, optionally filtered by type."""
        cps = list(self._checkpoints.values())
        if type_filter:
            cps = [cp for cp in cps if cp.type == type_filter]
        cps.sort(key=lambda cp: cp.timestamp, reverse=True)
        return cps[:limit]
    
    def delete_checkpoint(self, cp_id: str) -> bool:
        """Delete a checkpoint and its snapshot."""
        cp = self._checkpoints.get(cp_id)
        if not cp:
            return False
        
        # Delete snapshot file if it exists
        if cp.type == "file" and "snapshot_path" in cp.data:
            snapshot = Path(cp.data["snapshot_path"])
            if snapshot.exists():
                snapshot.unlink()
        
        del self._checkpoints[cp_id]
        self._save_index()
        logger.info("Deleted checkpoint: %s", cp_id)
        return True
    
    def cleanup_old(self, max_age_hours: int = 24) -> int:
        """Delete checkpoints older than max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        to_delete = [
            cp_id for cp_id, cp in self._checkpoints.items()
            if cp.timestamp < cutoff
        ]
        for cp_id in to_delete:
            self.delete_checkpoint(cp_id)
        return len(to_delete)


# Module-level singleton
checkpoint_manager = CheckpointManager()
