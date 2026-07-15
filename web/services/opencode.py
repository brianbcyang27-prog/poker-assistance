import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional, Dict

from config import OPENCODE_MODEL, OPENCODE_BINARY


class OpenCodeBrain:
    def __init__(self):
        self.model = OPENCODE_MODEL
        self.binary = OPENCODE_BINARY
        self._sessions: dict[str, str] = {}

    def _generate_session_id(self) -> str:
        return str(uuid.uuid4())[:8]

    async def chat(self, message: str, session_id: Optional[str] = None) -> dict:
        sid = session_id or self._generate_session_id()
        cmd = [self.binary, "run", "--format", "json", "-m", self.model]
        if sid and session_id:
            cmd += ["--session", sid]
        cmd.append(message)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        response_text = ""
        events = []
        for line in stdout.decode().strip().splitlines():
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)
                if event.get("type") == "message" and event.get("role") == "assistant":
                    response_text = event.get("content", response_text)
                elif "content" in event and event.get("role") == "assistant":
                    response_text = event["content"]
            except json.JSONDecodeError:
                continue

        if not response_text and events:
            for evt in reversed(events):
                if isinstance(evt, dict):
                    for key in ("text", "content", "message", "output"):
                        if key in evt and evt[key]:
                            response_text = evt[key]
                            break
                if response_text:
                    break

        if not response_text:
            response_text = stdout.decode().strip() or "No response from OpenCode."

        return {
            "session_id": sid,
            "response": response_text,
            "events": events,
        }

    async def chat_stream(
        self, message: str, session_id: Optional[str] = None
    ) -> AsyncGenerator[dict, None]:
        sid = session_id or self._generate_session_id()
        cmd = [self.binary, "run", "--format", "json", "-m", self.model]
        if sid and session_id:
            cmd += ["--session", sid]
        cmd.append(message)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async for line in proc.stdout:
            decoded = line.decode().strip()
            if not decoded:
                continue
            try:
                event = json.loads(decoded)
                yield {"type": "event", "data": event}
            except json.JSONDecodeError:
                yield {"type": "raw", "data": decoded}

        yield {"type": "done", "data": {"session_id": sid}}


brain = OpenCodeBrain()
