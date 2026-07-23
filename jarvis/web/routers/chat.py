"""Chat router - User communication with JARVIS."""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json
import uuid

import jarvis.web.main as web_main
from jarvis.core.database import get_db
from jarvis.core.config import get_config
from jarvis.web.rate_limit import rate_limit

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    voice_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    workspace_id: Optional[str] = None
    agents_active: list[dict] = []
    audio_url: Optional[str] = None


@router.post("", response_model=ChatResponse)
@rate_limit(max_requests=15, window_seconds=60)
async def chat(request: Request, req: ChatRequest):
    """Send a message to JARVIS and get a response."""
    session_id = req.session_id or str(uuid.uuid4())[:8]
    
    # Auto-create workspace for every user request (v6.3.0)
    workspace_id = None
    try:
        from jarvis.brain.mission_executor import mission_executor
        ws = await web_main.workspace_manager.create_workspace(
            goal=req.message[:200],
            owner="user",
            user_request=req.message,
        )
        workspace_id = ws.id if hasattr(ws, "id") else ws.get("id")
    except Exception:
        pass
    
    # Save user message
    db = await get_db()
    await db.index_conversation(session_id, "user", req.message)
    
    # Load LLM conversation context for multi-turn
    if hasattr(web_main.jarvis, '_llm') and web_main.jarvis._llm:
        await web_main.jarvis._llm.load_session_context(session_id)
    
    # Process through JARVIS agent hierarchy
    response = await web_main.jarvis.process_user_request(req.message)
    
    # Save assistant response
    await db.index_conversation(session_id, "assistant", response)
    
    # Record as a learned skill if task was delegated (from Hermes pattern)
    try:
        from jarvis.brain.skills import skill_manager
        intent = getattr(web_main.jarvis, '_last_intent', None)
        if intent and intent.get('tasks'):
            task = intent['tasks'][0]
            await skill_manager.record_skill(
                name=task.get('name', req.message[:30]),
                description=task.get('description', req.message),
                steps=[{"action": task.get('king', '?'), "input": req.message, "output": response[:200]}],
            )
            await skill_manager.update_outcome(task.get('name', req.message[:30]), success=True)
    except Exception:
        pass
    
    # Save LLM conversation context for next turn
    if hasattr(web_main.jarvis, '_llm') and web_main.jarvis._llm:
        await web_main.jarvis._llm.save_session_context(session_id)
    
    # Get active agents for UI
    active_agents = []
    for king in web_main.jarvis.get_all_kings():
        king_dict = king.to_dict()
        if king_dict.get("state") != "idle":
            active_agents.append(king_dict)
    
    # Generate TTS audio if enabled
    audio_url = None
    config = get_config()
    if config.tts_enabled:
        try:
            from jarvis.web.services.tts import voice_engine
            import hashlib
            import os
            
            # Generate audio filename
            audio_hash = hashlib.md5(f"{session_id}:{response[:50]}".encode()).hexdigest()[:12]
            audio_filename = f"chat_{audio_hash}"
            audio_path = Path("audio_cache") / audio_filename
            audio_path.parent.mkdir(exist_ok=True)
            
            # Generate audio (provider will add extension)
            result = voice_engine.generate(response, str(audio_path))
            if result:
                # Get the actual filename with extension
                actual_filename = Path(result).name
                audio_url = f"/api/voice/audio/{actual_filename}"
        except Exception as e:
            print(f"TTS error: {e}")
            pass  # TTS is optional
    
    return ChatResponse(
        response=response,
        session_id=session_id,
        workspace_id=workspace_id,
        agents_active=active_agents,
        audio_url=audio_url,
    )


@router.get("/stream")
async def chat_stream(message: str, session_id: Optional[str] = None):
    """Stream a chat response via SSE — true token-by-token streaming."""
    sid = session_id or str(uuid.uuid4())[:8]

    async def event_generator():
        yield f"data: {json.dumps({'type': 'state', 'state': 'thinking'})}\n\n"

        # Save user message to DB
        db = await get_db()
        await db.index_conversation(sid, "user", message)

        llm = getattr(web_main.jarvis, '_llm', None)
        if llm:
            await llm.load_session_context(sid)

        # Generate capability-aware system prompt
        from jarvis.core.capabilities import registry
        capability_prompt = await registry.generate_capability_prompt()
        
        # Build system prompt with capabilities
        system_prompt = capability_prompt if capability_prompt else None

        # Use the async streaming LLM if available
        if llm and hasattr(llm, 'achat_stream'):
            full_response: list[str] = []
            try:
                async for token in llm.achat_stream(message, system_prompt=system_prompt):
                    full_response.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            except Exception as e:
                error_msg = f"LLM error: {str(e)[:100]}"
                yield f"data: {json.dumps({'type': 'token', 'content': error_msg})}\n\n"
                full_response = [error_msg]

            response = "".join(full_response)

            await db.index_conversation(sid, "assistant", response)
            await llm.save_session_context(sid)
        else:
            # Fallback: non-streaming path
            response = await web_main.jarvis.process_user_request(message)
            await db.index_conversation(sid, "assistant", response)
            yield f"data: {json.dumps({'type': 'token', 'content': response})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'session_id': sid})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history/{session_id}")
async def chat_history(session_id: str):
    """Get chat history for a session."""
    db = await get_db()
    messages = await db.get_conversation(session_id)
    return messages


@router.get("/sessions")
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
):
    """List all conversation sessions."""
    db = await get_db()
    sessions = await db.get_all_sessions(limit=limit, offset=offset)
    total = await db.get_session_count()
    return {"sessions": sessions, "total": total}
