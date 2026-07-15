import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import BASE_DIR, HOST, PORT, TTS_ENABLED
from database import init_db, close_db
from routers import chat, voice, memory, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if TTS_ENABLED:
        from services.tts import voice_engine
        voice_engine.load()
    yield
    await close_db()


app = FastAPI(title="JARVIS Web", version="1.0.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(memory.router)
app.include_router(pages.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
