# JARVIS UI Foundation Audit

> **Purpose**: Stabilize the CSS/JS architecture before the v9.0.0 visual redesign.
> **Date**: 2026-07-30
> **Scope**: CSS architecture, component consistency, frontend technical debt
> **Base**: `style.css` (6428 lines, 41 sections), `app.js` (2195 lines), `base.html` (761 lines)

---

## 1. CSS Architecture Audit

### 1.1 Structure Overview

`style.css` is a single 6428-line file containing 41 sections. It has an excellent design-token foundation on top but suffers from accumulated structural debt.

| Metric | Value |
|--------|-------|
| Total lines | 6,428 |
| Named sections | 41 |
| `:root` blocks | 5 (only 1 should exist) |
| `@media` queries | 9 (multiple breakpoints) |
| Duplicate selectors | 15+ |
| Unused CSS variables | 64 (estimated) |
| Hardcoded values in components | ~120 occurrences |

### 1.2 The Five `:root` Blocks

Only the first `:root` (lines 8–216) is the canonical token definition. The rest should not exist as separate blocks:

| # | Line | Purpose | Verdict |
|---|------|---------|---------|
| 1 | 8 | **Canonical tokens** — brands, neutrals, spacing, radii, shadows, motion, z-index, breakpoints, layout | ✅ SSOT |
| 2 | 220 | **Light mode overrides** — inside `@media (prefers-color-scheme: light)` | ✅ Correct pattern |
| 3 | 261 | **Reduced motion** — inside `@media (prefers-reduced-motion: reduce)` | ✅ Correct pattern |
| 4 | 272 | **High contrast** — inside `@media (prefers-contrast: more)` | ✅ Correct pattern |
| 5 | 408 | **Legacy aliases** — flat `--bg-primary`, `--text-secondary`, `--accent`, `--shadow-sm` etc. | ⚠️ **Should be a single comment in tokens.css or eliminated** |

**Issues with Block #5 (Legacy Aliases, lines 408–464)**:
- Some aliases use invalid CSS syntax: `var(--color-brand-primary)1e` (line 430) and similar pattern on lines 432, 443 — the `1e`/`10`/`26` suffix is appended to a `var()` output, which is invalid CSS. These silently fail in all browsers.
- Introduced 30+ duplicate semantic paths (e.g., `--text-primary` = `--color-text-primary` — two ways to say the same thing).
- This block was previously "fixed" by removing self-referencing variables; the remaining aliases still pollute the global namespace.

### 1.3 Duplicate Selectors

The same selectors are defined in multiple places, creating specificity and maintenance issues:

| Selector | Appearances | Lines |
|----------|-------------|-------|
| `#dashboard` | 6 | ~460, ~610, ~6102, ~6111, plus grid, plus overflow |
| `#left-nav` | 3 | multiple spacing sets |
| `#right-panel` | 5 | display, width, padding, grid-col, media query |
| `.tool-card` | 3 | lines ~6134, plus 2 earlier versions |
| `.workspace-view` | 3 | + transition section + performance section |
| SCROLLBAR styles | 2 | lines ~1059 and ~3245 (identical block) |
| `.loading-step` | 2 | definition + animation target |
| `#chat-messages` | 2 | styles + scroll-behavior |

**Duplicate SCROLLBAR section** (lines 1059 and 3245):
- One is `/* SCROLLBAR — Premium minimal */` and the other is `/* Scrollbar */`
- They define identical `::-webkit-scrollbar` rules
- This wastes ~40 lines

### 1.4 Unused CSS Variables

Based on cross-referencing the `:root` block against all `var()` usage in style.css, the following tokens are **declared but never used**:

**Unused brand/color tokens:**
- `--color-brand-primary-hover`
- `--color-brand-primary-active`
- `--color-brand-secondary-hover`
- `--color-brand-tertiary` (Emerald)
- `--color-neutral-50`, `--color-neutral-100`, `--color-neutral-200`, `--color-neutral-300`, `--color-neutral-400`, `--color-neutral-600`, `--color-neutral-700`
- `--color-text-inverse`
- `--color-success-strong`, `--color-warning-strong`, `--color-danger-strong`
- `--color-info`, `--color-info-dim`
- `--color-spades`, `--color-hearts`, `--color-diamonds`, `--color-clubs`
- `--color-border-hairline`, `--color-border-emphasis`, `--color-border-focus-ring`, `--color-border-success`, `--color-border-warning`, `--color-border-danger`

