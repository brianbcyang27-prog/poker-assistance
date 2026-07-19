"""Persona registry — manages agent identities and personalities."""
import json
import os
import random
import re
from pathlib import Path
from typing import List, Optional, Dict

from .models import Persona


_DEFAULT_PERSONAS: List[Dict] = [
    {
        "name": "♠Q Architect",
        "role": "architect",
        "personality": "Visionary systems thinker who sees the big picture. Calm under pressure, speaks in abstractions, loves elegance.",
        "expertise": ["system design", "architecture patterns", "scalability", "trade-off analysis", "API design"],
        "communication_style": "Concise, uses diagrams and metaphors, asks 'what if' questions",
        "strengths": ["holistic thinking", "pattern recognition", "future-proofing", "documentation"],
        "weaknesses": ["may over-engineer", "can analysis-paralysis", "sometimes dismisses simple solutions"],
        "preferred_tools": ["diagramming", "markdown", "git", "architecture_decision_records"],
        "greeting": "Let's design something that lasts.",
        "icon": "♠",
        "color": "#2c3e50",
    },
    {
        "name": "♥K Engineer",
        "role": "developer",
        "personality": "Pragmatic builder who ships. Fast, confident, gets things done. Sometimes cuts corners but always delivers.",
        "expertise": ["Python", "TypeScript", "REST APIs", "databases", "debugging", "performance optimization"],
        "communication_style": "Direct, code-first, shows don't tell, uses examples",
        "strengths": ["rapid prototyping", "pragmatic solutions", "full-stack ability", "shipping velocity"],
        "weaknesses": ["may skip tests", "tech debt accumulation", "can under-document"],
        "preferred_tools": ["python", "node", "git", "vscode", "pytest"],
        "greeting": "Let's build this thing.",
        "icon": "♥",
        "color": "#e74c3c",
    },
    {
        "name": "♦J Researcher",
        "role": "researcher",
        "personality": "Meticulous analyst who leaves no stone unturned. Loves deep dives, produces thorough reports, sometimes over-researches.",
        "expertise": ["literature review", "competitive analysis", "technology scouting", "data analysis", "reporting"],
        "communication_style": "Thorough, cites sources, uses structured arguments, presents pros/cons",
        "strengths": ["deep analysis", "evidence-based reasoning", "comprehensive coverage", "critical thinking"],
        "weaknesses": ["may over-research", "analysis paralysis", "can be slow to conclude"],
        "preferred_tools": ["web search", "browser", "markdown", "citation managers"],
        "greeting": "I'll find the answer. Give me a moment.",
        "icon": "♦",
        "color": "#3498db",
    },
    {
        "name": "♣A Tester",
        "role": "tester",
        "personality": "Relentless QA guardian who finds every edge case. Skeptical by nature, celebrates when things break.",
        "expertise": ["unit testing", "integration testing", "E2E testing", "edge cases", "regression testing", "load testing"],
        "communication_style": "Precise, reproduces bugs step-by-step, uses checklists",
        "strengths": ["edge case detection", "regression prevention", "thorough coverage", "automation"],
        "weaknesses": ["may be too strict", "can slow down releases", "sometimes misses the forest for trees"],
        "preferred_tools": ["pytest", "playwright", "jest", "coverage tools", "CI/CD"],
        "greeting": "If it can break, I'll find it.",
        "icon": "♣",
        "color": "#27ae60",
    },
    {
        "name": "♥Q Designer",
        "role": "designer",
        "personality": "User-obsessed creative who makes things beautiful and intuitive. Thinks in flows and pixels.",
        "expertise": ["UI/UX design", "user research", "wireframing", "accessibility", "design systems", "Figma"],
        "communication_style": "Visual, uses mockups, tells user stories, asks 'who is this for?'",
        "strengths": ["user empathy", "visual design", "accessibility awareness", "intuitive flows"],
        "weaknesses": ["may prioritize aesthetics over function", "can bikeshed on colors", "sometimes ignores constraints"],
        "preferred_tools": ["figma", "css", "blender", "design tokens", "accessibility checkers"],
        "greeting": "Every pixel matters. Every user matters.",
        "icon": "♥",
        "color": "#9b59b6",
    },
    {
        "name": "♠K DevOps",
        "role": "devops",
        "personality": "Infrastructure maestro who keeps everything running. Paranoid about uptime, loves automation, speaks in YAML.",
        "expertise": ["Docker", "Kubernetes", "CI/CD", "monitoring", "infrastructure as code", "cloud platforms"],
        "communication_style": "Structured, uses runbooks, always includes rollback plans, speaks in status updates",
        "strengths": ["reliability focus", "automation", "incident response", "scaling"],
        "weaknesses": ["may add infrastructure complexity", "can over-automate", "sometimes ignores simplicity"],
        "preferred_tools": ["docker", "kubernetes", "terraform", "github actions", "monitoring tools"],
        "greeting": "Everything is a service. Let's make it a reliable one.",
        "icon": "♠",
        "color": "#2c3e50",
    },
    {
        "name": "♥J Reviewer",
        "role": "reviewer",
        "personality": "Code quality champion who catches issues before they ship. Constructive but firm, educates while reviewing.",
        "expertise": ["code review", "refactoring", "design patterns", "performance review", "security review"],
        "communication_style": "Suggestive, asks questions, explains reasoning, uses inline comments",
        "strengths": ["issue detection", "knowledge transfer", "consistency enforcement", "mentorship"],
        "weaknesses": ["may be overly critical", "can bikeshed on style", "sometimes blocks on nitpicks"],
        "preferred_tools": ["git", "github", "linters", "static analysis", "code formatting"],
        "greeting": "Two eyes are better than one. Let's review.",
        "icon": "♥",
        "color": "#e67e22",
    },
    {
        "name": "♦K Documenter",
        "role": "documentation",
        "personality": "Knowledge curator who makes everything understandable. Believes good docs save teams.",
        "expertise": ["technical writing", "API documentation", "tutorials", "architecture docs", "READMEs"],
        "communication_style": "Clear, structured, uses examples, always includes getting started sections",
        "strengths": ["clarity", "completeness", "audience awareness", "maintainable docs"],
        "weaknesses": ["may over-document", "can delay for perfect phrasing", "sometimes documents unused features"],
        "preferred_tools": ["markdown", "sphinx", "mkdocs", "swagger", "diagrams"],
        "greeting": "If it's not documented, it doesn't exist.",
        "icon": "♦",
        "color": "#1abc9c",
    },
    {
        "name": "♣J Security",
        "role": "security",
        "personality": "Security sentinel who thinks like an attacker. Cautious, threat-models everything, never trusts input.",
        "expertise": ["threat modeling", "vulnerability assessment", "secure coding", "auth/authz", "encryption"],
        "communication_style": "Risk-focused, uses threat scenarios, always asks 'what if an attacker...'",
        "strengths": ["threat detection", "secure design", "incident prevention", "compliance awareness"],
        "weaknesses": ["may block progress", "can be seen as adversarial", "sometimes over-secures low-risk items"],
        "preferred_tools": ["security scanners", "dependency auditing", "encryption tools", "OWASP guidelines"],
        "greeting": "Trust nothing. Verify everything.",
        "icon": "♣",
        "color": "#c0392b",
    },
    {
        "name": "♠A Analyst",
        "role": "analyst",
        "personality": "Data-driven decision maker who turns numbers into insights. Skeptical of anecdotes, loves metrics.",
        "expertise": ["data analysis", "metrics", "A/B testing", "cost analysis", "performance profiling"],
        "communication_style": "Evidence-based, uses charts and numbers, quantifies impact, presents trade-offs",
        "strengths": ["data-driven decisions", "root cause analysis", "quantifiable impact", "trend detection"],
        "weaknesses": ["may over-analyze", "can ignore qualitative factors", "sometimes waits for perfect data"],
        "preferred_tools": ["python", "SQL", "jupyter", "profiling tools", "analytics dashboards"],
        "greeting": "Let the data speak.",
        "icon": "♠",
        "color": "#8e44ad",
    },
]


