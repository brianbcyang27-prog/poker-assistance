"""Auth API endpoints for JARVIS v8.0.0."""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from jarvis.web.auth import auth_manager

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    api_key: str | None = None


@router.post("/login")
async def login(request: Request, response: Response, req: LoginRequest):
    """Login with API key to get a session cookie."""
    if req.api_key:
        if auth_manager.verify_api_key(req.api_key):
            session_id = auth_manager.create_session(
                ip=request.client.host if request.client else ""
            )
            response.set_cookie(
                "jarvis_session",
                session_id,
                httponly=True,
                samesite="lax",
                max_age=86400,  # 24 hours
            )
            return {"ok": True, "session_id": session_id}
        raise HTTPException(status_code=401, detail="Invalid API key")

    # No API key provided — check if we're on localhost
    host = request.client.host if request.client else ""
    if host in ("127.0.0.1", "::1", "localhost"):
        session_id = auth_manager.create_session(ip=host)
        response.set_cookie(
            "jarvis_session",
            session_id,
            httponly=True,
            samesite="lax",
            max_age=86400,
        )
        return {"ok": True, "session_id": session_id}

    raise HTTPException(status_code=401, detail="API key required")


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session."""
    session_id = request.cookies.get("jarvis_session")
    if session_id:
        auth_manager._sessions.pop(session_id, None)
        auth_manager._save()
    response.delete_cookie("jarvis_session")
    return {"ok": True}


@router.get("/status")
async def auth_status(request: Request):
    """Check authentication status."""
    host = request.client.host if request.client else ""
    is_local = host in ("127.0.0.1", "::1", "localhost")

    session_id = request.cookies.get("jarvis_session")
    has_session = session_id and auth_manager.verify_session(session_id)

    api_key = request.headers.get("X-API-Key")
    has_api_key = api_key and auth_manager.verify_api_key(api_key)

    return {
        "authenticated": is_local or has_session or has_api_key,
        "method": "local"
        if is_local
        else "session"
        if has_session
        else "api_key"
        if has_api_key
        else "none",
        "is_local": is_local,
        "has_api_key_configured": auth_manager.get_api_key() is not None,
    }


@router.get("/api-key")
async def get_api_key():
    """Get the current API key (only if no key exists yet)."""
    key = auth_manager.get_api_key()
    if key:
        return {"api_key": key, "message": "Store this key securely. It won't be shown again."}
    return {
        "api_key": None,
        "message": "No API key configured. Call POST /api/auth/api-key to generate.",
    }


class GenerateKeyRequest(BaseModel):
    confirm: bool = False


@router.post("/api-key")
async def generate_api_key(req: GenerateKeyRequest):
    """Generate a new API key (only if none exists)."""
    if auth_manager.get_api_key() and not req.confirm:
        raise HTTPException(
            status_code=400, detail="API key already exists. Set confirm=true to regenerate."
        )
    key = auth_manager.setup()
    return {"api_key": key, "message": "Store this key securely. It won't be shown again."}
