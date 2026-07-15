"""Chat router - User communication with JARVIS."""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import uuid

from jarvis.web.main import jarvis
from jarvis.core.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agents_active: list[dict] = []


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to JARVIS and get a response."""
    session_id = req.session_id or str(uuid.uuid4())[:8]
    
    # Save user message
    db = await get_db()
    await db.save_conversation(session_id, "user", req.message)
    
    # Process through JARVIS agent hierarchy
    response = await jarvis.process_user_request(req.message)
    
    # Save assistant response
    await db.save_conversation(session_id, "assistant", response)
    
    # Get active agents for UI
    active_agents = []
    for king in jarvis.get_all_kings():
        king_dict = king.to_dict()
        if king_dict.get("state") != "idle":
            active_agents.append(king_dict)
    
    return ChatResponse(
        response=response,
        session_id=session_id,
        agents_active=active_agents,
    )


@router.get("/stream")
async def chat_stream(message: str, session_id: Optional[str] = None):
    """Stream a chat response via SSE."""
    sid = session_id or str(uuid.uuid4())[:8]
    
    async def event_generator():
        # Send thinking state
        yield f"data: {json.dumps({'type': 'state', 'state': 'thinking'})}\n\n"
        
        # Process message
        response = await jarvis.process_user_request(message)
        
        # Send response
        yield f"data: {json.dumps({'type': 'response', 'content': response, 'session_id': sid})}\n\n"
        
        # Send idle state
        yield f"data: {json.dumps({'type': 'state', 'state': 'idle'})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history/{session_id}")
async def chat_history(session_id: str):
    """Get chat history for a session."""
    db = await get_db()
    messages = await db.get_conversation(session_id)
    return messages
