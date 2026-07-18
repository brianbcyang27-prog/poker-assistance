"""Architecture Planner — Creates implementation plans for missions.

Takes research findings and tool candidates, produces a structured
ArchitecturePlan with modules, files, dependencies, and estimates.
"""

import logging
from typing import List, Dict, Any, Optional
from ..mission.mission import (
    ArchitecturePlan, ResearchFinding, ToolCandidate,
)

log = logging.getLogger("jarvis.planner")


class ArchitecturePlanner:
    """Creates implementation plans for JARVIS missions.

    Follows the principle: plan in 30 minutes, code in 10.
    """

    def __init__(self):
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._register_templates()

    def _register_templates(self):
        """Register common project templates."""
        self._templates["web_app"] = {
            "modules": ["routing", "models", "services", "templates", "static"],
            "files": [
                "web/main.py", "web/routes.py", "web/models.py",
                "web/templates/*.html", "web/static/js/*.js",
            ],
            "dependencies": ["fastapi", "jinja2", "uvicorn"],
            "estimated_hours": 8,
        }
        self._templates["api"] = {
            "modules": ["endpoints", "models", "services", "auth"],
            "files": ["api/main.py", "api/routes.py", "api/models.py"],
            "dependencies": ["fastapi", "pydantic", "sqlalchemy"],
            "estimated_hours": 6,
        }
        self._templates["cli_tool"] = {
            "modules": ["cli", "commands", "utils"],
            "files": ["cli.py", "commands/*.py"],
            "dependencies": ["click", "rich"],
            "estimated_hours": 4,
        }
        self._templates["data_pipeline"] = {
            "modules": ["ingestion", "processing", "storage", "output"],
            "files": ["pipeline/ingest.py", "pipeline/process.py", "pipeline/store.py"],
            "dependencies": ["pandas", "sqlalchemy"],
            "estimated_hours": 10,
        }
        self._templates["ml_model"] = {
            "modules": ["data", "training", "evaluation", "inference"],
            "files": ["ml/data.py", "ml/train.py", "ml/evaluate.py", "ml/predict.py"],
            "dependencies": ["torch", "transformers", "datasets"],
            "estimated_hours": 16,
        }
        self._templates["browser_automation"] = {
            "modules": ["browser", "actions", "strategies"],
            "files": ["automation/browser.py", "automation/actions.py"],
            "dependencies": ["playwright", "beautifulsoup4"],
            "estimated_hours": 6,
        }
        self._templates["iot_project"] = {
            "modules": ["sensors", "actuators", "control", "networking"],
            "files": ["iot/sensors.py", "iot/control.py", "iot/main.py"],
            "dependencies": ["asyncio", "aiohttp"],
            "estimated_hours": 12,
        }

    async def create_plan(
        self,
        goal: str,
        research: Optional[List[ResearchFinding]] = None,
        tools: Optional[List[ToolCandidate]] = None,
    ) -> ArchitecturePlan:
        """Create an architecture plan for the mission.

        Args:
            goal: Mission goal description
            research: Research findings
            tools: Tool candidates

        Returns:
            ArchitecturePlan with full breakdown
        """
        research = research or []
        tools = tools or []

        # Select best matching template
        template = self._select_template(goal, tools)

        # Build module plan
        modules = template.get("modules", [])
        new_files = template.get("files", [])
        deps = template.get("dependencies", [])

        # Add tools from candidates
        for tool in tools[:5]:
            if tool.name not in deps:
                deps.append(tool.name)

        # Generate risks
        risks = self._assess_risks(goal, research, tools)

        # Generate interfaces
        interfaces = self._design_interfaces(modules)

        plan = ArchitecturePlan(
            objectives=[goal],
            modules=[{"name": m, "description": f"{m} module"} for m in modules],
            new_files=new_files,
            files_to_modify=[],
            dependencies=deps,
            risks=[r.get("description", "") for r in risks],
            estimated_hours=template.get("estimated_hours", 8),
        )

        log.info(f"Plan created: {len(modules)} modules, {len(new_files)} files, {len(risks)} risks")
        return plan

    def _select_template(
        self,
        goal: str,
        tools: List[ToolCandidate],
    ) -> Dict[str, Any]:
        """Select the best template for the goal."""
        goal_lower = goal.lower()

        # Match by keywords
        if any(w in goal_lower for w in ["web", "frontend", "ui", "html", "css"]):
            return self._templates["web_app"]
        if any(w in goal_lower for w in ["api", "rest", "graphql", "endpoint"]):
            return self._templates["api"]
        if any(w in goal_lower for w in ["cli", "command line", "terminal"]):
            return self._templates["cli_tool"]
        if any(w in goal_lower for w in ["pipeline", "etl", "data", "scrape"]):
            return self._templates["data_pipeline"]
        if any(w in goal_lower for w in ["ml", "model", "train", "neural", "ai"]):
            return self._templates["ml_model"]
        if any(w in goal_lower for w in ["browser", "automate", "scrape", "playwright"]):
            return self._templates["browser_automation"]
        if any(w in goal_lower for w in ["iot", "sensor", "arduino", "raspberry", "smart home"]):
            return self._templates["iot_project"]

        # Fallback — generic
        return {
            "modules": ["core", "utils", "tests"],
            "files": ["core/__init__.py", "core/main.py"],
            "dependencies": [],
            "estimated_hours": 8,
        }

    def _assess_risks(
        self,
        goal: str,
        research: List[ResearchFinding],
        tools: List[ToolCandidate],
    ) -> List[Dict[str, Any]]:
        """Assess implementation risks."""
        risks = []

        # No tools found
        if not tools:
            risks.append({
                "type": "no_tools",
                "severity": "high",
                "description": "No suitable tools found — may need custom implementation",
            })

        # External API dependencies
        if any(f.source == "external_api" for f in research):
            risks.append({
                "type": "external_dependency",
                "severity": "medium",
                "description": "External API dependency — may break without notice",
            })

        # Immature tools
        immature = [t for t in tools if t.maturity in ("experimental", "alpha", "unknown")]
        if immature:
            risks.append({
                "type": "immature_tools",
                "severity": "medium",
                "description": f"Using immature tools: {', '.join(t.name for t in immature[:3])}",
            })

        # Scope risks
        if len(tools) > 5:
            risks.append({
                "type": "scope_creep",
                "severity": "medium",
                "description": "Many dependencies — scope may be too large",
            })

        return risks

    def _design_interfaces(self, modules: List[str]) -> List[Dict[str, Any]]:
        """Design interfaces between modules."""
        interfaces = []

        for i, mod in enumerate(modules):
            if i < len(modules) - 1:
                interfaces.append({
                    "from": mod,
                    "to": modules[i + 1],
                    "type": "function_call",
                    "description": f"{mod} provides data to {modules[i + 1]}",
                })

        return interfaces

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by name."""
        return self._templates.get(name)

    def list_templates(self) -> List[str]:
        """List all available templates."""
        return list(self._templates.keys())
