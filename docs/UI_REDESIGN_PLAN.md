# JARVIS UI Redesign Plan

## Vision
Transform JARVIS from a developer dashboard into a calm, intelligent, futuristic personal AI operating system with Apple-level design quality.

**Core Identity:** The Golden 3D Neural Core is PERMANENT - it is the soul of JARVIS.

---

## Design Principles

### 1. Calm Technology
- Technology recedes into background until needed
- Peripheral awareness over central demand
- Golden Core = ambient status indicator
- Agent Stream = peripheral mission awareness

### 2. Contextual Interface
- Single adaptive view, not fixed dashboard
- Panels appear/disappear based on mission type
- No duplicated functionality

### 3. Mission-Based Interaction
- Every request = mission with goal, plan, execution, verification
- Visible progress through mission lifecycle
- Tool transparency at every step

### 4. Trust Through Transparency
- Show reasoning, sources, confidence
- Human approval gates for sensitive actions
- Verification visible for every tool result

### 4. Futuristic Professional
- Deep space aesthetic (not dark mode, but *space* mode)
- Cyan/gold accent system
- Spring physics motion
- Precision typography

---

## Architecture

### Layer System (Z-Depth)
```
Layer -1: Golden Core (fixed, WebGL canvas)
Layer 0:  Background (deep space gradient)
Layer 1:  Contextual Panels (translucent cards, blur)
Layer 2:  Tool Cards (inline, elevated)
Layer 3:  Modals/Overlays (full focus)
Layer 4:  Toasts/Notifications (top)
```

### State Machine (Golden Core)
```
Idle → Listening → Thinking → Planning → Executing → Verifying → Success/Error
     ↖___________________________________________________↙
```

Each state has:
- Core visual (color, pulse, rotation, particles)
- Panel behavior (slide, fade, resize)
- Audio feedback (subtle)
- Haptic (if supported)

---

## Workspace Redesign

### Current (6 documented, 4 implemented)
| Workspace | Status | Issues |
|-----------|--------|--------|
| Home | ✅ | Duplicated chat input |
| Chat | ✅ | Basic, no mission view |
| Dashboard | ✅ | Cluttered, dev-tool feel |
| Settings | ✅ | Functional but utilitarian |
| Agents | ❌ | Not implemented |
| Research | ❌ | Not implemented |
| Memory | ❌ | Not implemented |
| Command Center | ❌ | Not implemented |

### New Workspace Model (Contextual, not Fixed)

**Primary Views (adaptive):**

1. **Home / Idle** - Golden Core + single natural language input
   - No chat history visible
   - Agent Stream peripheral (right)
   - Quick actions: Research, Code, Computer, Memory

2. **Conversation** - Chat + Agent Stream
   - Full-width conversation
   - Right sidebar: Agent Stream (collapsible)
   - Mission cards inline for complex requests

3. **Research** - Sources (left) + Synthesis (center) + Agent Stream (right)
   - Three-panel layout
   - Source cards with citations
   - Synthesis updates in real-time

4. **Coding** - Files (left) + Editor/Diff (center) + Tests/Logs (right)
   - IDE-like but lighter
   - Live preview for web
   - Test results inline

5. **Computer** - Screen view (center) + Action log (right) + Controls (bottom)
   - Remote desktop feel
   - Action cards with approval gates
   - Safety overlay

6. **Memory** - Knowledge Graph (center) + Search/Filter (left) + Details (right)
   - Force-directed graph (WebGL)
   - Semantic clusters
   - Temporal navigation

7. **Agents** - Hierarchy Tree (left) + Details (right)
   - Interactive card hierarchy
   - Real-time state indicators
   - Drill-down to worker details

8. **Settings** - Categorized, searchable, with architecture switcher
   - AI Architecture panel
   - Model configuration
   - Permissions
   - Appearance
   - Advanced

---

## Component Library

### Core Components

