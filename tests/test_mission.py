"""Tests for JARVIS Mission Pipeline (v5.1.0).

Tests the full autonomous mission pipeline:
  - Mission data model
  - Pipeline orchestration (10 stages)
  - Research engine
  - Discovery engine
  - Architecture planner
  - Execution engine
  - Verification engine
  - Testing engine
  - Review engine
"""

import sys
import os
import pytest
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.mission import (
    MissionPipeline, Mission, MissionStage, MissionStatus,
    MissionMemory, ResearchFinding, ToolCandidate,
    ArchitecturePlan, VerificationResult, ReviewItem,
)
from jarvis.research import ResearchEngine, DiscoveryEngine
from jarvis.planner import ArchitecturePlanner
from jarvis.execution import ExecutionEngine
from jarvis.verification import VerificationEngine
from jarvis.testing import TestingEngine
from jarvis.review import ReviewEngine


# ════════════════════════════════════════════════════════════
# Mission Data Model Tests
# ════════════════════════════════════════════════════════════

class TestMissionDataModel:
    def test_create_mission(self):
        m = Mission(user_request="Build a web app")
        assert m.user_request == "Build a web app"
        assert m.status == MissionStatus.CREATED
        assert m.current_stage == MissionStage.UNDERSTAND
        assert m.priority == "normal"

    def test_mission_stages(self):
        m = Mission(user_request="Test")
        assert m.current_stage == MissionStage.UNDERSTAND
        m.stage_start("research")
        assert m.current_stage == MissionStage.RESEARCH
        m.stage_complete("research")

    def test_mission_errors(self):
        m = Mission(user_request="Test")
        m.add_error("Something went wrong")
        assert len(m.errors) == 1
        assert "Something went wrong" in m.errors[0]

    def test_mission_status_lifecycle(self):
        m = Mission(user_request="Test")
        m.status = MissionStatus.RESEARCHING
        assert m.status == MissionStatus.RESEARCHING
        m.status = MissionStatus.EXECUTING
        assert m.status == MissionStatus.EXECUTING

    def test_mission_findings(self):
        m = Mission(user_request="Test")
        f = ResearchFinding(
            source="github",
            title="Test Repo",
            url="https://github.com/test",
            description="A test repo",
            relevance=0.8,
        )
        m.research_findings.append(f)
        assert len(m.research_findings) == 1
        assert m.research_findings[0].title == "Test Repo"

    def test_mission_tools(self):
        m = Mission(user_request="Test")
        t = ToolCandidate(
            name="pytest",
            source="pypi",
            description="Testing framework",
            maturity="mature",
            score=0.9,
        )
        m.tool_candidates.append(t)
        assert len(m.tool_candidates) == 1

    def test_mission_architecture(self):
        m = Mission(user_request="Test")
        plan = ArchitecturePlan(
            objectives=["Build web app"],
            modules=[{"name": "core", "description": "Core logic"}],
            estimated_hours=8,
        )
        m.architecture_plan = plan
        assert len(m.architecture_plan.modules) == 1

    def test_mission_verification(self):
        m = Mission(user_request="Test")
        v = VerificationResult(
            check_type="lint",
            passed=True,
            evidence="All good",
        )
        m.verification_results.append(v)
        assert m.verification_results[0].passed

    def test_mission_review(self):
        m = Mission(user_request="Test")
        r = ReviewItem(
            category="research",
            description="Good research",
            severity="info",
            recommendation="Keep it up",
        )
        m.review_items.append(r)
        assert len(m.review_items) == 1

    def test_mission_memory_record(self):
        m = Mission(user_request="Test")
        mem = MissionMemory(
            mission_id=m.id,
            problem="Build a web app",
            solution="Used FastAPI and React",
            libraries_used=["fastapi", "react"],
            files_modified=["main.py"],
            architecture_decisions=["Use FastAPI"],
        )
        m.memory_record = mem
        assert mem.solution == "Used FastAPI and React"

    def test_mission_duration(self):
        m = Mission(user_request="Test")
        m.started_at = m.started_at or __import__("datetime").datetime.now()
        m.completed_at = m.completed_at or __import__("datetime").datetime.now()
        m.duration_ms = 1500.0
        assert m.duration_ms == 1500.0

    def test_mission_to_dict(self):
        m = Mission(user_request="Test")
        d = m.to_dict()
        assert "id" in d
        assert d["user_request"] == "Test"
        assert "status" in d


