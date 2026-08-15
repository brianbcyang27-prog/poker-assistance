"""Local notebook — import notes and answer questions over them (NotebookLM-style).

Notes and their chunks live in ~/.jarvis/notebook.json. Query scoring is a
lightweight token-overlap ranker (mirrors brain/rag._score); when the LLM is
reachable it synthesizes a final answer from the top chunks.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from uuid import uuid4

STATE_FILE = Path.home() / ".jarvis" / "notebook.json"

MAX_ENTRIES = 200
CHUNK_CHARS = 400
TOP_K = 5


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except (ValueError, OSError):
            state = {}
    else:
        state = {}
    state.setdefault("entries", {})
    return state


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\w{2,}", text.lower()))


def _chunks(body: str, size: int = CHUNK_CHARS) -> list[str]:
    words = re.findall(r"\S+", re.sub(r"\s+", " ", body).strip())
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        if current and length + len(word) + 1 > size:
            chunks.append(" ".join(current))
            current = []
            length = 0
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def add_entry(title: str, body: str, tags: list[str] | None = None) -> dict:
    state = _load_state()
    entry = {
        "id": uuid4().hex[:8],
        "title": (title or "").strip() or "Untitled",
        "body": body,
        "tags": list(tags or []),
        "created": time.time(),
    }
    state["entries"][entry["id"]] = entry
    if len(state["entries"]) > MAX_ENTRIES:
        for old in sorted(state["entries"].values(), key=lambda e: e["created"])[
            : len(state["entries"]) - MAX_ENTRIES
        ]:
            state["entries"].pop(old["id"], None)
    _save_state(state)
    return entry


def list_entries() -> list[dict]:
    state = _load_state()
    entries = []
    for entry in sorted(state["entries"].values(), key=lambda e: e["created"], reverse=True):
        entries.append({key: value for key, value in entry.items() if key != "body"})
    return entries


def delete_entry(entry_id: str) -> bool:
    state = _load_state()
    if entry_id not in state["entries"]:
        return False
    del state["entries"][entry_id]
    _save_state(state)
    return True


def _score(query_tokens: set[str], chunk_tokens: set[str]) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0
    return len(query_tokens & chunk_tokens) / len(query_tokens)


def _answer_with_llm(question: str, context: str) -> str | None:
    try:
        import jarvis.web.main as web_main

        llm = getattr(web_main.jarvis, "_llm", None)
        if llm is None or not llm.is_available():
            return None
        return llm.chat(
            "Answer the question using ONLY the notes below. "
            "If the notes do not contain the answer, say so plainly and briefly.\n\n"
            f"Notes:\n{context[:6000]}\n\nQuestion: {question}",
            system_prompt=(
                "You are JARVIS's local notebook assistant. Be concise and cite note titles."
            ),
            max_tokens=500,
        )
    except Exception:  # noqa: BLE001 — fall back to excerpt-based answers
        return None


def query(question: str, top_k: int = TOP_K) -> dict:
    state = _load_state()
    query_tokens = _tokenize(question)
    scored = []
    for entry in state["entries"].values():
        for chunk in _chunks(entry.get("body", "")):
            score = _score(query_tokens, _tokenize(chunk))
            if score > 0:
                scored.append(
                    {
                        "entry_id": entry["id"],
                        "title": entry["title"],
                        "chunk": chunk,
                        "score": score,
                    }
                )
    scored.sort(key=lambda s: s["score"], reverse=True)
    best = scored[:top_k]
    if not best:
        return {"answer": "No matching notes found — add some notes first.", "sources": []}

    context = "\n\n".join(f"[{s['title']}] {s['chunk']}" for s in best)
    answer = _answer_with_llm(question, context)
    if not answer:
        answer = "Based on your notes:\n" + "\n".join(
            f"• {s['title']}: {s['chunk'][:200]}" for s in best
        )
    return {
        "answer": answer,
        "sources": [{"title": s["title"], "excerpt": s["chunk"][:160]} for s in best],
    }
