"""Tests for the Apple macOS connector (osascript mocked)."""

import pytest

from jarvis.integrations.connectors.apple import AppleConnector


@pytest.fixture
def connector():
    return AppleConnector()


async def test_test_ok(connector, monkeypatch):
    async def fake_run(script):
        return "JARVIS"

    monkeypatch.setattr(connector, "_run_osascript", fake_run)
    ok, detail = await connector.test()
    assert ok is True
    assert "available" in detail


async def test_test_failure(connector, monkeypatch):
    async def fake_run(script):
        raise RuntimeError("not authorized")

    monkeypatch.setattr(connector, "_run_osascript", fake_run)
    ok, detail = await connector.test()
    assert ok is False
    assert "not authorized" in detail


async def test_calendar_upcoming(connector, monkeypatch):
    async def fake_run(script):
        return (
            "Standup\tMonday, August 10, 2026 at 9:00:00 AM\n"
            "Lunch\tMonday, August 10, 2026 at 12:00:00 PM\n"
        )

    monkeypatch.setattr(connector, "_run_osascript", fake_run)
    result = await connector.action("calendar_upcoming", {"limit": 5})
    assert result["ok"] is True
    assert len(result["events"]) == 2
    assert result["events"][0]["summary"] == "Standup"


async def test_reminders_list(connector, monkeypatch):
    async def fake_run(script):
        return "Buy milk\tMonday, August 10, 2026 at 9:00:00 AM\nCall dentist\n"

    monkeypatch.setattr(connector, "_run_osascript", fake_run)
    result = await connector.action("reminders_list", {})
    assert result["ok"] is True
    assert result["reminders"] == [
        {"name": "Buy milk", "due": "Monday, August 10, 2026 at 9:00:00 AM"},
        {"name": "Call dentist", "due": ""},
    ]


async def test_mail_unread(connector, monkeypatch):
    async def fake_run(script):
        return "Meeting changed\tboss@example.com\nInvoice\tbilling@example.com\n"

    monkeypatch.setattr(connector, "_run_osascript", fake_run)
    result = await connector.action("mail_unread", {"limit": 5})
    assert result["ok"] is True
    assert result["messages"][0]["subject"] == "Meeting changed"
    assert result["messages"][0]["sender"] == "boss@example.com"


async def test_contacts_search_filters(connector, monkeypatch):
    async def fake_run(script):
        return "Brian Yang\t+1 555 0100\nAda Lovelace\t+1 555 0199\n"

    monkeypatch.setattr(connector, "_run_osascript", fake_run)
    result = await connector.action("contacts_search", {"query": "ada"})
    assert result["ok"] is True
    assert len(result["contacts"]) == 1
    assert result["contacts"][0]["name"] == "Ada Lovelace"


async def test_unknown_action(connector, monkeypatch):
    result = await connector.action("nope", {})
    assert result["ok"] is False
    assert "Unknown apple action" in result["error"]


async def test_action_graceful_on_osascript_error(connector, monkeypatch):
    async def fake_run(script):
        raise RuntimeError("Application isn't running")

    monkeypatch.setattr(connector, "_run_osascript", fake_run)
    result = await connector.action("reminders_list", {})
    assert result["ok"] is False
    assert "Application isn't running" in result["error"]


def test_parse_events():
    raw = "A\tMon\nB\tTue\n\nC\tWed\n"
    events = AppleConnector._parse_events(raw)
    assert [e["summary"] for e in events] == ["A", "B", "C"]


def test_parse_mail_skips_malformed_lines():
    raw = "no tab here\nSubject\tSender\n"
    messages = AppleConnector._parse_mail(raw)
    assert len(messages) == 1
    assert messages[0]["subject"] == "Subject"
