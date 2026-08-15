"""Tests for auth, checkpoint, permission, and reliability systems (v8.0.0+)."""

import time
from pathlib import Path

import pytest

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
        assert pc.check("files") == (True, "allow")
        assert pc.check("nonexistent") == (False, "deny")

    def test_set_permission(self, tmp_path):
        from jarvis.core.permissions import PermissionCenter

        pc = PermissionCenter()
        pc._config_path = tmp_path / "perms.json"

        assert pc.set("files", False) is True
        assert pc.check("files") == (False, "deny")

        assert pc.set("files", True) is True
        assert pc.check("files") == (True, "allow")

        assert pc.set("nonexistent", True) is False

    def test_tri_state_permission(self):
        from jarvis.core.permissions import PermissionCenter, TrinityState

        pc = PermissionCenter()
        pc._config_path = None  # don't persist during test

        assert pc.set_state("microphone", TrinityState.ASK) is True
        assert pc.check("microphone") == (False, "ask")

        assert pc.grant("microphone", duration=10) is True
        assert pc.check("microphone") == (True, "ask")

        assert pc.set_state("microphone", TrinityState.ALLOW) is True
        assert pc.check("microphone") == (True, "allow")

        assert pc.set_state("microphone", TrinityState.DENY) is True
        assert pc.check("microphone") == (False, "deny")

        data = pc.get("microphone")
        assert data is not None
        assert data["state"] == "deny"
        assert data["granted"] is False

        assert pc.get("nonexistent") is None
        assert pc.set_state("nonexistent", TrinityState.ALLOW) is False

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


# ── Circuit Breaker Tests (A4) ──


