# JARVIS — Multi-Agent AI Operating System

A hierarchical AI system where JARVIS delegates to 4 Kings, each managing specialized Workers. Agents can control your computer, search the web, and manage IoT devices.

## Architecture

```
JARVIS (♠♥♦♣)
├── ♠ Engineering King
│   ├── ♠Q Architect    — system design
│   ├── ♠J Backend      — APIs, databases
│   ├── ♠10 Frontend    — UI, HTML/CSS/JS
│   ├── ♠9 React        — React components
│   ├── ♠8 Python       — Python tasks
│   ├── ♠7 Testing      — test suites
│   ├── ♠6 Docs         — documentation
│   └── ♠5 A11y         — accessibility
├── ♥ Personal King
│   ├── ♥Q Calendar     — scheduling
│   ├── ♥J Email        — email tasks
│   ├── ♥10 Tasks       — task management
│   └── ♥9 Scheduling   — time optimization
├── ♦ Research King
│   ├── ♦Q WebResearch  — web search, scraping
│   ├── ♦J Documentation — technical docs
│   └── ♦10 FactCheck   — verification
└── ♣ System King
    ├── ♣Q Files        — file management
    ├── ♣J Terminal     — shell commands
    └── ♣10 Apps        — application control
```

## Quick Start

```bash
cd /Users/brianyang/jarvis
python3 run.py
# Open http://127.0.0.1:8000
```

## Configuration

Edit `.env` or use Settings page:

```env
# LLM Backend
NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL=meta/llama-3.1-8b-instruct

# Interface
VIEW_MODE=graph          # core | graph
CHAT_MODE=popup          # popup | chat

# Voice
TTS_ENABLED=true
TTS_PROVIDER=macos       # macos | kokoro | openai
```

## Per-Agent LLM Models

Each agent can use a different LLM. Override in worker/king subclasses:

```python
class BackendWorker(BaseWorker):
    def get_model_config(self) -> dict:
        return {
            "model": "meta/llama-3.1-70b-instruct",
            "api_base": "https://integrate.api.nvidia.com/v1",
        }
```

## Computer Control

Agents use `ToolExecutor` to control the computer:

```python
from jarvis.agents.tools import tools

# Screen
await tools.execute("screen_capture")
await tools.execute("screen_list_windows")

# Mouse/Keyboard
await tools.execute("mouse_click", x=100, y=200)
await tools.execute("mouse_type", text="hello world")
await tools.execute("mouse_hotkey", keys=["cmd", "space"])

# Browser
await tools.execute("browser_navigate", url="https://google.com")
await tools.execute("browser_click", selector="button.submit")
await tools.execute("browser_text")

# Web
await tools.execute("web_search", query="python async tutorial")
await tools.execute("web_fetch", url="https://example.com")

# Shell
await tools.execute("shell_execute", command="ls -la ~/Desktop")
```

### Available Actions

| Category | Actions |
|----------|---------|
| Screen | `screen_capture`, `screen_capture_region`, `screen_list_windows`, `screen_active_window`, `screen_open_app`, `screen_open_url` |
| Mouse | `mouse_click`, `mouse_move`, `mouse_type`, `mouse_hotkey`, `mouse_scroll` |
| Browser | `browser_navigate`, `browser_click`, `browser_fill`, `browser_screenshot`, `browser_text`, `browser_press_key`, `browser_evaluate`, `browser_scroll` |
| Web | `web_search`, `web_fetch` |
| IoT | `arduino_list_devices`, `arduino_send`, `arduino_read`, `arduino_status` |
| System | `shell_execute`, `task_complete` |

## IoT / ESP32 Integration

### Arduino Library

Install `JarvisIoT` library in Arduino IDE (or copy `jarvis/iot/arduino_library/JarvisIoT/` to your Arduino libraries folder).

