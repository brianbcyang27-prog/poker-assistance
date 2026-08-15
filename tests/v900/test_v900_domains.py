"""v9.0.0 tests — domain model, registry, and execution (M1)."""

import asyncio


class TestDomainEnum:
    """Domain enum covers all seven v10 domains."""

    def test_seven_domains(self):
        from jarvis.domains.models import Domain

        assert {d.value for d in Domain} == {
            "engineering",
            "education",
            "research",
            "studio",
            "finance",
            "personal",
            "system",
        }

    def test_system_is_internal(self):
        from jarvis.domains.models import Domain

        assert Domain.SYSTEM.is_user_domain is False
        assert all(d.is_user_domain for d in Domain if d is not Domain.SYSTEM)

    def test_master_member_id(self):
        from jarvis.domains.models import Domain

        assert Domain.EDUCATION.master_member_id == "education.master"
        assert Domain.STUDIO.master_member_id == "studio.master"
        assert Domain.FINANCE.master_member_id == "finance.master"
        assert Domain.SYSTEM.master_member_id == "system.master"


class TestDomainInfo:
    """DOMAIN_INFO metadata table is complete and correct."""

    def test_all_domains_have_metadata(self):
        from jarvis.domains.models import DOMAIN_INFO, Domain

        assert set(DOMAIN_INFO) == set(Domain)

    def test_new_domain_workers(self):
        from jarvis.domains.models import DOMAIN_INFO, Domain

        assert DOMAIN_INFO[Domain.EDUCATION].worker_member_ids == (
            "education.tutor",
            "education.curriculum",
            "education.assessment",
            "education.explainer",
        )
        assert DOMAIN_INFO[Domain.STUDIO].worker_member_ids == (
            "studio.modeling",
            "studio.rendering",
            "studio.animation",
            "studio.fabrication",
        )
        assert DOMAIN_INFO[Domain.FINANCE].worker_member_ids == (
            "finance.budget",
            "finance.expense",
            "finance.investments",
            "finance.tax",
        )

    def test_system_marked_internal(self):
        from jarvis.domains.models import DOMAIN_INFO, Domain

        assert DOMAIN_INFO[Domain.SYSTEM].internal is True
        assert DOMAIN_INFO[Domain.SYSTEM].is_user_domain is False
        assert all(
            not info.internal for domain, info in DOMAIN_INFO.items() if domain is not Domain.SYSTEM
        )

    def test_king_backed_worker_ids(self):
        from jarvis.domains.models import DOMAIN_INFO, Domain

        assert len(DOMAIN_INFO[Domain.ENGINEERING].worker_member_ids) == 13
        assert "♠Q" in DOMAIN_INFO[Domain.ENGINEERING].worker_member_ids
        assert DOMAIN_INFO[Domain.RESEARCH].worker_member_ids == ("♦Q", "♦J", "♦10")
        assert DOMAIN_INFO[Domain.PERSONAL].worker_member_ids == ("♥Q", "♥J", "♥10", "♥9")
        assert DOMAIN_INFO[Domain.SYSTEM].worker_member_ids == ("♣Q", "♣J", "♣10")


class TestDomainAliases:
    """Alias resolution helpers."""

    def test_domain_by_alias(self):
        from jarvis.domains.models import Domain, domain_by_alias

        assert domain_by_alias("education") is Domain.EDUCATION
        assert domain_by_alias("3d studio") is Domain.STUDIO
        assert domain_by_alias("money") is Domain.FINANCE
        assert domain_by_alias("Unknown") is None

    def test_user_domains_order(self):
        from jarvis.domains.models import Domain, user_domains

        assert user_domains() == [
            Domain.ENGINEERING,
            Domain.EDUCATION,
            Domain.RESEARCH,
            Domain.STUDIO,
            Domain.FINANCE,
            Domain.PERSONAL,
        ]

    def test_domain_from_member_id(self):
        from jarvis.domains.models import Domain, domain_from_member_id

        assert domain_from_member_id("education.tutor") is Domain.EDUCATION
        assert domain_from_member_id("studio.modeling") is Domain.STUDIO
        assert domain_from_member_id("finance.tax") is Domain.FINANCE
        assert domain_from_member_id("") is None
        assert domain_from_member_id("unknown") is None


