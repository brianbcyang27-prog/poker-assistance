"""Tests for the local notebook service and its API router."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jarvis.web.routers.notebook import router as notebook_router
from jarvis.web.services import notebook


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(notebook, "STATE_FILE", tmp_path / "notebook.json")
    return tmp_path


def test_add_list_delete(tmp_state):
    entry = notebook.add_entry("Coffee Notes", "Use 18 grams of beans per cup.", ["coffee"])
    entries = notebook.list_entries()
    assert len(entries) == 1
    assert entries[0]["title"] == "Coffee Notes"
    assert entries[0]["tags"] == ["coffee"]
    assert "body" not in entries[0]
    assert notebook.delete_entry(entry["id"]) is True
    assert notebook.list_entries() == []


def test_delete_unknown_returns_false(tmp_state):
    assert notebook.delete_entry("missing") is False


def test_query_finds_matching_notes(tmp_state):
    notebook.add_entry("Server Setup", "JARVIS binds to 127.0.0.1 port 8000 by default.")
    notebook.add_entry("Poker", "Texas holdem uses two hole cards and five community cards.")
    result = notebook.query("what port does the server bind to?")
    assert result["sources"]
    assert any("Server Setup" in s["title"] for s in result["sources"])
    assert "port 8000" in result["answer"]
    assert any(s["title"] == "Poker" for s in result["sources"]) is False


def test_query_no_match(tmp_state):
    notebook.add_entry("Poker", "Texas holdem rules.")
    result = notebook.query("quantum physics")
    assert result["sources"] == []
    assert "No matching notes" in result["answer"]


def test_chunks_split_long_text(tmp_state):
    body = " ".join(f"word{index}" for index in range(300))
    chunks = notebook._chunks(body)
    assert len(chunks) > 1
    assert all(len(chunk) <= notebook.CHUNK_CHARS + 8 for chunk in chunks)


def test_entry_cap(tmp_state, monkeypatch):
    monkeypatch.setattr(notebook, "MAX_ENTRIES", 3)
    for index in range(5):
        notebook.add_entry(f"Note {index}", f"body {index}")
    assert len(notebook.list_entries()) == 3


def test_router_delete_unknown_404(tmp_state):
    app = FastAPI()
    app.include_router(notebook_router)
    client = TestClient(app)
    assert client.delete("/api/notebook/missing").status_code == 404


def test_router_create_and_query(tmp_state):
    app = FastAPI()
    app.include_router(notebook_router)
    client = TestClient(app)
    created = client.post("/api/notebook", json={"title": "T", "body": "hello world notes"})
    assert created.status_code == 200
    entry_id = created.json()["entry"]["id"]
    assert client.get("/api/notebook").json()["entries"][0]["id"] == entry_id
    assert client.delete(f"/api/notebook/{entry_id}").json() == {"ok": True}


def test_router_rejects_empty_body(tmp_state):
    app = FastAPI()
    app.include_router(notebook_router)
    client = TestClient(app)
    assert client.post("/api/notebook", json={"title": "T", "body": ""}).status_code == 422
