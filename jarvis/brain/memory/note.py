"""Markdown notes with Obsidian-style [[bidirectional links]]."""
import asyncio
import json
import re
import time
import uuid
from pathlib import Path
from typing import Optional, List

from .graph import graph, Node, Edge

NOTES_DIR = Path("memory_store/notes")
NOTES_DIR.mkdir(parents=True, exist_ok=True)


class NoteManager:
    """Manages markdown notes with bidirectional linking."""

    def __init__(self):
        self.notes_dir = NOTES_DIR

    def _note_path(self, note_id: str) -> Path:
        return self.notes_dir / f"{note_id}.md"

    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML-like frontmatter from markdown."""
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                fm = content[3:end].strip()
                body = content[end+3:].strip()
                meta = {}
                for line in fm.split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"').strip("'")
                return {"meta": meta, "body": body}
        return {"meta": {}, "body": content}

    def _extract_links(self, content: str) -> List[str]:
        """Extract [[bidirectional links]] from content."""
        return re.findall(r'\[\[(.+?)\]\]', content)

    async def create_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> dict:
        note_id = re.sub(r'[^a-z0-9_-]', '_', title.lower().replace(' ', '_'))
        now = time.time()

        # Add frontmatter
        fm_tags = json.dumps(tags or [])
        full_content = f"---\ntitle: {title}\ntags: {fm_tags}\ncreated: {now}\n---\n\n{content}"

        # Write file
        path = self._note_path(note_id)
        path.write_text(full_content)

        # Register in graph
        node = Node(
            id=f"note_{note_id}",
            label=title,
            type="note",
            content=content,
            metadata=json.dumps({"tags": tags or [], "path": str(path)}),
            created_at=now,
            updated_at=now
        )
        await graph.add_node(node)

        # Extract and create bidirectional links
        links = self._extract_links(content)
        for link in links:
            target_id = f"concept_{link.lower().replace(' ', '_')}"
            target_node = Node(id=target_id, label=link, type="concept", created_at=now, updated_at=now)
            await graph.add_node(target_node)
            await graph.add_edge(Edge(source=node.id, target=target_id, relation="references", created_at=now))
            await graph.add_edge(Edge(source=target_id, target=node.id, relation="referenced_by", created_at=now))

        # Also create edges for tags
        for tag in (tags or []):
            tag_id = f"tag_{tag.lower()}"
            tag_node = Node(id=tag_id, label=f"#{tag}", type="tag", created_at=now, updated_at=now)
            await graph.add_node(tag_node)
            await graph.add_edge(Edge(source=node.id, target=tag_id, relation="tagged_with", created_at=now))

        return {"ok": True, "id": note_id, "title": title, "links": links, "path": str(path)}

    async def get_note(self, note_id: str) -> dict:
        path = self._note_path(note_id)
        if not path.exists():
            return {"ok": False, "error": "Note not found"}
        content = path.read_text()
        parsed = self._parse_frontmatter(content)
        links = self._extract_links(content)
        backlinks = await self._get_backlinks(note_id)
        return {
            "ok": True,
            "id": note_id,
            "meta": parsed["meta"],
            "content": parsed["body"],
            "links": links,
            "backlinks": backlinks
        }

    async def _get_backlinks(self, note_id: str) -> List[dict]:
        """Find notes that link to this note."""
        node_id = f"note_{note_id}"
        result = await graph.get_neighbors(node_id, direction="incoming")
        backlinks = []
        for edge in result.get("neighbors", {}).get("incoming", []):
            if edge.get("relation") == "references":
                backlinks.append({"id": edge["source"], "label": edge.get("label", "")})
        return backlinks

    async def update_note(self, note_id: str, content: str) -> dict:
        path = self._note_path(note_id)
        if not path.exists():
            return {"ok": False, "error": "Note not found"}

        existing = await self.get_note(note_id)
        title = existing.get("meta", {}).get("title", note_id)
        tags = existing.get("meta", {}).get("tags", "[]")
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except:
                tags = []

        fm_tags = json.dumps(tags)
        full_content = f"---\ntitle: {title}\ntags: {fm_tags}\n---\n\n{content}"
        path.write_text(full_content)

        # Update graph node
        node_id = f"note_{note_id}"
        node = Node(
            id=node_id, label=title, type="note",
            content=content, updated_at=time.time()
        )
        await graph.add_node(node)

        # Re-extract links
        links = self._extract_links(content)
        for link in links:
            target_id = f"concept_{link.lower().replace(' ', '_')}"
            await graph.add_node(Node(id=target_id, label=link, type="concept"))
            await graph.add_edge(Edge(source=node_id, target=target_id, relation="references"))
            await graph.add_edge(Edge(source=target_id, target=node_id, relation="referenced_by"))

        return {"ok": True, "links": links}

    async def delete_note(self, note_id: str) -> dict:
        path = self._note_path(note_id)
        if path.exists():
            path.unlink()
        node_id = f"note_{note_id}"
        conn = graph._get_conn()
        conn.execute("DELETE FROM edges WHERE source = ? OR target = ?", (node_id, node_id))
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        conn.commit()
        return {"ok": True}

    async def list_notes(self, limit: int = 50) -> dict:
        conn = graph._get_conn()
        rows = conn.execute(
            "SELECT * FROM nodes WHERE type = 'note' ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        notes = []
        for r in rows:
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
            notes.append({
                "id": r["id"].replace("note_", ""),
                "title": r["label"],
                "tags": meta.get("tags", []),
                "updated_at": r["updated_at"]
            })
        return {"ok": True, "notes": notes}

    async def search_notes(self, query: str, limit: int = 20) -> dict:
        conn = graph._get_conn()
        rows = conn.execute(
            "SELECT * FROM nodes WHERE type = 'note' AND (label LIKE ? OR content LIKE ?) LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        results = []
        for r in rows:
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
            results.append({
                "id": r["id"].replace("note_", ""),
                "title": r["label"],
                "content_preview": r["content"][:200] if r["content"] else "",
                "tags": meta.get("tags", [])
            })
        return {"ok": True, "results": results}


notes = NoteManager()
