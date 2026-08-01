# JARVIS UI Component Status

> **Purpose**: Track consistency and state coverage for all UI components.
> **Date**: 2026-07-30
> **Base**: style.css (6428 lines), base.html (761 lines), app.js (2199 lines)

---

## 1. Button System

| Component | Selector(s) | Radius | Paddings | Hover | Active | Focus | Disabled | Loading | Notes |
|-----------|------------|--------|----------|-------|--------|-------|----------|---------|-------|
| Nav button | `.nav-btn` | 10px | 10px 12px | ✅ bg | ❌ | ❌ | ❌ | ❌ | 3 variants (default, active, settings) |
| Glass button | `.btn-glass` | — | — | ✅ | ❌ | ❌ | ❌ | ❌ | Used in timeline header |
| Mic button | `#mic-btn` | 8px | 8px | ✅ opacity | ❌ | ❌ | ❌ | ✅ ring anim | Has recording state animation |
| Send button | `#send-btn` | 8px | — | ✅ bg | ❌ | ❌ | ❌ | ❌ | Cyan fill on hover |
| Quick action | `.quick-action-btn` | 8px | 8px 14px | ✅ border | ❌ | ❌ | ❌ | ❌ | Right panel |
| Action button | `.btn-action` | 8px | 8px 16px | ✅ bg | ❌ | ❌ | ❌ | ❌ | Settings, voice profiles |
| Save button | `.btn-save` | — | — | ✅ | ❌ | ❌ | ❌ | ❌ | Settings form |
| Reset button | `.btn-reset` | — | — | ✅ | ❌ | ❌ | ❌ | ❌ | Ghost style |
| Remove button | `.btn-remove` | — | — | ✅ | ❌ | ❌ | ❌ | ❌ | Voice profile |
| Record button | `.btn-record` | 50% | — | ✅ | ❌ | ❌ | ❌ | ✅ | Has recording state |
| Close button | `.overlay-close` | — | — | ❌ | ❌ | ❌ | ❌ | ❌ | Settings overlay |
| Home send | `.home-send-btn` | 8px | 8px | ✅ bg | ❌ | ❌ | ❌ | ❌ | Home page |
| FAB | `#global-new-chat` | 50% | — | ✅ scale | ❌ | ❌ | ❌ | ❌ | Bottom-right |

**Issues:**
- **12 button variants**, zero share a common base class
- **No `:disabled` styling exists anywhere** — disabled buttons appear identical to enabled ones
- **No focus-visible ring** on any button (accessibility gap)
- **Inconsistent hover**: some use background change, some use opacity, some use scale, some have none

**Recommendation**: Create single `.btn` base class with modifier variants.

---

## 2. Card / Panel System

| Component | Border-Radius | Border | Background | Padding | Shadow | Hover Effect |
|-----------|--------------|--------|------------|---------|--------|-------------|
| Settings card | 12px | `var(--border)` | `var(--bg-elevated)` | — | ✅ shadow-1 | ❌ |
| Tool card | `var(--radius-md)` | `var(--border)` | `var(--bg-panel)` | 12px 16px | ❌ | ✅ border + bg |
| Mission step | — | — | — | — | — | ❌ |
| Onboarding feature | — | — | — | — | — | ❌ |
| Voice profile item | — | — | — | — | — | ❌ |
| Home list item | — | — | — | — | — | ❌ |

**Issues:**
- No unified `.card` base class
- `.settings-card` and `.tool-card` have different border-radius (12px vs var(--radius-md)=8px)
- Inconsistent padding patterns

---

## 3. Input System

| Component | Styling | Focus Ring | Autoresize | Placeholder | Disabled |
|-----------|---------|-----------|------------|-------------|----------|
| `#message-input` | Glass bg, border | ✅ cyan glow | ✅ | ✅ | ❌ |
| `#home-message-input` | Glass bg, border | ✅ cyan glow | ❌ | ✅ | ❌ |
| Voice textarea | Subdued bg | ✅ | ✅ | ❌ | ❌ |
| Settings inputs | Neutral border | ✅ cyan glow | ❌ | ✅ | ❌ |
| Settings search | Glass | ✅ | ❌ | ✅ | ❌ |

**Issues:**
- No disabled input styling
- No error state styling  
- Inputs have individual border-radius values rather than using `var(--radius-md)`

---

## 4. Navigation

