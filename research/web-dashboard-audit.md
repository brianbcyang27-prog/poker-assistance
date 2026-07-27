# Jarvis Web Dashboard - Full Computer Control Audit

**Date:** 2026-07-24
**Goal:** Ensure the website can FULLY control the computer, not just display data.

---

## What Already Works (67+ Actions)

The API is massive and mostly functional. These actions are wired through `/api/computer/action`:

| Category | Actions | Status |
|----------|---------|--------|
| **Terminal** | `terminal.run`, `terminal.run_safe`, `terminal.run_python` | Working |
| **Files** | `file.read`, `file.write`, `file.delete`, `file.move`, `file.list`, `file.search` | Working |
| **Screen** | `screen.screenshot`, `screen.state`, `screen.active_window`, `screen.windows` | Working |
| **Mouse** | `mouse.click`, `mouse.move` | Working |
| **Keyboard** | `keyboard.type`, `keyboard.press`, `keyboard.hotkey` | Working |
| **Apps** | `app.open`, `app.close` | Working |
| **Accessibility** | `accessibility.tree`, `accessibility.find`, `accessibility.click`, `accessibility.type_into`, `accessibility.activate`, `accessibility.apps`, `accessibility.summary` | Working |
| **Vision** | `vision.capture`, `vision.analyze`, `vision.find`, `vision.describe`, `vision.locate`, `vision.click` | Working |
| **Smart** | `smart.click`, `smart.type` | Working |
| **OS** | `os.notify`, `os.alert`, `os.confirm`, `os.clipboard_*`, `os.hotkey_*`, `os.watch_directory`, `os.system_info`, `os.status` | Working |
| **Browser** | Navigate, click, type, screenshot, JS eval, scroll, search (via BrowserManager) | Working |
| **Voice** | STT, TTS, voice cloning | Working |
| **IoT** | Device register/command/sensor/broadcast | Working |
| **Engineering** | CAD, PCB, firmware, materials, formulas | Working |
| **Security** | Vault, secrets, scan, git protection | Working |

---

## What's BROKEN or Missing

### CRITICAL - Website Can't Do These Things

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 1 | **No agent start/stop/restart** | Can't control agents from UI | Add `/api/agents/{id}/start`, `/stop`, `/restart` |
| 2 | **No mission launch from UI** | Can't start missions from dashboard | Add `/api/missions/start` or wire to chat |
| 3 | **No workspace delete** | Can't clean up workspaces | Add `DELETE /api/workspace/{id}` |
| 4 | **WebSocket bug** in `command_center.html` | Command center shows nothing (connects to `/ws` instead of `/ws/agents`) | Fix WS path |
| 5 | **No authentication** | Anyone on network has full computer control | Add auth middleware |
| 6 | **No bulk operations** | Can't clear memory, reset agents, etc. | Add bulk endpoints |

### MODERATE - Useful but Not Blocking

| # | Issue | Impact |
|---|-------|--------|
| 7 | No graph node/edge deletion | Can't clean knowledge graph |
| 8 | No individual message deletion | Can't edit chat history |
| 9 | Diagnostics are view-only | Can't fix issues from UI |
| 10 | No drag-and-drop file upload | Have to use chat for file ops |

---

## The Real Problem: UI Doesn't Expose Computer Control

The API endpoints exist but the **dashboard UI (base.html + app.js) doesn't expose them**. The frontend only has:

- Chat input (streams via `/api/chat/stream`)
- Screen capture button
- Shell execute (basic)
- Browser screenshot
- File list
- Voice toggle

**Missing UI for:**
- Mouse/keyboard control panel
- Accessibility tree browser with click-to-interact
- App launcher (open/close any app)
- Clipboard manager
- File manager (full CRUD, not just list)
- Notification sender
- Hotkey manager
- IoT device dashboard with live controls
- Agent lifecycle controls (start/stop/restart)
- Mission launch panel
- Real-time screen viewer with click overlay

---

## Action Plan: Make the Website Actually Control Everything

### Phase 1: Fix Critical Bugs (Do Now)

1. Fix WebSocket path in `command-center.html` (`/ws` -> `/ws/agents`)
2. Add authentication (even simple API key)

### Phase 2: Wire Existing Actions to UI (High Impact)

The backend already supports 67+ actions. The frontend just needs UI for them:

**Computer Control Panel** (new tab in dashboard):
- Screenshot viewer with click overlay (vision.click, mouse.click)
- Terminal emulator (terminal.run with streaming output)
- File browser with create/edit/delete
- App launcher grid
- Clipboard manager
- Keyboard shortcut tester

**Agent Controls** (add to agent cards):
- Start/Stop/Restart buttons
- View agent logs
- Send direct message to agent
- View agent's current task

**Mission Launcher** (add to missions tab):
- Create mission form (name, tasks, dependencies)
- Start/Cancel/Pause buttons
- Real-time progress view

### Phase 3: New Control Capabilities

- Real-time screen mirror (WebSocket stream of screenshots)
- Interactive accessibility tree (click nodes to interact)
- Voice command panel (live STT + TTS controls)
- IoT device dashboard with live sensor readings
- File watcher with live change feed

---

## Quick Win: Add Computer Control Tab to Dashboard

The backend at `POST /api/computer/action` already handles everything. The frontend just needs a proper control panel. Here's what to build:

```
┌─────────────────────────────────────────────────┐
│  JARVIS Computer Control                        │
├──────────────┬──────────────────────────────────┤
│ [Terminal]   │  $ ls -la                        │
│ [Files]      │  total 48                        │
│ [Screen]     │  drwxr-xr-x  5 user  staff  160  │
│ [Keyboard]   │  -rw-r--r--  1 user  staff  2048 │
│ [Mouse]      │  ...                             │
│ [Apps]       │                                  │
│ [Clipboard]  │  > _                             │
│ [Hotkeys]    │                                  │
├──────────────┴──────────────────────────────────┤
│ [Voice] [IoT] [Engineering] [Security]          │
└─────────────────────────────────────────────────┘
```

Every button in this panel calls `POST /api/computer/action` with the right action name and params. No new backend code needed.

---

## Summary

**The backend is 95% done.** You have 67+ registered actions covering keyboard, mouse, screen, accessibility, vision, browser, files, shell, OS integration, voice, IoT, engineering, and security.

**The frontend is 30% done.** It shows agent status and lets you chat, but doesn't expose the full computer control capabilities.

**Priority fix:** Build a proper Computer Control tab in the dashboard that maps to the existing `/api/computer/action` endpoint. This alone would give you full computer control from the website.
