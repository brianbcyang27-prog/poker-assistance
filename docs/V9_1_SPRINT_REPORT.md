# JARVIS v9.1.0 Sprint Report — Stability & Experience

> Generated: 2026-08-04
> Sprint: v9.1.0 Overnight Stability & Experience
> Goal: a stable, demonstration-ready AI Operating System

---

## 1. Bugs Found & Fixed

### Frontend / Workspace

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 1 | Opening Settings blanked the main workspace | `switchWorkspace('settings')` ran the full workspace switch (cleared containers, hid golden core) instead of just opening the overlay | Added early-return: settings short-circuits to overlay open, main area untouched. Verified: home + golden core remain visible behind the overlay |
| 2 | "Developer Mode" button did nothing | Nav button had no click handler / navigation | Wired to full-page navigation to `/dashboard` (JARVIS Developer Dashboard). Verified: click → `/dashboard` renders; `a[href="/"]` returns home |
| 3 | Command palette ⌘K "Toggle Voice" targeted a non-existent element | Command referenced a removed/unmounted DOM id | Retargeted to `#mic-btn` (the real mic button). Verified: command action resolves `#mic-btn` |
| 4 | Command palette appeared empty on first open after page load | Synthetic-event test artifact + results only render when the palette instance's `open()` runs | No code change needed — mechanism verified working: all 12 commands render (6 navigate, chat, projects, tools, info), Esc/close works |
| 5 | Right-side context panel did not follow workspace switching | Suspected stale `right-knowledge` lingering from earlier build | Verified fixed: `_updateSidebarContext` hides all `.right-context` panels and shows exactly one per workspace (chat→`right-chat`, knowledge→`right-knowledge`, home→`right-home`, etc.) |
| 6 | Right-home panel sections missing (dead DOM targets) | Restored `#right-home` sections (SYSTEM HEALTH, AGENT ACTIVITY, TERMINAL) never got their markup after the SPA rework | Rebuilt the three sections in `base.html` with live wiring: health rows (`health-status/health-agents/health-kings/health-events/health-uptime`), agent conversation stream (`#agent-conversation-stream`, max-height 200px scroll), terminal (`#terminal-entries`) |
| 7 | Settings had no Voice Cloning card | `#clone-status-text` / `#clone-profiles-list` targets existed in JS but no panel section rendered them | Added Voice Cloning settings card to `panel-voice`. Verified: endpoint 200, honest error surfaced ("TTS not installed: No module named 'torch'") when torch is absent |

### State Machine (Golden Core)

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 8 | Golden core could enter non-canonical states (`planning`, `delegating`, `reviewing`, `retrieving`, `complete`, `error`, `mission_active`) | `living-interface.js` `_stateThoughts` defined bespoke text for 12 states; consumers emitted raw state names | Collapsed to the 5 canonical states per the golden rule — `idle | listening | thinking | working | speaking` — with alias mapping (planning/delegating/reviewing/retrieving → working; complete/error → idle). Dead entries removed; `node --check` clean on all 5 touched JS files |

### Voice Pipeline

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 9 | No server-side TTS endpoint despite voice settings UI | `/api/voice/clone/status` existed but no generation route | Added `POST /api/voice/generate` (form: `text`/`voice`/`provider`) → `voice_engine.agenerate()` → AIFF/WAV `FileResponse` from `audio_cache/`. curl-verified: HTTP 200, AIFF-C audio via macOS `say` (ffmpeg absent → graceful fallback) |
| 10 | Mic flow ambiguity (dormant legacy class) | `voice-experience.js` `VoiceExperience` class is uninstantiated legacy; the real path is Web Speech API in `voice.js` (`initSpeechRecognition` → `jarvisState.startListening` → `sendMessage`) | Documented as tech debt (below); real flow confirmed wired |

### Computer Control

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 11 | All non-browser computer actions returned 500 (`ModuleNotFoundError: playwright`) | `controller.execute()` auto-initialized the browser for *every* action, so even `shell_execute`/`run_python` triggered the missing playwright import | Browser init only for `action.startswith("browser_")`; init failures return `{"ok": false, "error": "Browser unavailable: ..."}` instead of 500 |
| 12 | `_capture_snapshot` hung indefinitely | macOS accessibility calls (`screen.get_active_window()`) block forever on the dev machine | Wrapped window + screenshot calls in `asyncio.wait_for(..., timeout=2)` |
| 13 | No way to run Python from the UI/API | Action list lacked `run_python` | Added `run_python` to `controller.list_actions()`, actions map, and `_run_python` handler (tempfile + `python3` subprocess with timeout → `{ok, stdout, stderr, returncode}`); added `"run_python": ["terminal"]` to the router permission map |
| 14 | `/api/computer/shutdown` open to any caller | No host check | Gated local-only (host must be `127.0.0.1`/`::1`/`localhost`), else 403 |

**Live verification:** `run_python` `print(6*7)` → `{"ok":true,"stdout":"42\n","returncode":0}` HTTP 200 in ~2.07s; `shell_execute "echo hello-jarvis"` → 200 in ~2.02s; `/shutdown` → 200 local.

---

## 2. Improvements