```cpp
#include <JarvisIoT.h>

JarvisIoT jarvis("My Device", "WIFI_SSID", "WIFI_PASS");

void setup() {
    jarvis.begin();
    
    jarvis.onCommand("ledon", [](JsonDocument& p, JsonDocument& r) {
        digitalWrite(LED, HIGH);
        r["status"] = "ok";
    });
    
    jarvis.addSensor("temperature", []() {
        return String(analogRead(A0));
    });
    
    jarvis.registerWith("192.168.1.100", 8000);
}

void loop() {
    jarvis.update();
}
```

### JARVIS Control

From JARVIS or agents:

```python
# List devices
await tools.execute("arduino_list_devices")

# Send command
await tools.execute("arduino_send", device_id="esp32_abc", command="ledon")

# Read sensor
await tools.execute("arduino_read", device_id="esp32_abc", sensor="temperature")

# Broadcast to all devices
await tools.execute("arduino_send", device_id="*", command="emergency_stop")
```

### API Endpoints

```
GET  /api/iot/devices              — list all devices
POST /api/iot/register             — register device
GET  /api/iot/{device_id}          — device details
POST /api/iot/{device_id}/command  — send command
GET  /api/iot/{device_id}/sensor/{name} — read sensor
POST /api/iot/broadcast            — command all devices
```

## Chat Modes

- **Popup Bubble** — floating response that fades (cinematic mode)
- **Normal Chat** — scrollable conversation history

Change in Settings → Interface → Chat Mode.

## API Reference

### Chat
```
POST /api/chat              — send message
GET  /api/chat/sessions     — list sessions
GET  /api/chat/history/{id} — session messages
```

### Agents
```
GET  /api/agents            — list all agents
GET  /api/agents/{card_id}  — agent details
```

### Memory
```
GET  /api/memory/graph      — knowledge graph
POST /api/memory/notes      — create note
GET  /api/memory/notes      — list notes
POST /api/memory/extract    — extract from conversation
```

### Computer
```
POST /api/computer/action    — execute action
GET  /api/computer/actions   — list actions
```

### Settings
```
GET  /api/settings          — get settings
POST /api/settings          — update settings
```

## Project Structure

```
jarvis/
├── core/           — config, database, models
├── agents/         — JARVIS, Kings, Workers
│   ├── jarvis.py   — Chief Executive AI
│   ├── kings/      — Division managers
│   ├── workers/    — Specialized executors
│   └── tools.py    — ToolExecutor (computer, web, IoT)
├── brain/          — LLM interface, memory
│   ├── llm.py      — NVIDIA/Ollama LLM
│   └── memory/     — Knowledge graph, notes
├── computer/       — Real computer control
│   ├── browser.py  — Playwright browser
│   ├── mouse.py    — macOS mouse/keyboard
│   ├── screen.py   — Screenshots, app control
│   ├── search.py   — DuckDuckGo search
│   └── controller.py — Unified action dispatch
├── iot/            — ESP32/Arduino integration
│   ├── manager.py  — Device discovery/control
│   ├── protocol.py — HTTP JSON protocol
│   └── arduino_library/ — Arduino ESP32 library
├── web/            — FastAPI web interface
│   ├── routers/    — API endpoints
│   ├── templates/  — HTML pages
│   └── static/     — CSS, JS, Three.js
└── workspace/      — Task management
```

## Dependencies

```bash
pip3 install fastapi uvicorn aiosqlite aiohttp pydantic-settings openai Pillow
pip3 install playwright  # computer control
python3 -m playwright install chromium
```

## Examples

### "List files on my desktop"
JARVIS → ♣K (System King) → ♣J (Terminal Worker) → `shell_execute("ls ~/Desktop")` → returns file list

### "What's the weather in Tokyo?"
JARVIS → ♦K (Research King) → ♦Q (WebResearch) → `web_search("weather Tokyo")` → returns forecast

### "Turn on the workshop LED"
JARVIS → ♣K (System King) → tool → `arduino_send(device_id="esp32_workshop", command="ledon")` → LED turns on

### "Take a screenshot and describe what you see"
JARVIS → ♣K → ♣Q (Files) → `screen_capture()` → saves screenshot → ♦K → ♦Q (Research) → analyzes image
