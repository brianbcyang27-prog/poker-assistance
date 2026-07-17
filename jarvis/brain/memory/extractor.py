"""Auto-extract knowledge from conversations."""
import json
import re
import time
import uuid
from typing import List, Optional

from .graph import graph, Node, Edge


class KnowledgeExtractor:
    """Extracts knowledge from conversation messages and creates graph nodes."""

    def __init__(self):
        self._message_buffer: List[dict] = []
        self._flush_threshold = 5

    async def process_message(self, role: str, content: str, agent_id: str = "jarvis") -> dict:
        """Process a single message and extract knowledge."""
        if not content or len(content.strip()) < 10:
            return {"ok": True, "extracted": 0}

        self._message_buffer.append({
            "role": role,
            "content": content,
            "agent_id": agent_id,
            "timestamp": time.time()
        })

        created = []

        # Extract concepts (capitalized phrases, technical terms)
        concepts = self._extract_concepts(content)
        for concept in concepts:
            node_id = f"concept_{concept.lower().replace(' ', '_').replace('/', '_')}"
            node = Node(
                id=node_id, label=concept, type="concept",
                content=f"Mentioned in conversation with {agent_id}",
                updated_at=time.time()
            )
            await graph.add_node(node)
            created.append(("concept", concept))

        # Extract [[links]]
        links = re.findall(r'\[\[(.+?)\]\]', content)
        for link in links:
            node_id = f"concept_{link.lower().replace(' ', '_')}"
            await graph.add_node(Node(id=node_id, label=link, type="concept"))
            created.append(("link", link))

        # Extract decisions ("I'll", "we should", "decided to", etc.)
        decisions = self._extract_decisions(content)
        for decision in decisions:
            node_id = f"decision_{uuid.uuid4().hex[:8]}"
            await graph.add_node(Node(
                id=node_id, label=decision, type="decision",
                content=content[:500], updated_at=time.time()
            ))
            created.append(("decision", decision))

        # Extract code references
        code_refs = re.findall(r'`([^`]+)`', content)
        for ref in code_refs[:3]:
            if len(ref) > 3 and len(ref) < 100:
                node_id = f"code_{ref.lower().replace(' ', '_').replace('/', '_')[:50]}"
                await graph.add_node(Node(
                    id=node_id, label=ref, type="code",
                    updated_at=time.time()
                ))
                created.append(("code", ref))

        # Extract entity mentions (file paths, URLs, etc.)
        file_paths = re.findall(r'(/[\w./_-]+(?:\.\w+)?)', content)
        for fp in file_paths[:3]:
            node_id = f"path_{fp.replace('/', '_').strip('_')}"
            await graph.add_node(Node(
                id=node_id, label=fp, type="entity",
                updated_at=time.time()
            ))
            created.append(("path", fp))

        # Auto-link related concepts
        if len(created) > 1:
            types_created = [c[0] for c in created]
            for i, (t1, v1) in enumerate(created):
                for t2, v2 in created[i+1:]:
                    if t1 != t2:
                        id1 = f"{t1}_{v1.lower().replace(' ', '_')[:50]}"
                        id2 = f"{t2}_{v2.lower().replace(' ', '_')[:50]}"
                        await graph.add_edge(Edge(source=id1, target=id2, relation="co_occurs"))

        # Create conversation node
        conv_id = f"conv_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        await graph.add_node(Node(
            id=conv_id,
            label=f"{role} message ({len(content)} chars)",
            type="conversation",
            content=content[:2000],
            metadata=json.dumps({"agent": agent_id, "role": role}),
            updated_at=time.time()
        ))

        return {
            "ok": True,
            "extracted": len(created),
            "concepts": [c[1] for c in created if c[0] == "concept"],
            "decisions": [c[1] for c in created if c[0] == "decision"],
            "links": [c[1] for c in created if c[0] == "link"],
            "conversation_id": conv_id
        }

    def _extract_concepts(self, text: str) -> List[str]:
        """Extract meaningful concepts from text."""
        concepts = set()

        # Technical terms (CamelCase, snake_case)
        tech_terms = re.findall(r'\b([A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]+)+)\b', text)
        for t in tech_terms:
            if len(t) > 4 and t.lower() not in ('the', 'this', 'that', 'with', 'from'):
                concepts.add(t)

        # Specific domain terms
        domain_patterns = [
            r'\b(python|javascript|typescript|react|nextjs|fastapi|docker|kubernetes|git)\b',
            r'\b(API|SDK|HTTP|JSON|REST|GraphQL|WebSocket|OAuth)\b',
            r'\b(learning|training|model|neural|network|algorithm)\b',
        ]
        for pattern in domain_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                concepts.add(m.lower() if m.isupper() else m)

        return list(concepts)[:10]

    def _extract_decisions(self, text: str) -> List[str]:
        """Extract decisions and action items."""
        decisions = []
        patterns = [
            r'(?:I\'ll|we\'ll|let\'s|we should|decided to|going to|plan to)\s+([^.\n]+)',
            r'(?:decision|choice|selected|chosen):\s*([^.\n]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if len(m.strip()) > 5:
                    decisions.append(m.strip())
        return decisions[:5]

    async def flush_buffer(self) -> dict:
        """Process all buffered messages."""
        if not self._message_buffer:
            return {"ok": True, "processed": 0}

        count = len(self._message_buffer)
        self._message_buffer.clear()
        return {"ok": True, "processed": count}


knowledge_extractor = KnowledgeExtractor()