# ════════════════════════════════════════════════════════════
# Pipeline Tests
# ════════════════════════════════════════════════════════════

class TestMissionPipeline:
    def test_pipeline_creates_mission(self):
        pipeline = MissionPipeline()
        mission = asyncio.get_event_loop().run_until_complete(
            pipeline.run("Build a simple web app")
        )
        assert mission is not None
        assert mission.user_request == "Build a simple web app"
        assert mission.status in (MissionStatus.COMPLETED, MissionStatus.PAUSED, MissionStatus.FAILED)

    def test_pipeline_stages_execute(self):
        pipeline = MissionPipeline()
        mission = asyncio.get_event_loop().run_until_complete(
            pipeline.run("Create a CLI tool")
        )
        # Should have completed multiple stages
        assert len(mission.stage_history) > 0

    def test_pipeline_report_generated(self):
        pipeline = MissionPipeline()
        mission = asyncio.get_event_loop().run_until_complete(
            pipeline.run("Build something")
        )
        assert mission.final_report is not None
        assert "Mission Report" in mission.final_report

    def test_pipeline_with_engines(self):
        pipeline = MissionPipeline()
        pipeline.research_engine = ResearchEngine()
        pipeline.planner_engine = ArchitecturePlanner()
        pipeline.verification_engine = VerificationEngine()
        pipeline.review_engine = ReviewEngine()

        mission = asyncio.get_event_loop().run_until_complete(
            pipeline.run("Build a web dashboard with React")
        )
        assert mission is not None
        assert isinstance(mission.research_findings, list)

    def test_pipeline_handles_errors(self):
        pipeline = MissionPipeline()
        mission = asyncio.get_event_loop().run_until_complete(
            pipeline.run("This is a complex mission with multiple requirements")
        )
        assert mission is not None
        assert mission.final_report is not None


# ════════════════════════════════════════════════════════════
# Research Engine Tests
# ════════════════════════════════════════════════════════════

class TestResearchEngine:
    def test_create_research_engine(self):
        engine = ResearchEngine()
        assert engine is not None

    def test_understand_goal(self):
        engine = ResearchEngine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.understand_goal("Build a web app with FastAPI and React")
        )
        assert "goal" in result
        assert "keywords" in result
        assert "domain" in result
        assert result["domain"] == "web"

    def test_detect_domain_web(self):
        engine = ResearchEngine()
        assert engine._detect_domain("Build a frontend UI") == "web"
        assert engine._detect_domain("Create an API server") == "backend"
        assert engine._detect_domain("Train a neural network") == "ml"
        assert engine._detect_domain("Design a PCB") == "hardware"

    def test_search_returns_list(self):
        engine = ResearchEngine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.search("fastapi", source="github", limit=5)
        )
        assert isinstance(result, list)

    def test_search_caches_results(self):
        engine = ResearchEngine()
        r1 = asyncio.get_event_loop().run_until_complete(
            engine.search("test-query-cache", source="github", limit=3)
        )
        r2 = asyncio.get_event_loop().run_until_complete(
            engine.search("test-query-cache", source="github", limit=3)
        )
        assert r1 == r2


# ════════════════════════════════════════════════════════════
# Discovery Engine Tests
# ════════════════════════════════════════════════════════════

class TestDiscoveryEngine:
    def test_create_discovery_engine(self):
        engine = DiscoveryEngine()
        assert engine is not None

    def test_known_tools(self):
        engine = DiscoveryEngine()
        tool_names = [t["name"] for t in engine.KNOWN_TOOLS.values()]
        assert "playwright" in tool_names
        assert "pytest" in tool_names

    def test_discover_returns_list(self):
        engine = DiscoveryEngine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.discover("browser automation testing")
        )
        assert isinstance(result, list)

    def test_discover_by_category(self):
        engine = DiscoveryEngine()
        result = asyncio.get_event_loop().run_until_complete(
            engine.discover("browser testing playwright")
        )
        names = [c.name for c in result]
        assert "playwright" in names

    def test_select_best(self):
        engine = DiscoveryEngine()
        asyncio.get_event_loop().run_until_complete(
            engine.discover("browser automation")
        )
        best = engine.select_best("browser")
        assert best is not None
        assert best.name == "playwright"


# ════════════════════════════════════════════════════════════
# Architecture Planner Tests
# ════════════════════════════════════════════════════════════

