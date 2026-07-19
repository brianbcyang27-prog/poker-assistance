import sys
import os
import asyncio
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from jarvis.decisions.models import Decision, DecisionImpact, DecisionQuery, DecisionStatus
from jarvis.decisions.engine import DecisionEngine


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# TestDecisionModels
# ---------------------------------------------------------------------------


class TestDecisionModels:
    def test_decision_creation_with_defaults(self):
        d = Decision()
        assert d.id.startswith("decision_")
        assert len(d.id) == 17
        assert d.title == ""
        assert d.impact == "medium"
        assert d.status == "active"
        assert d.date == time.strftime("%Y-%m-%d")
        assert d.timestamp > 0
        assert d.alternatives == []
        assert d.related_entities == []
        assert d.tags == []
        assert d.outcome == ""
        assert d.superseded_by == ""

    def test_decision_creation_low_impact(self):
        d = Decision(title="Use tabs", impact="low", tags=["style"])
        assert d.impact == "low"
        assert d.tags == ["style"]

    def test_decision_creation_medium_impact(self):
        d = Decision(title="Pick ORM", impact="medium")
        assert d.impact == "medium"

    def test_decision_creation_high_impact(self):
        d = Decision(title="Cloud provider", impact="high")
        assert d.impact == "high"

    def test_decision_creation_critical_impact(self):
        d = Decision(title="Security protocol", impact="critical")
        assert d.impact == "critical"

    def test_decision_to_dict(self):
        d = Decision(
            id="d_test",
            title="Test decision",
            description="desc",
            reason="reason",
            alternatives=["a", "b"],
            chosen_option="a",
            impact="high",
            status="active",
            related_entities=["ent1"],
            tags=["tag1", "tag2"],
        )
        result = d.to_dict()
        assert result["id"] == "d_test"
        assert result["title"] == "Test decision"
        assert result["description"] == "desc"
        assert result["reason"] == "reason"
        assert result["alternatives"] == ["a", "b"]
        assert result["chosen_option"] == "a"
        assert result["impact"] == "high"
        assert result["status"] == "active"
        assert result["related_entities"] == ["ent1"]
        assert result["tags"] == ["tag1", "tag2"]
        assert result["outcome"] == ""
        assert result["superseded_by"] == ""
        assert isinstance(result["date"], str)
        assert isinstance(result["timestamp"], float)

    def test_decision_from_dict_roundtrip(self):
        d = Decision(
            id="rt_1",
            title="Roundtrip",
            description="Testing roundtrip",
            reason="Because",
            alternatives=["x", "y"],
            chosen_option="x",
            impact="critical",
            status="superseded",
            date="2025-06-15",
            timestamp=1234567890.0,
            related_entities=["e1", "e2"],
            tags=["t1"],
            outcome="good",
            superseded_by="rt_2",
        )
        data = d.to_dict()
        d2 = Decision.from_dict(data)
        assert d2.id == "rt_1"
        assert d2.title == "Roundtrip"
        assert d2.impact == "critical"
        assert d2.status == "superseded"
        assert d2.timestamp == 1234567890.0
        assert d2.alternatives == ["x", "y"]
        assert d2.tags == ["t1"]
        assert d2.outcome == "good"
        assert d2.superseded_by == "rt_2"

    def test_decision_from_dict_defaults(self):
        d = Decision.from_dict({"id": "", "title": "", "impact": "medium"})
        assert d.title == ""
        assert d.impact == "medium"
        assert d.status == "active"
        assert d.alternatives == []

    def test_decision_auto_id_uniqueness(self):
        d1 = Decision()
        d2 = Decision()
        assert d1.id != d2.id


# ---------------------------------------------------------------------------
# TestDecisionQuery
# ---------------------------------------------------------------------------


class TestDecisionQuery:
    def test_query_defaults(self):
        q = DecisionQuery()
        assert q.tags == []
        assert q.impact == ""
        assert q.status == "active"
        assert q.related_entity == ""
        assert q.start_date == ""
        assert q.end_date == ""
        assert q.limit == 50

    def test_query_custom(self):
        q = DecisionQuery(
            tags=["infra"],
            impact="high",
            status="superseded",
            related_entity="proj_x",
            start_date="2025-01-01",
            end_date="2025-12-31",
            limit=5,
        )
        assert q.tags == ["infra"]
        assert q.impact == "high"
        assert q.limit == 5

    def test_query_to_dict(self):
        q = DecisionQuery(tags=["a", "b"], impact="low", limit=10)
        d = q.to_dict()
        assert d["tags"] == ["a", "b"]
        assert d["impact"] == "low"
        assert d["limit"] == 10
        assert d["status"] == "active"

    def test_query_from_dict_roundtrip(self):
        q = DecisionQuery(
            tags=["x"],
            impact="critical",
            status="archived",
            related_entity="ent",
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit=25,
        )
        data = q.to_dict()
        q2 = DecisionQuery.from_dict(data)
        assert q2.tags == ["x"]
        assert q2.impact == "critical"
        assert q2.status == "archived"
        assert q2.related_entity == "ent"
        assert q2.limit == 25

    def test_query_from_dict_defaults(self):
        q = DecisionQuery.from_dict({})
        assert q.tags == []
        assert q.status == "active"
        assert q.limit == 50


