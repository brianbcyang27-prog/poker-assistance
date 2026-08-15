"""Notebook router — import notes and query them."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.web.services import notebook as notebook_service

router = APIRouter(prefix="/api/notebook", tags=["notebook"])


class NoteCreate(BaseModel):
    title: str = Field(default="", max_length=200)
    body: str = Field(min_length=1)
    tags: list[str] = []


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@router.get("")
async def get_notes():
    return {"entries": notebook_service.list_entries()}


@router.post("")
async def create_note(payload: NoteCreate):
    entry = notebook_service.add_entry(payload.title, payload.body, payload.tags)
    return {"entry": entry}


@router.delete("/{entry_id}")
async def delete_note(entry_id: str):
    if not notebook_service.delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Unknown entry")
    return {"ok": True}


@router.post("/query")
async def query_notes(payload: QueryRequest):
    return notebook_service.query(payload.question)