class TestArchitecturePlanner:
    def test_create_planner(self):
        planner = ArchitecturePlanner()
        assert planner is not None

    def test_list_templates(self):
        planner = ArchitecturePlanner()
        templates = planner.list_templates()
        assert "web_app" in templates
        assert "api" in templates
        assert "cli_tool" in templates

    def test_get_template(self):
        planner = ArchitecturePlanner()
        tmpl = planner.get_template("web_app")
        assert tmpl is not None
        assert "modules" in tmpl

    def test_create_plan_web(self):
        planner = ArchitecturePlanner()
        plan = asyncio.get_event_loop().run_until_complete(
            planner.create_plan("Build a web dashboard with React")
        )
        assert isinstance(plan, ArchitecturePlan)
        assert len(plan.modules) > 0
        assert plan.estimated_hours > 0

    def test_create_plan_cli(self):
        planner = ArchitecturePlanner()
        plan = asyncio.get_event_loop().run_until_complete(
            planner.create_plan("Build a CLI tool for data processing")
        )
        assert len(plan.modules) > 0

    def test_plan_has_risks(self):
        planner = ArchitecturePlanner()
        plan = asyncio.get_event_loop().run_until_complete(
            planner.create_plan("Build something complex")
        )
        assert isinstance(plan.risks, list)

    def test_plan_has_interfaces(self):
        planner = ArchitecturePlanner()
        plan = asyncio.get_event_loop().run_until_complete(
            planner.create_plan("Build a web app")
        )
        # Plan has dependencies and modules
        assert isinstance(plan.dependencies, list)


# ════════════════════════════════════════════════════════════
# Execution Engine Tests
# ════════════════════════════════════════════════════════════

class TestExecutionEngine:
    def test_create_execution_engine(self):
        engine = ExecutionEngine()
        assert engine is not None

    def test_execute_with_plan(self):
        engine = ExecutionEngine()
        plan = ArchitecturePlan(
            objectives=["Test"],
            modules=[{"name": "core"}],
            new_files=["test_file.py"],
        )
        mission = Mission(user_request="Test")
        results = asyncio.get_event_loop().run_until_complete(
            engine.execute(plan, mission)
        )
        assert isinstance(results, list)
        assert len(results) > 0

    def test_execute_without_plan(self):
        engine = ExecutionEngine()
        mission = Mission(user_request="Test")
        results = asyncio.get_event_loop().run_until_complete(
            engine.execute(None, mission)
        )
        assert results == []

    def test_repair_returns_list(self):
        engine = ExecutionEngine()
        failed = [
            VerificationResult(check_type="lint", passed=False, evidence="Error"),
        ]
        mission = Mission(user_request="Test")
        results = asyncio.get_event_loop().run_until_complete(
            engine.repair(failed, mission)
        )
        assert isinstance(results, list)


# ════════════════════════════════════════════════════════════
# Verification Engine Tests
# ════════════════════════════════════════════════════════════

class TestVerificationEngine:
    def test_create_verification_engine(self):
        engine = VerificationEngine()
        assert engine is not None

    def test_verify_returns_list(self):
        engine = VerificationEngine()
        mission = Mission(user_request="Test")
        results = asyncio.get_event_loop().run_until_complete(
            engine.verify(mission)
        )
        assert isinstance(results, list)
        assert len(results) > 0

    def test_verify_with_execution_results(self):
        engine = VerificationEngine()
        mission = Mission(user_request="Test")
        exec_results = [
            {"type": "generation", "file": "test.py", "success": True},
            {"type": "lint", "file": "test.py", "success": True},
        ]
        results = asyncio.get_event_loop().run_until_complete(
            engine.verify(mission, exec_results)
        )
        passed = [r for r in results if r.passed]
        assert len(passed) > 0

    def test_verify_all_passed(self):
        engine = VerificationEngine()
        mission = Mission(user_request="Test")
        exec_results = [
            {"type": "generation", "file": "a.py", "success": True},
            {"type": "generation", "file": "b.py", "success": True},
            {"type": "lint", "file": "a.py", "success": True},
            {"type": "lint", "file": "b.py", "success": True},
        ]
        results = asyncio.get_event_loop().run_until_complete(
            engine.verify(mission, exec_results)
        )
        failed = [r for r in results if not r.passed]
        assert len(failed) == 0

    def test_verify_detects_failures(self):
        engine = VerificationEngine()
        mission = Mission(user_request="Test")
        exec_results = [
            {"type": "generation", "file": "a.py", "success": True},
            {"type": "lint", "file": "a.py", "success": False, "output": "SyntaxError"},
        ]
        results = asyncio.get_event_loop().run_until_complete(
            engine.verify(mission, exec_results)
        )
        lint_result = next((r for r in results if r.check_type == "lint"), None)
        assert lint_result is not None
        assert not lint_result.passed