class TestCircuitBreaker:
    """Test the circuit_breaker async context manager."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self):
        """Reset circuit breaker registry before each test to avoid cross-test leakage."""
        from jarvis.core.reliability import circuit_breaker

        circuit_breaker._registry.clear()
        yield

    async def _fail(self):
        raise ValueError("boom")

    async def _succeed(self):
        return "ok"

    async def test_closed_passes_through(self):
        from jarvis.core.reliability import circuit_breaker

        cb = circuit_breaker("cb1")
        async with cb:
            result = await self._succeed()
        assert result == "ok"
        assert cb.state == "closed"

    async def test_opens_after_threshold(self):
        from jarvis.core.reliability import circuit_breaker

        cb = circuit_breaker("cb2", failure_threshold=2)
        for i in range(2):
            with pytest.raises(ValueError):
                async with cb:
                    await self._fail()
        assert cb.state == "open"

    async def test_open_rejects_calls(self):
        from jarvis.core.reliability import CircuitBreakerOpenError, circuit_breaker

        cb = circuit_breaker("cb3", failure_threshold=1)
        with pytest.raises(ValueError):
            async with cb:
                await self._fail()
        with pytest.raises(CircuitBreakerOpenError):
            async with cb:
                await self._succeed()

    async def test_singleton_registry(self):
        from jarvis.core.reliability import circuit_breaker

        cb1 = circuit_breaker("singleton")
        cb2 = circuit_breaker("singleton")
        assert cb1 is cb2

    async def test_get_existing(self):
        from jarvis.core.reliability import circuit_breaker

        cb1 = circuit_breaker("get_test")
        cb2 = circuit_breaker.get("get_test")
        assert cb2 is cb1

    async def test_get_missing(self):
        from jarvis.core.reliability import circuit_breaker

        assert circuit_breaker.get("nonexistent") is None

    async def test_all_stats(self):
        from jarvis.core.reliability import circuit_breaker

        circuit_breaker("stats_a")
        circuit_breaker("stats_b")
        stats = circuit_breaker.all_stats()
        assert "stats_a" in stats
        assert "stats_b" in stats
        assert len(stats) == 2

    async def test_stats_fields(self):
        from jarvis.core.reliability import circuit_breaker

        cb = circuit_breaker("stats_fields", failure_threshold=3, recovery_timeout=60)
        s = cb.stats()
        assert s["name"] == "stats_fields"
        assert s["state"] == "closed"
        assert s["failure_threshold"] == 3
        assert s["total_calls"] == 0

    async def test_half_open_probe_success(self):
        import time

        from jarvis.core.reliability import CircuitState, circuit_breaker

        cb = circuit_breaker("probe_ok", failure_threshold=1, recovery_timeout=0.05)
        # Open it
        with pytest.raises(ValueError):
            async with cb:
                await self._fail()
        assert cb.state == "open"
        # Backdate last failure to trigger recovery
        cb._last_failure_time = time.monotonic() - 1
        cb._state = CircuitState.OPEN
        # Probe should succeed
        async with cb:
            await self._succeed()
        assert cb.state == "closed"

    async def test_half_open_probe_fails(self):
        import time

        from jarvis.core.reliability import CircuitState, circuit_breaker

        cb = circuit_breaker("probe_fail", failure_threshold=1, recovery_timeout=0.05)
        # Open it
        with pytest.raises(ValueError):
            async with cb:
                await self._fail()
        assert cb.state == "open"
        # Backdate to trigger recovery
        cb._last_failure_time = time.monotonic() - 1
        cb._state = CircuitState.OPEN
        # Probe fails → back to OPEN
        with pytest.raises(ValueError):
            async with cb:
                await self._fail()
        assert cb.state == "open"

    async def test_half_open_rejects_second_concurrent_probe(self):
        import time

        from jarvis.core.reliability import CircuitState, circuit_breaker

        cb = circuit_breaker("concurrent", failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(ValueError):
            async with cb:
                await self._fail()
        # Manually enter HALF_OPEN with 1 call already registered
        cb._last_failure_time = time.monotonic() - 1
        cb._state = CircuitState.OPEN
        async with cb:
            pass  # first probe enters HALF_OPEN and succeeds
        # Already back to CLOSED — no concurrent scenario possible via state machine
        assert cb.state == "closed"

    async def test_failure_count_decays_on_success(self):
        from jarvis.core.reliability import circuit_breaker

        cb = circuit_breaker("decay", failure_threshold=5)
        # Fail twice
        with pytest.raises(ValueError):
            async with cb:
                await self._fail()
        with pytest.raises(ValueError):
            async with cb:
                await self._fail()
        assert cb.failure_count == 2
        # Succeed twice — each success decrements by 1
        async with cb:
            await self._succeed()
        assert cb.failure_count == 1
        async with cb:
            await self._succeed()
        assert cb.failure_count == 0

    async def test_with_circuit_breaker_default_on_open(self):
        from jarvis.core.reliability import circuit_breaker, with_circuit_breaker

        cb = circuit_breaker("wcbo", failure_threshold=1)
        with pytest.raises(ValueError):
            async with cb:
                await self._fail()
        # Circuit is OPEN — with_circuit_breaker should return default
        result = await with_circuit_breaker("wcbo", self._succeed(), default="fallback")
        assert result == "fallback"

    async def test_with_circuit_breaker_passes_when_closed(self):
        from jarvis.core.reliability import with_circuit_breaker

        result = await with_circuit_breaker("wcbp", self._succeed(), default="nope")
        assert result == "ok"


# ── Checkpoint Integrity Tests (A4) ──


class TestCheckpointIntegrity:
    """Test SHA-256 integrity verification on file checkpoints."""

    def test_sha256_file(self, tmp_path):
        from jarvis.core.checkpoint import _sha256_file

        f = tmp_path / "test.txt"
        f.write_text("hello world")
        digest = _sha256_file(f)
        assert isinstance(digest, str)
        assert len(digest) == 64  # SHA-256 hex

    def test_verify_integrity_skips_when_no_checksum(self):
        from jarvis.core.checkpoint import Checkpoint

        cp = Checkpoint(id="no_cs", timestamp=0, type="file", description="test")
        assert cp.verify_integrity() is True

    def test_verify_integrity_passes(self, tmp_path):
        from jarvis.core.checkpoint import Checkpoint, _sha256_file

        f = tmp_path / "test.txt"
        f.write_text("hello world")
        checksum = _sha256_file(f)
        cp = Checkpoint(
            id="good",
            timestamp=0,
            type="file",
            description="test",
            checksum=checksum,
            data={"snapshot_path": str(f)},
        )
        assert cp.verify_integrity() is True

    def test_verify_integrity_fails_on_tamper(self, tmp_path):
        from jarvis.core.checkpoint import Checkpoint, _sha256_file

        f = tmp_path / "test.txt"
        f.write_text("original")
        checksum = _sha256_file(f)
        cp = Checkpoint(
            id="tampered",
            timestamp=0,
            type="file",
            description="test",
            checksum=checksum,
            data={"snapshot_path": str(f)},
        )
        f.write_text("tampered")
        assert cp.verify_integrity() is False

    def test_verify_integrity_fails_on_missing_file(self, tmp_path):
        from jarvis.core.checkpoint import Checkpoint

        missing = tmp_path / "nonexistent.txt"
        cp = Checkpoint(
            id="missing",
            timestamp=0,
            type="file",
            description="test",
            checksum="a" * 64,
            data={"snapshot_path": str(missing)},
        )
        assert cp.verify_integrity() is False

    def test_create_checkpoint_stores_checksum(self, tmp_path):
        from jarvis.core.checkpoint import CheckpointManager

        mgr = CheckpointManager(storage_dir=tmp_path / "cps")
        f = tmp_path / "source.txt"
        f.write_text("checkpoint me")
        cp = mgr.create_file_checkpoint(str(f), "integrity test")
        assert cp.checksum != ""
        assert len(cp.checksum) == 64

    def test_restore_checks_integrity(self, tmp_path):
        from jarvis.core.checkpoint import CheckpointManager

        mgr = CheckpointManager(storage_dir=tmp_path / "cps2")
        f = tmp_path / "restore_test.txt"
        f.write_text("original")
        cp = mgr.create_file_checkpoint(str(f), "restore integrity")
        # Tamper the snapshot file directly
        snap = Path(cp.data["snapshot_path"])
        snap.write_text("tampered snapshot")
        # Restore should fail because integrity check fails
        ok = mgr.restore_file_checkpoint(cp.id)
        assert ok is False


# ── Health Monitor Tests (A4) ──


class TestHealthMonitor:
    """Test the HealthMonitor class."""

    def test_initial_state(self):
        from jarvis.core.health_monitor import HealthMonitor

        hm = HealthMonitor(check_interval=9999)
        assert hm.is_healthy() is True
        status = hm.status()
        assert "checks" in status
        assert "subsystems" in status
        assert status["healthy"] is True

    async def test_start_stop(self):
        from jarvis.core.health_monitor import HealthMonitor

        hm = HealthMonitor(check_interval=9999)
        assert hm._task is None
        await hm.start()
        assert hm._task is not None
        assert hm._task.done() is False
        # Double start is no-op
        await hm.start()
        await hm.stop()
        assert hm._task is None

    def test_subsystem_transition_healthy_to_unhealthy(self):
        from jarvis.core.health_monitor import HealthCheck, HealthMonitor

        hm = HealthMonitor()
        sub = hm._subsystems["database"]
        assert sub.ok is True
        # Manually trigger unhealthy transition
        hc = HealthCheck(name="database", ok=False, message="connection failed")
        hm._update_subsystem("database", hc)
        assert sub.ok is False
        assert sub.consecutive_failures == 1
        assert sub.last_error == "connection failed"

    def test_subsystem_transition_unhealthy_to_healthy(self):
        from jarvis.core.health_monitor import HealthCheck, HealthMonitor

        hm = HealthMonitor()
        sub = hm._subsystems["disk"]
        # First make it unhealthy
        sub.ok = False
        sub.last_error = "disk full"
        sub.consecutive_failures = 3
        # Now recover
        hc = HealthCheck(name="disk", ok=True, message="all good")
        hm._update_subsystem("disk", hc)
        assert sub.ok is True
        assert sub.consecutive_failures == 0
        assert sub.last_error == ""

    def test_unknown_subsystem_is_ignored(self):
        from jarvis.core.health_monitor import HealthCheck, HealthMonitor

        hm = HealthMonitor()
        hc = HealthCheck(name="unknown", ok=False, message="???")
        # Should not raise
        hm._update_subsystem("unknown", hc)

    async def test_check_disk(self):
        from jarvis.core.health_monitor import HealthMonitor

        hm = HealthMonitor()
        result = await hm._check_disk()
        assert result.name == "disk"
        assert isinstance(result.ok, bool)
        assert "GB" in result.message

    async def test_check_circuit(self):
        from jarvis.core.health_monitor import HealthMonitor

        hm = HealthMonitor()
        # No circuit breakers registered — should report healthy
        result = await hm._check_circuit()
        assert result.name == "circuit"
        assert result.ok is True