class TestDomainMasters:
    """Standalone masters build their canonical member rosters."""

    def test_education_master(self):
        from jarvis.domains.education import EducationMaster

        master = EducationMaster()
        assert master.member_id == "education.master"
        assert master.card_id == "education.master"
        assert master.domain.value == "education"
        assert master.is_master is True
        assert master.is_king_backed is False
        assert [m.member_id for m in master.get_all_members()] == [
            "education.tutor",
            "education.curriculum",
            "education.assessment",
            "education.explainer",
        ]

    def test_studio_master(self):
        from jarvis.domains.studio import StudioMaster

        master = StudioMaster()
        assert [m.member_id for m in master.get_all_members()] == [
            "studio.modeling",
            "studio.rendering",
            "studio.animation",
            "studio.fabrication",
        ]

    def test_finance_master(self):
        from jarvis.domains.finance import FinanceMaster

        master = FinanceMaster()
        assert [m.member_id for m in master.get_all_members()] == [
            "finance.budget",
            "finance.expense",
            "finance.investments",
            "finance.tax",
        ]

    def test_worker_fields(self):
        from jarvis.domains.education import TutorWorker
        from jarvis.domains.models import Domain

        worker = TutorWorker(Domain.EDUCATION, "education.tutor")
        assert worker.member_id == "education.tutor"
        assert worker.card_id == "education.tutor"
        assert worker.role.value == "worker"
        assert worker.is_master is False
        assert "Tutor" in worker.get_system_prompt()
        data = worker.to_dict()
        assert data["member_id"] == "education.tutor"
        assert data["domain"] == "education"
        assert data["card_id"] == "education.tutor"
        assert data["role"] == "worker"

    def test_master_status_shape(self):
        from jarvis.domains.education import EducationMaster

        status = EducationMaster().get_status()
        assert status["member_id"] == "education.master"
        assert status["domain"] == "education"
        assert "education.tutor" in status["members"]
        assert status["active_tasks"] == 0
        assert status["backed_by_king"] is None


class TestDomainRegistry:
    """DomainRegistry builds masters and attaches Kings."""

    def test_standalone_domains_built(self):
        from jarvis.domains.education import EducationMaster
        from jarvis.domains.finance import FinanceMaster
        from jarvis.domains.models import Domain
        from jarvis.domains.registry import DomainRegistry
        from jarvis.domains.studio import StudioMaster

        reg = DomainRegistry()
        assert isinstance(reg.get("education"), EducationMaster)
        assert isinstance(reg.get(Domain.STUDIO), StudioMaster)
        assert isinstance(reg.get("finance"), FinanceMaster)
        assert reg.get("bogus") is None
        assert {m.domain for m in reg.all_user()} == {
            Domain.ENGINEERING,
            Domain.EDUCATION,
            Domain.RESEARCH,
            Domain.STUDIO,
            Domain.FINANCE,
            Domain.PERSONAL,
        }

    def test_attach_king(self):
        from jarvis.agents.kings import EngineeringKing
        from jarvis.domains.registry import DomainRegistry

        reg = DomainRegistry()
        reg.attach_kings([EngineeringKing()])
        eng = reg.get("engineering")
        assert eng is not None
        assert eng.is_king_backed is True
        assert eng.get_status()["backed_by_king"] == "♠K"
        assert len(eng.get_all_members()) == 13
        assert "♠Q" in eng.get_status()["members"]

    def test_all_excludes_nothing_but_system_not_user(self):
        from jarvis.agents.kings import EngineeringKing
        from jarvis.domains.registry import DomainRegistry

        reg = DomainRegistry()
        reg.attach_kings([EngineeringKing()])
        values = [m.domain.value for m in reg.all()]
        assert "engineering" in values
        assert "system" not in [m.domain.value for m in reg.all_user()]

    def test_get_member_across_domains(self):
        from jarvis.domains.registry import DomainRegistry

        reg = DomainRegistry()
        assert reg.get_member("education.tutor") is not None
        assert reg.get_member("studio.animation") is not None
        assert reg.get_member("missing") is None