# ---------------------------------------------------------------------------
# TestDecisionEngine
# ---------------------------------------------------------------------------


class TestDecisionEngine:
    @pytest.fixture
    def engine(self, tmp_path):
        return DecisionEngine(storage_dir=str(tmp_path))

    def test_record_basic(self, engine):
        d = _run(engine.record(title="Use pytest", reason="It's better"))
        assert d.title == "Use pytest"
        assert d.reason == "It's better"
        assert d.id.startswith("decision_")
        assert d.impact == "medium"
        assert d.status == "active"

    def test_record_with_all_fields(self, engine):
        d = _run(engine.record(
            title="Architecture",
            description="Choose architecture",
            reason="Scalability",
            alternatives=["monolith", "microservices"],
            chosen_option="microservices",
            impact="high",
            related_entities=["proj1"],
            tags=["arch", "infra"],
        ))
        assert d.description == "Choose architecture"
        assert d.chosen_option == "microservices"
        assert d.impact == "high"
        assert d.tags == ["arch", "infra"]

    def test_record_multiple_decisions(self, engine):
        d1 = _run(engine.record(title="First", tags=["a"]))
        d2 = _run(engine.record(title="Second", tags=["b"]))
        d3 = _run(engine.record(title="Third", tags=["a"]))
        assert d1.id != d2.id != d3.id
        all_d = _run(engine.get_all())
        assert len(all_d) == 3

    def test_get_existing(self, engine):
        d = _run(engine.record(title="Findable"))
        found = _run(engine.get(d.id))
        assert found is not None
        assert found.id == d.id

    def test_get_nonexistent(self, engine):
        found = _run(engine.get("decision_nonexistent"))
        assert found is None

    def test_query_by_impact(self, engine):
        _run(engine.record(title="Low one", impact="low"))
        _run(engine.record(title="High one", impact="high"))
        _run(engine.record(title="Another high", impact="high"))
        q = DecisionQuery(impact="high")
        results = _run(engine.query(q))
        assert len(results) == 2
        assert all(d.impact == "high" for d in results)

    def test_query_by_tags(self, engine):
        _run(engine.record(title="Tagged", tags=["infra", "dev"]))
        _run(engine.record(title="Other", tags=["prod"]))
        q = DecisionQuery(tags=["infra"])
        results = _run(engine.query(q))
        assert len(results) == 1
        assert results[0].title == "Tagged"

    def test_query_by_status(self, engine):
        d = _run(engine.record(title="Will supersede"))
        _run(engine.record(title="Active"))
        _run(engine.supersede(d.id, "New", "Better", "opt"))
        q_superseded = DecisionQuery(status="superseded")
        results_superseded = _run(engine.query(q_superseded))
        assert len(results_superseded) == 1
        assert results_superseded[0].title == "Will supersede"
        q_active = DecisionQuery(status="active")
        results_active = _run(engine.query(q_active))
        assert len(results_active) == 2

    def test_query_limit(self, engine):
        for i in range(10):
            _run(engine.record(title=f"Decision {i}"))
        q = DecisionQuery(limit=3)
        results = _run(engine.query(q))
        assert len(results) == 3

    def test_query_by_related_entity(self, engine):
        _run(engine.record(title="A", related_entities=["proj_x"]))
        _run(engine.record(title="B", related_entities=["proj_y"]))
        q = DecisionQuery(related_entity="proj_x")
        results = _run(engine.query(q))
        assert len(results) == 1
        assert results[0].title == "A"

    def test_update_outcome(self, engine):
        d = _run(engine.record(title="Update me"))
        updated = _run(engine.update_outcome(d.id, "Worked great"))
        assert updated is not None
        assert updated.outcome == "Worked great"

    def test_update_outcome_nonexistent(self, engine):
        result = _run(engine.update_outcome("decision_fake", "nope"))
        assert result is None

    def test_supersede(self, engine):
        old = _run(engine.record(title="Old way", related_entities=["e1"], tags=["t1"]))
        new = _run(engine.supersede(old.id, "New way", "Better", "new_opt"))
        old_reloaded = _run(engine.get(old.id))
        assert old_reloaded.status == "superseded"
        assert old_reloaded.superseded_by == new.id
        assert new.title == "New way"
        assert new.status == "active"
        assert new.related_entities == ["e1"]
        assert new.tags == ["t1"]

    def test_supersede_nonexistent(self, engine):
        new = _run(engine.supersede("decision_ghost", "Replacement", "Because", "r"))
        assert new.title == "Replacement"

    def test_reverse(self, engine):
        d = _run(engine.record(title="Reversible"))
        rev = _run(engine.reverse(d.id, "Not working out"))
        assert rev.status == "reversed"
        assert rev.outcome == "Reversed: Not working out"

    def test_reverse_without_reason(self, engine):
        d = _run(engine.record(title="No reason"))
        rev = _run(engine.reverse(d.id))
        assert rev.status == "reversed"
        assert rev.outcome == ""

    def test_reverse_nonexistent(self, engine):
        result = _run(engine.reverse("decision_no", "Because"))
        assert result is None

    def test_why(self, engine):
        _run(engine.record(title="About proj_x", related_entities=["proj_x"]))
        _run(engine.record(title="About proj_y", related_entities=["proj_y"]))
        _run(engine.record(title="Superseded proj_x", related_entities=["proj_x"]))
        old = _run(engine.get_all())
        for d in old:
            if d.title == "Superseded proj_x":
                _run(engine.supersede(d.id, "New", "R", "C"))
        results = _run(engine.why("proj_x"))
        assert len(results) == 2
        titles = {d.title for d in results}
        assert "About proj_x" in titles
        assert "New" in titles

    def test_why_no_results(self, engine):
        results = _run(engine.why("nonexistent_entity"))
        assert results == []

    def test_get_active(self, engine):
        d1 = _run(engine.record(title="Active 1"))
        d2 = _run(engine.record(title="Active 2"))
        _run(engine.record(title="Will be reversed"))
        all_d = _run(engine.get_all())
        for d in all_d:
            if d.title == "Will be reversed":
                _run(engine.reverse(d.id))
        active = _run(engine.get_active())
        assert len(active) == 2

    def test_get_by_impact(self, engine):
        _run(engine.record(title="L", impact="low"))
        _run(engine.record(title="H1", impact="high"))
        _run(engine.record(title="H2", impact="high"))
        _run(engine.record(title="C", impact="critical"))
        high = _run(engine.get_by_impact("high"))
        assert len(high) == 2
        low = _run(engine.get_by_impact("low"))
        assert len(low) == 1
        critical = _run(engine.get_by_impact("critical"))
        assert len(critical) == 1

    def test_get_recent(self, engine):
        for i in range(5):
            _run(engine.record(title=f"R{i}"))
        recent = _run(engine.get_recent(3))
        assert len(recent) == 3

    def test_get_recent_more_than_exist(self, engine):
        _run(engine.record(title="Only one"))
        recent = _run(engine.get_recent(100))
        assert len(recent) == 1

    def test_search(self, engine):
        _run(engine.record(title="FastAPI decision", reason="Async support"))
        _run(engine.record(title="Database choice", reason="Performance"))
        _run(engine.record(title="Logging setup", chosen_option="loguru"))
        results = _run(engine.search("fast"))
        assert len(results) == 1
        assert results[0].title == "FastAPI decision"

    def test_search_in_reason(self, engine):
        _run(engine.record(title="X", reason="Performance benchmarks"))
        results = _run(engine.search("performance"))
        assert len(results) == 1

    def test_search_in_chosen_option(self, engine):
        _run(engine.record(title="Logger", chosen_option="loguru"))
        results = _run(engine.search("loguru"))
        assert len(results) == 1

    def test_search_no_results(self, engine):
        _run(engine.record(title="Something"))
        results = _run(engine.search("zzz_nonexistent"))
        assert results == []

    def test_save_and_load(self, tmp_path):
        engine1 = DecisionEngine(storage_dir=str(tmp_path))
        _run(engine1.record(title="Saved decision", impact="high", tags=["persist"]))
        engine2 = DecisionEngine(storage_dir=str(tmp_path))
        _run(engine2.load())
        all_d = _run(engine2.get_all())
        assert len(all_d) == 1
        assert all_d[0].title == "Saved decision"
        assert all_d[0].impact == "high"
        assert all_d[0].tags == ["persist"]

    def test_load_nonexistent_file(self, engine):
        _run(engine.load())
        assert _run(engine.get_all()) == []

    def test_query_sorted_by_timestamp(self, engine):
        d1 = _run(engine.record(title="First"))
        d2 = _run(engine.record(title="Second"))
        q = DecisionQuery()
        results = _run(engine.query(q))
        assert results[0].id == d2.id
        assert results[1].id == d1.id