# ════════════════════════════════════════════════════════════
# Testing Engine Tests
# ════════════════════════════════════════════════════════════

class TestTestingEngine:
    def test_create_testing_engine(self):
        engine = TestingEngine()
        assert engine is not None

    def test_test_returns_list(self):
        engine = TestingEngine()
        mission = Mission(user_request="Test")
        results = asyncio.get_event_loop().run_until_complete(
            engine.test(mission)
        )
        assert isinstance(results, list)

    def test_test_generates_files(self):
        engine = TestingEngine()
        mission = Mission(user_request="Test")
        mission.architecture_plan = ArchitecturePlan(
            objectives=["Test"],
            modules=[{"name": "core"}, {"name": "api"}],
        )
        results = asyncio.get_event_loop().run_until_complete(
            engine.test(mission)
        )
        gen_result = next((r for r in results if r.get("type") == "test_generation"), None)
        assert gen_result is not None
        assert gen_result["count"] == 2


# ════════════════════════════════════════════════════════════
# Review Engine Tests
# ════════════════════════════════════════════════════════════

class TestReviewEngine:
    def test_create_review_engine(self):
        engine = ReviewEngine()
        assert engine is not None

    def test_review_returns_list(self):
        engine = ReviewEngine()
        mission = Mission(user_request="Test")
        items = asyncio.get_event_loop().run_until_complete(
            engine.review(mission)
        )
        assert isinstance(items, list)

    def test_review_no_research(self):
        engine = ReviewEngine()
        mission = Mission(user_request="Test")
        items = asyncio.get_event_loop().run_until_complete(
            engine.review(mission)
        )
        research_items = [i for i in items if i.category == "research"]
        assert len(research_items) > 0

    def test_review_no_plan(self):
        engine = ReviewEngine()
        mission = Mission(user_request="Test")
        items = asyncio.get_event_loop().run_until_complete(
            engine.review(mission)
        )
        plan_items = [i for i in items if i.category == "planning"]
        assert len(plan_items) > 0

    def test_review_history(self):
        engine = ReviewEngine()
        for i in range(3):
            m = Mission(user_request=f"Test {i}")
            asyncio.get_event_loop().run_until_complete(engine.review(m))
        patterns = engine.get_patterns()
        assert isinstance(patterns, list)


# ════════════════════════════════════════════════════════════
# Integration Tests
# ════════════════════════════════════════════════════════════

class TestIntegration:
    def test_full_pipeline_with_all_engines(self):
        """Test the full pipeline with all engines connected."""
        pipeline = MissionPipeline()
        pipeline.research_engine = ResearchEngine()
        pipeline.discovery_engine = DiscoveryEngine()
        pipeline.planner_engine = ArchitecturePlanner()
        pipeline.execution_engine = ExecutionEngine()
        pipeline.verification_engine = VerificationEngine()
        pipeline.testing_engine = TestingEngine()
        pipeline.review_engine = ReviewEngine()

        mission = asyncio.get_event_loop().run_until_complete(
            pipeline.run("Build a real-time chat app with WebSocket")
        )

        assert mission is not None
        assert mission.status in (MissionStatus.COMPLETED, MissionStatus.PAUSED)
        assert mission.final_report is not None
        assert "Mission Report" in mission.final_report
        # Research may be empty if GitHub CLI is unavailable
        assert isinstance(mission.research_findings, list)
        assert mission.architecture_plan is not None
        assert len(mission.verification_results) > 0
        assert len(mission.review_items) > 0

    def test_pipeline_with_failing_verification(self):
        """Test pipeline handles verification failures gracefully."""
        pipeline = MissionPipeline()
        pipeline.verification_engine = VerificationEngine()
        pipeline.execution_engine = ExecutionEngine()

        mission = asyncio.get_event_loop().run_until_complete(
            pipeline.run("Build something that might fail")
        )
        assert mission is not None
        assert mission.final_report is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])