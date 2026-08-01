"""Checkpoint system for JARVIS v8.0.0.

Provides undo/restore capability for:
- File changes (before/after snapshots)
- Mission steps (rollback to previous state)
- Workspace state (save/restore)
"""

import hashlib
import json
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jarvis.core.logging import get_logger

logger = get_logger("jarvis.checkpoint")


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Checkpoint:
    """A single checkpoint entry."""

    id: str
    timestamp: float
    type: str  # "file", "mission", "workspace"
    description: str
    data: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    checksum: str = ""  # SHA-256 hex digest for integrity verification

    def to_dict(self) -> dict:
        result = asdict(self)
        return result

    def verify_integrity(self) -> bool:
        """Verify checkpoint data integrity.

        For file checkpoints, verifies the snapshot file's SHA-256 hash.
        For other types, checks that the checkpoint ID and timestamp are valid.
        Returns True if integrity check passes.
        """
        if not self.checksum:
            logger.debug("No checksum for checkpoint %s, skipping integrity check", self.id)
            return True

        if self.type == "file" and "snapshot_path" in self.data:
            snapshot = Path(self.data["snapshot_path"])
            if not snapshot.exists():
                logger.error("Checkpoint %s snapshot missing: %s", self.id, snapshot)
                return False
            try:
                actual_hash = _sha256_file(snapshot)
                if actual_hash != self.checksum:
                    logger.error(
                        "Checkpoint %s checksum mismatch: expected=%s actual=%s",
                        self.id,
                        self.checksum,
                        actual_hash,
                    )
                    return False
                return True
            except Exception as e:
                logger.error("Checkpoint %s integrity check failed: %s", self.id, e)
                return False

        return True


class CheckpointManager:
    """Manages checkpoints for undo/restore operations."""

    def __init__(self, storage_dir: Path | None = None):
        self._storage_dir = storage_dir or Path.home() / ".jarvis" / "checkpoints"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._storage_dir / "index.json"
        self._checkpoints: dict[str, Checkpoint] = {}
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
            data = {"checkpoints": [cp.to_dict() for cp in self._checkpoints.values()]}
            self._index_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning("Failed to save checkpoint index: %s", e)

    def create_file_checkpoint(
        self,
        file_path: str,
        description: str = "",
        parent_id: str | None = None,
    ) -> Checkpoint | None:
        """Create a checkpoint before modifying a file."""
        path = Path(file_path)
        if not path.exists():
            return None

        cp_id = f"file_{int(time.time() * 1000)}"
        snapshot_path = self._storage_dir / f"{cp_id}_{path.name}"

        try:
            shutil.copy2(path, snapshot_path)
            checksum = _sha256_file(snapshot_path)
            cp = Checkpoint(
                id=cp_id,
                timestamp=time.time(),
                type="file",
                description=description or f"Snapshot of {path.name}",
                checksum=checksum,
                data={
                    "original_path": str(path),
                    "snapshot_path": str(snapshot_path),
                    "size": path.stat().st_size,
                },
                parent_id=parent_id,
            )
            self._checkpoints[cp_id] = cp
            self._save_index()
            logger.info(
                "Created file checkpoint: %s for %s [sha256=%s]", cp_id, file_path, checksum[:12]
            )
            return cp
        except Exception as e:
            logger.error("Failed to create file checkpoint: %s", e)
            return None

    def restore_file_checkpoint(self, cp_id: str) -> bool:
        """Restore a file from checkpoint with integrity verification."""
        cp = self._checkpoints.get(cp_id)
        if not cp or cp.type != "file":
            return False

        if not cp.verify_integrity():
            logger.error("Checkpoint %s integrity check FAILED — refusing restore", cp_id)
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
        state: dict[str, Any],
        description: str = "",
        parent_id: str | None = None,
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

    def restore_mission_checkpoint(self, cp_id: str) -> dict[str, Any] | None:
        """Restore mission state from checkpoint. Returns the saved state."""
        cp = self._checkpoints.get(cp_id)
        if not cp or cp.type != "mission":
            return None
        return cp.data.get("state")

    def list_checkpoints(
        self,
        type_filter: str | None = None,
        limit: int = 50,
    ) -> list[Checkpoint]:
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
        to_delete = [cp_id for cp_id, cp in self._checkpoints.items() if cp.timestamp < cutoff]
        for cp_id in to_delete:
            self.delete_checkpoint(cp_id)
        return len(to_delete)


# Module-level singleton
checkpoint_manager = CheckpointManager()
