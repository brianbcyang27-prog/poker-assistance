# Human-Centered UI Research — JARVIS v8.0.0

## Design Philosophy

> Calm. Elegant. Fast. Premium. Alive.

Every decision in JARVIS v8.0.0 is grounded in established UX principles, not imitation of other products.

---

## 1. Apple Human Interface Guidelines

**Key Principles Applied:**
- **Clarity**: Text must be legible at all sizes. Use SF Pro family. Minimum 11px body text.
- **Deference**: UI shouldn't compete with content. The Golden Core IS the content — chrome must recede.
- **Depth**: Visual layers communicate hierarchy. Use backdrop-filter blur for glass panels.

**Implementation:**
- Sidebar: 60px collapsed icon rail (matches macOS Finder sidebar)
- Spacing follows 8pt grid (Apple standard)
- System colors with semantic meaning (green=success, amber=warning, red=error)
- Subtle vibrancy via `backdrop-filter: blur(20px) saturate(180%)`
- Title bar integrated into content, no separate chrome
- Dark mode as primary (matches developer tools aesthetic)

---

## 2. Google Material 3 / Material You

**Key Principles Applied:**
- **Dynamic Color**: System-wide color harmony from a single seed color
- **Elevation**: Shadow depth communicates interactive hierarchy
- **Motion**: Shared axis transitions for navigation, container transform for expand/collapse

**Implementation:**
- Seed color: `#00dcff` (cyan accent) — all semantic colors derived from this
- Elevation levels: 0 (flat), 1 (cards), 2 (sidebars), 3 (dialogs), 4 (modals)
- Container transform for workspace switching (not hard cuts)
- State layers: hover 4%, focus 8%, pressed 12%, dragged 16%

---

## 3. Linear.app Patterns

**Why Linear feels premium:**
- **Zero-latency perception**: Optimistic UI updates, skeleton loading, no loading spinners for <300ms
- **Keyboard-first**: Every action has a shortcut. Cmd+K command palette.
- **Visual density**: High information density without clutter — compact list items, subtle separators
- **Color restraint**: Mostly monochrome with one accent color used sparingly

**Implementation:**
- Skeleton loading states for all data fetches
- Cmd+K command palette (already exists — enhance it)
- Compact list items: 32px height, single-line text
- Color: cyan accent used only for interactive elements and active states
- Inline status badges instead of separate status pages

---

## 4. Raycast Patterns

**Key Patterns:**
- **Command Palette**: Cmd+K as primary navigation (already in JARVIS as command-palette.js)
- **Section Headers**: Uppercase, muted, small caps for category grouping
- **Subtle Selection**: Highlight background without borders
- **Detail Panel**: Right panel shows preview of selected item

**Implementation:**
- Enhance existing command-palette.js with fuzzy search
- Section headers: `font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted)`
- Selection: `background: var(--bg-active)` with no border change
- Right sidebar serves as detail panel (Phase 8)

---

## 5. Arc Browser Patterns

**Key Patterns:**
- **Spaces**: Virtual desktops for different contexts (work, personal, research)
- **Command Bar**: Omnibar that combines navigation + search + commands
- **Sidebar as navigation**: Vertical list with icon + label, collapsible
- **Boost**: User customization of web content

**Implementation:**
- Workspaces ARE spaces (Home, Chat, Projects, Research, Memory, Settings)
- Persistent input bar at bottom = command bar equivalent
- Left nav = Arc sidebar (icon + label, 60px width)
- User settings as personalization layer

---

## 6. Cursor IDE Patterns

**Key Patterns for AI Transparency:**
- **Diff View**: Show exactly what the AI changed
- **Streaming**: Real-time text appearance (already in JARVIS chat)
- **Tool Calls**: Visual cards showing which tool is running, duration, result
- **Plan Mode**: Show the AI's reasoning before execution

**Implementation:**
- Tool cards (Phase 12): Show tool name, purpose, duration, status, result
- Streaming chat (already exists) — enhance with word-by-word animation
- Mission timeline (Phase 11): Shows AI's plan and execution steps
- Reasoning display: Subtle expandable "Thinking..." with actual reasoning text

---