**Unused typography tokens:**
- `--line-height-loose`
- `--letter-spacing-wider`, `--letter-spacing-widest`
- `--font-size-4xl`
- `--font-weight-regular`, `--font-weight-medium`

**Unused spacing tokens:**
- `--space-0`, `--space-px`, `--space-0-5`, `--space-1-5`, `--space-2-5`, `--space-3-5`, `--space-5`, `--space-7`, `--space-10`, `--space-12`, `--space-16`, `--space-20`, `--space-24`

**Unused border-radius tokens:**
- `--radius-none`, `--radius-px`, `--radius-xs`, `--radius-2xl`, `--radius-3xl`

**Unused shadow tokens:**
- `--shadow-4`, `--shadow-5`, `--shadow-6`, `--shadow-inner`, `--shadow-glow-sm`, `--shadow-glow-lg`, `--shadow-glow-gold`, `--shadow-glow-success`

**Unused motion tokens:**
- `--ease-linear`, `--ease-spring-sharp`, `--ease-bounce`
- `--duration-base`, `--duration-slowest`
- `--motion-exit`, `--motion-spring-gentle`

**Unused z-index tokens:**
- `--z-below`, `--z-raised`, `--z-popover`

**Unused breakpoint tokens:**
- `--bp-sm`, `--bp-md`, `--bp-lg`, `--bp-xl`, `--bp-2xl`

> **Note**: Unused tokens are not harmful but add maintenance overhead. They should be pruned after the v9.0 redesign stabilizes usage.

### 1.5 Hardcoded Values in Components

Despite a comprehensive token system, many components still use hardcoded values:

| Location | Hardcoded Value | Should Use |
|----------|----------------|------------|
| `.settings-content` | `padding: 32px` | `var(--space-8)` |
| `.settings-panel` | `padding: 24px` | `var(--space-6)` |
| `.settings-nav-item` | `padding: 10px 16px` | `var(--space-2-5) var(--space-4)` |
| `.settings-card` | `border-radius: 12px` | `var(--radius-lg)` |
| `.overlay` | `background: rgba(0, 0, 0, 0.6)` | `var(--color-bg-overlay)` |
| `.nav-btn` | `border-radius: 10px` | `var(--radius-md)` or `--radius-lg` |
| `.quick-action-btn` | `padding: 8px 14px` | `var(--space-2) var(--space-3-5)` |
| `.home-send-btn` | `width: 36px; height: 36px` | `var(--space-9)` (missing from scale) |
| `.mission-step-dot` | `width: 24px; height: 24px` | `var(--space-6)` |
| `.record-icon` | `width: 16px; height: 16px` | `var(--space-4)` |
| Various borders | `rgba(255,255,255,0.08)` | `var(--color-border-default)` |
| Various backgrounds | `rgba(0,0,0,0.2)` | `var(--color-bg-overlay)` variant |

### 1.6 Section Order Disorder

Current section order is chaotic — utility classes appear before the loading screen, the `#dashboard` grid is defined piecemeal across 6 locations, and v8.0 components (`.tool-card`, `.mission-timeline`) are tacked on at the end instead of grouped logically.

**Recommended section order for v9.0:**
```
1.  Design Tokens (→ tokens.css)       — SSOT
2.  Reset & Base                       — *, html, body
3.  Utility Classes                    — spacing, typography, borders, shadows
4.  Loading Screen                     — #loading-screen
5.  Layout Grid                        — #dashboard, #left-nav, #center-panel, #right-panel
6.  Navigation                         — #left-nav, .nav-btn, .nav-logo
7.  Workspace: Home                    — #home-container, .home-*
8.  Workspace: Chat                    — #chat-container, .chat-messages, #chat-sidebar
9.  Input Bar                          — #bottom-panel, #input-bar, #mic-btn
10. Right Panel                        — #right-panel, .right-context, .right-section
11. Settings Overlay                   — #settings-overlay, .settings-*
12. Components                         — .tool-card, .mission-timeline, .toast
13. Motion System                      — @keyframes, .anim-* classes
14. Media Queries                      — responsive @media blocks
15. Accessibility & Performance        — prefers-reduced-motion, contain hints
```

### 1.7 Media Query Fragmentation

9 media queries scattered across the file with 4 different breakpoint values:

