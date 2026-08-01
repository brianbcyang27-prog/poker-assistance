# JARVIS Design System — Architecture & Design Specification

**Version:** 1.0.0  
**Status:** Research & Specification Phase  
**Date:** 2025-07-31  
**Classification:** Internal — Design System Authority

---

## Executive Summary

This document establishes the authoritative design system for JARVIS v8+, synthesizing research from Apple Human Interface Guidelines (HIG), VisionOS spatial computing patterns, Arc Browser's command-centric UX, Raycast's keyboard-first workflow, Linear's opinionated product design, Notion AI's contextual intelligence, Perplexity's answer-first architecture, and The Founder's OS's operational clarity.

**Design Philosophy:** *Calm Intelligence* — Interfaces that feel inevitable, not impressive. Every pixel serves cognition; every animation serves understanding; every interaction builds trust.

---

## Part I: Foundational Design Tokens

### 1.1 Spacing System — The 4px Golden Grid

**Base Unit:** 4px (matches iOS/macOS touch targets and VisionOS spatial grid)

```css
:root {
  /* Spatial Scale — Exponential for breathing room */
  --space-0: 0;
  --space-1: 4px;    /* 1×  — Hairline, inline gaps */
  --space-2: 8px;    /* 2×  — Tight related elements */
  --space-3: 12px;   /* 3×  — Component internal padding */
  --space-4: 16px;   /* 4×  — Standard component gap */
  --space-5: 20px;   /* 5×  — Card padding */
  --space-6: 24px;   /* 6×  — Section spacing */
  --space-7: 32px;   /* 8×  — Major section breaks */
  --space-8: 40px;   /* 10× — Page margins */
  --space-9: 48px;   /* 12× — Hero sections */
  --space-10: 64px;  /* 16× — Full-screen breathing */
  
  /* Semantic Aliases — Use these, not raw values */
  --space-inline: var(--space-1);
  --space-tight: var(--space-2);
  --space-card: var(--space-5);
  --space-section: var(--space-7);
  --space-page: var(--space-8);
  --space-hero: var(--space-10);
}
```

**Rationale:** 4px base aligns with Apple's point grid, ensures crisp rendering on all displays, and creates harmonic vertical rhythm. Semantic aliases prevent design drift.

---

### 1.2 Typography — SF Pro + JetBrains Mono System

```css
:root {
  /* Font Families */
  --font-sans: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', system-ui, sans-serif;
  --font-mono: 'SF Mono', 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  
  /* Fluid Type Scale — clamp(min, preferred, max) */
  --text-2xs: clamp(0.625rem, 0.6rem + 0.125vw, 0.6875rem);   /* 10-11px — Labels, timestamps */
  --text-xs:  clamp(0.6875rem, 0.65rem + 0.1875vw, 0.75rem);   /* 11-12px — Captions, metadata */
  --text-sm:  clamp(0.75rem, 0.7rem + 0.25vw, 0.8125rem);      /* 12-13px — Secondary UI */
  --text-base: clamp(0.8125rem, 0.75rem + 0.3125vw, 0.875rem); /* 13-14px — Body text */
  --text-md:  clamp(0.875rem, 0.8rem + 0.375vw, 0.9375rem);    /* 14-15px — Emphasized body */
  --text-lg:  clamp(1rem, 0.9rem + 0.5vw, 1.125rem);           /* 16-18px — Headings, cards */
  --text-xl:  clamp(1.25rem, 1.1rem + 0.75vw, 1.5rem);         /* 20-24px — Section titles */
  --text-2xl: clamp(1.5rem, 1.3rem + 1vw, 2rem);               /* 24-32px — Page titles */
  --text-3xl: clamp(2rem, 1.7rem + 1.5vw, 3rem);               /* 32-48px — Hero headlines */
  --text-4xl: clamp(3rem, 2.5rem + 2.5vw, 5rem);               /* 48-80px — Display */
  
  /* Font Weights */
  --weight-regular: 400;
  --weight-medium: 500;
  --weight-semibold: 600;
  --weight-bold: 700;
  
  /* Line Heights — Tight for UI, relaxed for reading */
  --leading-tight: 1.15;    /* Headlines, buttons */
  --leading-snug: 1.35;     /* UI text, labels */
  --leading-normal: 1.5;    /* Body text */
  --leading-relaxed: 1.65;  /* Long-form reading */
  --leading-code: 1.7;      /* Code blocks */
  
  /* Letter Spacing */
  --tracking-tight: -0.02em;    /* Large headlines */
  --tracking-normal: 0;         /* Default */
  --tracking-wide: 0.01em;      /* Small caps, labels */
  --tracking-wider: 0.05em;     /* Button text, codes */
}
```

**Semantic Text Styles (Use these combinations):**

| Style | Size | Weight | Leading | Tracking | Use Case |
|-------|------|--------|---------|----------|----------|
| `display` | 4xl | 700 | tight | tight | Hero, empty states |
| `h1` | 3xl | 700 | tight | tight | Page titles |
| `h2` | 2xl | 600 | tight | normal | Section headers |
| `h3` | xl | 600 | snug | normal | Card titles |
| `h4` | lg | 600 | snug | normal | Subsections |
| `body-lg` | md | 400 | normal | normal | Primary content |
| `body` | base | 400 | normal | normal | Standard text |
| `body-sm` | sm | 400 | snug | normal | Secondary text |
| `caption` | xs | 400 | snug | wide | Metadata, timestamps |
| `overline` | 2xs | 500 | tight | wider | Category labels |
| `button` | sm | 500 | tight | wider | Interactive elements |
| `code` | sm | 400 | code | normal | Inline code |
| `code-block` | sm | 400 | code | normal | Code blocks |
| `mono-lg` | base | 400 | code | normal | Terminal output |

**Rationale:** Fluid scaling ensures readability from 320px mobile to 32" 6K displays. SF Pro matches system UI for familiarity; JetBrains Mono provides superior code legibility with ligatures.

