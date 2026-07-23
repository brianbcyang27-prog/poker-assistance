"""Voice router - Voice samples, TTS, and voice cloning."""

import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import shutil
import uuid

from jarvis.core.config import get_config
from jarvis.core.database import get_db
from jarvis.web.services.tts import voice_engine

router = APIRouter(prefix="/api/voice", tags=["voice"])


class VoiceSampleResponse(BaseModel):
    id: int
    name: str
    file_path: str


@router.post("/sample")
async def upload_voice_sample(name: str = "", audio: UploadFile = File(...)):
    """Upload a voice sample."""
    config = get_config()
    
    # Save file
    sample_id = str(uuid.uuid4())[:8]
    ext = Path(audio.filename).suffix or ".wav"
    filename = f"{sample_id}{ext}"
    filepath = Path("voices") / filename
    filepath.parent.mkdir(exist_ok=True)
    
    with open(filepath, "wb") as f:
        shutil.copyfileobj(audio.file, f)
    
    # Save to database
    db = await get_db()
    cursor = await db._db.execute(
        "INSERT INTO voice_samples (name, file_path) VALUES (?, ?)",
        (name or filename, str(filepath)),
    )
    await db._db.commit()
    
    return {"id": cursor.lastrowid, "name": name or filename, "file_path": str(filepath)}


@router.get("/samples")
async def get_voice_samples():
    """Get all voice samples."""
    db = await get_db()
    cursor = await db._db.execute("SELECT * FROM voice_samples")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.delete("/sample/{sample_id}")
async def delete_voice_sample(sample_id: int):
    """Delete a voice sample."""
    db = await get_db()
    await db._db.execute("DELETE FROM voice_samples WHERE id = ?", (sample_id,))
    await db._db.commit()
    return {"status": "deleted"}


@router.get("/models")
async def get_voice_models():
    """Get available TTS providers and voices."""
    return {
        "providers": list(voice_engine.providers.keys()),
        "voices": voice_engine.get_all_voices(),
    }


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files."""
    audio_path = Path("audio_cache") / filename
    if audio_path.exists():
        # Determine media type based on extension
        ext = audio_path.suffix.lower()
        media_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".aiff": "audio/aiff",
            ".ogg": "audio/ogg",
        }
        media_type = media_types.get(ext, "application/octet-stream")
        return FileResponse(audio_path, media_type=media_type)
    return {"error": "Audio file not found"}


# === Voice Cloning Endpoints ===

@router.get("/clone/status")
async def clone_status():
    """Get voice cloning system status."""
    from jarvis.voice.voice_clone import voice_cloner
    return {
        "available": voice_cloner.is_available,
        "error": voice_cloner.error,
        "profiles_count": len(voice_cloner.list_profiles()),
        "profiles_dir": str(voice_cloner.profiles_dir)
    }


@router.get("/clone/profiles")
async def list_clone_profiles():
    """List all voice profiles for cloning."""
    from jarvis.voice.voice_clone import voice_cloner
    profiles = voice_cloner.list_profiles()
    return {
        "profiles": [p.to_dict() for p in profiles],
        "available": voice_cloner.is_available,
        "error": voice_cloner.error
    }


@router.post("/clone/profiles")
async def create_clone_profile(
    name: str = Form(...),
    audio: UploadFile = File(...)
):
    """Create a new voice profile from uploaded audio.
    
    Upload a 6-30 second audio sample of the voice to clone.
    """
    from jarvis.voice.voice_clone import voice_cloner
    
    if not voice_cloner.is_available:
        raise HTTPException(
            status_code=503,
            detail=f"Voice cloning not available: {voice_cloner.error}"
        )
    
    # Validate audio file
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Save uploaded audio
    try:
        suffix = Path(audio.filename).suffix if audio.filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Create profile
        profile = voice_cloner.create_profile(name, tmp_path)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if not profile:
            raise HTTPException(status_code=500, detail="Failed to create voice profile")
        
        return {
            "profile": profile.to_dict(),
            "message": f"Voice profile '{name}' created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clone/profiles/{profile_id}")
async def delete_clone_profile(profile_id: str):
    """Delete a voice profile."""
    from jarvis.voice.voice_clone import voice_cloner
    if not voice_cloner.delete_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": f"Profile {profile_id} deleted"}


@router.get("/clone/profiles/{profile_id}/audio")
async def get_clone_profile_audio(profile_id: str):
    """Get the reference audio for a voice profile."""
    from jarvis.voice.voice_clone import voice_cloner
    profile = voice_cloner.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if not os.path.exists(profile.audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        profile.audio_path,
        media_type="audio/wav",
        filename=f"{profile.name}.wav"
    )


@router.post("/clone/generate")
async def generate_cloned_voice(
    text: str = Form(...),
    profile_id: str = Form(...),
    language: str = Form(default="en")
):
    """Generate speech using a cloned voice."""
    from jarvis.voice.voice_clone import voice_cloner
    
    if not voice_cloner.is_available:
        raise HTTPException(
            status_code=503,
            detail=f"Voice cloning not available: {voice_cloner.error}"
        )
    
    profile = voice_cloner.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    
    # Generate audio
    output_dir = Path("~/.jarvis/voice_output").expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = str(output_dir / f"clone_{uuid.uuid4().hex[:8]}.wav")
    
    result = voice_cloner.clone_voice(
        text=text,
        profile_id=profile_id,
        output_path=output_path,
        language=language
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Voice generation failed")
    
    return FileResponse(
        result,
        media_type="audio/wav",
        filename="cloned_voice.wav"
    )


@router.get("/clone/languages")
async def get_clone_languages():
    """Get supported languages for voice cloning."""
    from jarvis.voice.voice_clone import voice_cloner
    return {"languages": voice_cloner.get_supported_languages()}