| Location | Breakpoint | Purpose |
|----------|-----------|---------|
| Line 259 | `prefers-reduced-motion: reduce` | Accessibility |
| Line 271 | `prefers-contrast: more` | Accessibility |
| Line 219 | `prefers-color-scheme: light` | Light mode |
| ~1059 (inline) | `max-width: 768px` | Mobile scrollbar |
| Line ~6101 | `max-width: 1024px` | Tablet layout |
| Line ~6110 | `min-width: 1025px` | Desktop layout |
| Line ~6367 | `prefers-reduced-motion: reduce` | Duplicate reduced motion block |

The two `prefers-reduced-motion` blocks (lines 259–268 and 6367–6384) have **different implementations** — one changes CSS variable values, the other uses `!important` on animation/transition durations. This is a conflict.

---

## 2. Component Consistency Audit

### 2.1 Button System

| Button Class | Locations | Border Radius | Padding | Background | Hover | Disabled |
|-------------|-----------|---------------|---------|------------|-------|----------|
| `.nav-btn` | Nav sidebar | 10px | 10px 12px | Transparent | yes | **none** |
| `.btn-glass` | Timeline header | — | — | Glass | yes | **none** |
| `.input-icon-btn` | Input bar | 50%? | 8px | Transparent | yes | **none** |
| `.input-send-btn` | Input bar | full? | — | Cyan | yes | **none** |
| `.quick-action-btn` | Right panel | 8px | 8px 14px | Glass | yes | **none** |
| `.btn-action` | Settings | 8px | 8px 16px | Cyan | yes | has `:disabled` but no style |
| `.btn-save` | Settings | — | — | Cyan | yes | **none** |
| `.btn-reset` | Settings | — | — | Ghost | yes | **none** |
| `.btn-remove` | Voice profile | — | — | Ghost | yes | **none** |
| `.overlay-close` | Settings | — | — | Ghost | no | **none** |
| `.btn-record` | Voice | 50%? | — | Red | yes | **none** |

**Issues:**
- 11+ button variants with no shared base class
- No `:disabled` styling on any button
- Inconsistent border-radius (6px, 8px, 10px, full)
- Inconsistent hover effects (opacity vs background change vs none)

### 2.2 Card System

| Card Class | Border Radius | Border | Background | Padding |
|-----------|--------------|--------|------------|---------|
| `.settings-card` | 12px | 1px solid var(--border) | var(--bg-elevated) | — |
| `.tool-card` | var(--radius-md) | 1px solid var(--border) | var(--bg-panel) | 12px 16px |
| `.onboarding-feature` | — | — | — | — |
| `.home-section-title` | — | — | — | — |

No unified `.card` base class. Three separate card implementations with different visual characteristics.

### 2.3 Empty States

| Component | Has Empty State? | Quality |
|-----------|-----------------|---------|
| Chat messages | ❌ | Blank white space |
| Session list | ❌ | Empty `<div>` |
| Voice profiles list | ❌ | Empty `<div>` |
| Providers list | ❌ | Shows "Loading..." permanently if no data |
| Active tools | ✅ | "No tools in use" text |
| Memory references | ✅ | "Memory references will appear here" |
| Chat summary | ✅ | "Start a conversation to see summary" |

### 2.4 Missing CSS Classes

The following classes are referenced in HTML but have **no corresponding CSS rules**:

| Class | Used In | Likely Broken |
|-------|---------|---------------|
| `.status-text` | base.html (voice) | ✅ Rendered — unstyled |
| `.file-name` | base.html (voice upload) | ✅ Rendered — unstyled |
| `.status-message` | base.html (voice test) | ✅ Rendered — unstyled |
| `.status-indicator` | base.html (voice test) | ✅ Rendered — unstyled |
| Various `developer_dashboard` classes | developer_dashboard.html | ✅ Rendered — unstyled (~65 classes) |

---

## 3. Frontend Technical Debt (JS)

### 3.1 Undefined Functions (Dangling Calls)

These functions are **called from HTML but never defined in any JS file**:

| Function | Called In | Risk |
|----------|-----------|------|
| `loadSession()` | base.html (via onclick, though no direct onclick — check app.js) | ⚠️ Referenced but may be dead code path |
| `testCloneVoice()` | base.html voice section | ⚠️ Dead click handler |
| `deleteCloneProfile()` | base.html voice section | ⚠️ Dead click handler |

### 3.2 Event Listener Leaks

| Issue | Location | Impact |
|-------|----------|--------|
| `voice-test-text` input listener | `_loadSettings()` in app.js | **Each** settings load adds a new listener. 10 opens = 10 listeners firing |
| `setInterval(_refreshHealth, 10000)` | app.js startup | **Never cleared** — runs forever even if page/workspace changes |
| `window.addEventListener('keydown', ...)` for Cmd+K | app.js | Only added once (OK), but never removed on page unload |

