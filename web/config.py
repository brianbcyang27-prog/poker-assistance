import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "opencode/big-pickle")
OPENCODE_BINARY = os.getenv("OPENCODE_BINARY", "/Users/brianyang/.opencode/bin/opencode")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
STT_ENABLED = os.getenv("STT_ENABLED", "true").lower() == "true"
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "jarvis.db"
VOICES_DIR = BASE_DIR / "voices"
VOICES_DIR.mkdir(exist_ok=True)
AUDIO_DIR = BASE_DIR / "static" / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
