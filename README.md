# JARVIS

Multi-Agent AI Operating System inspired by Iron Man's JARVIS.

## Architecture

```
JARVIS (Chief Executive AI)
    │
    ├── ♠ King (Engineering)
    │   ├── ♠Q Architect
    │   ├── ♠J Backend
    │   ├── ♠10 Frontend
    │   ├── ♠9 React
    │   ├── ♠8 Python
    │   ├── ♠7 Testing
    │   ├── ♠6 Docs
    │   └── ♠5 A11y
    │
    ├── ♥ King (Personal)
    │   ├── ♥Q Calendar
    │   ├── ♥J Email
    │   ├── ♥10 Tasks
    │   └── ♥9 Scheduling
    │
    ├── ♦ King (Research)
    │   ├── ♦Q Web Research
    │   ├── ♦J Documentation
    │   └── ♦10 Fact Check
    │
    └── ♣ King (System)
        ├── ♣Q Files
        ├── ♣J Terminal
        └── ♣10 Applications
```

## Quick Start

### Web Interface

```bash
# Install dependencies
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python -m jarvis.web.main
```

### CLI Interface

```bash
python -m jarvis.cli
```

## Configuration

Copy `.env.example` to `.env` and configure:

- `NVIDIA_API_KEY` - Your NVIDIA API key (required)
- `OPENCODE_BINARY` - Path to OpenCode binary (optional)
- `DB_PATH` - SQLite database path

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
```

## Project Structure

```
jarvis/
├── core/           # Config, database, models
├── agents/         # Agent hierarchy
│   ├── kings/      # Division managers
│   └── workers/    # Specialized executors
├── brain/          # LLM integration
├── workspace/      # Mission tracking
├── memory/         # Persistent storage
├── voice/          # Speech I/O
├── safety/         # Validation
└── web/            # FastAPI + Three.js UI
```
