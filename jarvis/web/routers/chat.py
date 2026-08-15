"""Chat router - User communication with JARVIS."""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import jarvis.web.main as web_main
from jarvis.architectures import get_architecture, get_settings_manager
from jarvis.architectures.base import MissionContext
from jarvis.brain.interaction import ConversationTracker, InteractionLayer
from jarvis.core.config import get_config
from jarvis.core.database import get_db
from jarvis.web.rate_limit import rate_limit

router = APIRouter(prefix="/api/chat", tags=["chat"])

# v9.0.0: Human Interaction Layer — classifies intent, tracks conversation mode
_interaction = InteractionLayer()
_session_trackers: dict[str, "ConversationTracker"] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    voice_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    workspace_id: str | None = None
    agents_active: list[dict] = []
    audio_url: str | None = None


class SessionRenameRequest(BaseModel):
    title: str


@router.post("", response_model=ChatResponse)
@rate_limit(max_requests=15, window_seconds=60)
async def chat(request: Request, req: ChatRequest):
    """Send a message to JARVIS and get a response."""
    session_id = req.session_id or str(uuid.uuid4())[:8]

    # Auto-create workspace for every user request (v6.3.0)
    workspace_id = None
    try:
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

    # Ensure session row exists
    await db.set_session_title(session_id, req.message[:80] if not req.session_id else "")

    # Load LLM conversation context for multi-turn
    if hasattr(web_main.jarvis, "_llm") and web_main.jarvis._llm:
        await web_main.jarvis._llm.load_session_context(session_id)

    # v9.0.0: Classify intent through the Human Interaction Layer
    intent = _interaction.classify(req.message)
    tracker = _session_trackers.setdefault(session_id, type(_interaction.tracker)())
    tracker.record(req.message, intent)
    web_main.jarvis._last_intent = web_main.jarvis._last_intent or {}
    web_main.jarvis._last_intent["interaction_mode"] = tracker.current_mode.value
    web_main.jarvis._last_intent["interaction_intent"] = intent.value

    # v9.0.0 M2: Project Intelligence task flow (task/project intents only)
    task_flow_result = None
    if intent.value in ("task", "project"):
        from jarvis.projects.task_flow import route_task

        task_flow_result = await route_task(
            req.message,
            domain_registry=web_main.domain_registry,
            session_id=session_id,
        )
        if not task_flow_result.get("skipped"):
            task_flow_result["workspace_id"] = workspace_id
            web_main.jarvis._last_intent["project_id"] = task_flow_result.get("project_id")

    # Process through active architecture (with timeout)
    import asyncio

    try:
        if task_flow_result is not None and not task_flow_result.get("skipped"):
            if task_flow_result.get("result") and task_flow_result["result"].get("status") in (
                "completed",
                "needs_revision",
            ):
                response = task_flow_result["result"].get("content", "Task completed.")
            else:
                response = (
                    f"Task flow failed: domain '{task_flow_result.get('domain')}' "
                    "could not execute the mission."
                )
        else:
            # Get active architecture
            arch = get_architecture()
            get_settings_manager().get()

        if arch and arch.name == "Hermes":
            # Use Hermes architecture for planning and execution
            mission_ctx = MissionContext(
                mission_id=session_id,
                user_request=req.message,
            )

            # Plan
            plan = await arch.plan(mission_ctx)

            # Execute
            results = await arch.execute(mission_ctx, plan)

            # Build response from execution results
            response_parts = []
            for result in results:
                if result.success and result.output:
                    output = result.output
                    if isinstance(output, dict):
                        if output.get("type") == "research":
                            response_parts.append(
                                f"📚 **Research: {output.get('query', '')}**\n"
                                f"{output.get('synthesis', '')}"
                            )
                        elif output.get("type") == "code":
                            response_parts.append(
                                f"💻 **Code ({output.get('language', 'python')})**\n```"
                                f"{output.get('language', 'python')}\n{output.get('code', '')}\n```"
                            )
                        elif output.get("type") == "review":
                            response_parts.append(f"✅ **Review**\n{output.get('review', '')}")
                        else:
                            response_parts.append(str(output))
                    else:
                        response_parts.append(str(output))

            response = "\n\n".join(response_parts) if response_parts else "Task completed."
        else:
            # Use native JARVIS agent hierarchy
            response = await asyncio.wait_for(
                web_main.jarvis.process_user_request(req.message),
                timeout=120,
            )
    except TimeoutError:
        response = "Request timed out. Please try a simpler request or try again later."

    # Save assistant response
    await db.index_conversation(session_id, "assistant", response)

    # Record as a learned skill if task was delegated (from Hermes pattern)
    try:
        from jarvis.brain.skills import skill_manager

        intent = getattr(web_main.jarvis, "_last_intent", None)
        if intent and intent.get("tasks"):
            task = intent["tasks"][0]
            await skill_manager.record_skill(
                name=task.get("name", req.message[:30]),
                description=task.get("description", req.message),
                steps=[
                    {
                        "action": task.get("king", "?"),
                        "input": req.message,
                        "output": response[:200],
                    }
                ],
            )
            await skill_manager.update_outcome(task.get("name", req.message[:30]), success=True)
    except Exception:
        pass

    # Save LLM conversation context for next turn
    if hasattr(web_main.jarvis, "_llm") and web_main.jarvis._llm:
        await web_main.jarvis._llm.save_session_context(session_id)

    # Get active agents for UI
    active_agents = []
    for king in web_main.jarvis.get_all_kings():
        king_dict = king.to_dict()
        if king_dict.get("state") != "idle":
            active_agents.append(king_dict)

    # Generate TTS audio if enabled (async, non-blocking)
    audio_url = None
    config = get_config()
    if config.tts_enabled:
        try:
            import hashlib

            from jarvis.web.services.tts import voice_engine

            # Generate audio filename
            audio_hash = hashlib.md5(f"{session_id}:{response[:50]}".encode()).hexdigest()[:12]
            audio_filename = f"chat_{audio_hash}"
            audio_path = Path("audio_cache") / audio_filename
            audio_path.parent.mkdir(exist_ok=True)

            # Generate audio async (non-blocking)
            result = await voice_engine.agenerate(response, str(audio_path))
            if result:
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
async def chat_stream(message: str, session_id: str | None = None):
    """Stream a chat response via SSE — true token-by-token streaming."""
    sid = session_id or str(uuid.uuid4())[:8]
    tool_calls = []
    mission_data = None

    async def event_generator():
        nonlocal mission_data, tool_calls
        try:
            yield f"data: {json.dumps({'type': 'state', 'state': 'thinking'})}\n\n"

            # Save user message to DB
            db = await get_db()
            await db.index_conversation(sid, "user", message)

            # Ensure session row exists in conversation_sessions
            await db.set_session_title(sid, message[:80] if not session_id else "")

            llm = getattr(web_main.jarvis, "_llm", None)
            if llm:
                await llm.load_session_context(sid)

            # v9.0.0: Classify intent — only inject capabilities for non-casual modes
            intent = _interaction.classify(message)
            tracker = _session_trackers.setdefault(sid, type(_interaction.tracker)())
            tracker.record(message, intent)
            web_main.jarvis._last_intent = web_main.jarvis._last_intent or {}
            web_main.jarvis._last_intent["interaction_mode"] = tracker.current_mode.value
            web_main.jarvis._last_intent["interaction_intent"] = intent.value

            include_caps = _interaction.should_expose_capabilities(message)
            system_prompt = None
            if include_caps:
                from jarvis.core.capabilities import registry

                capability_prompt = await registry.generate_capability_prompt()
                system_prompt = capability_prompt if capability_prompt else None

            # v9.0.0 M2: Project Intelligence task flow (task/project intents only)
            task_flow_result = None
            if intent.value in ("task", "project"):
                import asyncio as _asyncio

                from jarvis.agents.workers.research import FactCheckWorker
                from jarvis.projects.task_flow import route_task

                event_queue: _asyncio.Queue = _asyncio.Queue()

                async def _emit(event: dict):
                    await event_queue.put(event)

                flow_task = _asyncio.create_task(
                    route_task(
                        message,
                        domain_registry=web_main.domain_registry,
                        emit=_emit,
                        session_id=sid,
                        fact_checker=FactCheckWorker().verify,
                    )
                )
                while not flow_task.done() or not event_queue.empty():
                    try:
                        event = await _asyncio.wait_for(event_queue.get(), timeout=0.5)
                        yield (
                            f"data: {json.dumps({'type': event['type'], **event['payload']})}"
                            "\n\n"
                        )
                    except TimeoutError:
                        pass
                task_flow_result = flow_task.result()
                if not task_flow_result.get("skipped"):
                    web_main.jarvis._last_intent["project_id"] = task_flow_result.get("project_id")

            # Get active architecture
            arch = get_architecture()

            if task_flow_result is not None and not task_flow_result.get("skipped"):
                if task_flow_result.get("result") and task_flow_result["result"].get(
                    "status"
                ) in ("completed", "needs_revision"):
                    response = task_flow_result["result"].get("content", "Task completed.")
                else:
                    response = (
                        f"Task flow failed: domain '{task_flow_result.get('domain')}' "
                        "could not execute the mission."
                    )
                for token in response:
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # If Hermes architecture, use plan/execute flow and emit mission events
            elif arch and arch.name == "Hermes":
                mission_ctx = MissionContext(
                    mission_id=sid,
                    user_request=message,
                )

                # Emit mission start
                mission_data = {"goal": message, "plan": None, "steps": []}
                yield f"data: {json.dumps({'type': 'mission_start', 'mission': mission_data})}\n\n"

                # Plan
                plan = await arch.plan(mission_ctx)

                mission_data["plan"] = {
                    "id": plan.id,
                    "goal": plan.goal,
                    "steps": [s.to_dict() for s in plan.steps],
                }
                yield (
                    f"data: {json.dumps({'type': 'mission_plan', 'plan': mission_data['plan']})}"
                    "\n\n"
                )

                # Execute
                results = await arch.execute(mission_ctx, plan)

                # Build response from execution results
                response_parts = []
                for i, result in enumerate(results):
                    step = plan.steps[i] if i < len(plan.steps) else None

                    # Emit step execution event
                    step_payload = {
                        "type": "mission_step",
                        "step": step.to_dict() if step else {},
                        "result": (
                            result.to_dict()
                            if hasattr(result, "to_dict")
                            else {
                                "success": result.success,
                                "output": str(result.output)[:500],
                                "duration_ms": result.duration_ms,
                            }
                        ),
                    }
                    yield f"data: {json.dumps(step_payload)}\n\n"

                    if result.success and result.output:
                        output = result.output
                        if isinstance(output, dict):
                            if output.get("type") == "research":
                                response_parts.append(
                                    f"📚 **Research: {output.get('query', '')}**\n"
                                    f"{output.get('synthesis', '')}"
                                )
                            elif output.get("type") == "code":
                                response_parts.append(
                                    f"💻 **Code ({output.get('language', 'python')})**\n```"
                                    f"{output.get('language', 'python')}\n"
                                    f"{output.get('code', '')}\n```"
                                )
                            elif output.get("type") == "review":
                                response_parts.append(f"✅ **Review**\n{output.get('review', '')}")
                            else:
                                response_parts.append(str(output))
                        else:
                            response_parts.append(str(output))

                response = "\n\n".join(response_parts) if response_parts else "Task completed."

                # Emit verification results
                for i, result in enumerate(results):
                    verification = await arch.verify(
                        plan.steps[i] if i < len(plan.steps) else None, result
                    )
                    verify_payload = {
                        "type": "mission_verify",
                        "step_id": (plan.steps[i].id if i < len(plan.steps) else f"step_{i}"),
                        "verification": verification,
                    }
                    yield f"data: {json.dumps(verify_payload)}\n\n"

                # Emit reflection
                reflection = await arch.reflect(mission_ctx)
                yield (
                    f"data: {json.dumps({'type': 'mission_reflect', 'reflection': reflection})}\n\n"
                )
            else:
                # Native JARVIS flow
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

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)[:200]})}\n\n"
        finally:
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


@router.post("/sessions")
async def create_session():
    """Create a new empty conversation session."""
    session_id = str(uuid.uuid4())[:8]
    db = await get_db()
    await db.set_session_title(session_id, "New conversation")
    return {"ok": True, "session_id": session_id, "title": "New conversation"}


@router.post("/sessions/{session_id}/rename")
async def rename_session(session_id: str, req: SessionRenameRequest):
    """Rename a conversation session."""
    db = await get_db()
    title = req.title.strip()
    if not title:
        return {"detail": "Title cannot be empty"}
    await db.set_session_title(session_id, title)
    return {"ok": True, "session_id": session_id, "title": title}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    db = await get_db()
    await db.delete_session(session_id)
    return {"ok": True, "session_id": session_id}
