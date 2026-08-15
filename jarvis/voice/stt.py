"""Speech-to-Text module."""

import threading
import time

from Foundation import NSURL, NSDate, NSRunLoop

_RUN_LOOP_MODE = "kCFRunLoopDefaultMode"


class SpeechToText:
    """Speech-to-text interface."""

    def __init__(self, model: str = "base"):
        self.model_name = model
        self._model = None

    def load(self):
        """Load the whisper model."""
        try:
            import whisper

            self._model = whisper.load_model(self.model_name)
        except ImportError:
            print("Whisper not installed. Install with: pip install openai-whisper")
        except Exception as e:
            print(f"Failed to load whisper model: {e}")

    @property
    def is_available(self) -> bool:
        """Check if STT is available."""
        return self._model is not None

    def transcribe_file(self, file_path: str) -> str | None:
        """Transcribe an audio file."""
        if not self._model:
            return None

        try:
            result = self._model.transcribe(file_path)
            return result.get("text", "")
        except Exception as e:
            print(f"Transcription failed: {e}")
            return None

    def transcribe_audio(self, audio_data: bytes) -> str | None:
        """Transcribe raw audio data."""
        if not self._model:
            return None

        try:
            import numpy as np

            # Convert to numpy array (assuming WAV format)
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            result = self._model.transcribe(audio_array)
            return result.get("text", "")
        except Exception as e:
            print(f"Transcription failed: {e}")
            return None


# === macOS-native transcription (SFSpeechRecognizer via pyobjc-framework-Speech) ===

_STATUS_NAMES = {0: "notDetermined", 1: "denied", 2: "restricted", 3: "authorized"}


def _speech_module():
    try:
        import Speech

        return Speech
    except ImportError:
        return None


def sfspeech_available() -> bool:
    """Check whether SFSpeechRecognizer can be imported."""
    return _speech_module() is not None and hasattr(_speech_module(), "SFSpeechRecognizer")


def sfspeech_authorization_status() -> str:
    """Return the current macOS speech-recognition authorization state."""
    mod = _speech_module()
    if mod is None:
        return "unavailable"
    return _STATUS_NAMES.get(int(mod.SFSpeechRecognizer.authorizationStatus()), "unknown")


def _pump_run_loop(event, timeout):
    deadline = time.time() + timeout
    while not event.is_set() and time.time() < deadline:
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            _RUN_LOOP_MODE, NSDate.dateWithTimeIntervalSinceNow_(0.2)
        )
    return event.is_set()


def request_sfspeech_authorization(timeout: float = 90.0) -> str:
    """Trigger the macOS permission prompt and wait for the user's choice."""
    mod = _speech_module()
    if mod is None:
        return "unavailable"
    if int(mod.SFSpeechRecognizer.authorizationStatus()) == 3:
        return "authorized"

    done = threading.Event()
    result = {"status": 0}

    def handler(status):
        result["status"] = int(status)
        done.set()

    mod.SFSpeechRecognizer.requestAuthorization_(handler)
    _pump_run_loop(done, timeout)
    return _STATUS_NAMES.get(result["status"], "unknown")


def _transcribe_main_thread(audio_path: str, timeout: float = 60.0) -> str | None:
    """Transcribe on the caller's thread (must be the process main thread).

    SFSpeechRecognizer delivers its callback via the main-thread run loop only,
    so this must never be called from uvicorn's event-loop thread.
    """
    mod = _speech_module()
    if mod is None:
        return None

    result = {}
    done = threading.Event()

    recognizer = mod.SFSpeechRecognizer.alloc().init()
    request = mod.SFSpeechURLRecognitionRequest.alloc().initWithURL_(
        NSURL.fileURLWithPath_(audio_path)
    )

    def handler(res, err):
        if err is not None:
            result["error"] = str(err)
        elif res is not None:
            result["text"] = res.bestTranscription().formattedString()
        else:
            result["error"] = "no recognition result"
        done.set()

    recognizer.recognitionTaskWithRequest_resultHandler_(request, handler)
    _pump_run_loop(done, timeout)
    if not done.is_set():
        recognizer.cancel()
        return None
    if "error" in result:
        return None
    return result.get("text")


_CHILD_SCRIPT = (
    "import json,sys;"
    "from jarvis.voice.stt import _transcribe_main_thread;"
    "d=json.loads(sys.argv[1]);"
    "t=_transcribe_main_thread(d['path'], d['timeout']);"
    "print(json.dumps({'text': t}))"
)


def transcribe_with_sfspeech(audio_path: str, timeout: float = 60.0) -> str | None:
    """Transcribe an audio file with macOS speech recognition.

    SFSpeechRecognizer only delivers callbacks on the process main thread, so
    recognition cannot run inside uvicorn's event-loop thread. A short-lived
    subprocess (same venv python, same TCC identity) owns the main thread and
    prints a single JSON line.
    """
    import json
    import subprocess
    import sys

    payload = json.dumps({"path": audio_path, "timeout": timeout})
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _CHILD_SCRIPT, payload],
            capture_output=True,
            text=True,
            timeout=timeout + 30,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    return data.get("text") or None