### 3.3 Empty Catch Blocks

These error handlers silently swallow exceptions:

| Location | Code | Risk |
|----------|------|------|
| `sendMessage()` | `catch (e) {}` | Hides message send failures |
| `_loadHomeRecent()` | `catch (e) {}` | Hides API failures on home screen |
| `saveSettings()` | Multiple `catch (e) {}` | Hides settings save errors |
| WebSocket reconnect | `catch (e) {}` | Hides connection failures |
| `_refreshHealth()` | `catch (e) {}` | Hides health check failures |

### 3.4 Fragile DOM References

| Element ID | Referenced In | Risk |
|-----------|---------------|------|
| `#terminal-log` | app.js | No longer in base.html |
| `#vision-container` | app.js | No longer in base.html |
| `#computer-view` | app.js | May not exist |
| `#health-panel` | app.js | May not exist |
| `#health-kings`, `#health-workers` | app.js | May not exist |
| `#health-agent-count` | app.js | May not exist |

These are cross-page dead references from a previous layout that will throw `Cannot read properties of null` if their code paths are triggered.

### 3.5 API Endpoint Issues

| Endpoint in JS | Status | Notes |
|----------------|--------|-------|
| `GET /api/chat/sessions` | ✅ Fixed from `/api/sessions` | |
| `POST /api/voice/generate` | ⚠️ May be wrong path | Verify against backend router |
| `GET /api/settings` | ✅ Works | |
| `POST /api/settings` | ✅ Works | |

---

## 4. Priority Action Items for Stabilization

### P0 — Fix Now (Before v9.0 Redesign)

- [ ] **Fix event listener leak**: Debounce `voice-test-text` handler registration in `_loadSettings()`
- [ ] **Fix empty catch blocks**: Add `console.warn` at minimum to all empty catch clauses in `app.js`
- [ ] **Guard DOM references**: Wrap `#health-*`, `#terminal-*`, `#vision-*` references in existence checks
- [ ] **Guard `startVision()`**: Add null check for container element
- [ ] **Clear health interval**: Store `_refreshHealth` interval ID and clear on page navigation

### P1 — Structure (Pre-Redesign Preparation)

- [ ] **Declare tokens.css as SSOT**: Migrate style.css to `@import url('tokens.css')` in v9.0
- [ ] **Fix invalid CSS aliases**: Remove `var(--x)1e` pattern on lines 430, 432, 443 of style.css
- [ ] **Consolidate duplicate sections**: Remove duplicate scrollbar block, merge duplicate `.tool-card` definitions
- [ ] **Reconcile reduced-motion blocks**: Unify line 259 block (prefers CSS vars) with line 6367 block (uses !important)
- [ ] **Create `.btn` base class**: All button variants should extend a single base

### P2 — Polish (During v9.0 Redesign)

- [ ] **Prune unused CSS variables**: Remove ~64 unused tokens after redesign stabilizes usage
- [ ] **Replace hardcoded values**: Audit ~120 locations and replace with `var()` tokens
- [ ] **Add empty states**: Chat messages, session list, voice profiles, providers
- [ ] **Add `:disabled` styling**: Every button variant
- [ ] **Fix undefined functions**: `testCloneVoice()`, `deleteCloneProfile()` — either implement or remove
- [ ] **Reorder CSS sections**: Group logically per the recommended order in §1.6

---

## 5. Current Health Score

| Category | Score | Trend |
|----------|-------|-------|
| Token system completeness | 8/10 | ✅ Excellent foundation |
| Token usage in components | 4/10 | ⬇️ Hardcoded values everywhere |
| Section organization | 3/10 | ⬇️ Chaotic, many duplicates |
| CSS variable hygiene | 5/10 | → 4 :root blocks, unused vars |
| Button consistency | 3/10 | ⬇️ 11 variants, no base class |
| Card consistency | 4/10 | → Multiple implementations |
| JS error handling | 3/10 | ⬇️ Empty catches, dead refs |
| JS memory hygiene | 3/10 | ⬇️ Listener leaks, uncleared intervals |
| Empty states | 3/10 | → Mostly missing |
| **Overall Foundation** | **4/10** | → Needs structural cleanup before redesign |

---

*Next step: Execute P0 items, then proceed with v9.0.0 redesign plan.*