class TestDomainExecution:
    """DomainMaster execution flow with a mocked LLM."""

    def _fake_llm(self, plan=None):
        class FakeLLM:
            def chat_json(self, message, system_prompt=None, **kwargs):
                if plan is None:
                    return {"parse_error": True, "raw_response": "not json"}
                return plan

            def chat(self, message, system_prompt=None, **kwargs):
                if "confidence" in system_prompt:
                    return "0.9"
                if "potential issues" in system_prompt:
                    return "None"
                return "A complete, verified answer."

        return FakeLLM()

    def _stub_llms(self, master, plan=None):
        master._get_llm = lambda: self._fake_llm(plan)
        for member in master.get_all_members():
            member._get_llm = lambda: self._fake_llm()

    def test_execute_returns_completed(self):
        from jarvis.core.models import Task
        from jarvis.domains.education import EducationMaster

        master = EducationMaster()
        plan = {
            "subtasks": [
                {
                    "name": "Explain X",
                    "description": "Teach the concept",
                    "assigned_member": "education.tutor",
                    "priority": 5,
                }
            ]
        }
        self._stub_llms(master, plan)

        async def run():
            return await master.execute_task(
                Task(name="Teach", description="Explain X", assigned_to="education.master")
            )

        result = asyncio.run(run())
        assert result.status == "completed"
        assert result.confidence >= 0.8
        assert "A complete, verified answer." in result.content

    def test_execute_auto_assigns_on_parse_failure(self):
        from jarvis.core.models import Task
        from jarvis.domains.finance import FinanceMaster

        master = FinanceMaster()
        self._stub_llms(master)

        async def run():
            return await master.execute_task(
                Task(name="Budget", description="Plan a budget", assigned_to="finance.master")
            )

        result = asyncio.run(run())
        assert result.status == "completed"
        assert result.sender == "finance.master"

    def test_execute_no_members_returns_error(self):
        from jarvis.core.models import Task
        from jarvis.domains.base import DomainMaster
        from jarvis.domains.models import Domain

        master = DomainMaster(Domain.EDUCATION, "education.master")

        async def run():
            return await master.execute_task(
                Task(name="Teach", description="Explain X", assigned_to="education.master")
            )

        result = asyncio.run(run())
        assert result.status == "error"
        assert "No workers" in result.content

    def test_king_backed_delegates_to_king(self):
        from jarvis.core.models import AgentMessage, Suit, Task
        from jarvis.domains.registry import DomainRegistry

        class FakeKing:
            def __init__(self):
                self.suit = Suit.SPADES
                self.card_id = "♠K"

            def get_all_workers(self):
                return []

            async def execute_task(self, task):
                return AgentMessage(
                    sender="♠K",
                    receiver="J",
                    task_id=task.id,
                    content="king handled it",
                    status="completed",
                    confidence=0.95,
                )

        reg = DomainRegistry()
        reg.attach_kings([FakeKing()])
        master = reg.get("engineering")
        assert master.is_king_backed is True
        assert master.get_status()["backed_by_king"] == "♠K"

        async def run():
            return await master.execute_task(
                Task(name="Build", description="Do it", assigned_to="♠K")
            )

        result = asyncio.run(run())
        assert result.status == "completed"
        assert "king handled it" in result.content


class TestDomainsRouter:
    """The /api/domains router is registered with the expected routes."""

    def test_router_routes(self):
        from jarvis.web.routers import domains

        paths = {r.path for r in domains.router.routes}
        assert "/api/domains" in paths
        assert "/api/domains/{domain_id}" in paths

    def test_web_main_has_registry_global(self):
        import jarvis.web.main as web_main

        assert hasattr(web_main, "domain_registry")
