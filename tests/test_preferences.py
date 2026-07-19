"""Tests for JARVIS Preferences module (v5.4.0)."""

import sys
import os
import asyncio
import tempfile
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.preferences.models import (
    Preference,
    PreferenceCategory,
    PreferenceProfile,
)
from jarvis.preferences.engine import PreferenceEngine


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestPreferenceModels:
    def test_preference_creation(self):
        p = Preference(category="coding", key="language", value="python")
        assert p.category == "coding"
        assert p.key == "language"
        assert p.value == "python"
        assert p.id.startswith("pref_")
        assert p.first_seen > 0
        assert p.last_seen > 0

    def test_preference_defaults(self):
        p = Preference()
        assert p.confidence == 0.8
        assert p.source == ""
        assert p.evidence == []
        assert p.times_reinforced == 1
        assert p.category == "general"

    def test_preference_to_dict(self):
        p = Preference(
            category="coding", key="editor", value="vscode",
            confidence=0.9, source="observation",
            evidence=["user always opens vscode"], times_reinforced=3,
        )
        d = p.to_dict()
        assert d["category"] == "coding"
        assert d["key"] == "editor"
        assert d["value"] == "vscode"
        assert d["confidence"] == 0.9
        assert d["times_reinforced"] == 3
        assert len(d["evidence"]) == 1

    def test_preference_from_dict(self):
        data = {
            "id": "pref_test1", "category": "tools", "key": "vcs",
            "value": "git", "confidence": 0.95, "source": "manual",
            "evidence": ["known fact"], "first_seen": 1000.0,
            "last_seen": 2000.0, "times_reinforced": 5,
        }
        p = Preference.from_dict(data)
        assert p.id == "pref_test1"
        assert p.confidence == 0.95
        assert p.times_reinforced == 5

    def test_preference_from_dict_generates_id_when_empty(self):
        p = Preference.from_dict({"category": "test", "key": "k", "value": "v"})
        assert p.id.startswith("pref_")
        assert p.confidence == 0.8

    def test_preference_from_dict_preserves_timestamps(self):
        data = {"first_seen": 100.0, "last_seen": 200.0}
        p = Preference.from_dict(data)
        assert p.first_seen == 100.0
        assert p.last_seen == 200.0

    def test_preference_all_categories(self):
        for cat in PreferenceCategory:
            p = Preference(category=cat.value, key="test", value="val")
            assert p.category == cat.value

    def test_preference_auto_id_unique(self):
        a = Preference()
        b = Preference()
        assert a.id != b.id

    def test_preference_evidence_list(self):
        p = Preference(evidence=["obs1", "obs2", "obs3"])
        assert len(p.evidence) == 3

    def test_preference_category_enum_values(self):
        assert PreferenceCategory.CODING.value == "coding"
        assert PreferenceCategory.HARDWARE.value == "hardware"
        assert PreferenceCategory.TOOLS.value == "tools"
        assert PreferenceCategory.WORKFLOW.value == "workflow"
        assert PreferenceCategory.DESIGN.value == "design"
        assert PreferenceCategory.DEPLOYMENT.value == "deployment"
        assert PreferenceCategory.LEARNING.value == "learning"
        assert PreferenceCategory.GENERAL.value == "general"

    def test_preference_to_dict_roundtrip(self):
        p = Preference(category="x", key="k", value="v", confidence=0.7,
                       source="test", evidence=["e1"], times_reinforced=3)
        d = p.to_dict()
        p2 = Preference.from_dict(d)
        assert p2.category == p.category
        assert p2.key == p.key
        assert p2.value == p.value
        assert p2.confidence == p.confidence


class TestPreferenceProfile:
    def test_profile_defaults(self):
        prof = PreferenceProfile()
        assert prof.category == ""
        assert prof.preferences == []
        assert prof.dominant_values == {}

    def test_profile_to_dict(self):
        p = Preference(category="coding", key="lang", value="python")
        prof = PreferenceProfile(
            category="coding",
            preferences=[p],
            dominant_values={"lang": "python"},
        )
        d = prof.to_dict()
        assert d["category"] == "coding"
        assert len(d["preferences"]) == 1
        assert d["dominant_values"]["lang"] == "python"

    def test_profile_to_dict_serializes_preferences(self):
        p1 = Preference(category="coding", key="a", value="1")
        p2 = Preference(category="coding", key="b", value="2")
        prof = PreferenceProfile(category="coding", preferences=[p1, p2])
        d = prof.to_dict()
        assert all(isinstance(pd, dict) for pd in d["preferences"])

    def test_profile_from_dict(self):
        data = {
            "category": "tools",
            "preferences": [
                {"id": "p1", "category": "tools", "key": "editor", "value": "vim"}
            ],
            "dominant_values": {"editor": "vim"},
        }
        prof = PreferenceProfile.from_dict(data)
        assert prof.category == "tools"
        assert len(prof.preferences) == 1
        assert prof.dominant_values["editor"] == "vim"

    def test_profile_from_dict_empty(self):
        prof = PreferenceProfile.from_dict({})
        assert prof.category == ""
        assert prof.preferences == []
        assert prof.dominant_values == {}


