# JARVIS Reliability Review — July 2026

> 12 critical reliability issues found across core systems

---

## Executive Summary

| Category | Count | Severity |
|----------|-------|----------|
| Silent error swallowing | 2 | HIGH |
| Missing timeouts | 3 | HIGH |
| No retry logic | 1 | HIGH |
| Resource leaks | 2 | MEDIUM |
| Race conditions | 2 | MEDIUM |
| Blocking I/O in async | 2 | HIGH |
| **Total** | **12** | **8 HIGH, 4 MEDIUM** |

---

## Issues Found

### 1. Silent Exception Swallowing in Session Context
**File:** `jarvis/brain/llm.py:262-273`
```python
async def load_session_context(self, session_id: str):
    ...
    except Exception:
        pass
```
**Risk:** DB outage → lost context → degraded responses with no indication
**Fix:** Log the exception and set a degraded-state flag

### 2. Blocking `time.sleep()` in Async Context
**File:** `jarvis/brain/llm.py:128-140`
```python
import time as _time

_time.sleep(delay)
```
**Risk:** Blocks entire event loop, stalling all concurrent requests
**Fix:** Use `asyncio.sleep` or make method async

### 3. No Retry on Streaming Responses
**File:** `jarvis/brain/llm.py:278-300`
```python
def _chat_completion_stream(self, ...):
    with self._http.stream("POST", url, ...) as resp:
        resp.raise_for_status()
```
**Risk:** Transient 500 kills entire response with no recovery
**Fix:** Wrap stream open in retry loop

### 4. Screenshot Disk Leak
**File:** `jarvis/computer/screen.py:8-9`
```python
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)
```
**Risk:** ~17GB/day of screenshots with no cleanup
**Fix:** Add TTL-based cleanup (delete files > 1 hour old)

### 5. No Process Timeout on Shell Commands
**File:** `jarvis/computer/mouse.py` (all methods)
```python
proc = await asyncio.create_subprocess_exec("cliclick", ...)
await proc.communicate()  # can hang forever
```
**Risk:** Accessibility API hangs tie up event loop forever
**Fix:** Wrap with `asyncio.wait_for(timeout=10)`

### 6. `run_until_complete` on Running Event Loop
**File:** `jarvis/brain/llm.py:93-94`
```python
asyncio.get_event_loop().run_until_complete(self._async_http.aclose())
```
**Risk:** Raises RuntimeError (masked by `except: pass`), HTTP client never closed
**Fix:** Make `close()` async or use different pattern

### 7. Unsynchronized WebSocket Client Set
**File:** `jarvis/web/routers/websocket.py:12, 219`
```python
_clients: Set[WebSocket] = set()
_clients.add(websocket)
_clients -= disconnected
```
**Risk:** Concurrent mutation during iteration can miss messages
**Fix:** Use `asyncio.Lock` or per-client queues

### 8. Fire-and-Forget Event Bridge Tasks
**File:** `jarvis/web/routers/websocket.py:189-195`
```python
t = loop.create_task(event_bus.on(event_type, handler))
_bridge_tasks.append(t)
```
**Risk:** If task dies, all subsequent WS clients silently stop receiving events
**Fix:** Add exception callbacks, re-setup on failure

### 9. No Request Timeout on Chat Endpoint
**File:** `jarvis/web/routers/chat.py:62`
```python
response = await web_main.jarvis.process_user_request(req.message)
```
**Risk:** Slow LLM/hung agent exhausts server capacity
**Fix:** Wrap with `asyncio.wait_for(timeout=120)`

### 10. Non-Atomic Mission File Writes
**File:** `jarvis/mission/manager.py:160-174`
```python
self._storage.write_text(json.dumps(data, ...))
```
**Risk:** Crash mid-write corrupts all mission data
**Fix:** Write to temp file, then atomic rename

### 11. SSE Generator Error Handling
**File:** `jarvis/web/routers/chat.py:109-155`
```python
async def event_generator():
    yield f"data: ...\n\n"
    db = await get_db()  # can throw before first yield
```
**Risk:** DB failure → 500 instead of SSE stream, client hangs
**Fix:** Wrap entire generator body in try/finally

### 12. Shared Mutable Conversation History
**File:** `jarvis/brain/llm.py:206-211`
```python
self.conversation_history.append(...)
self.conversation_history = self.conversation_history[-20:]
```
**Risk:** Concurrent chat/achat calls interleave, corrupting history
**Fix:** Add `asyncio.Lock` for history mutations

---

## Fix Priority

### Critical (Fix Now)
1. **#5** — Subprocess timeouts (prevents event loop stall)
2. **#9** — Request timeout (prevents capacity exhaustion)
3. **#6** — Event loop fix (prevents connection leak)
4. **#8** — Event bridge error handling (prevents silent WS failure)

### High (Fix This Week)
5. **#1** — Silent exception logging
6. **#2** — Blocking sleep fix
7. **#3** — Streaming retry logic
8. **#10** — Atomic file writes
9. **#12** — History lock

### Medium (Fix Next Week)
10. **#4** — Screenshot cleanup
11. **#7** — WS client synchronization
12. **#11** — SSE error handling

---

*Compiled: 2026-07-25 | Target: v7.6.0 release*