---

### 1.3 Color System — Semantic, Accessible, Dark-First

```css
:root {
  /* === BRAND COLORS — Minimal, Purposeful === */
  --brand-primary: #00D4FF;        /* Cyan — Primary actions, links, focus */
  --brand-primary-hover: #00B8E0;
  --brand-primary-active: #009CC4;
  --brand-primary-subtle: rgba(0, 212, 255, 0.12);
  
  --brand-gold: #F5A623;           /* Gold — Neural core, premium, warnings */
  --brand-gold-hover: #E0941E;
  --brand-gold-subtle: rgba(245, 166, 35, 0.12);
  
  --brand-emerald: #34D399;        /* Emerald — Success, online, confirmed */
  --brand-emerald-subtle: rgba(52, 211, 153, 0.12);
  
  /* === NEUTRAL SCALE — 13 Steps for Precision === */
  --neutral-0: #FFFFFF;            /* Pure white */
  --neutral-50: #F8FAFC;
  --neutral-100: #F1F5F9;
  --neutral-200: #E2E8F0;
  --neutral-300: #CBD5E1;
  --neutral-400: #94A3B8;
  --neutral-500: #64748B;
  --neutral-600: #475569;
  --neutral-700: #334155;
  --neutral-800: #1E293B;
  --neutral-900: #0F172A;
  --neutral-950: #080D16;          /* Deepest dark — Canvas base */
  
  /* === SEMANTIC BACKGROUNDS (Dark Mode Native) === */
  --bg-canvas: var(--neutral-950);           /* App background */
  --bg-base: var(--neutral-900);             /* Cards, panels */
  --bg-elevated: var(--neutral-800);         /* Modals, dropdowns */
  --bg-overlay: rgba(8, 13, 22, 0.92);       /* Sheets, drawers */
  --bg-glass: rgba(15, 23, 42, 0.72);        /* Frosted glass */
  --bg-glass-strong: rgba(15, 23, 42, 0.88); /* Strong glass */
  --bg-hover: rgba(255, 255, 255, 0.04);     /* Hover states */
  --bg-active: rgba(255, 255, 255, 0.08);    /* Active/pressed */
  --bg-selected: var(--brand-primary-subtle); /* Selection */
  --bg-danger: rgba(248, 113, 113, 0.12);    /* Destructive */
  
  /* === SEMANTIC BORDERS === */
  --border-hairline: rgba(255, 255, 255, 0.04);
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.08);
  --border-emphasis: rgba(255, 255, 255, 0.12);
  --border-focus: var(--brand-primary);
  --border-focus-ring: rgba(0, 212, 255, 0.35);
  --border-brand: rgba(0, 212, 255, 0.2);
  --border-success: rgba(52, 211, 153, 0.2);
  --border-warning: rgba(245, 166, 35, 0.2);
  --border-danger: rgba(248, 113, 113, 0.2);
  
  /* === SEMANTIC TEXT === */
  --text-primary: rgba(248, 250, 252, 0.94);    /* Headlines, primary */
  --text-secondary: rgba(203, 213, 225, 0.72);  /* Body, descriptions */
  --text-tertiary: rgba(148, 163, 184, 0.56);   /* Captions, hints */
  --text-quaternary: rgba(100, 116, 139, 0.44); /* Disabled, placeholders */
  --text-inverse: var(--neutral-950);           /* On colored backgrounds */
  --text-brand: var(--brand-primary);           /* Links, brand */
  --text-success: #4ADE80;                      /* Success states */
  --text-warning: #FBBF24;                      /* Warning states */
  --text-danger: #F87171;                       /* Error states */
  
  /* === DEPARTMENT COLORS (Card Suit System) === */
  --dept-engineering: #00D4FF;   /* ♠ Spades — Cyan */
  --dept-personal: #F472B6;      /* ♥ Hearts — Pink */
  --dept-research: #FBBF24;      /* ♦ Diamonds — Amber */
  --dept-system: #4ADE80;        /* ♣ Clubs — Emerald */
  
  /* === STATE SEMANTICS === */
  --state-idle: var(--neutral-500);
  --state-listening: var(--brand-primary);
  --state-thinking: var(--brand-gold);
  --state-working: #A855F7;      /* Purple — Active processing */
  --state-complete: var(--brand-emerald);
  --state-error: var(--text-danger);
}
```

**Light Mode Override (Automatic via `prefers-color-scheme`):**

```css
@media (prefers-color-scheme: light) {
  :root {
    --bg-canvas: var(--neutral-50);
    --bg-base: var(--neutral-0);
    --bg-elevated: var(--neutral-50);
    --bg-overlay: rgba(255, 255, 255, 0.95);
    --bg-glass: rgba(255, 255, 255, 0.8);
    --bg-glass-strong: rgba(255, 255, 255, 0.92);
    --bg-hover: rgba(8, 13, 22, 0.04);
    --bg-active: rgba(8, 13, 22, 0.08);
    --bg-selected: var(--brand-primary-subtle);
    
    --border-hairline: rgba(8, 13, 22, 0.06);
    --border-subtle: rgba(8, 13, 22, 0.08);
    --border-default: rgba(8, 13, 22, 0.12);
    --border-emphasis: rgba(8, 13, 22, 0.16);
    
    --text-primary: rgba(8, 13, 22, 0.94);
    --text-secondary: rgba(30, 41, 59, 0.72);
    --text-tertiary: rgba(71, 85, 105, 0.56);
    --text-quaternary: rgba(100, 116, 139, 0.44);
    --text-inverse: var(--neutral-0);
  }
}
```

**Accessibility Guarantees:**
- All semantic colors meet WCAG AA (4.5:1) on their designated backgrounds
- Focus ring always visible (3px, brand-primary, 0.35 opacity)
- Color never sole carrier of meaning (icons + text + color)
- Reduced motion respected via `prefers-reduced-motion`

---

### 1.4 Motion System — Spring Physics, Purposeful Animation

