import time
from dataclasses import dataclass


@dataclass
class StartupMetrics:
    cli_launch: float = 0.0
    server_ready: float = 0.0
    first_ai_response: float = 0.0
    first_voice_response: float = 0.0

    @property
    def as_dict(self) -> dict:
        return {
            "cli_launch_s": round(self.cli_launch, 2),
            "server_ready_s": round(self.server_ready, 2),
            "first_ai_response_s": round(self.first_ai_response, 2),
            "first_voice_response_s": round(self.first_voice_response, 2),
        }


class StartupTimer:
    def __init__(self):
        self._start = time.monotonic()
        self.metrics = StartupMetrics()

    def mark(self, name: str) -> float:
        elapsed = time.monotonic() - self._start
        if name == "cli_launch":
            self.metrics.cli_launch = elapsed
        elif name == "server_ready":
            self.metrics.server_ready = elapsed
        elif name == "first_ai":
            self.metrics.first_ai_response = elapsed
        elif name == "first_voice":
            self.metrics.first_voice_response = elapsed
        return elapsed

    def report(self) -> str:
        lines = [
            "JARVIS Startup Report",
            "─" * 40,
        ]
        for key, value in self.metrics.as_dict.items():
            label = key.replace("_s", "").replace("_", " ").title()
            lines.append(f"{label:30s} {value:.2f}s")
        lines.append("─" * 40)
        return "\n".join(lines)


startup_timer = StartupTimer()
