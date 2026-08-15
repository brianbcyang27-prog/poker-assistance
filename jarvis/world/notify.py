"""Alert channels for the world monitor — Telegram, iMessage, macOS fallback."""

from __future__ import annotations

import asyncio

from jarvis.core.logging import get_logger

log = get_logger("jarvis.world")

_OSASCRIPT_TIMEOUT = 10.0


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


async def telegram_config() -> tuple[bool, str | None]:
    """Return (configured, chat_id) for the Telegram connector."""
    try:
        from jarvis.integrations import get_registry

        connector = get_registry().get("telegram")
        if connector is None:
            return False, None
        cfg = connector.config or {}
        chat_id = cfg.get("chat_id") or None
        token = cfg.get("bot_token") or ""
        return bool(token and chat_id), chat_id
    except Exception as exc:  # noqa: BLE001 — config lookup must never crash status
        log.debug("telegram config lookup failed: %s", exc)
        return False, None


async def send_telegram(text: str) -> bool:
    try:
        from jarvis.integrations import get_registry

        connector = get_registry().get("telegram")
        if connector is None:
            return False
        chat_id = (connector.config or {}).get("chat_id")
        if not chat_id:
            return False
        result = await connector.action("send_message", {"chat_id": chat_id, "text": text})
        return bool(result.get("ok"))
    except Exception as exc:  # noqa: BLE001 — a failed send must not crash the scan
        log.warning("telegram send failed: %s", exc)
        return False


async def send_imessage(target: str, text: str) -> bool:
    if not target:
        return False
    script = (
        f'tell application "Messages" to send "{_escape(text)}" '
        f'to buddy "{_escape(target)}"'
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "osascript",
            "-e",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, _ = await asyncio.wait_for(proc.communicate(), timeout=_OSASCRIPT_TIMEOUT)
        return proc.returncode == 0
    except (TimeoutError, OSError) as exc:
        log.warning("imessage send failed: %s", exc)
        return False


async def send_local(title: str, message: str) -> bool:
    try:
        from jarvis.os.notifications import NotificationManager

        return await NotificationManager().send(title=title, message=message)
    except Exception as exc:  # noqa: BLE001 — best-effort local notification
        log.debug("local notification failed: %s", exc)
        return False


async def notify_alert(text: str, imessage_target: str | None) -> dict[str, bool]:
    """Send an alert via every configured channel; fall back to a local notification."""
    telegram = await send_telegram(text)
    imessage = await send_imessage(imessage_target, text) if imessage_target else False
    if not telegram and not imessage:
        await send_local("JARVIS — World Monitor", text)
    return {"telegram": telegram, "imessage": imessage}