| Component | Purpose | States |
|-----------|---------|--------|
| `GoldenCore` | Identity anchor | 8 states |
| `MissionCard` | Request → plan → result | planning/executing/verifying/done |
| `ToolCard` | Tool execution transparency | pending/running/success/error |
| `AgentCard` | Worker/King representation | idle/busy/error/offline |
| `AgentStream` | Real-time delegation feed | live/paused/filtered |
| `SourceCard` | Research citation | loading/loaded/error |
| `FileCard` | Code file representation | clean/modified/conflict |
| `DiffView` | Code changes | unified/split |
| `KnowledgeGraph` | Memory visualization | cluster/temporal/search |
| `SettingsPanel` | Configuration | collapsed/expanded |

### Design Tokens (from design-tokens.css)
```css
--color-bg-deepest: #080d16
--color-bg-deep: #0d1420
--color-bg-elevated: #111a2a
--color-bg-card: #142038
--color-brand-primary: #00d4ff
--color-brand-secondary: #ffd700
--color-success: #30d158
--color-warning: #ff9f0a
--color-error: #ff453a

--font-sans: 'SF Pro Display', -apple-system, system-ui
--font-mono: 'SF Mono', 'Monaco', monospace

--space-1: 4px ... --space-8: 32px
--radius-sm: 8px --radius-lg: 16px
--shadow-1: 0 1px 3px ... --shadow-3: 0 12px 40px

--duration-fast: 150ms --duration-normal: 220ms --duration-slow: 350ms
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1)
--ease-out: cubic-bezier(0.16, 1, 0.3, 1)
```

---

## Motion Design

### Spring Physics (Framer Motion style)
- Damping: 0.8 (slightly bouncy, feels alive)
- Stiffness: 180 (responsive)
- Mass: 1

### Staggered Entrance
- Panel: 0ms
- Section headers: 50ms
- Content items: 100ms + index * 20ms
- Golden Core state change: immediate

### Micro-interactions
- Button press: scale(0.98), 100ms
- Hover card: translateY(-2px), shadow-2, 150ms
- Toggle: spring, 200ms
- Input focus: ring expansion, 150ms
- Toast: slide + fade, 300ms

### Reduced Motion
- All animations → 0ms or simple fade
- Respects `prefers-reduced-motion`

---

## Implementation Phases

### Phase 1: Foundation (Week 1) ✅ PARTIAL
- [x] Design tokens (design-tokens.css)
- [x] Animation system (animations.css)
- [x] Architecture switcher in Settings
- [ ] Golden Core state machine integration
- [ ] Panel system (slide/fade)

### Phase 2: Core Views (Week 2)
- [ ] Home/Idle view
- [ ] Conversation view (chat + agent stream)
- [ ] Mission card component
- [ ] Tool card component
- [ ] Agent card component

### Phase 3: Specialized Views (Week 3)
- [ ] Research view (3-panel)
- [ ] Coding view (files + diff + tests)
- [ ] Computer view (screen + actions)
- [ ] Memory view (knowledge graph)
- [ ] Agents view (hierarchy tree)

### Phase 4: Polish (Week 4)
- [ ] Settings redesign
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Performance optimization
- [ ] Cross-browser testing
- [ ] Documentation

---

## Technical Requirements

### Frontend Stack
- Vanilla JS (no framework overhead)
- Three.js for Golden Core
- CSS Custom Properties for theming
- IntersectionObserver for lazy loading
- RequestAnimationFrame for 60fps

### Performance Targets
- Initial load: < 2s
- Core interaction: 60fps
- Golden Core: 60fps WebGL
- Panel transitions: 60fps
- Bundle: < 200KB gzipped

### Browser Support
- Chrome 100+
- Firefox 100+
- Safari 15+
- Edge 100+

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Lighthouse Performance | > 90 |
| Lighthouse Accessibility | 100 |
| Lighthouse Best Practices | > 90 |
| First Contentful Paint | < 1.5s |
| Time to Interactive | < 2.5s |
| Animation FPS | 60fps sustained |
| Bundle Size (gzipped) | < 200KB |
| User Task Completion | > 95% |
| Error Recovery Rate | > 90% |

---

*Plan created: 2026-07-29*
*Based on: Human Interface Research, Agent Architecture Research*
*Status: Phase 1 partial, Phase 2 ready to begin*