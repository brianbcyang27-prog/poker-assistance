"""Memory extractor for automatic knowledge extraction from conversations."""
import asyncio
import json
import re
import time
from typing import List, Optional, Dict, Any

from jarvis.extraction.models import (
    ExtractedType,
    ImportanceLevel,
    ExtractionResult,
    ExtractedMemory,
)


class MemoryExtractor:
    """Extract structured memories from text and conversations."""

    def __init__(self, knowledge_graph=None):
        self.knowledge_graph = knowledge_graph

    async def extract_from_text(self, text: str, source: str = "conversation") -> ExtractionResult:
        result = ExtractionResult(source_text=text)

        entities = await self.extract_entities(text)
        relationships = await self.extract_relationships(text)
        decisions = await self.extract_decisions(text)
        preferences = await self.extract_preferences(text)
        projects = await self.extract_projects(text)
        technologies = await self.extract_technologies(text)
        people = await self.extract_people(text)
        lessons = await self.extract_lessons(text)
        importance = await self.classify_importance(text)

        for item in entities:
            memory = ExtractedMemory(
                content=item.get("content", ""),
                extracted_type=ExtractedType.FACT.value,
                importance=importance.value,
                confidence=item.get("confidence", 0.7),
                source=source,
                related_entities=[item.get("name", "")] if item.get("name") else [],
                metadata={"entity_type": item.get("entity_type", "")},
            )
            result.extracted_items.append(memory.to_dict())

        for item in decisions:
            memory = ExtractedMemory(
                content=item.get("content", ""),
                extracted_type=ExtractedType.DECISION.value,
                importance=ImportanceLevel.IMPORTANT.value,
                confidence=item.get("confidence", 0.7),
                source=source,
                metadata={"decision": item},
            )
            result.extracted_items.append(memory.to_dict())

        for item in preferences:
            memory = ExtractedMemory(
                content=item.get("content", ""),
                extracted_type=ExtractedType.PREFERENCE.value,
                importance=ImportanceLevel.USEFUL.value,
                confidence=item.get("confidence", 0.6),
                source=source,
                metadata={"preference": item},
            )
            result.extracted_items.append(memory.to_dict())

        for item in projects:
            memory = ExtractedMemory(
                content=item.get("content", ""),
                extracted_type=ExtractedType.PROJECT.value,
                importance=ImportanceLevel.IMPORTANT.value,
                confidence=item.get("confidence", 0.7),
                source=source,
                related_entities=item.get("name", "").split() if isinstance(item.get("name"), str) else [],
                metadata={"project": item},
            )
            result.extracted_items.append(memory.to_dict())

        for item in technologies:
            memory = ExtractedMemory(
                content=item.get("content", ""),
                extracted_type=ExtractedType.TECHNOLOGY.value,
                importance=ImportanceLevel.USEFUL.value,
                confidence=item.get("confidence", 0.7),
                source=source,
                related_entities=[item.get("name", "")] if item.get("name") else [],
                metadata={"technology": item},
            )
            result.extracted_items.append(memory.to_dict())

        for item in people:
            memory = ExtractedMemory(
                content=item.get("content", ""),
                extracted_type=ExtractedType.PERSON.value,
                importance=ImportanceLevel.IMPORTANT.value,
                confidence=item.get("confidence", 0.6),
                source=source,
                related_entities=[item.get("name", "")] if item.get("name") else [],
                metadata={"person": item},
            )
            result.extracted_items.append(memory.to_dict())

        for item in lessons:
            memory = ExtractedMemory(
                content=item.get("content", ""),
                extracted_type=ExtractedType.LESSON.value,
                importance=ImportanceLevel.PERMANENT.value,
                confidence=item.get("confidence", 0.8),
                source=source,
                metadata={"lesson": item},
            )
            result.extracted_items.append(memory.to_dict())

        if self.knowledge_graph and entities:
            for entity in entities:
                try:
                    from jarvis.brain.memory.graph import Node, Edge

                    entity_id = entity.get("id") or entity.get("name", "").lower().replace(" ", "_")
                    node = Node(
                        id=entity_id,
                        label=entity.get("name", entity_id),
                        type=entity.get("entity_type", "concept"),
                        content=entity.get("content", ""),
                        metadata=json.dumps({"extracted_at": time.time(), "source": source}),
                    )
                    kg_result = await self.knowledge_graph.add_node(node)
                    if kg_result.get("ok"):
                        result.entities_created.append(entity_id)
                except Exception:
                    pass

            for rel in relationships:
                try:
                    from jarvis.brain.memory.graph import Edge

                    edge = Edge(
                        source=rel.get("source", ""),
                        target=rel.get("target", ""),
                        relation=rel.get("relation", "related_to"),
                        weight=rel.get("weight", 1.0),
                        metadata=json.dumps({"extracted_at": time.time()}),
                    )
                    kg_result = await self.knowledge_graph.add_edge(edge)
                    if kg_result.get("ok"):
                        result.relationships_created.append(f"{rel.get('source', '')}->{rel.get('target', '')}")
                except Exception:
                    pass

        return result

    async def extract_from_conversation(self, messages: List[dict]) -> ExtractionResult:
        combined_result = ExtractionResult()

        for i, msg in enumerate(messages):
            content = ""
            if isinstance(msg, dict):
                content = msg.get("content", msg.get("text", str(msg)))
            elif isinstance(msg, str):
                content = msg

            if not content.strip():
                continue

            result = await self.extract_from_text(content, source=f"conversation")
            combined_result.extracted_items.extend(result.extracted_items)
            combined_result.entities_created.extend(result.entities_created)
            combined_result.relationships_created.extend(result.relationships_created)

        combined_result.source_text = f"extracted from {len(messages)} messages"
        return combined_result

    async def classify_importance(self, text: str) -> ImportanceLevel:
        decision_keywords = ["decided", "decision", "chose", "selected", "agreed", "approved", "rejected"]
        permanent_keywords = ["always", "never", "must", "critical", "essential", "requirement"]
        important_keywords = ["important", "significant", "major", "key", "priority", "remember"]
        project_keywords = ["project", "developing", "building", "working on", "create", "implement"]

        lower = text.lower()

        for kw in permanent_keywords:
            if kw in lower:
                return ImportanceLevel.PERMANENT

        for kw in decision_keywords:
            if kw in lower:
                return ImportanceLevel.IMPORTANT

        for kw in project_keywords:
            if kw in lower:
                return ImportanceLevel.IMPORTANT

        for kw in important_keywords:
            if kw in lower:
                return ImportanceLevel.IMPORTANT

        if len(text.split()) < 5:
            return ImportanceLevel.TEMPORARY

        return ImportanceLevel.USEFUL

    async def extract_entities(self, text: str) -> List[dict]:
        entities = []
        lower = text.lower()

        project_pattern = re.compile(r'(?:project|repo|repository)\s+["\']?([A-Za-z0-9_/-]+)["\']?', re.IGNORECASE)
        for match in project_pattern.finditer(text):
            entities.append({
                "name": match.group(1),
                "entity_type": "project",
                "content": match.group(0),
                "confidence": 0.8,
            })

        tech_pattern = re.compile(r'(?:using|written in|built with|technology|framework|library|language)\s+["\']?([A-Za-z0-9_.+#]+)["\']?', re.IGNORECASE)
        for match in tech_pattern.finditer(text):
            entities.append({
                "name": match.group(1),
                "entity_type": "technology",
                "content": match.group(0),
                "confidence": 0.7,
            })

        person_pattern = re.compile(r'@(\w+)|(?:user|developer|person|teammate)\s+["\']?([A-Za-z]+(?:\s+[A-Za-z]+)?)["\']?', re.IGNORECASE)
        for match in person_pattern.finditer(text):
            name = match.group(1) or match.group(2)
            entities.append({
                "name": name,
                "entity_type": "person",
                "content": match.group(0),
                "confidence": 0.6,
            })

        concept_pattern = re.compile(r'\[\[([^\]]+)\]\]')
        for match in concept_pattern.finditer(text):
            entities.append({
                "name": match.group(1),
                "entity_type": "concept",
                "content": match.group(0),
                "confidence": 0.9,
            })

        return entities

    async def extract_relationships(self, text: str) -> List[dict]:
        relationships = []

        patterns = [
            (r'(\w+(?:\s+\w+)?)\s+(?:is\s+a|belongs\s+to|part\s+of|depends\s+on)\s+(\w+(?:\s+\w+)?)', "depends_on"),
            (r'(\w+(?:\s+\w+)?)\s+(?:related\s+to|connected\s+to|associated\s+with)\s+(\w+(?:\s+\w+)?)', "related_to"),
            (r'(\w+(?:\s+\w+)?)\s+(?:contains|includes|has)\s+(\w+(?:\s+\w+)?)', "contains"),
        ]

        for pattern, rel_type in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                relationships.append({
                    "source": match.group(1).lower().replace(" ", "_"),
                    "target": match.group(2).lower().replace(" ", "_"),
                    "relation": rel_type,
                    "weight": 1.0,
                })

        return relationships

    async def extract_decisions(self, text: str) -> List[dict]:
        decisions = []
        lower = text.lower()

        if any(kw in lower for kw in ["decided", "decision", "chose", "selected", "agreed"]):
            decisions.append({
                "content": text.strip(),
                "confidence": 0.7,
            })

        return decisions

    async def extract_preferences(self, text: str) -> List[dict]:
        preferences = []
        lower = text.lower()

        pref_patterns = [
            (r"(?:prefer|like|love|enjoy|favor).+?(?:over|than|more)", 0.7),
            (r"(?:don't like|dislike|hate|avoid).+", 0.8),
            (r"(?:better to|best way|preferred).+", 0.6),
        ]

        for pattern, confidence in pref_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                preferences.append({
                    "content": match.group(0).strip(),
                    "confidence": confidence,
                })

        return preferences

    async def extract_projects(self, text: str) -> List[dict]:
        projects = []
        lower = text.lower()

        project_pattern = re.compile(
            r"(?:project|working on|developing|building|creating|implementing)\s+"
            r'["\']?([A-Za-z0-9_/\- ]+)["\']?',
            re.IGNORECASE
        )
        for match in project_pattern.finditer(text):
            projects.append({
                "name": match.group(1).strip(),
                "content": match.group(0).strip(),
                "confidence": 0.8,
            })

        return projects

    async def extract_technologies(self, text: str) -> List[dict]:
        technologies = []
        tech_patterns = [
            r'\b(Python|JavaScript|TypeScript|Rust|Go|Java|C\+\+|Ruby|PHP|Swift|Kotlin)\b',
            r'\b(React|Vue|Angular|Svelte|Next\.js|Nuxt|Express|Flask|Django|FastAPI)\b',
            r'\b(PostgreSQL|MySQL|SQLite|MongoDB|Redis|Elasticsearch)\b',
            r'\b(Docker|Kubernetes|AWS|GCP|Azure|Terraform|Ansible)\b',
            r'\b(Git|Linux|Node\.?js|npm|yarn|pip|conda)\b',
        ]

        for pattern in tech_patterns:
            for match in re.finditer(pattern, text):
                technologies.append({
                    "name": match.group(1),
                    "content": match.group(0),
                    "confidence": 0.9,
                })

        return technologies

    async def extract_people(self, text: str) -> List[dict]:
        people = []

        mention_pattern = re.compile(r'@(\w+)')
        for match in mention_pattern.finditer(text):
            people.append({
                "name": match.group(1),
                "content": match.group(0),
                "confidence": 0.9,
            })

        name_pattern = re.compile(
            r'(?:user|developer|engineer|teammate|colleague)\s+is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            re.IGNORECASE
        )
        for match in name_pattern.finditer(text):
            people.append({
                "name": match.group(1),
                "content": match.group(0),
                "confidence": 0.7,
            })

        return people

    async def extract_lessons(self, text: str) -> List[dict]:
        lessons = []
        lower = text.lower()

        lesson_patterns = [
            r"(?:learned|lesson|realized|discovered).+",
            r"(?:next time|in the future|going forward).+(?:should|will|must|need to)",
            r"(?:turned out|turns out|as it turns out).+",
        ]

        for pattern in lesson_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lessons.append({
                    "content": match.group(0).strip(),
                    "confidence": 0.8,
                })

        return lessons