- **State machine discipline**: golden core now strictly obeys the 5-state golden rule; visual consistency across `living-interface.js`, `state-machine.js`, `graph-3d.js`.
- **Graceful degradation**: missing playwright / missing torch / missing ffmpeg no longer produce 500s or hangs — they surface as honest, structured errors in the UI (`{"ok": false, ...}`, red TTS status text).
- **Real computer control**: `run_python` end-to-end from API → permission map → controller → subprocess.
- **Live dashboard**: SYSTEM HEALTH / AGENT ACTIVITY / TERMINAL sections now render real data (health: OK, agents 0/23, kings 4/4, uptime ticking; terminal logs the chat command during demo).
- **Security**: `/api/computer/shutdown` now refuses non-local callers (403).
- **Resilient WS layer** (audited): `ws-manager.js` provides heartbeat (10s, server drops silent clients at 30s), exponential-backoff reconnect (1s→30s), intentional-close flag, typed event dispatch — verified sound.
- **Zero console errors** across the entire browser walkthrough.

---

## 3. Screenshots

| File | Caption |
|------|---------|
| `docs/after-home.png` | Home — golden core centered, right panel with SYSTEM HEALTH / AGENT ACTIVITY / TERMINAL live |
| `docs/after-chat.png` | Chat — user message + LLM response rendered, core state IDLE after reply |
| `docs/after-projects.png` | Projects workspace active with matching right-context |
| `docs/after-knowledge.png` | Knowledge workspace active (static "No knowledge loaded" empty state) |
| `docs/after-settings-voice.png` | Settings → Voice — built-in voices + Voice Cloning card with honest TTS status |
| `docs/after-dev-dashboard.png` | JARVIS Developer Dashboard (`/dashboard`) |

---

## 4. Verification Evidence

### Automated tests
```
625 passed, 5 warnings in 26.62s
```
(Full suite minus documented hang-prone files: computer/brain-core/plugins/browser/eng-intel/refactoring/repo-intelligence. The suite prints green then hangs at asyncio teardown — known baseline behavior.)

### JS syntax
`node --check` clean on all touched files: `app.js`, `command-palette.js`, `state-machine.js`, `graph-3d.js`, `living-interface.js`.

### Live API (curl)
| Endpoint | Result |
|----------|--------|
| `POST /api/voice/generate` (text="hello") | 200, AIFF-C audio |
| `POST /api/computer/action` run_python `print(6*7)` | 200, stdout `42`, returncode 0 |
| `POST /api/computer/action` shell_execute `echo hello-jarvis` | 200 |
| `POST /api/computer/shutdown` (local) | 200 |
| `GET /api/voice/clone/status` | 200, `tts_installed: false` (honest error) |
| `GET /api/system/health` | 200, status OK |

### E2E demo walkthrough (Playwright, real browser)
1. Launch → home loads, golden core centered (482,302 in 1200×676), health panel live.
2. Settings open → main area NOT blanked; overlay close → home restored.
3. Dev button → `/dashboard`; back-link → `/`.
4. Chat: sent "Say hello in exactly five words." → LLM replied "Hello, I am very happy." (exactly 5 words) → core returned to IDLE → terminal logged the event.
5. Workspace walk chat → projects → execution → knowledge → home: exactly one right-context panel per workspace.
6. ⌘K palette: opens, all 12 commands render, Toggle Voice targets `#mic-btn`, Esc closes.
7. **Console: 0 errors, 0 warnings** across the whole session.

---

## 5. Tech Debt

| Item | Impact | Suggested path |
|------|--------|----------------|
| `voice-experience.js` (`VoiceExperience`) is dead code | Confusion; two "voice" systems | Delete or migrate its useful bits into `voice.js`, then remove |
| TTS lacks torch/ffmpeg on this machine | Voice cloning + high-quality TTS unavailable in demo; falls back to macOS `say` | `pip install -e ".[voice]"` + install ffmpeg; re-test clone/status |
| Python test suite hangs at asyncio teardown | CI can't rely on exit code | Fix event-loop cleanup in fixtures (long-standing, pre-existing) |
| Playwright browser actions depend on optional module | `browser_*` actions degrade gracefully but are non-functional here | Install playwright + chromium to enable the full action set |
| Command palette "System Status" logs to console only | Weak UX for an info command | Surface result in a toast/terminal line |
| `?v=9.0.0` cache-buster stale across JS files | Browser may serve stale assets after edits | Bump to `?v=9.1.0` |

---

## 6. v9.2.0 Priorities

1. **Make the voice story real end-to-end**: install torch/ffmpeg, verify cloning + TTS from the UI, wire Web Speech API output to the golden core `speaking` state.
2. **Enable browser control**: install playwright, exercise `browser_*` actions, add a live preview surface for screenshots.
3. **Project/mission experience**: wire the mission DAG adapter (timeline `{nodes,edges}` vs `MissionDAG` `{name,layer}/{from,to}`), empty-state polish, first real mission demo.
4. **CI hardening**: fix the asyncio teardown hang so the 625-test suite returns a clean exit code; add a Playwright smoke test (launch → chat → screenshot) to the pipeline.
5. **Polish the developer dashboard**: real agent health, memory graphs, and a test-runner panel.
6. **Cache busting + asset pipeline**: versioned static assets (`?v=9.1.0`), optionally move to a build step.

---

*Reload instructions: `launchctl kickstart -k gui/$(id -u)/com.jarvis.web` (or `python run.py`), open http://127.0.0.1:8000. Full demo path in section 4.*
