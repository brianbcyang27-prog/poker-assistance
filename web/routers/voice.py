import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from services.tts import voice_engine
from database import get_db
from config import VOICES_DIR

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/sample")
async def upload_voice_sample(name: str = Form(...), audio: UploadFile = File(...)):
    ext = Path(audio.filename).suffix or ".wav"
    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    file_path = VOICES_DIR / filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO voice_samples (name, file_path) VALUES (?, ?)",
        (name, str(file_path)),
    )
    await db.commit()

    return {
        "id": cursor.lastrowid,
        "name": name,
        "file_path": str(file_path),
    }


@router.get("/samples")
async def list_voice_samples():
    db = await get_db()
    cursor = await db.execute("SELECT id, name, file_path, created_at FROM voice_samples ORDER BY id DESC")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.delete("/sample/{sample_id}")
async def delete_voice_sample(sample_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT file_path FROM voice_samples WHERE id = ?", (sample_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sample not found")

    file_path = Path(row["file_path"])
    if file_path.exists():
        file_path.unlink()

    await db.execute("DELETE FROM voice_samples WHERE id = ?", (sample_id,))
    await db.commit()
    return {"deleted": True}


@router.post("/tts")
async def text_to_speech(text: str = Form(...), voice_id: int = Form(...)):
    if not voice_engine.is_available():
        raise HTTPException(status_code=503, detail="TTS engine not available (KokoClone not installed)")

    db = await get_db()
    cursor = await db.execute("SELECT file_path FROM voice_samples WHERE id = ?", (voice_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Voice sample not found")

    audio_url = voice_engine.generate(text, row["file_path"])
    if not audio_url:
        raise HTTPException(status_code=500, detail="TTS generation failed")

    return {"audio_url": audio_url}