## 7. Claude (Anthropic) Patterns

**Key Patterns:**
- **Thinking Indicators**: "Thinking..." with subtle animation communicates processing
- **Clean Typography**: Large, readable text with generous line-height
- **Minimal Chrome**: Almost no UI elements compete with the conversation
- **Artifact Cards**: Side panels for code, documents, visualizations

**Implementation:**
- Neural Core states communicate what AI is doing (Phase 9)
- Typography: 14px body, 1.6 line-height for readability
- Chat messages: Generous padding (16px vertical), no avatar clutter
- Right sidebar for artifacts (Phase 8): tool outputs, research results, file previews

---

## 8. Cognitive Load Theory

**Principle:** Working memory holds 4±1 chunks. Every additional UI element competes for attention.

**Application to JARVIS:**
- **Navigation**: Max 6 primary items (Miller's Law applied to nav)
- **Information density**: Show summary first, detail on demand (progressive disclosure)
- **Visual grouping**: Related items proximity < 8px, unrelated > 24px
- **Consistent patterns**: Same action = same UI everywhere (recognition over recall)
- **Reduce choices**: One chat input, not multiple. One way to navigate, not three.

---

## 9. Fitts' Law

**Principle:** Time to reach a target = f(distance, size). Closer + bigger = faster.

**Application:**
- **Primary actions** at screen edges (nav sidebar on left edge, input at bottom edge)
- **Large click targets**: Min 32px height for buttons, 40px for primary actions
- **Keyboard shortcuts**: Cmd+1-6 for workspace switching (zero mouse travel)
- **Sticky input**: Chat input always in same position — muscle memory
- **Corner targets**: Settings gear in bottom-left corner (infinite edge = easiest to hit)

---

## 10. Hick's Law

**Principle:** Decision time = a + b × ln(choices). Fewer choices = faster decisions.

**Application:**
- **6 nav items** (not 10+): Home, Chat, Projects, Research, Memory, Settings
- **Dev mode**: Hides 4+ developer items behind toggle (reduces visible choices)
- **Command palette**: Type to filter (converts many choices into search)
- **Contextual actions**: Show relevant buttons only when relevant (not always visible)

---

## 11. Miller's Law

**Principle:** Average person can hold 7±2 chunks in working memory.

**Application:**
- **6 nav items** (within 7±2 range)
- **Settings sections**: Max 8 sections in settings sidebar
- **Chat history**: Show recent 20 conversations (scroll for more)
- **Tool cards**: Max 3 visible at a time (scroll for more)

---

## 12. Gestalt Principles

**Proximity:** Items within 8px are perceived as a group.
**Similarity:** Same visual treatment = same function (all buttons look like buttons).
**Continuity:** Visual flow follows reading direction (left→right, top→bottom).
**Closure:** Incomplete shapes perceived as complete (loading ring = circle).

**Application:**
- Nav items grouped by function (primary | dev | settings) with dividers
- All interactive elements share: border-radius, hover state, active state
- Content flows: nav → main → sidebar (left→right)
- Loading animation uses closure (partial ring perceived as full circle)

---

## 13. Progressive Disclosure

**Principle:** Show only what's needed now. Reveal complexity on demand.

**Application:**
- **Dev mode toggle**: Hides developer features until needed
- **Settings sections**: Collapsible cards within sections
- **Chat**: Simple input → slash commands for power users
- **Tool cards**: Collapsed by default (name + status), expand for logs
- **Right sidebar**: Collapsible panel, only shows when content is available

---

## 14. Peak-End Rule

**Principle:** People judge experience by the peak (most intense) and the end.

**Application:**
- **First impression**: Premium loading screen with golden core animation (Phase 2)
- **Last impression**: Graceful shutdown, "Goodbye" message, state preserved
- **Peak moments**: 
  - AI completes a task successfully (success animation on Neural Core)
  - First conversation exchange (streaming response feels alive)
  - Mission completion (celebratory micro-animation)

---

## 15. Visual Hierarchy

**Principle:** Guide the eye through importance. Size, color, contrast, position.

**Application (from most to least prominent):**
1. **Golden Core** — Largest, most colorful element. Always the focal point.
2. **Chat messages** — Primary content area. Large text, generous spacing.
3. **Navigation** — Visible but not competing. Muted colors, small icons.
4. **Status indicators** — Small, colored dots. Only noticed when relevant.
5. **Labels/tertiary text** — Muted, small. For metadata and timestamps.

**Typographic hierarchy:**
- H1: 24px, weight 700 (page titles)
- H2: 20px, weight 600 (section titles)
- H3: 16px, weight 600 (subsection titles)
- Body: 13px, weight 400 (default text)
- Caption: 11px, weight 400 (labels, timestamps)
- Micro: 10px, weight 500 (badges, uppercase labels)

---

## 16. Motion Psychology

**Principle:** Animation must communicate, not decorate.

**When animation helps:**
- **State changes**: Element appears/disappears (fade + scale)
- **Spatial relationships**: Moving between views (slide/translate)
- **Feedback**: Button press, action confirmation (micro-bounce)
- **Loading**: Progress indication (pulse, shimmer)
- **Celebration**: Task completion (subtle particle effect)

**When animation hurts:**
- Every hover state (too much noise)
- Page load delays (frustrating)
- Repeated elements animating in sequence (dizzying)
- Animation that blocks interaction

**Easing:**
- `ease-out` (deceleration): Elements entering view → `cubic-bezier(0.16, 1, 0.3, 1)`
- `ease-in` (acceleration): Elements leaving view → `cubic-bezier(0.4, 0, 1, 1)`
- `spring`: Playful interactions → `cubic-bezier(0.34, 1.56, 0.64, 1)`
- `linear`: Progress bars, continuous animations

**Durations:**
- Micro (hover, focus): 120ms
- Small (toggle, button): 200ms
- Medium (panel, sidebar): 350ms
- Large (workspace, page): 500ms

---

## 17. Trust in AI Systems

**Key factors:**
- **Transparency**: Show what the AI is doing, not just the result
- **Predictability**: Consistent behavior builds trust over time
- **Control**: User can always undo, cancel, or override
- **Competence**: Fast, accurate responses build confidence
- **Honesty**: Admit uncertainty ("I'm not sure" vs hallucinating)

**Application:**
- **Tool cards**: Show exactly which tool the AI is using and why
- **Mission timeline**: Show the AI's plan before execution
- **Error recovery**: Always show what went wrong and how to fix it
- **Neural Core states**: Communicate AI's current activity clearly
- **Confirmation for dangerous actions**: "Are you sure?" before destructive operations

---

## 18. Eye Tracking Research

**F-Pattern**: Users scan in F-shape on text-heavy pages.
- **Top bar**: Most important actions (workspace tabs)
- **Left side**: Navigation (icon rail)
- **Center**: Primary content
- **Right side**: Secondary/tertiary info

**Z-Pattern**: Users scan in Z-shape on visual pages.
- **Top-left**: Logo/brand (JARVIS)
- **Top-right**: Status/settings
- **Bottom-left**: Navigation
- **Bottom-right**: Actions (chat input)

**Gutenberg Diagram**: Primary optical area (top-left) gets most attention.
- **Golden Core**: Center of screen (breaks pattern intentionally — draws eye to the AI)

---

## Summary: JARVIS v8.0.0 Design Principles

| Principle | Implementation |
|-----------|---------------|
| Cognitive Load | 6 nav items max, progressive disclosure, dev mode toggle |
| Fitts' Law | Edge-mounted nav, large targets, keyboard shortcuts |
| Hick's Law | Command palette, contextual actions, filtered choices |
| Miller's Law | 6 nav, 8 settings sections, 20 recent conversations |
| Gestalt | Proximity grouping, similar styling, visual continuity |
| Progressive Disclosure | Dev mode, collapsible panels, expandable tool cards |
| Peak-End | Premium loading, success animations, graceful shutdown |
| Visual Hierarchy | Core > Content > Nav > Status > Labels |
| Motion Psychology | Purposeful animation, spring easing, 120-500ms durations |
| Trust | Tool transparency, mission plans, error recovery, confirmation |
| Eye Tracking | F-pattern nav, Z-pattern actions, center focal point |
