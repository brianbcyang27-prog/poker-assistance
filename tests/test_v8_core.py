"""Tests for auth, checkpoint, and permission systems (v8.0.0)."""

import pytest
import time
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


# ── Auth Tests ──

class TestAuthManager:
    """Test the AuthManager class."""

    def _make_manager(self, tmp_path, load_existing=True):
        from jarvis.web.auth import AuthManager
        mgr = AuthManager.__new__(AuthManager)
        mgr._config_path = tmp_path / "auth.json"
        mgr._api_keys = {}
        mgr._sessions = {}
        mgr._api_key = None
        if load_existing and mgr._config_path.exists():
            mgr._load()
        return mgr

    def test_setup_generates_key(self, tmp_path):
        mgr = self._make_manager(tmp_path, load_existing=False)
        key = mgr.setup()
        assert key is not None
        assert key.startswith("jrv_")
        assert len(key) > 20

    def test_verify_api_key(self, tmp_path):
        mgr = self._make_manager(tmp_path, load_existing=False)
        key = mgr.setup()
        assert mgr.verify_api_key(key) is True
        assert mgr.verify_api_key("wrong_key") is False
        assert mgr.verify_api_key("") is False
        assert mgr.verify_api_key(None) is False

    def test_session_create_and_verify(self, tmp_path):
        mgr = self._make_manager(tmp_path, load_existing=False)
        session_id = mgr.create_session(ip="127.0.0.1")
        assert session_id is not None
        assert len(session_id) == 32
        assert mgr.verify_session(session_id) is True

    def test_session_expiry(self, tmp_path):
        mgr = self._make_manager(tmp_path, load_existing=False)
        session_id = mgr.create_session()
        mgr._sessions[session_id]["created"] = time.time() - 86401
        assert mgr.verify_session(session_id) is False

    def test_persistence(self, tmp_path):
        mgr1 = self._make_manager(tmp_path, load_existing=False)
        key = mgr1.setup()
        
        mgr2 = self._make_manager(tmp_path, load_existing=True)
        assert mgr2.verify_api_key(key) is True


# ── Checkpoint Tests ──

class TestCheckpointManager:
    """Test the CheckpointManager class."""

    def test_file_checkpoint_create_and_restore(self, tmp_path):
        from jarvis.core.checkpoint import CheckpointManager
        mgr = CheckpointManager(storage_dir=tmp_path / "checkpoints")
        
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")
        
        # Create checkpoint
        cp = mgr.create_file_checkpoint(str(test_file), "test checkpoint")
        assert cp is not None
        assert cp.type == "file"
        
        # Modify the file
        test_file.write_text("modified content")
        assert test_file.read_text() == "modified content"
        
        # Restore from checkpoint
        ok = mgr.restore_file_checkpoint(cp.id)
        assert ok is True
        assert test_file.read_text() == "original content"

    def test_mission_checkpoint(self, tmp_path):
        from jarvis.core.checkpoint import CheckpointManager
        mgr = CheckpointManager(storage_dir=tmp_path / "checkpoints")
        
        state = {"step": 3, "status": "running", "data": {"key": "value"}}
        cp = mgr.create_mission_checkpoint("mission-123", state, "test")
        assert cp is not None
        assert cp.type == "mission"
        
        restored = mgr.restore_mission_checkpoint(cp.id)
        assert restored == state

    def test_list_checkpoints(self, tmp_path):
        from jarvis.core.checkpoint import CheckpointManager
        mgr = CheckpointManager(storage_dir=tmp_path / "checkpoints")
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        mgr.create_file_checkpoint(str(test_file), "cp1")
        time.sleep(0.01)  # Ensure unique millisecond IDs
        mgr.create_file_checkpoint(str(test_file), "cp2")
        
        all_cps = mgr.list_checkpoints()
        assert len(all_cps) == 2
        
        file_cps = mgr.list_checkpoints(type_filter="file")
        assert len(file_cps) == 2

    def test_delete_checkpoint(self, tmp_path):
        from jarvis.core.checkpoint import CheckpointManager
        mgr = CheckpointManager(storage_dir=tmp_path / "checkpoints")
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        cp = mgr.create_file_checkpoint(str(test_file))
        assert mgr.delete_checkpoint(cp.id) is True
        assert mgr.delete_checkpoint("nonexistent") is False
        assert len(mgr.list_checkpoints()) == 0


# ── Permission Tests ──

class TestPermissionCenter:
    """Test the PermissionCenter class."""

    def test_default_permissions(self):
        from jarvis.core.permissions import PermissionCenter
        pc = PermissionCenter()
        all_perms = pc.get_all()
        names = [p["name"] for p in all_perms]
        assert "files" in names
        assert "terminal" in names
        assert "screen" in names
        assert "browser" in names
        assert "accessibility" in names

    def test_check_permission(self):
        from jarvis.core.permissions import PermissionCenter
        pc = PermissionCenter()
        assert pc.check("files") is True
        assert pc.check("nonexistent") is False

    def test_set_permission(self, tmp_path):
        from jarvis.core.permissions import PermissionCenter
        pc = PermissionCenter()
        pc._config_path = tmp_path / "perms.json"
        
        assert pc.set("files", False) is True
        assert pc.check("files") is False
        
        assert pc.set("files", True) is True
        assert pc.check("files") is True
        
        assert pc.set("nonexistent", True) is False

    def test_check_required(self):
        from jarvis.core.permissions import PermissionCenter
        pc = PermissionCenter()
        
        # All required permissions granted
        ok, missing = pc.check_required(["files", "terminal"])
        assert ok is True
        assert missing == []
        
        # Some missing
        pc.set("accessibility", False)
        ok, missing = pc.check_required(["files", "accessibility"])
        assert ok is False
        assert "accessibility" in missing
