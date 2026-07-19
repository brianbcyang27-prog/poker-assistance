import sys
import os
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from jarvis.memory_privacy.models import (
    AuditAction,
    AuditEntry,
    ExportData,
    MemoryPrivacySettings,
    PrivacyLevel,
)
from jarvis.memory_privacy.manager import MemoryPrivacyManager


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# TestPrivacyModels
# ---------------------------------------------------------------------------


class TestPrivacyModels:
    def test_settings_defaults(self):
        s = MemoryPrivacySettings()
        assert s.paused is False
        assert s.default_level == "private"
        assert s.encrypted_categories == []
        assert s.forgotten_topics == []
        assert s.private_projects == []
        assert s.audit_enabled is True
        assert s.auto_forget_days == 0

    def test_settings_custom(self):
        s = MemoryPrivacySettings(
            paused=True,
            default_level="encrypted",
            encrypted_categories=["secrets"],
            forgotten_topics=["passwords"],
            private_projects=["secret-proj"],
            audit_enabled=False,
            auto_forget_days=30,
        )
        assert s.paused is True
        assert s.default_level == "encrypted"
        assert s.encrypted_categories == ["secrets"]
        assert s.forgotten_topics == ["passwords"]
        assert s.private_projects == ["secret-proj"]
        assert s.audit_enabled is False
        assert s.auto_forget_days == 30

    def test_settings_to_dict(self):
        s = MemoryPrivacySettings(
            paused=True,
            default_level="public",
            forgotten_topics=["topic_a"],
        )
        d = s.to_dict()
        assert d["paused"] is True
        assert d["default_level"] == "public"
        assert d["forgotten_topics"] == ["topic_a"]
        assert d["audit_enabled"] is True
        assert d["auto_forget_days"] == 0

    def test_settings_from_dict_roundtrip(self):
        s = MemoryPrivacySettings(
            paused=True,
            default_level="encrypted",
            encrypted_categories=["cat1"],
            forgotten_topics=["t1", "t2"],
            private_projects=["p1"],
            audit_enabled=False,
            auto_forget_days=60,
        )
        d = s.to_dict()
        s2 = MemoryPrivacySettings.from_dict(d)
        assert s2.paused is True
        assert s2.default_level == "encrypted"
        assert s2.encrypted_categories == ["cat1"]
        assert s2.forgotten_topics == ["t1", "t2"]
        assert s2.private_projects == ["p1"]
        assert s2.audit_enabled is False
        assert s2.auto_forget_days == 60

    def test_settings_from_dict_defaults(self):
        s = MemoryPrivacySettings.from_dict({})
        assert s.paused is False
        assert s.default_level == "private"
        assert s.forgotten_topics == []

    def test_audit_entry_creation(self):
        e = AuditEntry(action="view", target="note:123", details="Viewed note")
        assert e.id.startswith("audit_")
        assert len(e.id) == 14
        assert e.action == "view"
        assert e.target == "note:123"
        assert e.details == "Viewed note"
        assert e.timestamp > 0

    def test_audit_entry_to_dict(self):
        e = AuditEntry(
            id="a_test",
            action="delete",
            target="proj:x",
            details="Deleted project",
            timestamp=1234567890.0,
        )
        d = e.to_dict()
        assert d["id"] == "a_test"
        assert d["action"] == "delete"
        assert d["target"] == "proj:x"
        assert d["details"] == "Deleted project"
        assert d["timestamp"] == 1234567890.0

    def test_audit_entry_from_dict_roundtrip(self):
        e = AuditEntry(
            id="a_rt",
            action="forget",
            target="topic:secrets",
            details="Forgotten",
            timestamp=9876543210.0,
        )
        data = e.to_dict()
        e2 = AuditEntry.from_dict(data)
        assert e2.id == "a_rt"
        assert e2.action == "forget"
        assert e2.target == "topic:secrets"
        assert e2.timestamp == 9876543210.0

    def test_audit_entry_from_dict_defaults(self):
        e = AuditEntry.from_dict({})
        assert e.action == "view"
        assert e.target == ""
        assert e.details == ""
        assert e.id.startswith("audit_")
        assert e.timestamp > 0

    def test_export_data_defaults(self):
        exp = ExportData()
        assert exp.entities == []
        assert exp.relationships == []
        assert exp.preferences == []
        assert exp.decisions == []
        assert exp.timeline == []
        assert exp.exported_at > 0

    def test_export_data_to_dict(self):
        exp = ExportData(
            entities=[{"name": "e1"}],
            relationships=[{"from": "a", "to": "b"}],
            exported_at=1234567890.0,
        )
        d = exp.to_dict()
        assert d["entities"] == [{"name": "e1"}]
        assert d["relationships"] == [{"from": "a", "to": "b"}]
        assert d["exported_at"] == 1234567890.0
        assert d["decisions"] == []

    def test_export_data_from_dict_roundtrip(self):
        exp = ExportData(
            entities=[{"x": 1}],
            relationships=[{"y": 2}],
            preferences=[{"z": 3}],
            decisions=[{"w": 4}],
            timeline=[{"v": 5}],
            exported_at=1111111111.0,
        )
        data = exp.to_dict()
        exp2 = ExportData.from_dict(data)
        assert exp2.entities == [{"x": 1}]
        assert exp2.decisions == [{"w": 4}]
        assert exp2.exported_at == 1111111111.0

    def test_privacy_level_enum(self):
        assert PrivacyLevel.PUBLIC == "public"
        assert PrivacyLevel.PRIVATE == "private"
        assert PrivacyLevel.ENCRYPTED == "encrypted"
        assert PrivacyLevel.FORGOTTEN == "forgotten"

    def test_audit_action_enum(self):
        assert AuditAction.VIEW == "view"
        assert AuditAction.DELETE == "delete"
        assert AuditAction.FORGET == "forget"
        assert AuditAction.EXPORT == "export"
        assert AuditAction.IMPORT == "import"
        assert AuditAction.PAUSE == "pause"
        assert AuditAction.RESUME == "resume"
        assert AuditAction.ENCRYPT == "encrypt"
        assert AuditAction.DECRYPT == "decrypt"
        assert AuditAction.SEARCH == "search"


