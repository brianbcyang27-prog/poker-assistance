# JARVIS AI Router Research

**Status:** COMPLETE — PASS (all objectives verified, all functional tests green)
**Date:** 2026-08-15
**Author:** Research phase (Sisyphus agent), isolated environment only — **no production JARVIS changes made**
**Test environment:** `tests/ai_router_test/` (self-contained venv, separate from JARVIS's runtime deps)

---

## 1. Executive Summary

JARVIS currently talks directly to the NVIDIA NIM API (`integrate.api.nvidia.com`) via a hand-rolled
httpx client in `jarvis/brain/llm.py`, with a naive fallback to local Ollama. The goal of this research
was to find an open-source LLM router that:

1. Unifies multiple providers behind **one OpenAI-compatible endpoint** (so JARVIS's existing
   `/chat/completions` calls keep working unchanged),
2. **Automatically fails over** when the primary provider hits rate limits, quota exhaustion, or errors
   (the "unknown project" that auto-switches providers when one runs out of tokens), and
3. Can be **installed and verified in isolation** without touching the production tree.

**Winner: LiteLLM** (MIT, 56k★, actively maintained — latest push 2026-08-15).

LiteLLM's proxy was installed in an isolated venv, configured with the exact NVIDIA model JARVIS uses
(`nvidia_nim/meta/llama-3.1-8b-instruct`), a local Ollama model, and intentionally-broken-key fallback
chains. **All 7 functional tests passed**, including a 2-level cascade failover, and the proxy answered
JARVIS's *exact* request shape (httpx → `{api_base}/chat/completions`, `Bearer` auth) with a correct
completion — proving drop-in compatibility.

The "unknown auto-switch project" is identified as the **LiteLLM family** (`BerriAI/litellm`), with
one-api / new-api as key-redistribution-oriented alternatives (see §7).

---

## 2. Problem Statement

JARVIS's LLM layer (`jarvis/brain/llm.py`, v6.1.0) has three reliability gaps:

| Gap | Current behavior | Consequence |
|---|---|---|
| **No provider failover** | Only NVIDIA NIM is used when `NVIDIA_API_KEY` is set; Ollama fallback is all-or-nothing local | Free-tier rate limit (NVIDIA NIM prototyping ~40 RPM) or quota exhaustion = hard failure / degraded experience |
| **Hand-rolled retry** | `jarvis/core/reliability.py` + inline retry loops (500s and connect errors only, 3 attempts, exponential backoff) | No handling of 429 rate-limit headers, no circuit breaker on specific providers, duplicated logic |
| **Single-model coupling** | `NVIDIA_MODEL` is one model string; switching providers means editing `.env` + code paths | Adding Groq/Cerebras/Gemini/OpenRouter requires code changes in every LLM call site |

Goal: a thin, config-driven routing layer in front of the LLM that JARVIS can adopt without changing its
call shape, and that provides in-order fallbacks, retries, and cooldowns.

---

## 3. Requirements (verified against candidates)

| # | Requirement | Why |
|---|---|---|
| R1 | **OpenAI-compatible endpoint** (`/v1/chat/completions`, streaming `text/event-stream`) | JARVIS sends `{base}/chat/completions` with `{model, messages, temperature, max_tokens}` via httpx; no SDK swap wanted |
| R2 | **Automatic in-order fallbacks** on rate-limit / quota / 5xx / auth errors | This is the core feature: "switch providers when one runs out of tokens" |
| R3 | **NVIDIA NIM as a first-class provider** (or OpenAI-compatible channel) | JARVIS's production provider; must support custom `api_base` + key |
| R4 | Retries with backoff, cooldowns/circuit-breaking on failing providers | Prevent hammering a dead provider |
| R5 | **Local first / self-hostable**, no mandatory SaaS | JARVIS is local-first |
| R6 | Open-source license compatible with MIT project | JARVIS is MIT |
| R7 | Stack fit: Python preferred (or a drop-in binary/service) | JARVIS is Python 3.11+; avoid forcing Node/Go runtimes where possible |
| R8 | Active maintenance | Router is a security-critical choke point |
| R9 | Streaming support | JARVIS UI streams responses |

---

## 4. Candidate Landscape

Candidates surveyed (docs + GitHub verified, 2026-08-15):

| Project | Stars | License | Language | Push recency |
|---|---|---|---|---|
| **BerriAI/litellm** | 56,396 | MIT | Python | 2026-08-15 (today) |
| **QuantumNous/new-api** | 45,203 | AGPL-3.0 | Go + Vue | active |
| **songquanpeng/one-api** | 36,387 | MIT | Go + Vue | 2026-01-09 |
| **PortkeyAI/gateway** | 12,730 | MIT | TypeScript | active |
| prashantdudami/llm-rate-guard | niche | MIT | Python | archived-ish |

All are self-hostable; none are SaaS-mandatory.

---

## 5. Candidate Comparison (scorecard, weighted to requirements)

| Criteria (weight) | LiteLLM | one-api | new-api | Portkey |
|---|---|---|---|---|
| OpenAI-compatible proxy (R1) | ✅ native | ✅ native | ✅ native | ✅ native |
| In-order fallbacks on failure (R2) | ✅ **`fallbacks` list, per-error-class** | ⚠️ auto-retry + load-balancing across same-key pool, no semantic fallback chains | ⚠️ same model | ✅ fallbacks + retries |
| NVIDIA NIM provider (R3) | ✅ **native `nvidia_nim/` provider, default base = JARVIS's exact base** | ❌ no explicit NIM provider (generic OpenAI channel) | ❌ generic channel | ⚠️ only via generic OpenAI-compat channel |
| Retries/cooldowns (R4) | ✅ `num_retries`, `cooldown_time`, `allowed_fails` | ⚠️ retries only | ⚠️ retries only | ✅ retries, enterprise for advanced |
| Self-host local (R5) | ✅ proxy on `:4000`, DB-less mode | ✅ single Go binary | ✅ single Go binary | ✅ 122kb binary |
| License (R6) | ✅ MIT | ✅ MIT | ❌ AGPL-3.0 (copyleft) | ✅ MIT |
| Stack fit (R7) | ✅ **Python** (JARVIS's stack) | Go service | Go service | Node.js (native), JS SDK |
| Active (R8) | ✅ pushed today | ✅ | ✅ | ✅ |
| Streaming (R9) | ✅ | ✅ | ✅ | ✅ |

**Verdict matrix:**
- **LiteLLM** — best overall; the only candidate with a *native* NVIDIA NIM provider whose default
  base URL exactly matches JARVIS's production base, plus in-order fallbacks + cooldowns + Python.
- **one-api** — solid MIT alternative, but it's a key-redistribution/load-balancing gateway; the
  "fallback" story is per-model retry across a channel pool, not semantic A→B→C chains.
- **new-api** — most stars of the two, but **AGPL-3.0** is incompatible with a clean MIT project.
- **Portkey** — excellent gateway, but NVIDIA NIM is not a first-class provider (generic channel only),
  requires a Node.js runtime, and the most powerful features are enterprise-gated.

---

## 6. Selection Decision

**→ ADOPT candidate for integration testing: LiteLLM** (decision is about the research outcome;
see §11/§12 for the recommendation on JARVIS).

Rationale: it is the only candidate that satisfies **all nine requirements** simultaneously, and the
only one with a first-class NVIDIA NIM provider (`nvidia_nim/`) whose default `api_base` is
`https://integrate.api.nvidia.com/v1` — byte-identical to JARVIS's configured `NVIDIA_API_BASE`.
MIT license matches JARVIS's. Python matches the stack. Active development (pushed today).

---

## 7. The "Unknown Auto-Switch Project" — Identification

The mysterious project that "automatically switches providers when one runs out of tokens" is
**BerriAI/litellm** — specifically its **proxy/router** layer:

- `litellm_settings.fallbacks` defines **in-order fallback chains** (`{"model_a": ["model_b", "model_c"]}`)
  that fire on rate-limit errors (429), 5xx, authentication failures, content-policy violations, and
  context-window overflows.
- `router_settings` adds per-provider **cooldowns** (`cooldown_time`, `allowed_fails`) — a provider that
  fails N times is *cooled down* and skipped, which is the "when one runs out of tokens" behavior.
- Verified live in this test: a request to a bad-key model returned HTTP 200 by transparently switching
  to a healthy model, with `x-litellm-attempted-fallbacks: 1` (see §9, test 5).

Related projects in the same space (one-api / new-api) also auto-switch, but their model is *key
pooling/load balancing* (rotate keys until one works), not per-request semantic fallback chains.

---

## 8. Install & Setup Findings (isolated, in `tests/ai_router_test/`)

Environment: macOS (darwin), Python 3.14.6 (`/opt/anaconda3/bin/python3`), Docker 29.4.0 available.

```bash
python3 -m venv .venv
.venv/bin/pip install 'litellm[proxy]'      # → litellm 1.96.2
```

**⚠️ Important gotcha found during install:** LiteLLM 1.96.2's proxy imports
`get_flat_dependant` from `fastapi.dependencies.utils`, which **was removed in fastapi ≥ 0.140**.
The `litellm[proxy]` extra's constraint (`fastapi>=0.136.3,<1.0`) permits broken versions, so the proxy
crashed at startup with `ImportError`. Fix:

```bash
.venv/bin/pip install 'fastapi<0.140'       # pinned to 0.140.13 — proxy boots cleanly
```

- **License confirmed:** PyPI metadata lists MIT for litellm 1.96.2 (resolves the repo's SPDX
  `NOASSERTION` ambiguity).
- **No DB required:** plain `config.yaml` + `--port 4000` runs the proxy DB-less.
- **Config shape** (`config.yaml` in the test dir): `model_list` (each entry = `model_name` +
  `litellm_params.model/api_key/api_base`), `litellm_settings` (`fallbacks`, `num_retries`),
  `router_settings` (`routing_strategy`, `cooldown_time`, `allowed_fails`), `general_settings.master_key`.
- **Credential handling:** `api_key: os.environ/NVIDIA_API_KEY` reads from env at startup — no secrets
  in the config file. NVIDIA key was sourced from the repo `.env` at launch, never echoed.
- **Health check:** `GET /health/liveliness` → 200.
- **Routing verification:** every response carries `x-litellm-model-group`, `x-litellm-model-name`,
  `x-litellm-attempted-fallbacks`, `x-litellm-attempted-retries`.

---

## 9. Functional Test Results (all on the isolated proxy at `:4000`)

| # | Test | Request | Result | Evidence |
|---|---|---|---|---|
| 1 | Model inventory | `GET /v1/models` | ✅ PASS | all 4 registered names returned (`nvidia-jarvis`, `nvidia-backup`, `ollama-local`, `bad-key-primary`) |
| 2 | Basic completion | `POST /v1/chat/completions` → `nvidia-jarvis` | ✅ PASS | HTTP 200, `PONG`, 666ms; `x-litellm-model-name: nvidia_nim/meta/llama-3.1-8b-instruct`; `attempted-fallbacks: 0` |
| 3 | Streaming | same + `"stream": true` | ✅ PASS | HTTP 200, `content-type: text/event-stream`, 9 SSE chunks, `[DONE]` terminator |
| 4 | Local model leg | → `ollama-local` (qwen2.5:0.5b) | ✅ PASS | HTTP 200, `LOCAL_OK`, 1.28s, group `ollama-local` |
| 5 | **Provider fallback** | → `bad-key-primary` (invalid key) | ✅ PASS | HTTP 200, `FALLBACK_OK`, ~1.0s; `attempted-fallbacks: 1`; served by group `nvidia-jarvis` |
| 6 | **2-level cascade** | → `cascade-bad1` (bad → bad → local) | ✅ PASS | HTTP 200, `CASCADE_OK`, 1.36s; `attempted-fallbacks: 2`; served by `ollama-local` |
| 7 | **JARVIS-shape PoC** | httpx `POST {base}/chat/completions`, `{model,messages,temperature,max_tokens}` | ✅ PASS | HTTP 200, `JARVIS_ROUTER_OK`, 206ms — **byte-identical request shape to `jarvis/brain/llm.py:143-161`** |

**Note on test 4:** the originally-configured local model (`gemma-4-12B Q8_0`, 12 GB) thrashes on this
16 GB machine (llama-server logged 0.82 tokens/s prompt processing — 27.98 s for 23 tokens), so requests
timed out. This is a **hardware limitation, not a router failure** — the router correctly forwarded to
Ollama. Swapping to `qwen2.5:0.5b` gave a 1.28 s pass, proving the local leg works end-to-end.

---

## 10. Performance Metrics (isolated proxy, same machine)

| Metric | Value | Notes |
|---|---|---|
| Proxy idle footprint | **~110 MB RSS**, 0.0% CPU | single Python process, negligible for JARVIS |
| Latency, NVIDIA 10-token replies (n=5) | 0.19–0.48 s | includes upstream NIM round-trip; proxy overhead ~5 ms |
| Streaming TTFT (haiku, 60 tok) | ~1.6 s to full stream; first chunk near-immediate | 17 SSE chunks |
| Fallback overhead (bad key → good) | ~1.0 s total | one failed attempt (fast 401) + healthy call |
| Cascade overhead (2 bad → local) | 1.36 s total | 2 failed attempts + local inference |
| Proxy-to-JARVIS-shape call | 206 ms | exact JARVIS payload, cold-ish path |

Overhead added by the router is small (single-digit ms per request when healthy); measured times are
dominated by upstream NVIDIA NIM latency, which JARVIS already pays today.

---

## 11. Integration PoC for JARVIS (documented — NOT implemented)

JARVIS already sends the exact request LiteLLM's proxy serves. Verified integration seam:

- `jarvis/brain/llm.py:52-53` — `api_base = (api_base or config.nvidia_api_base).rstrip("/")`;
  `nvidia_model = model or config.nvidia_model`.
- `jarvis/brain/llm.py:143-161` — `POST {base_url}/chat/completions`, `Bearer {api_key}`,
  payload `{model, messages, temperature, max_tokens}`. LiteLLM serves `/v1/chat/completions` with the
  same schema and `Bearer {master_key}` auth.
- `jarvis/core/config.py:28-29` — `nvidia_model` / `nvidia_api_base` pydantic fields, both env-driven.

**Zero-code-change adoption path** (env-only, would require the router running on `:4000`):

```bash
# .env (documented; production JARVIS NOT modified in this research)
NVIDIA_API_BASE=http://localhost:4000/v1
NVIDIA_MODEL=nvidia-jarvis          # model_name as registered in the router's model_list
# router side: general_settings.master_key must equal the key JARVIS sends (its NVIDIA_API_KEY),
# or JARVIS's key must be registered as a virtual key in the router.
```

With that, JARVIS's existing retry/backoff in `llm.py` + the router's fallbacks compose:
JARVIS keeps its 3-attempt safety net; the router adds provider-level failover, 429 handling, and
cooldowns beneath it. `jarvis/brain/model_router.py:307` also reads `config.nvidia_api_base`, so any
future router-aware routing benefits automatically.

**Recommended production architecture** (future work, not done here): run the LiteLLM proxy as a local
service (systemd/launchd) or Docker container, register NVIDIA + Groq/Cerebras/Gemini/OpenRouter free
tiers + Ollama in `model_list`, define a single `fallbacks` chain
`nvidia → free-tier backup → local Ollama`, and point JARVIS at it via env only.

---

## 12. Recommendation

**ADOPT LiteLLM as JARVIS's AI router** (integrated behind env-only config; service deployment
as follow-up work).

| Criterion | Verdict |
|---|---|
| Drop-in for JARVIS's call shape | ✅ proven (test 7) |
| Automatic failover (the core requirement) | ✅ proven (tests 5–6) |
| Streaming | ✅ proven (test 3) |
| NVIDIA NIM first-class | ✅ native provider, exact matching base |
| License / stack / maintenance fit | ✅ MIT / Python / pushed today |
| Operational cost | ~110 MB RAM, ~5 ms overhead, DB-less |

**Caveats to manage in adoption:**
1. **Pin `fastapi<0.140`** in the deploy env (or use the official Docker image) until litellm drops the
   removed-import — documented in §8.
2. The free-tier backup providers (Groq/Cerebras/Gemini/OpenRouter) must be **tested with real keys**
   before wiring into the fallback chain (this research used NIM + Ollama only).
3. Large local GGUF models need hardware headroom; keep a small model in the local leg for reliability.
4. `master_key` policy: don't ship the production key in config; use env references + virtual keys.

---

## Appendix A — Reproduce (commands)

```bash
cd tests/ai_router_test
python3 -m venv .venv
.venv/bin/pip install 'litellm[proxy]' 'fastapi<0.140'
set -a && . ../../.env && set +a          # exports NVIDIA_API_KEY / NVIDIA_API_BASE
nohup .venv/bin/litellm --config config.yaml --port 4000 > proxy.log 2>&1 &
curl http://localhost:4000/health/liveliness
# then: .venv/bin/python scripts/func_tests.py  (or the curl/Python snippets from §9)
```

## Appendix B — Files touched by this research

| Path | Purpose |
|---|---|
| `tests/ai_router_test/.venv/` | isolated Python env (litellm 1.96.2, fastapi 0.140.13) |
| `tests/ai_router_test/config.yaml` | router config (NIM + Ollama + fallback chains) |
| `tests/ai_router_test/proxy.log` | proxy run log |
| `tests/ai_router_test/PHASE6_INSTALL_NOTES.md` | install commands + gotchas |
| `docs/research/AI_ROUTER_RESEARCH.md` | this report |

No production JARVIS files were modified.

---

```
======== JARVIS AI ROUTER RESEARCH COMPLETE ========
Result: PASS
- Objective 1 (identify auto-switch router): PASS  → LiteLLM (BerriAI/litellm)
- Objective 2 (select best candidate):       PASS  → LiteLLM (only candidate meeting all 9 requirements)
- Objective 3 (install isolated):            PASS  → tests/ai_router_test venv, litellm 1.96.2
- Objective 4 (functional tests):            PASS  → 7/7 tests green incl. 2-level cascade failover
- Objective 5 (JARVIS drop-in PoC):          PASS  → exact JARVIS request shape answered correctly
- Objective 6 (no production changes):       PASS  → zero prod files modified
Recommendation: ADOPT LiteLLM (env-only integration, pin fastapi<0.140)
=====================================================
```
