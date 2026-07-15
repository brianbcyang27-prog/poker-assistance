"""Voice router - Voice samples and TTS."""

from fastapi import APIRouter, UploadFile, File
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
