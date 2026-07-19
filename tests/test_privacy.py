import sys
import os
import asyncio
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from jarvis.privacy.models import AuditEntry, PrivacySettings
from jarvis.privacy.manager import PrivacyManager
from jarvis.privacy import Privacy


# ---------------------------------------------------------------------------
# PrivacyModels
# ---------------------------------------------------------------------------


class TestPrivacyModels:
    def test_privacy_settings_defaults(self):
        s = PrivacySettings()
        assert s.application_monitoring is True
        assert s.browser_monitoring is False
        assert s.file_monitoring is False
        assert s.calendar_access is False
        assert s.email_access is False
        assert s.clipboard_monitoring is False
        assert s.microphone_access is False
        assert s.camera_access is False
        assert s.location_access is False
        assert s.notification_level == "suggestions"
        assert s.data_retention_days == 90

    def test_privacy_settings_custom(self):
        s = PrivacySettings(
            browser_monitoring=True,
            file_monitoring=True,
            notification_level="all",
            data_retention_days=30,
        )
        assert s.browser_monitoring is True
        assert s.notification_level == "all"
        assert s.data_retention_days == 30

    def test_privacy_settings_to_dict(self):
        s = PrivacySettings(browser_monitoring=True, data_retention_days=60)
        d = s.to_dict()
        assert d["browser_monitoring"] is True
        assert d["data_retention_days"] == 60
        assert d["application_monitoring"] is True

    def test_privacy_settings_from_dict_roundtrip(self):
        s = PrivacySettings(
            browser_monitoring=True,
            clipboard_monitoring=True,
            notification_level="none",
            data_retention_days=14,
        )
        d = s.to_dict()
        s2 = PrivacySettings.from_dict(d)
        assert s2.browser_monitoring is True
        assert s2.clipboard_monitoring is True
        assert s2.notification_level == "none"
        assert s2.data_retention_days == 14

    def test_privacy_settings_from_dict_defaults(self):
        s = PrivacySettings.from_dict({})
        assert s.application_monitoring is True
        assert s.browser_monitoring is False
        assert s.data_retention_days == 90

    def test_audit_entry_creation(self):
        e = AuditEntry(
            timestamp="2025-06-15T10:00:00Z",
            category="browser",
            action="observe",
            detail="Opened Chrome",
            allowed=True,
        )
        assert e.category == "browser"
        assert e.allowed is True

    def test_audit_entry_to_dict(self):
        e = AuditEntry(
            timestamp="2025-01-01T00:00:00Z",
            category="clipboard",
            action="observe",
            detail="Copied text",
            allowed=False,
        )
        d = e.to_dict()
        assert d["category"] == "clipboard"
        assert d["allowed"] is False
        assert d["timestamp"] == "2025-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# PrivacyManager
# ---------------------------------------------------------------------------