```css
:root {
  /* === EASING CURVES === */
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);      /* Spring — Default for UI */
  --ease-spring-gentle: cubic-bezier(0.25, 1.2, 0.5, 1);  /* Gentle spring — Cards */
  --ease-spring-snappy: cubic-bezier(0.4, 1.4, 0.6, 1);   /* Snappy — Buttons, toggles */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);              /* Ease out — Entrances */
  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);               /* Ease in — Exits */
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);            /* Standard — Transitions */
  --ease-linear: linear;                                   /* Linear — Progress, loading */
  
  /* === DURATION SCALE === */
  --duration-instant: 0ms;          /* Immediate — Color changes */
  --duration-fast: 80ms;            /* Micro — Button press, checkbox */
  --duration-normal: 150ms;         /* Standard — Hover, focus, small panels */
  --duration-smooth: 250ms;         /* Smooth — Modals, drawers, cards */
  --duration-slow: 350ms;           /* Deliberate — Page transitions */
  --duration-hero: 500ms;           /* Hero — Onboarding, major reveals */
  
  /* === SPRING PRESETS (for JS animations) === */
  --spring-default: "stiffness: 300, damping: 30, mass: 1";        /* General UI */
  --spring-gentle: "stiffness: 180, damping: 22, mass: 1";         /* Cards, panels */
  --spring-snappy: "stiffness: 450, damping: 28, mass: 0.8";       /* Buttons, toggles */
  --spring-bouncy: "stiffness: 280, damping: 18, mass: 1";         /* Celebration, success */
  --spring-damped: "stiffness: 200, damping: 35, mass: 1.2";       /* Heavy drawers */
}

/* Reduced Motion — Respect user preference */
@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-fast: 0ms;
    --duration-normal: 0ms;
    --duration-smooth: 0ms;
    --duration-slow: 0ms;
    --duration-hero: 0ms;
  }
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Animation Principles:**

| Principle | Implementation |
|-----------|----------------|
| **Motion serves meaning** | Entrance = "appearing"; Exit = "dismissing"; Transition = "changing context" |
| **Staggered choreography** | 20-40ms stagger for lists; parent before children |
| **Spring defaults** | Use spring for position/scale; ease-out for opacity/color |
| **No gratuitous motion** | Loading spinners only when >300ms; skeleton screens preferred |
| **Spatial consistency** | Elements enter from their logical source (sidebar from left, modal from center) |

---

### 1.5 Border Radius System

```css
:root {
  --radius-none: 0;
  --radius-xs: 4px;      /* Chips, badges, small buttons */
  --radius-sm: 8px;      /* Inputs, buttons, cards */
  --radius-md: 12px;     /* Panels, modals, dropdowns */
  --radius-lg: 16px;     /* Sheets, major cards */
  --radius-xl: 24px;     /* Hero cards, onboarding */
  --radius-full: 9999px; /* Pills, avatars, FABs */
  
  /* Semantic */
  --radius-input: var(--radius-sm);
  --radius-button: var(--radius-sm);
  --radius-card: var(--radius-md);
  --radius-panel: var(--radius-lg);
  --radius-modal: var(--radius-lg);
  --radius-sheet: var(--radius-xl);
  --radius-fab: var(--radius-full);
}
```

---

### 1.6 Shadow & Elevation System

```css
:root {
  /* Layered shadows for depth perception */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.3);           /* Hairline — Inline elements */
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.35);          /* Subtle — Cards at rest */
  --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.4);          /* Elevated — Hovered cards */
  --shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.45);        /* Modal — Sheets, drawers */
  --shadow-xl: 0 24px 64px rgba(0, 0, 0, 0.5);         /* Hero — Onboarding, empty */
  
  /* Colored shadows for brand moments */
  --shadow-brand: 0 8px 32px rgba(0, 212, 255, 0.25);   /* Primary actions */
  --shadow-gold: 0 8px 32px rgba(245, 166, 35, 0.25);   /* Neural core, premium */
  --shadow-danger: 0 8px 32px rgba(248, 113, 113, 0.25); /* Destructive */
  
  /* Inner shadows for depth */
  --shadow-inset: inset 0 1px 2px rgba(255, 255, 255, 0.05);
  --shadow-inset-strong: inset 0 2px 8px rgba(0, 0, 0, 0.3);
}
```

**Elevation Map:**

| Elevation | Shadow | Use Case |
|-----------|--------|----------|
| 0 (Canvas) | None | App background |
| 1 (Base) | xs | Cards, panels at rest |
| 2 (Raised) | sm | Hovered cards, focused inputs |
| 3 (Floating) | md | Dropdowns, tooltips, popovers |
| 4 (Modal) | lg | Sheets, drawers, modals |
| 5 (Hero) | xl | Onboarding, empty states |

---

### 1.7 Z-Index Scale

```css
:root {
  --z-base: 0;           /* Canvas content */
  --z-raised: 10;        /* Hovered cards */
  --z-sticky: 20;        /* Sticky headers */
  --z-dropdown: 30;      /* Dropdowns, popovers */
  --z-drawer: 40;        /* Side drawers */
  --z-modal: 50;         /* Modals, sheets */
  --z-toast: 60;         /* Toasts, notifications */
  --z-tooltip: 70;       /* Tooltips */
  --z-onboarding: 80;    /* Onboarding overlay */
  --z-debug: 9999;       /* Debug tools only */
}
```

---

## Part II: Component Architecture

### 2.1 Button System — Hierarchical, Accessible

```css
.btn {
  /* Base */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-wider);
  border: none;
  border-radius: var(--radius-button);
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-spring-snappy);
  white-space: nowrap;
  user-select: none;
}

/* === Variants === */
.btn-primary {
  background: var(--brand-primary);
  color: var(--text-inverse);
  box-shadow: var(--shadow-brand);
}
.btn-primary:hover { background: var(--brand-primary-hover); }
.btn-primary:active { background: var(--brand-primary-active); transform: scale(0.98); }
.btn-primary:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--border-focus-ring); }