# ---------------------------------------------------------------------------
# TestMemoryPrivacyManager
# ---------------------------------------------------------------------------


class TestMemoryPrivacyManager:
    @pytest.fixture
    def manager(self, tmp_path):
        return MemoryPrivacyManager(storage_dir=str(tmp_path))

    def test_get_settings_default(self, manager):
        s = _run(manager.get_settings())
        assert s.paused is False
        assert s.default_level == "private"
        assert s.audit_enabled is True

    def test_update_settings(self, manager):
        _run(manager.update_settings(default_level="encrypted", auto_forget_days=7))
        s = _run(manager.get_settings())
        assert s.default_level == "encrypted"
        assert s.auto_forget_days == 7

    def test_update_settings_ignored_key(self, manager):
        _run(manager.update_settings(nonexistent_key="value"))
        s = _run(manager.get_settings())
        assert s.paused is False

    def test_pause(self, manager):
        _run(manager.pause())
        assert _run(manager.is_paused()) is True

    def test_resume(self, manager):
        _run(manager.pause())
        assert _run(manager.is_paused()) is True
        _run(manager.resume())
        assert _run(manager.is_paused()) is False

    def test_pause_returns_dict(self, manager):
        result = _run(manager.pause())
        assert result == {"paused": True}

    def test_resume_returns_dict(self, manager):
        result = _run(manager.resume())
        assert result == {"paused": False}

    def test_add_private_project(self, manager):
        result = _run(manager.add_private_project("secret-proj"))
        assert result["added"] == "secret-proj"
        assert "secret-proj" in result["private_projects"]

    def test_add_private_project_no_duplicates(self, manager):
        _run(manager.add_private_project("proj"))
        _run(manager.add_private_project("proj"))
        s = _run(manager.get_settings())
        assert s.private_projects.count("proj") == 1

    def test_remove_private_project(self, manager):
        _run(manager.add_private_project("proj"))
        result = _run(manager.remove_private_project("proj"))
        assert "proj" not in result["private_projects"]

    def test_remove_nonexistent_project(self, manager):
        result = _run(manager.remove_private_project("ghost"))
        assert result["removed"] == "ghost"
        assert result["private_projects"] == []

    def test_add_forgotten_topic(self, manager):
        result = _run(manager.add_forgotten_topic("passwords"))
        assert result["added"] == "passwords"
        assert "passwords" in result["forgotten_topics"]

    def test_add_forgotten_topic_no_duplicates(self, manager):
        _run(manager.add_forgotten_topic("secret"))
        _run(manager.add_forgotten_topic("secret"))
        s = _run(manager.get_settings())
        assert s.forgotten_topics.count("secret") == 1

    def test_is_forgotten_true(self, manager):
        _run(manager.add_forgotten_topic("passwords"))
        assert _run(manager.is_forgotten("passwords")) is True

    def test_is_forgotten_case_insensitive(self, manager):
        _run(manager.add_forgotten_topic("Passwords"))
        assert _run(manager.is_forgotten("PASSWORDS")) is True

    def test_is_forgotten_false(self, manager):
        assert _run(manager.is_forgotten("anything")) is False

    def test_forget_topic(self, manager):
        result = _run(manager.forget_topic("ssn"))
        assert "ssn" in result["forgotten_topics"]
        assert _run(manager.is_forgotten("ssn")) is True

    def test_log_audit(self, manager):
        entry = _run(manager.log_audit("view", "note:1", "Viewed"))
        assert entry.action == "view"
        assert entry.target == "note:1"
        assert entry.details == "Viewed"

    def test_log_audit_multiple_entries(self, manager):
        _run(manager.log_audit("view", "note:1", "First"))
        _run(manager.log_audit("delete", "note:2", "Second"))
        _run(manager.log_audit("export", "all", "Third"))
        log = _run(manager.get_audit_log())
        assert len(log) == 3

    def test_get_audit_log_order(self, manager):
        _run(manager.log_audit("view", "a"))
        _run(manager.log_audit("delete", "b"))
        log = _run(manager.get_audit_log())
        assert log[0].target == "b"
        assert log[1].target == "a"

    def test_get_audit_log_limit(self, manager):
        for i in range(10):
            _run(manager.log_audit("view", f"target:{i}"))
        log = _run(manager.get_audit_log(limit=3))
        assert len(log) == 3

    def test_export_all_empty(self, manager):
        export = _run(manager.export_all())
        assert export.entities == []
        assert export.relationships == []
        assert export.preferences == []
        assert export.decisions == []
        assert export.timeline == []
        assert export.exported_at > 0

    def test_export_all_with_mock_engines(self, manager):
        class MockEntity:
            def to_dict(self):
                return {"name": "entity1"}

        class MockRel:
            def to_dict(self):
                return {"from": "a", "to": "b"}

        class MockKG:
            def get_all_entities(self):
                return [MockEntity()]

            def get_all_relationships(self):
                return [MockRel()]

        class MockPref:
            def to_dict(self):
                return {"key": "color", "value": "blue"}

        class MockPrefEngine:
            def get_all(self):
                return [MockPref()]

        class MockDecision:
            def to_dict(self):
                return {"title": "Use X"}

        class MockDecisionEngine:
            def get_all(self):
                return [MockDecision()]

        export = _run(manager.export_all(
            knowledge_graph=MockKG(),
            preference_engine=MockPrefEngine(),
            decision_engine=MockDecisionEngine(),
        ))
        assert len(export.entities) == 1
        assert export.entities[0]["name"] == "entity1"
        assert len(export.relationships) == 1
        assert len(export.preferences) == 1
        assert export.preferences[0]["key"] == "color"
        assert len(export.decisions) == 1

    def test_export_all_logs_audit(self, manager):
        _run(manager.export_all())
        log = _run(manager.get_audit_log())
        export_entries = [e for e in log if e.action == "export"]
        assert len(export_entries) == 2

    def test_save_and_load(self, tmp_path):
        m1 = MemoryPrivacyManager(storage_dir=str(tmp_path))
        _run(m1.update_settings(default_level="encrypted", auto_forget_days=14))
        _run(m1.add_forgotten_topic("passwords"))
        _run(m1.add_private_project("secret-proj"))
        _run(m1.log_audit("view", "target1", "detail1"))
        m2 = MemoryPrivacyManager(storage_dir=str(tmp_path))
        _run(m2.load())
        s = _run(m2.get_settings())
        assert s.default_level == "encrypted"
        assert s.auto_forget_days == 14
        assert "passwords" in s.forgotten_topics
        assert "secret-proj" in s.private_projects
        log = _run(m2.get_audit_log())
        assert len(log) >= 1

    def test_load_nonexistent_file(self, manager):
        _run(manager.load())
        s = _run(manager.get_settings())
        assert s.paused is False

    def test_is_allowed_normal(self, manager):
        assert _run(manager.is_allowed("note", "meeting notes")) is True

    def test_is_allowed_when_paused(self, manager):
        _run(manager.pause())
        assert _run(manager.is_allowed("note", "anything")) is False

    def test_is_allowed_forgotten_topic(self, manager):
        _run(manager.add_forgotten_topic("passwords"))
        assert _run(manager.is_allowed("note", "my passwords are here")) is False

    def test_is_allowed_private_project(self, manager):
        _run(manager.add_private_project("secret-proj"))
        assert _run(manager.is_allowed("note", "about secret-proj")) is False

    def test_is_allowed_encrypted_category(self, manager):
        _run(manager.update_settings(encrypted_categories=["secrets"]))
        assert _run(manager.is_allowed("secrets", "data")) is True