# ════════════════════════════════════════════════════════════
# Engine Tests
# ════════════════════════════════════════════════════════════

class TestPreferenceEngine:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.engine = PreferenceEngine(storage_dir=self._tmpdir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_learn_new(self):
        p = _run(self.engine.learn("coding", "language", "python"))
        assert p.key == "language"
        assert p.value == "python"
        assert p.confidence == 0.8

    def test_learn_reinforces_existing(self):
        _run(self.engine.learn("coding", "language", "python"))
        p2 = _run(self.engine.learn("coding", "language", "python"))
        assert p2.times_reinforced == 2
        assert p2.confidence > 0.8

    def test_learn_with_evidence(self):
        p = _run(self.engine.learn("coding", "style", "clean",
                                   evidence=["user requested clean code"]))
        assert "user requested clean code" in p.evidence

    def test_learn_with_source(self):
        p = _run(self.engine.learn("coding", "linting", "ruff", source="config"))
        assert p.source == "config"

    def test_reinforce(self):
        p = _run(self.engine.learn("coding", "type_checking", "mypy"))
        original_conf = p.confidence
        reinforced = _run(self.engine.reinforce(p.id, delta=0.1))
        assert reinforced is not None
        assert reinforced.confidence == pytest.approx(original_conf + 0.1)
        assert reinforced.times_reinforced == 2

    def test_reinforce_not_found(self):
        result = _run(self.engine.reinforce("nonexistent", delta=0.1))
        assert result is None

    def test_reinforce_caps_at_1(self):
        p = _run(self.engine.learn("coding", "x", "y", confidence=0.99))
        _run(self.engine.reinforce(p.id, delta=0.2))
        found = _run(self.engine.get("coding", "x"))
        assert found.confidence == 1.0

    def test_get(self):
        _run(self.engine.learn("coding", "editor", "vscode"))
        p = _run(self.engine.get("coding", "editor"))
        assert p is not None
        assert p.value == "vscode"

    def test_get_not_found(self):
        p = _run(self.engine.get("coding", "nonexistent"))
        assert p is None

    def test_get_by_category(self):
        _run(self.engine.learn("coding", "a", "1"))
        _run(self.engine.learn("coding", "b", "2"))
        _run(self.engine.learn("tools", "c", "3"))
        prefs = _run(self.engine.get_by_category("coding"))
        assert len(prefs) == 2

    def test_get_profile(self):
        _run(self.engine.learn("coding", "lang", "python", confidence=0.9))
        _run(self.engine.learn("coding", "editor", "vscode", confidence=0.8))
        _run(self.engine.learn("tools", "vcs", "git", confidence=0.95))
        profiles = _run(self.engine.get_profile())
        assert "coding" in profiles
        assert "tools" in profiles
        assert profiles["coding"].category == "coding"
        assert len(profiles["coding"].preferences) == 2

    def test_get_dominant(self):
        _run(self.engine.learn("coding", "lang", "python", confidence=0.6))
        _run(self.engine.learn("coding", "lang2", "rust", confidence=0.9))
        dominant = _run(self.engine.get_dominant("coding"))
        assert dominant is not None
        assert dominant.key == "lang2"

    def test_get_dominant_empty(self):
        dominant = _run(self.engine.get_dominant("nonexistent"))
        assert dominant is None

    def test_search(self):
        _run(self.engine.learn("coding", "language", "python"))
        _run(self.engine.learn("coding", "linter", "pylint"))
        _run(self.engine.learn("tools", "editor", "vscode"))
        results = _run(self.engine.search("pyth"))
        assert len(results) == 1
        assert results[0].value == "python"

    def test_search_by_value(self):
        _run(self.engine.learn("tools", "vcs", "git"))
        _run(self.engine.learn("tools", "ci", "github_actions"))
        results = _run(self.engine.search("git"))
        assert len(results) >= 1

    def test_search_case_insensitive(self):
        _run(self.engine.learn("coding", "lang", "Python"))
        results = _run(self.engine.search("python"))
        assert len(results) == 1

    def test_contradict_existing(self):
        _run(self.engine.learn("coding", "lang", "python"))
        p = _run(self.engine.contradict("coding", "lang", "rust"))
        assert p.value == "rust"
        assert p.times_reinforced == 1
        assert len(p.evidence) == 1
        assert "contradicted" in p.evidence[0]

    def test_contradict_new(self):
        p = _run(self.engine.contradict("coding", "lang", "go"))
        assert p.value == "go"
        assert p.confidence == 0.8

    def test_forget(self):
        p = _run(self.engine.learn("coding", "temp", "val"))
        success = _run(self.engine.forget(p.id))
        assert success is True
        found = _run(self.engine.get("coding", "temp"))
        assert found is None

    def test_forget_nonexistent(self):
        success = _run(self.engine.forget("nonexistent"))
        assert success is False

    def test_get_coding_preferences(self):
        _run(self.engine.learn("coding", "language", "python"))
        _run(self.engine.learn("coding", "style", "clean"))
        _run(self.engine.learn("tools", "editor", "vscode"))
        coding = _run(self.engine.get_coding_preferences())
        assert "language" in coding
        assert "style" in coding
        assert "editor" not in coding

    def test_get_hardware_preferences(self):
        _run(self.engine.learn("hardware", "mcu", "esp32"))
        _run(self.engine.learn("hardware", "cad", "fusion360"))
        _run(self.engine.learn("coding", "lang", "python"))
        hw = _run(self.engine.get_hardware_preferences())
        assert "mcu" in hw
        assert "cad" in hw
        assert "lang" not in hw

    def test_save_and_load(self):
        _run(self.engine.learn("coding", "language", "python"))
        assert os.path.exists(os.path.join(self._tmpdir, "preferences.json"))

        engine2 = PreferenceEngine(storage_dir=self._tmpdir)
        _run(engine2.load())
        p = _run(engine2.get("coding", "language"))
        assert p is not None
        assert p.value == "python"

    def test_load_missing_file(self):
        engine = PreferenceEngine(storage_dir="/tmp/prefs_nonexistent_test_dir_xyz")
        _run(engine.load())
        assert engine._preferences == {}

    def test_bootstrap(self):
        _run(self.engine.bootstrap())
        coding = _run(self.engine.get_coding_preferences())
        assert "language" in coding
        assert coding["language"] == "python"
        hw = _run(self.engine.get_hardware_preferences())
        assert "mcu" in hw

    def test_bootstrap_skips_if_exists(self):
        _run(self.engine.learn("coding", "language", "rust"))
        _run(self.engine.bootstrap())
        p = _run(self.engine.get("coding", "language"))
        assert p.value == "rust"

    def test_get_all(self):
        _run(self.engine.learn("coding", "a", "1"))
        _run(self.engine.learn("tools", "b", "2"))
        all_prefs = _run(self.engine.get_all())
        assert len(all_prefs) == 2

    def test_learn_multiple_categories(self):
        for cat in ["coding", "hardware", "tools", "workflow", "design"]:
            _run(self.engine.learn(cat, "key", "val"))
        profiles = _run(self.engine.get_profile())
        assert len(profiles) == 5

    def test_get_profile_dominant_values(self):
        _run(self.engine.learn("coding", "lang", "python", confidence=0.7))
        _run(self.engine.learn("coding", "lang", "rust", confidence=0.9))
        profiles = _run(self.engine.get_profile())
        assert profiles["coding"].dominant_values["lang"] == "rust"

    def test_save_persists_json(self):
        _run(self.engine.learn("coding", "language", "python"))
        with open(os.path.join(self._tmpdir, "preferences.json"), "r") as f:
            data = json.load(f)
        assert len(data) == 1
        key = list(data.keys())[0]
        assert data[key]["value"] == "python"

    def test_forget_does_not_affect_others(self):
        p1 = _run(self.engine.learn("coding", "a", "1"))
        _run(self.engine.learn("coding", "b", "2"))
        _run(self.engine.forget(p1.id))
        remaining = _run(self.engine.get_by_category("coding"))
        assert len(remaining) == 1
        assert remaining[0].key == "b"

    def test_contradict_increases_evidence(self):
        _run(self.engine.learn("coding", "lang", "python"))
        _run(self.engine.contradict("coding", "lang", "rust"))
        _run(self.engine.contradict("coding", "lang", "go"))
        p = _run(self.engine.get("coding", "lang"))
        assert p.value == "go"
        assert len(p.evidence) == 2