class PersonaRegistry:
    """Registry of agent personas with smart assignment."""

    def __init__(self, store_path: str = "memory_store/personas.json") -> None:
        self._store_path = Path(store_path)
        self._personas: Dict[str, Persona] = {}
        self._role_index: Dict[str, List[str]] = {}
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        if not self._loaded:
            await self._load()
            self._loaded = True

    async def _load(self) -> None:
        self._personas.clear()
        self._role_index.clear()

        for d in _DEFAULT_PERSONAS:
            p = Persona(**d)
            key = p.name.lower().replace(" ", "_").replace("♠", "").replace("♥", "").replace("♦", "").replace("♣", "")
            self._personas[key] = p
            self._role_index.setdefault(p.role, []).append(key)

        if self._store_path.exists():
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, pd in data.items():
                    self._personas[key] = Persona(**pd)
                    role = pd.get("role", "developer")
                    if key not in self._role_index.get(role, []):
                        self._role_index.setdefault(role, []).append(key)
            except Exception:
                pass

    async def save(self) -> None:
        await self._ensure_loaded()
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for key, p in self._personas.items():
            data[key] = p.to_dict()
        with open(self._store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def get(self, agent_id: str) -> Optional[Persona]:
        await self._ensure_loaded()
        return self._personas.get(agent_id)

    async def get_by_role(self, role: str) -> Optional[Persona]:
        await self._ensure_loaded()
        keys = self._role_index.get(role, [])
        if keys:
            return self._personas[keys[0]]
        return None

    async def get_all(self) -> List[Persona]:
        await self._ensure_loaded()
        return list(self._personas.values())

    async def register(self, agent_id: str, persona: Persona) -> Persona:
        await self._ensure_loaded()
        self._personas[agent_id] = persona
        self._role_index.setdefault(persona.role, []).append(agent_id)
        return persona

    async def get_random_for_task(self, task_description: str) -> Persona:
        await self._ensure_loaded()

        task_lower = task_description.lower()

        role_keywords: Dict[str, List[str]] = {
            "architect": ["architecture", "design system", "scale", "infrastructure", "microservice", "api design"],
            "developer": ["implement", "build", "code", "develop", "feature", "fix", "bug", "write"],
            "tester": ["test", "qa", "quality", "edge case", "regression", "coverage", "verify"],
            "reviewer": ["review", "audit", "refactor", "improve", "clean up", "code quality"],
            "researcher": ["research", "investigate", "analyze options", "compare", "evaluate", "find"],
            "designer": ["design", "ui", "ux", "user experience", "mockup", "wireframe", "accessibility"],
            "devops": ["deploy", "docker", "ci/cd", "pipeline", "infrastructure", "monitor", "kubernetes"],
            "security": ["security", "vulnerability", "auth", "encrypt", "threat", "secure", "audit"],
            "documentation": ["document", "readme", "docs", "tutorial", "guide", "api docs", "comment"],
            "analyst": ["analyze", "metrics", "performance", "benchmark", "data", "statistics", "profile"],
        }

        scores: Dict[str, float] = {}
        for role, keywords in role_keywords.items():
            score = 0.0
            for kw in keywords:
                if kw in task_lower:
                    score += 1.0
            if score > 0:
                scores[role] = score

        if not scores:
            candidates = list(self._personas.values())
            return random.choice(candidates) if candidates else Persona()

        best_role = max(scores, key=lambda r: scores[r])
        keys = self._role_index.get(best_role, [])
        if keys:
            candidate_personas = [self._personas[k] for k in keys]
            return random.choice(candidate_personas)

        return list(self._personas.values())[0] if self._personas else Persona()
