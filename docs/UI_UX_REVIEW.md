# JARVIS UI/UX Review — July 2026

> Apple HIG compliance, competitive benchmarking, and UX gap analysis
> Target: Premium personal AI OS quality

---

## Executive Summary

JARVIS v7.x has strong technical foundations (223 endpoints, 67+ computer actions, voice I/O) but the UI still feels like a developer dashboard rather than a consumer product. Compared to Apple HIG and competitors like Cursor's Agents Window, the main gaps are:

1. **Too much chrome** — developer elements visible by default
2. **No permission UX** — critical safety gap with no user-facing controls
3. **Inconsistent design language** — mixed typography, spacing, color usage
4. **No empty/error/loading states** — poor first-run and failure experiences

**Overall: 5/10** — Up from 4/10 in v7.0 audit, but still needs polish.

---

## 1. Apple HIG Compliance Checklist

### Typography (Score: 5/10)
| HIG Principle | JARVIS Status | Fix |
|---------------|---------------|-----|
| SF Pro system font | Uses system font stack (close) | Verify `-apple-system` is primary |
| 3-level type hierarchy (Title/Body/Caption) | 6+ font sizes (9-20px) | Standardize to 3 sizes: 20/14/12 |
| Consistent weight usage | Mixed regular/medium/semibold | Use: Regular (body), Semibold (headings), Bold (actions) |
| Dynamic Type support | No | Add `rem`-based scaling |

### Color (Score: 6/10)
| HIG Principle | JARVIS Status | Fix |
|---------------|---------------|-----|
| Semantic color system | Semantic vars exist but overused accent | Add: `.text-primary`, `.text-secondary`, `.text-tertiary` |
| Contrast ratio ≥ 4.5:1 | `--text-secondary` at 0.6 opacity fails | Increase to 0.7 minimum |
| Vibrancy/translucency | Glass morphism present | Good — maintain |
| Dark mode (default) | Single dark theme | Add light mode toggle |

### Spacing (Score: 4/10)
| HIG Principle | JARVIS Status | Fix |
|---------------|---------------|-----|
| 8px grid system | Mixed: 4-32px gaps | Standardize to 4/8/12/16/24/32 |
| Consistent padding | Cards: 12-16px, Sections: 20-24px | Use 16px for cards, 24px for sections |
| Visual rhythm | No consistent vertical rhythm | Add `margin-bottom: 16px` between sections |

### Layout (Score: 5/10)
| HIG Principle | JARVIS Status | Fix |
|---------------|---------------|-----|
| Content-first | Developer panels always visible | Hide dev panels by default |
| Progressive disclosure | Everything shown at once | Add disclosure triangles for advanced options |
| Responsive | Fixed widths, no breakpoints | Add `@media` for tablet/phone |
| Collapsible sidebars | Right panel always visible | Make collapsible with animation |

### Interaction (Score: 4/10)
| HIG Principle | JARVIS Status | Fix |
|---------------|---------------|-----|
| Immediate feedback | Some actions have no feedback | Add loading states for all async operations |
| Spring animations | Basic CSS transitions | Add spring physics for natural feel |
| Haptic feedback | None | Add subtle haptics on critical actions |
| Keyboard shortcuts | Limited | Add Cmd+K command palette |

### Accessibility (Score: 3/10)
| HIG Principle | JARVIS Status | Fix |
|---------------|---------------|-----|
| Reduced motion | No `prefers-reduced-motion` | Add motion-reduced variants |
| Focus management | No focus traps in modals | Add focus trapping |
| ARIA labels | Minimal | Add to all interactive elements |
| Screen reader support | None | Add semantic HTML + ARIA |

---

## 2. Competitive UX Benchmarking

### vs. Cursor Agents Window
| Feature | Cursor | JARVIS | Gap |
|---------|--------|--------|-----|
| Task status cards | ✅ Planning → Executing → Reviewing → Done | ❌ Text-only mission log | HIGH |
| File diff previews | ✅ Inline diffs before apply | ❌ No diff preview | HIGH |
| Drag-to-reorder queue | ✅ Reorder while agent works | ❌ No task queue UI | MEDIUM |
| Background agent status | ✅ Persistent panel with progress | ⚠️ WebSocket exists but weak UI | MEDIUM |
| Checkpoint/restore | ✅ Snapshots before changes | ❌ No checkpoints | HIGH |

### vs. Claude Code Permission UX
| Feature | Claude Code | JARVIS | Gap |
|---------|-------------|--------|-----|
| Permission dialog | ✅ Inline approval with context | ❌ No permission UX | CRITICAL |
| Auto mode | ✅ ML classifier with visual indicator | ❌ No auto mode | CRITICAL |
| Depth indicator | ✅ Shows sub-agent nesting depth | ❌ No nesting visibility | MEDIUM |
| Context window display | ✅ Shows usage percentage | ⚠️ Memory graph only | LOW |