class TestPrivacyManager:
    @pytest.fixture
    def manager(self, tmp_path):
        settings_path = str(tmp_path / "settings.json")
        audit_path = str(tmp_path / "audit.json")
        return PrivacyManager(settings_path=settings_path, audit_path=audit_path)

    def test_init(self, manager):
        assert manager._settings is not None
        assert manager._audit_log == []

    def test_get_settings(self, manager):
        settings = asyncio.get_event_loop().run_until_complete(manager.get_settings())
        assert isinstance(settings, PrivacySettings)
        assert settings.application_monitoring is True
        assert settings.browser_monitoring is False

    def test_update_setting(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.update_setting("browser_monitoring", True)
        )
        settings = asyncio.get_event_loop().run_until_complete(manager.get_settings())
        assert settings.browser_monitoring is True

    def test_update_setting_multiple(self, manager):
        asyncio.get_event_loop().run_until_complete(manager.update_setting("browser_monitoring", True))
        asyncio.get_event_loop().run_until_complete(manager.update_setting("file_monitoring", True))
        asyncio.get_event_loop().run_until_complete(manager.update_setting("clipboard_monitoring", True))
        settings = asyncio.get_event_loop().run_until_complete(manager.get_settings())
        assert settings.browser_monitoring is True
        assert settings.file_monitoring is True
        assert settings.clipboard_monitoring is True

    def test_update_setting_invalid_raises(self, manager):
        with pytest.raises(ValueError):
            asyncio.get_event_loop().run_until_complete(
                manager.update_setting("nonexistent_category", True)
            )

    def test_is_allowed_default(self, result=None):
        mgr = PrivacyManager(
            settings_path=os.path.join(tempfile.mkdtemp(), "s.json"),
            audit_path=os.path.join(tempfile.mkdtemp(), "a.json"),
        )
        result = asyncio.get_event_loop().run_until_complete(mgr.is_allowed("application_monitoring"))
        assert result is True

    def test_is_allowed_disabled(self):
        mgr = PrivacyManager(
            settings_path=os.path.join(tempfile.mkdtemp(), "s.json"),
            audit_path=os.path.join(tempfile.mkdtemp(), "a.json"),
        )
        result = asyncio.get_event_loop().run_until_complete(mgr.is_allowed("browser_monitoring"))
        assert result is False

    def test_log_observation(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.log_observation("app", "Switched to Terminal")
        )
        log = asyncio.get_event_loop().run_until_complete(manager.get_audit_log())
        assert len(log) == 1
        assert log[0].category == "app"
        assert log[0].action == "observe"

    def test_log_observation_allowed(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.log_observation("application_monitoring", "Testing")
        )
        log = asyncio.get_event_loop().run_until_complete(manager.get_audit_log())
        assert log[0].allowed is True

    def test_log_observation_not_allowed(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.log_observation("browser_monitoring", "Testing")
        )
        log = asyncio.get_event_loop().run_until_complete(manager.get_audit_log())
        assert log[0].allowed is False

    def test_get_audit_log_newest_first(self, manager):
        for i in range(5):
            asyncio.get_event_loop().run_until_complete(
                manager.log_observation("app", f"event_{i}")
            )
        log = asyncio.get_event_loop().run_until_complete(manager.get_audit_log())
        assert len(log) == 5
        for i in range(len(log) - 1):
            assert log[i].timestamp >= log[i + 1].timestamp

    def test_save_and_load(self, tmp_path):
        settings_path = str(tmp_path / "settings.json")
        audit_path = str(tmp_path / "audit.json")
        m1 = PrivacyManager(settings_path=settings_path, audit_path=audit_path)
        asyncio.get_event_loop().run_until_complete(
            m1.update_setting("browser_monitoring", True)
        )
        asyncio.get_event_loop().run_until_complete(
            m1.log_observation("app", "Test observation")
        )
        asyncio.get_event_loop().run_until_complete(m1.save())

        m2 = PrivacyManager(settings_path=settings_path, audit_path=audit_path)
        asyncio.get_event_loop().run_until_complete(m2.load())
        settings = asyncio.get_event_loop().run_until_complete(m2.get_settings())
        assert settings.browser_monitoring is True
        log = asyncio.get_event_loop().run_until_complete(m2.get_audit_log())
        assert len(log) == 1
        assert log[0].detail == "Test observation"


# ---------------------------------------------------------------------------
# Privacy Facade
# ---------------------------------------------------------------------------


class TestPrivacyFacade:
    def test_facade_get_settings(self):
        p = Privacy()
        settings = asyncio.get_event_loop().run_until_complete(p.get_settings())
        assert isinstance(settings, PrivacySettings)

    def test_facade_is_allowed(self):
        p = Privacy()
        result = asyncio.get_event_loop().run_until_complete(p.is_allowed("application_monitoring"))
        assert result is True

    def test_facade_update_setting(self):
        p = Privacy()
        asyncio.get_event_loop().run_until_complete(
            p.update_setting("browser_monitoring", True)
        )
        result = asyncio.get_event_loop().run_until_complete(p.is_allowed("browser_monitoring"))
        assert result is True
