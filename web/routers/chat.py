from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from services.opencode import brain
from services.tts import voice_engine
from database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    voice_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    audio_url: Optional[str] = None


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = await brain.chat(req.message, req.session_id)

    db = await get_db()
    await db.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (result["session_id"], "user", req.message),
    )
    await db.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (result["session_id"], "assistant", result["response"]),
    )
    await db.commit()

    audio_url = None
    if req.voice_id and voice_engine.is_available():
        sample = await db.execute(
            "SELECT file_path FROM voice_samples WHERE id = ?", (req.voice_id,)
        )
        row = await sample.fetchone()
        if row:
            audio_url = voice_engine.generate(result["response"], row["file_path"])

    return ChatResponse(
        response=result["response"],
        session_id=result["session_id"],
        audio_url=audio_url,
    )


@router.get("/stream")
async def chat_stream(message: str, session_id: Optional[str] = None):
    async def event_generator():
        async for event in brain.chat_stream(message, session_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history/{session_id}")
async def chat_history(session_id: str):
    db = await get_db()
    cursor = await db.execute(
        "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    rows = await cursor.fetchall()
    return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in rows]