### vs. Manus Evidence Artifacts
| Feature | Manus | JARVIS | Gap |
|---------|-------|--------|-----|
| Screenshot proof | ✅ After each major action | ⚠️ Screenshot endpoint exists but not auto-captured | MEDIUM |
| Execution log | ✅ Timestamped action trail | ⚠️ Terminal log exists but hard to read | LOW |
| Cost display | ✅ Per-task cost tracking | ❌ No cost tracking | MEDIUM |

---

## 3. Critical UX Gaps (Must Fix for v7.6)

### Gap 1: No Permission UX
**Impact:** CRITICAL — users have no way to control what the AI can do
**Current:** All 67+ actions execute without user approval
**Fix:** Add permission panel with per-action-category toggles (allow/ask/deny)
**Pattern:** Follow Claude Code's 3-tier model but with visual UI instead of CLI flags

### Gap 2: No Checkpoint/Rollback UI
**Impact:** HIGH — users can't undo AI mistakes
**Current:** No way to see or restore previous states
**Fix:** Auto-checkpoint before mutations, show checkpoint list with restore button
**Pattern:** Roo Code's checkpoint system + Cursor's snapshot UX

### Gap 3: No Progress Indicators
**Impact:** HIGH — users don't know what the AI is doing
**Current:** WebSocket sends data but UI doesn't show structured progress
**Fix:** Add task card with status progression (Planning → Executing → Reviewing → Done)
**Pattern:** Cursor's Agents Window task cards

### Gap 4: Developer Dashboard by Default
**Impact:** MEDIUM — overwhelming for daily use
**Current:** Health panel, agent stream, terminal log all visible
**Fix:** Create "Clean Mode" that hides all dev elements, toggle with Cmd+Shift+D
**Pattern:** Apple's progressive disclosure + Cursor's clean default

---

## 4. Design System Gaps

### Missing Components
| Component | Status | Priority |
|-----------|--------|----------|
| Permission toggle | ❌ Doesn't exist | CRITICAL |
| Checkpoint card | ❌ Doesn't exist | HIGH |
| Task status card | ❌ Doesn't exist | HIGH |
| Loading skeleton | ❌ Doesn't exist | MEDIUM |
| Empty state | ❌ Mostly missing | MEDIUM |
| Error boundary | ❌ Basic alerts only | MEDIUM |
| Toast notifications | ❌ `os.notify` exists but no UI | LOW |
| Command palette | ❌ Doesn't exist | LOW |

### Inconsistent Components
| Component | Current State | Fix |
|-----------|---------------|-----|
| Buttons | 4+ styles (`.btn-action`, `.btn-save`, `.btn-reset`, `.btn-remove`) | Unified `.btn` with variants: primary, secondary, danger |
| Cards | 3+ styles (`.computer-card`, `.project-card`, `.metric-card`) | Unified `.card` with variants |
| Status dots | Multiple patterns | Unified `.status` with: online, warning, error, offline |
| Inputs | Mixed styling | Unified `.input` with states: default, focus, error, disabled |

---

## 5. Recommended Design System

### Typography Scale
```css
--text-title: 20px / 600 weight
--text-body: 14px / 400 weight  
--text-caption: 12px / 400 weight
```

### Spacing Scale
```css
--space-xs: 4px
--space-sm: 8px
--space-md: 12px
--space-lg: 16px
--space-xl: 24px
--space-2xl: 32px
```

### Color System
```css
--color-text-primary: rgba(255, 255, 255, 0.9)
--color-text-secondary: rgba(255, 255, 255, 0.7)  /* was 0.6 */
--color-text-tertiary: rgba(255, 255, 255, 0.5)
--color-accent: #00d4ff  /* keep as accent only */
--color-success: #34c759
--color-warning: #ff9500
--color-danger: #ff3b30
```

### Border Radius
```css
--radius-sm: 6px
--radius-md: 10px
--radius-lg: 16px
```

---

## 6. Implementation Priority

### Phase 1: Safety UX (Week 1)
1. Permission panel with per-action toggles
2. Checkpoint list with restore button
3. Step limit indicator

### Phase 2: Progress UX (Week 2)
4. Task status cards (Planning → Executing → Reviewing → Done)
5. Loading skeletons for all views
6. Empty states for all views

### Phase 3: Design System (Week 3)
7. Unified button/card/input components
8. Typography scale standardization
9. Spacing grid standardization
10. Color system cleanup

### Phase 4: Polish (Week 4)
11. Spring animations for transitions
12. Reduced motion support
13. Focus management for modals
14. Cmd+K command palette

---

*Compiled: 2026-07-25 | Target: v7.6.0 release*