.btn-secondary {
  background: var(--bg-elevated);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}
.btn-secondary:hover { background: var(--bg-hover); border-color: var(--border-emphasis); }
.btn-secondary:active { background: var(--bg-active); transform: scale(0.98); }

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}
.btn-ghost:hover { background: var(--bg-hover); color: var(--text-primary); }
.btn-ghost:active { background: var(--bg-active); transform: scale(0.98); }

.btn-danger {
  background: var(--text-danger);
  color: var(--text-inverse);
  box-shadow: var(--shadow-danger);
}
.btn-danger:hover { background: #E03E3E; }
.btn-danger:active { transform: scale(0.98); }

/* === Sizes === */
.btn-sm { padding: var(--space-1) var(--space-3); font-size: var(--text-xs); gap: var(--space-1); }
.btn-lg { padding: var(--space-3) var(--space-6); font-size: var(--text-base); gap: var(--space-2); }

/* === States === */
.btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none !important; }
.btn-loading { position: relative; color: transparent !important; }
.btn-loading::after {
  content: "";
  width: 16px; height: 16px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s var(--ease-linear) infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

**Button Hierarchy (Per View):**
- **1 Primary** — Main action
- **2-3 Secondary** — Supporting actions  
- **Unlimited Ghost** — Tertiary, contextual
- **0-1 Danger** — Destructive only

---

### 2.2 Input System — Calm, Forgiving, Informative

```css
.input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
}

.input-label {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.input-field {
  width: 100%;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--text-primary);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-input);
  padding: var(--space-3) var(--space-4);
  transition: all var(--duration-fast) var(--ease-out);
}

.input-field::placeholder { color: var(--text-quaternary); }

.input-field:hover { border-color: var(--border-emphasis); }
.input-field:focus {
  outline: none;
  border-color: var(--brand-primary);
  box-shadow: 0 0 0 3px var(--border-focus-ring);
  background: var(--bg-base);
}
.input-field:disabled { opacity: 0.5; cursor: not-allowed; }
.input-field[aria-invalid="true"] {
  border-color: var(--text-danger);
  box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.2);
}
.input-field[aria-invalid="true"]:focus {
  box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.35);
}

.input-hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.input-hint.error { color: var(--text-danger); }
.input-hint.success { color: var(--text-success); }

/* Textarea — Auto-resize */
.textarea-field {
  min-height: 100px;
  resize: vertical;
  font-family: var(--font-mono);
  line-height: var(--leading-code);
}

/* Search Input — Special variant */
.search-input {
  padding-left: var(--space-10);
  background-image: url("data:image/svg+49...");
  background-position: var(--space-3) center;
  background-repeat: no-reppeat;
  background-size: 18px;
}
```

---

### 2.3 Card System — Glass, Elevated, Interactive

```css
.card {
  background: var(--bg-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-normal) var(--ease-spring-gentle);
  overflow: hidden;
}

.card-glass {
  background: var(--bg-glass);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--border-subtle);
}

.card:hover {
  border-color: var(--border-default);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card-interactive {
  cursor: pointer;
}
.card-interactive:active { transform: translateY(0) scale(0.99); }

.card-selected {
  border-color: var(--brand-primary);
  box-shadow: 0 0 0 2px var(--brand-primary), var(--shadow-md);
}

/* Card Sections */
.card-header { padding: var(--space-5) var(--space-5) var(--space-3); border-bottom: 1px solid var(--border-hairline); }
.card-body { padding: var(--space-5); }
.card-footer { padding: var(--space-3) var(--space-5) var(--space-5); border-top: 1px solid var(--border-hairline); display: flex; justify-content: flex-end; gap: var(--space-2); }
```

---

### 2.4 Navigation — Command-Centric, Spatial

**Left Rail (Persistent, Collapsible):**

```css
.nav-rail {
  position: fixed;
  left: 0; top: 0; bottom: 0;
  width: var(--nav-width, 72px);
  background: var(--bg-base);
  border-right: 1px solid var(--border-hairline);
  display: flex;
  flex-direction: column;
  z-index: var(--z-sticky);
  transition: width var(--duration-smooth) var(--ease-spring);
}

.nav-rail.expanded { --nav-width: 240px; }

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  color: var(--text-tertiary);
  border-radius: var(--radius-md);
  margin: var(--space-1) var(--space-2);
  transition: all var(--duration-fast) var(--ease-spring-snappy);
  white-space: nowrap;
  text-decoration: none;
}
.nav-item:hover { background: var(--bg-hover); color: var(--text-primary); }
.nav-item.active { background: var(--bg-selected); color: var(--brand-primary); }
.nav-item .icon { flex-shrink: 0; width: 20px; height: 20px; }
.nav-item .label { opacity: 0; transform: translateX(-10px); transition: all var(--duration-fast); }
.nav-rail.expanded .nav-item .label { opacity: 1; transform: translateX(0); }
```

**Command Palette (⌘K — Central Nervous System):**

```css
.cmd-palette {
  position: fixed;
  top: 15%; left: 50%; transform: translateX(-50%);
  width: min(640px, 90vw);
  background: var(--bg-overlay);
  backdrop-filter: blur(40px) saturate(180%);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  z-index: var(--z-modal);
  overflow: hidden;
}

.cmd-input {
  width: 100%;
  font-size: var(--text-lg);
  background: transparent;
  border: none;
  padding: var(--space-4) var(--space-5);
  color: var(--text-primary);
}
.cmd-input::placeholder { color: var(--text-tertiary); }

.cmd-results { max-height: 400px; overflow-y: auto; }
.cmd-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  color: var(--text-secondary);
  transition: background var(--duration-instant);
}
.cmd-item:hover, .cmd-item.selected { background: var(--bg-hover); color: var(--text-primary); }
.cmd-item .shortcut { margin-left: auto; color: var(--text-quaternary); font-size: var(--text-xs); }
```

---

### 2.5 Feedback System — Toast, Inline, Progressive

```css
/* Toast — Non-blocking, auto-dismiss */
.toast {
  position: fixed;
  bottom: var(--space-6); right: var(--space-6);
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-toast);
  animation: toast-in var(--duration-smooth) var(--ease-spring);
  max-width: 400px;
}
@keyframes toast-in {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.toast.success { border-left: 3px solid var(--text-success); }
.toast.warning { border-left: 3px solid var(--text-warning); }
.toast.error { border-left: 3px solid var(--text-danger); }
.toast.info { border-left: 3px solid var(--brand-primary); }

/* Inline Alert — Contextual, persistent */
.alert {
  display: flex; align-items: flex-start; gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid;
}
.alert.info { background: var(--brand-primary-subtle); border-color: var(--border-brand); color: var(--text-primary); }
.alert.success { background: var(--brand-emerald-subtle); border-color: var(--border-success); color: var(--text-primary); }
.alert.warning { background: var(--brand-gold-subtle); border-color: var(--border-warning); color: var(--text-primary); }
.alert.error { background: rgba(248, 113, 113, 0.12); border-color: var(--border-danger); color: var(--text-primary); }
.alert .icon { flex-shrink: 0; margin-top: 2px; }
.alert .content { flex: 1; }
.alert .title { font-weight: var(--weight-semibold); margin-bottom: var(--space-1); }
.alert .message { font-size: var(--text-sm); color: var(--text-secondary); }
.alert .dismiss { flex-shrink: 0; color: var(--text-tertiary); }

/* Progressive Disclosure — Reveal complexity on demand */
.disclosure {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.disclosure-summary {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  background: var(--bg-base);
  transition: background var(--duration-fast);
}
.disclosure-summary:hover { background: var(--bg-hover); }
.disclosure-summary .chevron { transition: transform var(--duration-normal) var(--ease-spring); }
.disclosure[open] .disclosure-summary .chevron { transform: rotate(180deg); }
.disclosure-content { padding: var(--space-4); border-top: 1px solid var(--border-hairline); animation: disclosure-open var(--duration-smooth) var(--ease-out); }
@keyframes disclosure-open {
  from { opacity: 0; max-height: 0; }
  to { opacity: 1; max-height: 500px; }
}
```

---

## Part III: AI Feedback Principles

### 3.1 Visibility of System Status (Jakob Nielsen + AI Context)

| AI State | Visual Signal | Duration | Location |
|----------|---------------|----------|----------|
| **Idle** | Golden core breathing (1.5s cycle) | Continuous | Center canvas |
| **Listening** | Core pulse accelerates (2x), cyan ring expands | While mic active | Core + mic button |
| **Thinking** | Core rotates, particles converge, gold→amber shift | 0.5-30s | Core |
| **Planning** | Rings separate, neural pulses increase, grid forms | 1-10s | Core + timeline panel |
| **Working** | Pulses travel paths, agents light up in rail | Active duration | Core + agent avatars |
| **Verifying** | Green check ripples, connections highlight | 0.5-5s | Core + verification panel |
| **Complete** | Golden burst → settle to idle, subtle haptic | 2s | Core + toast |
| **Error** | Red flash → pulse → return to idle | 3s | Core + inline alert |

**Core Principle:** *The neural core IS the status indicator.* No separate loading spinners. The core's behavior communicates state through motion, color, and particle choreography.

---

### 3.2 Trust-Building Patterns

| Pattern | Implementation | Rationale |
|---------|----------------|-----------|
| **Show the Work** | Expandable reasoning trace for every AI response | Users trust what they can inspect |
| **Cite Sources** | Inline citations with hover preview for research | Verifiable claims build credibility |
| **Confidence Indicators** | Subtle % badge on AI assertions (>80% only) | Calibrated trust, not false precision |
| **Reversible Actions** | All AI actions undoable within 30s | Safety encourages exploration |
| **Explainable Decisions** | "Why this approach?" affordance on every output | Mental model alignment |
| **Graceful Degradation** | "I'm not confident — here's what I need" vs hallucination | Honesty > false competence |

---

### 3.3 Cognitive Load Reduction

| Technique | Implementation |
|-----------|----------------|
| **Progressive Disclosure** | Show 1 action → reveal next after completion |
| **Smart Defaults** | Pre-fill from context (project, recent, patterns) |
| **Chunked Workflows** | Max 3 steps visible; "Continue" reveals next chunk |
| **Contextual Help** | Inline `?` icons → popover with 1-sentence + "Learn more" |
| **Keyboard-First** | Every action accessible via ⌘K palette + shortcuts |
| **Spatial Memory** | Panels remember position, size, state per project |
| **Predictive Prefetch** | Load next likely view in background |

---

## Part IV: Project Visualization — Living Projects

### 4.1 Project Dashboard (Not "Sessions" — Projects)

**Mental Model:** *Projects are living workspaces, not chat histories.*

```
┌─────────────────────────────────────────────────────────────┐
│  PROJECT: "Q3 Autonomous Refactor"        [● Active]  [⋮]  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────┐ │
│  │  MISSIONS   │ │  ARTIFACTS  │ │  DECISIONS  │ │ INSIGHTS │
│  │    12/47    │ │    23       │ │     8       │ │    5     │
│  │  ████░░ 25% │ │  📄 📊 💻   │ │  ✅ ⚠️ 🔄   │ │  💡 📈   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────┘ │
├─────────────────────────────────────────────────────────────┤
│  RECENT ACTIVITY                                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 2m ago    ✅ Mission "Extract API Contracts" complete │ │
│  │ 15m ago   🔄 Mission "Analyze Dependency Graph" 67%   │ │
│  │ 1h ago    💡 Insight: "Circular deps in auth module"  │ │
│  │ 3h ago    📝 Decision: "Adopt gRPC for internal APIs" │ │
│  └───────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [New Mission]  [View Timeline]  [Export Report]  [Share]  │
└─────────────────────────────────────────────────────────────┘
```

**Key Concepts:**
- **Mission** = Goal-directed work unit (plan → execute → verify → reflect)
- **Artifact** = Durable output (code, doc, diagram, decision record)
- **Decision** = Recorded choice with rationale, alternatives, owner
- **Insight** = Synthesized learning, auto-extracted or manual

---

### 4.2 Mission Timeline — Spatial, Not Linear

```mermaid
timeline
    title Mission: "Implement Auth Refactor"
    
    section Plan
      09:00 : Goal received
      09:01 : Planner decomposed into 7 tasks
      09:02 : Dependencies mapped
    
    section Execute
      09:03 : Researcher → API contracts extracted
      09:05 : Coder → Interface definitions written
      09:08 : Executor → Tests generated
      09:12 : Reviewer → Security audit passed
    
    section Verify
      09:15 : All 7 tasks verified ✅
      09:16 : Integration test passed ✅
    
    section Reflect
      09:18 : Reflection: "gRPC migration saved 40% latency"
      09:19 : Skill extracted: "Auth migration pattern"
      09:20 : Mission complete
```

**Visualization Principles:**
- **Spatial layout** — Time flows vertically; parallel tracks horizontal
- **Agent swimlanes** — Each agent = column; shows parallelism
- **State glyphs** — ● pending, ◐ active, ✅ done, ⚠️ issue, ❌ failed
- **Zoomable** — Day → Hour → Minute → Second granularity
- **Filterable** — By agent, state, tag, outcome

---

### 4.3 Agent Visualization — Transparent Delegation

```css
.agent-avatar {
  width: 32px; height: 32px;
  border-radius: var(--radius-full);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-xs); font-weight: var(--weight-bold);
  border: 2px solid var(--bg-canvas);
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-fast) var(--ease-spring);
}

/* Department colors */
.agent-avatar.engineering { background: var(--dept-engineering); color: var(--text-inverse); }
.agent-avatar.personal { background: var(--dept-personal); color: var(--text-inverse); }
.agent-avatar.research { background: var(--dept-research); color: var(--text-inverse); }
.agent-avatar.system { background: var(--dept-system); color: var(--text-inverse); }

/* States */
.agent-avatar.idle { opacity: 0.5; }
.agent-avatar.active { 
  animation: agent-pulse 1.5s var(--ease-spring) infinite;
  box-shadow: 0 0 0 2px currentColor, var(--shadow-md);
}
.agent-avatar.complete { opacity: 1; }
.agent-avatar.error { background: var(--text-danger); animation: none; }

@keyframes agent-pulse {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 currentColor, var(--shadow-sm); }
  50% { transform: scale(1.05); box-shadow: 0 0 0 4px transparent, var(--shadow-md); }
}

/* Agent Rail — Right sidebar */
.agent-rail {
  position: fixed; right: 0; top: 0; bottom: 0;
  width: 280px;
  background: var(--bg-base);
  border-left: 1px solid var(--border-hairline);
  display: flex; flex-direction: column;
  overflow-y: auto;
  z-index: var(--z-drawer);
}
.agent-section { padding: var(--space-4); border-bottom: 1px solid var(--border-hairline); }
.agent-section-title { font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--text-tertiary); text-transform: uppercase; letter-spacing: var(--tracking-wider); margin-bottom: var(--space-3); }
.agent-list { display: flex; flex-direction: column; gap: var(--space-2); }
.agent-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  transition: background var(--duration-fast);
}
.agent-item:hover { background: var(--bg-hover); }
.agent-info { flex: 1; min-width: 0; }
.agent-name { font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.agent-task { font-size: var(--text-xs); color: var(--text-tertiary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.agent-progress { font-size: var(--text-2xs); color: var(--brand-primary); font-variant-numeric: tabular-nums; }
```

---

## Part V: Domain Architecture Improvements

### 5.1 Current Domain Issues

| Issue | Impact | Evidence |
|-------|--------|----------|
| **Session-centric** | Treats work as ephemeral chats | Users lose context across "sessions" |
| **Flat agent hierarchy** | No visual distinction between Kings/Workers | Hard to understand delegation flow |
| **Implicit state** | Mission state only in SSE, not persisted | Refresh loses context |
| **No artifact lineage** | Can't trace output → mission → goal | Auditability gap |
| **Single-threaded UI** | One mission at a time | Blocks parallel work |

---

### 5.2 Recommended Architecture: Living Projects + Mission Graph

```
┌────────────────────────────────────────────────────────────────┐
│                        PROJECT (Persistent)                     │
│  • Identity, metadata, members, settings                       │
│  • Timeline (append-only event log)                            │
│  • Artifact registry (code, docs, decisions, insights)        │
└────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌────────────┐  ┌────────────┐  ┌────────────┐
       │  MISSION   │  │  MISSION   │  │  MISSION   │
       │  (Active)  │  │  (Queued)  │  │ (Complete) │
       └────────────┘  └────────────┘  └────────────┘
              │               │               │
       ┌──────┴──────┐        │        ┌──────┴──────┐
       ▼             ▼        │        ▼             ▼
    PLAN          EXECUTE     │      ARTIFACTS    DECISIONS
    (DAG)         (Stream)    │      (Registry)   (Log)
       │             │        │        │             │
       ▼             ▼        │        ▼             ▼
    VERIFY      REFLECT      │    INSIGHTS     SKILLS
       │             │        │        │             │
       └─────────────┴────────┴────────┴─────────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │   KNOWLEDGE GRAPH  │
                    │  (Cross-project)   │
                    └────────────────────┘
```

**Key Changes:**

1. **Project = First-class entity** (not session)
   - Persistent across browser restarts
   - Owned by user/team, not tied to browser tab
   - Has settings, members, integrations

2. **Mission = DAG, not Linear**
   - Explicit dependency graph (planner outputs)
   - Parallel execution visible in UI
   - Partial completion = valid state

3. **Artifact Registry**
   - Every output registered with metadata
   - Versioned, searchable, referenceable
   - Links back to mission + agent + step

4. **Decision Log**
   - Explicit decisions with rationale
   - Alternatives considered
   - Revisit triggers (time, new info)

5. **Cross-Project Knowledge Graph**
   - Entities: People, Components, Patterns, Decisions
   - Relationships: Owns, Depends, Implements, Decided
   - Queryable: "Who owns auth?" "What patterns for migrations?"

---

### 5.3 Data Model (TypeScript Interfaces)

```typescript
// Core Entities
interface Project {
  id: string;
  name: string;
  description: string;
  owner: UserRef;
  members: ProjectMember[];
  settings: ProjectSettings;
  createdAt: Date;
  updatedAt: Date;
  archivedAt?: Date;
}

interface Mission {
  id: string;
  projectId: string;
  goal: string;
  status: MissionStatus; // 'planning' | 'executing' | 'verifying' | 'reflecting' | 'complete' | 'failed' | 'paused'
  plan?: PlanDAG;
  timeline: MissionEvent[]; // Append-only
  artifacts: ArtifactRef[];
  decisions: DecisionRef[];
  insights: InsightRef[];
  startedAt: Date;
  completedAt?: Date;
  parentMissionId?: string; // For sub-missions
}

interface PlanDAG {
  nodes: PlanNode[];
  edges: PlanEdge[];
  entryPoints: string[]; // Node IDs
}

interface PlanNode {
  id: string;
  type: 'task' | 'milestone' | 'gate';
  name: string;
  description: string;
  agentRole: AgentRole; // 'planner' | 'researcher' | 'coder' | 'executor' | 'reviewer' | 'human'
  inputs: Record<string, any>;
  expectedOutput: OutputSchema;
  dependencies: string[]; // Node IDs
  status: NodeStatus;
  assignedAgentId?: string;
  startedAt?: Date;
  completedAt?: Date;
  output?: any;
  verification?: VerificationResult;
}

interface Artifact {
  id: string;
  projectId: string;
  missionId?: string;
  type: 'code' | 'document' | 'diagram' | 'decision' | 'insight' | 'skill';
  title: string;
  content: string; // or reference to storage
  version: number;
  tags: string[];
  createdBy: AgentRef | UserRef;
  createdAt: Date;
  updatedAt: Date;
  lineage: ArtifactLineage; // What produced this
}

interface Decision {
  id: string;
  projectId: string;
  missionId?: string;
  question: string;
  context: string;
  options: DecisionOption[];
  chosen: string;
  rationale: string;
  decidedBy: UserRef;
  decidedAt: Date;
  revisitTriggers: RevisitTrigger[];
  status: 'active' | 'superseded' | 'revisited';
}

interface Insight {
  id: string;
  projectId: string;
  missionId?: string;
  type: 'pattern' | 'learning' | 'metric' | 'risk' | 'opportunity';
  title: string;
  description: string;
  confidence: number; // 0-1
  evidence: ArtifactRef[];
  extractedBy: AgentRef;
  extractedAt: Date;
  applicableContexts: string[]; // Tags for reuse
}

interface Skill {
  id: string;
  name: string;
  description: string;
  steps: SkillStep[];
  trigger: SkillTrigger;
  successRate: number;
  useCount: number;
  createdFromMission: string;
  createdAt: Date;
  lastUsedAt: Date;
}
```

---

## Part VI: UX Patterns for Trust & Cognitive Load

### 6.1 Onboarding — Progressive, Contextual

| Phase | Trigger | Content | Dismissal |
|-------|---------|---------|-----------|
| **Welcome** | First visit | 3-screen carousel: Chat, Code, Control | "Get Started" |
| **First Mission** | User sends first request | Inline: "I'll plan this → execute → verify" | Auto after mission complete |
| **Architecture Switch** | User opens Settings → Architecture | Tooltip: "Hermes = planning; Native = direct" | Dismiss or switch |
| **Command Palette** | User hovers ⌘K hint | "⌘K opens everything — missions, agents, settings" | First use |
| **Golden Core** | Idle > 30s | Subtle: "The core shows my state. Click to inspect." | Click or dismiss |

**Principle:** *Teach at point of need, not upfront.*

---

### 6.2 Error States — Honest, Actionable

```css
/* Error Pattern: What happened + Why + What to do */
.error-state {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-4);
  padding: var(--space-8);
  text-align: center;
}
.error-icon { width: 48px; height: 48px; color: var(--text-danger); }
.error-title { font-size: var(--text-lg); font-weight: var(--weight-semibold); color: var(--text-primary); }
.error-message { font-size: var(--text-base); color: var(--text-secondary); max-width: 400px; }
.error-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; justify-content: center; }
.error-details {
  width: 100%; max-width: 600px;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  background: var(--bg-canvas);
  border: 1px solid var(--border-danger);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  text-align: left;
  overflow-x: auto;
}
```

**Error Message Template:**
> **Title:** Connection to LLM failed  
> **Message:** The model endpoint returned a timeout after 30s. This usually means the request was too complex or the service is busy.  
> **Actions:** [Retry with simpler request] [Switch to faster model] [Check status page]  
> **Details:** `GET https://api.nvidia.com/v1/chat/completions → 504 Gateway Timeout`

---

### 6.3 Empty States — Guiding, Not Blaming

| Context | Empty State | Primary Action |
|---------|-------------|----------------|
| **No Projects** | "Start your first project" — illustration of project card | [Create Project] |
| **No Missions** | "Projects come alive with missions" — animated mission flow | [New Mission] |
| **No Artifacts** | "Missions produce artifacts" — show example artifact types | [Run a Mission] |
| **No Search Results** | "Nothing matches '...'" — suggest broader terms | [Clear Filters] |
| **No Agents Active** | "Agents appear when missions run" — show idle agent grid | [Start Mission] |
| **Error History Empty** | "No errors — smooth sailing!" — subtle celebration | — |

---

### 6.4 Loading — Skeleton Over Spinners

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-elevated) 25%,
    var(--bg-hover) 50%,
    var(--bg-elevated) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s var(--ease-in-out) infinite;
  border-radius: var(--radius-sm);
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Skeleton Variants */
.skeleton-text { height: 1rem; margin-bottom: var(--space-2); }
.skeleton-text:last-child { width: 70%; }
.skeleton-card { height: 200px; border-radius: var(--radius-card); }
.skeleton-avatar { width: 32px; height: 32px; border-radius: var(--radius-full); }
.skeleton-button { height: 36px; width: 120px; border-radius: var(--radius-button); }
```

**Rule:** Show skeleton immediately (<100ms). Replace with real content as it arrives. No spinners unless >3s.

---

## Part VII: Interaction Patterns — Reference

### 7.1 Keyboard Shortcuts (Canonical)

| Shortcut | Action | Context |
|----------|--------|---------|
| `⌘K` | Open Command Palette | Global |
| `⌘N` | New Mission | Project view |
| `⌘/` | Focus Chat Input | Global |
| `⌘⇧K` | Open Command Palette (History) | Global |
| `⌘1-4` | Switch Workspace (Home/Chat/Settings/Project) | Global |
| `⌘J` | Toggle Agent Rail | Chat/Project |
| `⌘M` | Toggle Memory Panel | Chat |
| `⌘⇧M` | Toggle Mission Panel | Chat |
| `Esc` | Close Modal/Drawer/Palette | Any |
| `Tab` / `⇧Tab` | Navigate Focusable | Forms/Palette |
| `Enter` | Activate/Submit | Buttons/Inputs |
| `⌘Enter` | Send Message (Multi-line) | Chat Input |
| `↑/↓` | Navigate List | Palette/History |
| `⌘.` | Cancel Current Operation | Mission/Streaming |

---

### 7.2 Mouse/Touch Interactions

| Gesture | Action | Feedback |
|---------|--------|----------|
| Click | Activate/Select | Ripple (100ms) |
| Double-click | Rename/Edit | Inline editor appears |
| Right-click | Context Menu | Menu at cursor |
| Drag (Card) | Reorder/Move | Ghost + drop zones |
| Drag (Agent) | Reassign Task | Target highlights |
| Hover (Agent) | Show Tooltip | 200ms delay |
| Long Press (Touch) | Context Menu | Haptic + menu |
| Swipe (Touch) | Dismiss/Archive | Spring animation |

---

### 7.3 Voice Interaction

| Trigger | Behavior |
|---------|----------|
| `Hey JARVIS` / Click Mic | Start listening → Core shows listening state |
| Speak | Real-time waveform in core + transcript preview |
| Pause >1.5s | Auto-submit → Core shows thinking |
| "Cancel" / Click Mic | Abort → Core returns to idle |
| Error | Core flashes red → Speak "I didn't catch that" |

---

## Part VIII: Implementation Roadmap

### Phase 1: Foundations (Week 1-2)
- [ ] Design token system (CSS custom properties)
- [ ] Base components: Button, Input, Card, Toast
- [ ] Color system with dark/light auto-switch
- [ ] Motion primitives (spring, easing, reduced motion)
- [ ] Typography scale + font loading

### Phase 2: Navigation & Layout (Week 2-3)
- [ ] Collapsible Nav Rail with labels
- [ ] Command Palette (⌘K) with fuzzy search
- [ ] Workspace Switcher (Home/Chat/Project/Settings)
- [ ] Responsive layout (Mobile drawer, Desktop rail)
- [ ] Agent Rail (Right sidebar)

### Phase 3: Project & Mission UI (Week 3-5)
- [ ] Project Dashboard with metrics
- [ ] Mission Timeline (Spatial DAG view)
- [ ] Mission Panel (Plan/Execute/Verify/Reflect tabs)
- [ ] Artifact Registry Browser
- [ ] Decision Log View
- [ ] Agent Visualization (Avatars, Swimlanes)

### Phase 4: AI Feedback & Trust (Week 4-5)
- [ ] Golden Core State Choreography
- [ ] Streaming Chat with Token/Tool/Reasoning
- [ ] Inline Citations + Source Preview
- [ ] Confidence Indicators
- [ ] Expandable Reasoning Traces
- [ ] Error States with Actions

### Phase 5: Polish & Systems (Week 5-6)
- [ ] Empty/Loading/Error States
- [ ] Keyboard Shortcuts Help (⌘⇧?)
- [ ] Onboarding Flow
- [ ] Accessibility Audit (WCAG AA)
- [ ] Performance Budget (<100ms interactions)
- [ ] Design Token Documentation Site

---

## Appendix: Design Decision Log

| Date | Decision | Rationale | Alternatives Considered |
|------|----------|-----------|------------------------|
| 2025-07-31 | 4px base spacing | Aligns with Apple point grid, crisp on all displays | 8px (too coarse), 5px (fractional pixels) |
| 2025-07-31 | SF Pro + JetBrains Mono | System familiarity + code excellence | Inter (good but not system), Fira Code (no SF fallback) |
| 2025-07-31 | Cyan primary + Gold accent | Cyan = tech/trust; Gold = neural core/premium | Blue (generic), Purple (AI cliché) |
| 2025-07-31 | Spring physics default | Feels alive, matches VisionOS | CSS transitions (mechanical), Framer Motion (heavy) |
| 2025-07-31 | Project > Session | Work is persistent, not ephemeral | Session-based (current), Workspace-based (vague) |
| 2025-07-31 | Mission = DAG | Real work is parallel with dependencies | Linear (simple but wrong), Tree (too rigid) |
| 2025-07-31 | Core = Status | Single source of truth, spatial | Status bar (hidden), Toast (transient), Badge (small) |

---

**Document Status:** Ready for Review  
**Next Step:** Stakeholder Review → Phase 1 Implementation  
**Owner:** Design Engineering  
**Reviewers:** Product, Engineering, AI Research