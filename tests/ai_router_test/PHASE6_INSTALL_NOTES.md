# Phase 6 - Isolated Install Notes (LiteLLM)

Environment: macOS (darwin), Python 3.14.6 (/opt/anaconda3/bin/python3), Docker 29.4.0 available

## Commands (all inside tests/ai_router_test/, isolated from production)
1. mkdir -p tests/ai_router_test && cd tests/ai_router_test
2. /opt/anaconda3/bin/python3 -m venv .venv
3. .venv/bin/pip install 'litellm[proxy]'

## Result
- litellm 1.96.2 installed into .venv (License: MIT per PyPI metadata)
- No changes to production JARVIS environment (separate venv)
