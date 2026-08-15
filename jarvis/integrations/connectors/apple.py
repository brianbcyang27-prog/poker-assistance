"""Apple macOS connector — Calendar, Reminders, Mail, Contacts via osascript.

No credentials required: talks to the user's local macOS apps through
``osascript`` (AppleScript). Actions are best-effort; each capability
returns structured data or a graceful error message.
"""

from __future__ import annotations

import asyncio
import logging

from jarvis.integrations.base import Connector, ConnectorCategory, ConnectorStatus

log = logging.getLogger("jarvis.integrations.apple")

_OSASCRIPT = "/usr/bin/osascript"


class AppleConnector(Connector):
    id = "apple"
    name = "Apple"
    category = ConnectorCategory.APPLE
    description = (
        "Your Mac's built-in apps — Calendar, Reminders, Mail, and Contacts — "
        "via local AppleScript. No account needed."
    )
    capabilities = [
        "calendar_upcoming",
        "reminders_list",
        "reminders_complete",
        "mail_unread",
        "contacts_search",
    ]
    config_fields = []
    requires_config = False
    needs_setup_guide = True
    setup_guide = (
        "1. Make sure Calendar, Reminders, Mail, and Contacts are signed in on this Mac.\n"
        "2. The first action may ask for automation permission — click Allow.\n"
        "3. That's it — no token or account setup required."
    )

    # ── subprocess boundary (monkeypatched in tests) ──────────────

    _OSASCRIPT_TIMEOUT = 10.0

    async def _run_osascript(self, script: str, timeout: float | None = None) -> str:
        """Execute an AppleScript snippet and return its stdout.

        macOS Automation (TCC) permission prompts can block ``osascript``
        indefinitely, so every call runs under a hard timeout — a pending
        "allow automation" dialog must never hang the caller.
        """
        if timeout is None:
            timeout = self._OSASCRIPT_TIMEOUT
        proc = await asyncio.create_subprocess_exec(
            _OSASCRIPT,
            "-e",
            script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                "osascript timed out — macOS automation permission may be "
                "pending. Grant automation access in System Settings > "
                "Privacy & Security > Automation."
            )
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(err or f"osascript exited with {proc.returncode}")
        return stdout.decode("utf-8", errors="replace")

    # ── lifecycle ─────────────────────────────────────────────────

    async def test(self) -> tuple[bool, str]:
        """Verify macOS automation is reachable by listing reminders."""
        try:
            await self._run_osascript(
                "tell application \"System Events\" to get name of first process "
                "whose frontmost is true"
            )
            return True, "macOS automation available"
        except (RuntimeError, OSError) as exc:
            return False, f"macOS automation unavailable: {exc}"

    async def disconnect(self) -> None:
        # Nothing to clear — no credentials involved.
        await super().disconnect()
        self.status = ConnectorStatus.AVAILABLE

    async def action(self, action: str, params: dict | None = None) -> dict:
        params = params or {}
        handlers = {
            "calendar_upcoming": self._calendar_upcoming,
            "reminders_list": self._reminders_list,
            "reminders_complete": self._reminders_complete,
            "mail_unread": self._mail_unread,
            "contacts_search": self._contacts_search,
        }
        handler = handlers.get(action)
        if handler is None:
            return {"ok": False, "error": f"Unknown apple action: {action}"}
        try:
            return await handler(params)
        except (RuntimeError, OSError) as exc:
            log.warning("Apple action %s failed: %s", action, exc)
            return {"ok": False, "error": str(exc), "action": action}

    # ── capabilities ──────────────────────────────────────────────

    async def _calendar_upcoming(self, params: dict) -> dict:
        limit = int(params.get("limit", 5))
        script = (
            'tell application "Calendar"\n'
            '  set out to ""\n'
            "  repeat with c in calendars\n"
            "    set evs to (events of c whose start date > (current date))\n"
            "    repeat with e in evs\n"
            "      set out to out & (summary of e) & tab & "
            "((start date of e) as string) & linefeed\n"
            f"      if (count of paragraphs of out) > {limit} then exit repeat\n"
            "    end repeat\n"
            f"    if (count of paragraphs of out) > {limit} then exit repeat\n"
            "  end repeat\n"
            '  return out\n'
            "end tell"
        )
        raw = await self._run_osascript(script)
        events = self._parse_events(raw)[:limit]
        return {"ok": True, "action": "calendar_upcoming", "events": events}

    async def _reminders_list(self, params: dict) -> dict:
        list_name = params.get("list") or "all"
        if list_name == "today":
            script = (
                'tell application "Reminders"\n'
                '  set out to ""\n'
                "  repeat with r in (reminders whose completed is false)\n"
                "    try\n"
                "      set d to due date of r\n"
                "      if d is not missing value then\n"
                "        if d ≤ (end of (current date)) then\n"
                '          set out to out & (name of r) & tab & (d as string) & linefeed\n'
                "        end if\n"
                "      end if\n"
                "    end try\n"
                "  end repeat\n"
                "  return out\n"
                "end tell"
            )
        else:
            script = (
                'tell application "Reminders"\n'
                '  set out to ""\n'
                "  repeat with r in (reminders whose completed is false)\n"
                "    try\n"
                "      set d to due date of r\n"
                "      if d is missing value then\n"
                '        set out to out & (name of r) & linefeed\n'
                "      else\n"
                '        set out to out & (name of r) & tab & (d as string) & linefeed\n'
                "      end if\n"
                "    end try\n"
                "  end repeat\n"
                "  return out\n"
                "end tell"
            )
        raw = await self._run_osascript(script)
        reminders = self._parse_reminders(raw)
        return {"ok": True, "action": "reminders_list", "list": list_name, "reminders": reminders}

    async def _reminders_complete(self, params: dict) -> dict:
        name = str(params.get("name", "")).strip()
        if not name:
            return {"ok": False, "error": "reminder name required"}
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        script = (
            'tell application "Reminders"\n'
            '  set done to false\n'
            '  repeat with r in (reminders whose completed is false)\n'
            f'    if (name of r) is "{escaped}" then\n'
            "      set completed of r to true\n"
            "      set done to true\n"
            "      exit repeat\n"
            "    end if\n"
            "  end repeat\n"
            "  return done\n"
            "end tell"
        )
        raw = await self._run_osascript(script)
        return {
            "ok": raw.strip() == "true",
            "action": "reminders_complete",
            "name": name,
            "completed": raw.strip() == "true",
        }

    async def _mail_unread(self, params: dict) -> dict:
        limit = int(params.get("limit", 5))
        script = (
            'tell application "Mail"\n'
            '  set out to ""\n'
            "  set msgs to (messages of inbox whose read status is false)\n"
            f"  if (count of msgs) > {limit} then set msgs to items 1 thru {limit} of msgs\n"
            "  repeat with m in msgs\n"
            '    set out to out & (subject of m) & tab & (sender of m) & linefeed\n'
            "  end repeat\n"
            "  return out\n"
            "end tell"
        )
        raw = await self._run_osascript(script)
        messages = []
        for line in raw.splitlines():
            if "\t" in line:
                subject, sender = line.split("\t", 1)
                messages.append({"subject": subject.strip(), "sender": sender.strip()})
        return {"ok": True, "action": "mail_unread", "messages": messages[:limit]}

    async def _contacts_search(self, params: dict) -> dict:
        query = str(params.get("query", "")).strip().lower()
        script = (
            'tell application "Contacts"\n'
            '  set out to ""\n'
            "  repeat with p in people\n"
            '    set out to out & (name of p) & tab & (value of first phone of p) & linefeed\n'
            "  end repeat\n"
            "  return out\n"
            "end tell"
        )
        raw = await self._run_osascript(script)
        matches = []
        for line in raw.splitlines():
            if "\t" not in line:
                continue
            name, phone = line.split("\t", 1)
            name = name.strip()
            phone = phone.strip()
            if not query or query in name.lower() or query in phone.lower():
                matches.append({"name": name, "phone": phone})
        return {
            "ok": True,
            "action": "contacts_search",
            "query": query,
            "contacts": matches[:20],
        }

    # ── parsing helpers (pure — unit-tested) ──────────────────────

    @staticmethod
    def _parse_events(raw: str, limit: int = 20) -> list[dict]:
        events = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            summary = parts[0].strip() if parts else ""
            when = parts[1].strip() if len(parts) > 1 else ""
            if summary:
                events.append({"summary": summary, "when": when})
        return events[:limit]

    @staticmethod
    def _parse_reminders(raw: str) -> list[dict]:
        reminders = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if "\t" in line:
                name, due = line.split("\t", 1)
                reminders.append({"name": name.strip(), "due": due.strip()})
            else:
                reminders.append({"name": line, "due": ""})
        return reminders

    @staticmethod
    def _parse_mail(raw: str) -> list[dict]:
        messages = []
        for line in raw.splitlines():
            if "\t" in line:
                subject, sender = line.split("\t", 1)
                messages.append({"subject": subject.strip(), "sender": sender.strip()})
        return messages
