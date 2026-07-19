import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import tempfile
import pytest

from jarvis.agents.personas.models import Persona, AgentIdentity, AgentRole
from jarvis.agents.personas.registry import PersonaRegistry


loop = asyncio.get_event_loop()


# ── Persona ───────────────────────────────────────────────────────────────────

class TestPersona:
    def test_create_default(self):
        p = Persona()
        assert p.name == ""
        assert p.role == "developer"
        assert p.active is True

    def test_create_explicit(self):
        p = Persona(
            name="TestAgent",
            role="tester",
            personality="thorough",
            expertise=["pytest", "coverage"],
            communication_style="precise",
        )
        assert p.name == "TestAgent"
        assert p.role == "tester"
        assert "pytest" in p.expertise

    def test_to_dict(self):
        p = Persona(name="Agent1", role="developer", greeting="Let's code!")
        d = p.to_dict()
        assert d["name"] == "Agent1"
        assert d["role"] == "developer"
        assert d["greeting"] == "Let's code!"
        assert "strengths" in d
        assert "weaknesses" in d
        assert "preferred_tools" in d

    def test_to_dict_all_fields(self):
        p = Persona(
            name="X",
            role="architect",
            personality="visionary",
            expertise=["systems"],
            communication_style="abstract",
            strengths=["holistic"],
            weaknesses=["over-engineer"],
            preferred_tools=["diagrams"],
            greeting="Design!",
            icon="♠",
            color="#000",
            active=False,
        )
        d = p.to_dict()
        assert d["icon"] == "♠"
        assert d["color"] == "#000"
        assert d["active"] is False

    def test_defaults_empty_lists(self):
        p = Persona()
        assert p.expertise == []
        assert p.strengths == []
        assert p.weaknesses == []
        assert p.preferred_tools == []


# ── AgentIdentity ─────────────────────────────────────────────────────────────

class TestAgentIdentity:
    def test_create_default(self):
        i = AgentIdentity()
        assert i.agent_id == ""
        assert i.persona is None
        assert i.mission_count == 0
        assert i.success_rate == 0.0

    def test_create_with_persona(self):
        p = Persona(name="Tester", role="tester")
        i = AgentIdentity(agent_id="agent_1", persona=p, mission_count=5, success_rate=0.9)
        assert i.persona.name == "Tester"
        assert i.mission_count == 5

    def test_to_dict(self):
        p = Persona(name="Dev", role="developer")
        i = AgentIdentity(agent_id="a1", persona=p, mission_count=10, success_rate=0.85)
        d = i.to_dict()
        assert d["agent_id"] == "a1"
        assert d["persona"]["name"] == "Dev"
        assert d["mission_count"] == 10
        assert d["success_rate"] == 0.85

    def test_to_dict_no_persona(self):
        i = AgentIdentity(agent_id="a2")
        d = i.to_dict()
        assert d["persona"] is None

    def test_to_dict_achievements(self):
        i = AgentIdentity(
            agent_id="a3",
            special_achievements=["100 missions", "zero bugs"],
        )
        d = i.to_dict()
        assert len(d["special_achievements"]) == 2


# ── PersonaRegistry ───────────────────────────────────────────────────────────

class TestPersonaRegistry:
    def _make(self):
        tmpdir = tempfile.mkdtemp()
        return PersonaRegistry(store_path=os.path.join(tmpdir, "personas.json"))

    def test_create(self):
        reg = self._make()
        assert reg._personas == {}

    def test_load_defaults(self):
        reg = self._make()
        all_p = loop.run_until_complete(reg.get_all())
        assert len(all_p) >= 10

    def test_get_by_id(self):
        reg = self._make()
        persona = loop.run_until_complete(reg.get("k_engineer"))
        assert persona is not None
        assert persona.role == "developer"

    def test_get_nonexistent(self):
        reg = self._make()
        persona = loop.run_until_complete(reg.get("nonexistent_agent"))
        assert persona is None

    def test_get_by_role(self):
        reg = self._make()
        persona = loop.run_until_complete(reg.get_by_role("tester"))
        assert persona is not None
        assert persona.role == "tester"

    def test_get_by_role_missing(self):
        reg = self._make()
        persona = loop.run_until_complete(reg.get_by_role("nonexistent_role"))
        assert persona is None

    def test_get_all(self):
        reg = self._make()
        all_p = loop.run_until_complete(reg.get_all())
        roles = {p.role for p in all_p}
        assert "developer" in roles
        assert "architect" in roles
        assert "tester" in roles

    def test_register(self):
        reg = self._make()
        p = Persona(name="Custom Agent", role="custom", personality="unique")
        result = loop.run_until_complete(reg.register("custom_1", p))
        assert result.name == "Custom Agent"
        fetched = loop.run_until_complete(reg.get("custom_1"))
        assert fetched is not None

    def test_get_random_for_task_coding(self):
        reg = self._make()
        persona = loop.run_until_complete(
            reg.get_random_for_task("implement a new feature in Python")
        )
        assert persona.role == "developer"

    def test_get_random_for_task_testing(self):
        reg = self._make()
        persona = loop.run_until_complete(
            reg.get_random_for_task("write unit tests and check edge cases")
        )
        assert persona.role == "tester"

    def test_get_random_for_task_research(self):
        reg = self._make()
        persona = loop.run_until_complete(
            reg.get_random_for_task("investigate and compare database options")
        )
        assert persona.role == "researcher"

    def test_get_random_for_task_architecture(self):
        reg = self._make()
        persona = loop.run_until_complete(
            reg.get_random_for_task("design the system architecture for microservices")
        )
        assert persona.role == "architect"

    def test_get_random_for_task_unknown(self):
        reg = self._make()
        persona = loop.run_until_complete(
            reg.get_random_for_task("xyzzy nothing matches")
        )
        assert persona is not None  # returns random persona

    def test_save_and_reload(self):
        reg = self._make()
        loop.run_until_complete(reg._ensure_loaded())
        p = Persona(name="Persisted", role="dev")
        loop.run_until_complete(reg.register("persist_1", p))
        loop.run_until_complete(reg.save())

        reg2 = PersonaRegistry(store_path=reg._store_path)
        fetched = loop.run_until_complete(reg2.get("persist_1"))
        assert fetched is not None
        assert fetched.name == "Persisted"

    def test_agent_role_enum(self):
        assert AgentRole.ARCHITECT.value == "architect"
        assert AgentRole.DEVELOPER.value == "developer"
        assert AgentRole.TESTER.value == "tester"
        assert AgentRole.SECURITY.value == "security"
