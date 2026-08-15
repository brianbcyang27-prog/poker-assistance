"""Structured logging system for JARVIS v9.0.0.

Provides centralized log configuration with:
- JSON-formatted file output for log aggregation
- Colored console output for development
- Automatic file rotation (10 MB, 5 backups)
- Consistent module-level logger access
- Per-module log level control

Usage:
    from jarvis.core.logging import setup_logging, get_logger

    # Call once at application startup
    setup_logging()

    # Use in any module
    log = get_logger(__name__)
    log.info("Server started", extra={"port": 8000})
    log.error("Connection failed", extra={"host": host, "timeout": timeout})
"""

import json
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Level Aliases ──────────────────────────────────────────────────────────

_SKIP_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }
)

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

# ── Formatters ─────────────────────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """Formats log records as newline-delimited JSON.

    Produces structured output suitable for log aggregation systems
    (Datadog, Splunk, ELK, etc.).

    Schema per record:
        timestamp: ISO-8601 with millisecond precision
        level:     Uppercase log level name
        logger:    Logger name (module path)
        message:   Formatted log message
        module:    Module where the record originated
        function:  Function where the record originated
        line:      Line number
        extra:     Any additional fields passed via extra={...}
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, object] = {
            "timestamp": self._format_time(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in _SKIP_ATTRS:
                log_entry[key] = value

        return json.dumps(log_entry, default=str, ensure_ascii=False)

    @staticmethod
    def _format_time(timestamp: float) -> str:
        """Format unix timestamp as ISO-8601 with millisecond precision."""
        t = time.localtime(timestamp)
        ms = int((timestamp - int(timestamp)) * 1000)
        return (
            f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d}"
            f"T{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}"
        )


class ColoredConsoleFormatter(logging.Formatter):
    """Formats log records for human-readable console output with colors.

    Color scheme:
        DEBUG   → dim white
        INFO    → green
        WARNING → yellow
        ERROR   → red
        CRITICAL → red background
    """

    _COLORS = {
        "DEBUG": "\033[2;37m",  # dim white
        "INFO": "\033[32m",  # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",  # red
        "CRITICAL": "\033[41;97m",  # white on red bg
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        level_color = self._COLORS.get(record.levelname, self._RESET)
        level_padded = f"{record.levelname:<8}"

        formatted = (
            f"{level_color}{level_padded}{self._RESET}{record.name:>24} │ {record.getMessage()}"
        )

        if record.exc_info and record.exc_info[0]:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


# ── Configuration ──────────────────────────────────────────────────────────


class LogConfig:
    """Centralized logging configuration.

    Defaults are production-sensible. Override via Config (env vars) before
    calling setup_logging().
    """

    def __init__(self) -> None:
        self.level: str = "INFO"
        self.log_dir: str = str(Path.home() / ".jarvis" / "logs")
        self.json_file: bool = True
        self.json_filename: str = "jarvis.json.log"
        self.json_max_bytes: int = 10 * 1024 * 1024
        self.json_backup_count: int = 5
        self.console_output: bool = True
        self.console_use_colors: bool = True
        self.module_levels: dict[str, str] = {}


log_config = LogConfig()


# ── Logger Cache ───────────────────────────────────────────────────────────

_loggers: dict[str, logging.Logger] = {}
_initialized = False


def get_logger(name: str) -> logging.Logger:
    """Get a cached logger by name.

    Prefer __name__ as the argument — this gives automatic module hierarchy.
    Loggers are configured once by setup_logging(); subsequent calls return
    the same logger with its level potentially overridden by module_levels.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    _loggers[name] = logger

    if _initialized:
        for module_prefix, level_name in log_config.module_levels.items():
            if name.startswith(module_prefix):
                level = LOG_LEVELS.get(level_name.lower(), logging.INFO)
                logger.setLevel(level)
                break

    return logger


# ── Setup ──────────────────────────────────────────────────────────────────


def setup_logging(config: LogConfig | None = None) -> None:
    """Configure JARVIS logging system.

    Must be called once at application startup, before any get_logger() calls.
    If called a second time, it is a no-op (idempotent).

    Args:
        config: Override default configuration. If None, uses module-level
                ``log_config`` which can be modified before calling this.
    """
    global _initialized
    if _initialized:
        return

    cfg = config or log_config
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # ── File handler (structured JSON) ──
    log_dir = Path(cfg.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=str(log_dir / cfg.json_filename),
        maxBytes=cfg.json_max_bytes,
        backupCount=cfg.json_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(LOG_LEVELS.get(cfg.level.upper(), logging.INFO))
    file_handler.setFormatter(JSONFormatter())
    root.addHandler(file_handler)

    # ── Console handler (colored text) ──
    if cfg.console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LOG_LEVELS.get(cfg.level.upper(), logging.INFO))
        if cfg.console_use_colors:
            console_handler.setFormatter(ColoredConsoleFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter("%(levelname)-8s %(name)s │ %(message)s")
            )
        root.addHandler(console_handler)

    for module_prefix, level_name in cfg.module_levels.items():
        level = LOG_LEVELS.get(level_name.lower())
        if level is not None:
            child = logging.getLogger(module_prefix)
            child.setLevel(level)

    for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _initialized = True
    root.info(
        "Logging initialized",
        extra={
            "level": cfg.level,
            "json_file": cfg.json_filename,
            "console": cfg.console_output,
        },
    )


def shutdown_logging() -> None:
    """Flush and close all logging handlers.

    Call during graceful shutdown to ensure all log records are written.
    """
    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.flush()
        handler.close()
        root.removeHandler(handler)

    _loggers.clear()
    global _initialized
    _initialized = False


# ── Convenience ────────────────────────────────────────────────────────────


def set_level(level_name: str) -> None:
    """Change root log level at runtime.

    Args:
        level_name: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    level = LOG_LEVELS.get(level_name.lower())
    if level is None:
        raise ValueError(f"Unknown log level: {level_name!r}")
    log_config.level = level_name.upper()
    root = logging.getLogger()
    for handler in root.handlers:
        handler.setLevel(level)
    logging.getLogger().info("Log level changed", extra={"level": level_name.upper()})