| Element | Active State | Hover State | Transitions | Accessibility |
|---------|-------------|-------------|-------------|---------------|
| `.nav-btn` | ✅ Cyan bg + text | ✅ Subtle bg | ✅ All 0.18s | ✅ aria-label on nav items |
| `.nav-logo` | — | ❌ | ✅ Pulse anim | ❌ No label |
| `.nav-footer` | — | — | — | — |
| `#version-badge` | — | ❌ | ✅ | ❌ |

---

## 5. State Coverage Summary

| Component | Normal | Hover | Active | Focus | Disabled | Loading | Error | Empty |
|-----------|--------|-------|--------|-------|----------|---------|-------|-------|
| Buttons | 12/12 | 10/12 | 0/12 | 0/12 | **0/12** | 2/12 | 0/12 | N/A |
| Inputs | 5/5 | ❌ | ❌ | 5/5 | 0/5 | 0/5 | 0/5 | N/A |
| Cards | 4/4 | 1/4 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Nav items | 2/2 | 2/2 | 2/2 | ❌ | ❌ | ❌ | ❌ | N/A |
| Toasts | 1/1 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| Loading screen | 1/1 | N/A | N/A | N/A | N/A | N/A | ❌ | N/A |
| Empty states | — | — | — | — | — | — | — | 4/8 |

**Overall State Coverage: ~25%** — Most components only define the default state. Hover is inconsistently covered. Active, Focus, Disabled, Loading, and Error states are largely missing.

---

## 6. Animation State Coverage

| Component | Enter | Exit | State Change | Reduced Motion |
|-----------|-------|------|-------------|----------------|
| Loading screen | ✅ Fade out | ❌ | ❌ | ❌ |
| Workspace views | ✅ Fade | ❌ | ✅ Opacity | ✅ |
| Chat messages | ✅ chatFadeIn | ❌ | ❌ | ✅ (global) |
| Toast | ✅ Slide + fade | ✅ | ❌ | ✅ (global) |
| Tool cards | ❌ | ❌ | ❌ | ✅ (global) |
| Mission timeline | ❌ | ❌ | ❌ | ✅ (global) |
| Buttons | ❌ | ❌ | ❌ | ✅ (global) |

Global `prefers-reduced-motion: reduce` block exists at EOF but uses `!important` — conflicts with the CSS-variable-based reduced motion block at line 259.

---

## 7. Accessibility Audit

| Requirement | Status | Notes |
|-------------|--------|-------|
| Color contrast (text) | ⚠️ Partial | `--text-secondary` at 0.72 opacity may fail WCAG AA on dark bg |
| Focus visible | ⚠️ Partial | Inputs have glow ring, buttons don't |
| ARIA labels | ⚠️ Partial | Nav buttons have `title`, but no `aria-label` on icon-only buttons |
| Keyboard navigation | ⚠️ Partial | Tab order works, but no visible focus for buttons |
| Screen reader support | ❌ | No `role` or `aria-*` on dynamic panels |
| Reduced motion | ✅ | Two implementations (need unification) |
| Touch targets | ⚠️ | Some buttons < 44px (`.home-send-btn` is 36px) |

---

## 8. Component Inventory (Complete)

| Component | Lines in CSS | Lines in JS | Status |
|-----------|-------------|-------------|--------|
| Loading screen | ~70 | 0 | ✅ Stable |
| Left nav | ~80 | 0 | ✅ Stable |
| Home workspace | ~120 | ~80 | ⚠️ Partial (empty states missing) |
| Chat workspace | ~180 | ~250 | ⚠️ Partial (missing empty states, session UI) |
| Settings overlay | ~280 | ~200 | ⚠️ Partial (listener leak fixed) |
| Right panel | ~100 | ~50 | ⚠️ Partial (health panel not present in HTML) |
| Input bar | ~60 | ~20 | ✅ Stable |
| Tool cards (v8) | ~75 | 0 | ✅ Stable |
| Mission timeline (v8) | ~85 | ~100 | ✅ Stable |
| Voice workspace | ~200 | ~350 | ⚠️ Partial (features integrated into settings) |
| Command palette | ~40 | ~15 | ✅ Stable |
| Toast | ~20 | ~10 | ✅ Stable |
| Golden core container | ~30 | 0 | ✅ Stable (golden, never touch) |

---

*This document serves as the component reference for the v9.0.0 redesign planning.*
