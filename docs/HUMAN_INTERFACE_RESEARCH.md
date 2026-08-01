# JARVIS Human Interface Research

## Overview
Research on human-computer interaction principles, cognitive psychology, and Apple's design philosophy to inform JARVIS UI redesign.

---

## Core Principles

### 1. Cognitive Load Theory (Sweller, 1988)

**Key Insight:** Working memory has limited capacity (~4±1 items). Interfaces must minimize extraneous load.

**Application to JARVIS:**
- Show only relevant information for current task
- Progressive disclosure: reveal complexity on demand
- Chunk information into meaningful groups
- Use visual hierarchy to guide attention
- Avoid split-attention effect (integrate related info)

**Implementation:**
- Contextual panels that appear/disappear based on mission type
- Single primary focus at a time (Golden Core + one panel)
- Collapsible detail sections
- Clear visual grouping with spacing/typography

---

### 2. Miller's Law (7±2 → 4±1)

**Key Insight:** Humans can hold ~4 items in working memory simultaneously.

**Application to JARVIS:**
- Limit visible agents/tools to 4 at once
- Group 23 workers into 4 King categories
- Show max 4 conversation threads
- Max 4 mission steps visible

---

### 3. Hick's Law

**Key Insight:** Decision time increases logarithmically with number of choices.

**Application to JARVIS:**
- Reduce menu items
- Use smart defaults
- Contextual actions (not global menus)
- Progressive disclosure for advanced features

---

### 4. Fitts's Law

**Key Insight:** Time to acquire target = function of distance/size.

**Application to JARVIS:**
- Primary actions large and close
- Golden Core as central anchor
- Frequently used controls at edges/corners
- Generous touch targets (44pt minimum)

---

### 5. Gestalt Principles

**Proximity:** Related elements grouped together  
**Similarity:** Consistent styling for related functions  
**Continuity:** Flow guides eye through process  
**Closure:** Complete visual forms feel resolved  
**Figure/Ground:** Clear focus vs background

**Application to JARVIS:**
- Agent cards grouped by King (proximity)
- Consistent card design (similarity)
- Mission flow visualization (continuity)
- Completed tasks fade (closure)
- Active panel highlighted (figure/ground)

---

### 6. Progressive Disclosure (Nielsen Norman Group)

**Key Insight:** Show only what's needed now; reveal more on demand.

**Application to JARVIS:**
- Home: Golden Core + single input
- Chat: Conversation + agent stream
- Settings: Categorized, searchable
- Mission view: Expandable steps
- Agent details: On hover/click

---

### 7. Trust in AI Interfaces

**Research Findings (Microsoft, Google, Nielsen Norman):**
- Transparency builds trust: show reasoning, sources, confidence
- Control builds trust: undo, approve, configure
- Consistency builds trust: predictable behavior
- Anthropomorphism: careful balance (too much = uncanny)
- Error handling: graceful, explanatory, recoverable

**Application to JARVIS:**
- Agent Stream shows real-time delegation (transparency)
- Tool cards show execution + verification (transparency)
- Permission prompts for sensitive actions (control)
- Consistent motion language (consistency)
- Golden Core as calm presence, not chatty avatar (anthropomorphism)
- Error states with recovery actions (error handling)

---

### 8. Motion Psychology

**Principles (Apple HIG, Material Motion):**
- Motion communicates state change
- Easing feels natural (spring physics)
- Duration: 100-300ms for UI, 300-500ms for transitions
- Staggered entrance creates hierarchy
- Respect reduced motion preference

**JARVIS State Animations:**

| State | Golden Core | Panels | Particles |
|-------|-------------|--------|-----------|
| Idle | Slow pulse | Static | Drift |
| Listening | Expand glow | Slide in | Converge |
| Thinking | Rotate inward | - | Spiral |
| Planning | Expand rings | - | Orbit |
| Executing | Pulse outward | Progress | Flow |
| Verifying | Check pulse | - | Validate |
| Success | Burst glow | Fade out | Disperse |
| Error | Red pulse | Shake | Scatter |

---

### 9. Apple Human Interface Guidelines Alignment

**Clarity:**
- Legible text at all sizes (Dynamic Type support)
- Clear visual hierarchy
- Meaningful icons with labels
- High contrast ratios (WCAG AA)

**Deference:**
- Content over chrome
- Translucency for depth
- Minimal borders
- Fluid motion

**Depth:**
- Layer hierarchy (background → content → controls)
- Shadows for elevation
- Scale/opacity for focus
- Z-space for modal states

**Application to JARVIS:**
- Golden Core = deepest layer (background)
- Panels = floating cards (content layer)
- Controls = top layer (control layer)
- Translucent panels with blur
- Spring animations for all transitions

---

### 10. Calm Technology (Amber Case, Mark Weiser)

**Principles:**
- Technology should require minimal attention
- Inform without demanding focus
- Peripheral awareness > central focus
- Fail gracefully

**Application to JARVIS:**
- Agent Stream = peripheral awareness
- Golden Core state = ambient status
- Notifications only for approvals/errors
- Background missions continue silently

---

## UI Redesign Implications

### Current Problems
1. **Dashboard feel** - Too many panels visible
2. **Developer tool aesthetic** - Technical, not human
3. **Duplicated chat boxes** - Home input + Chat workspace
4. **Clutter** - All agents always visible
5. **No clear hierarchy** - Everything same visual weight

### Redesign Solutions

#### 1. Single Contextual Interface
- One primary view that adapts to mission type
- Golden Core always present (identity anchor)
- Panels slide in/out based on context

#### 2. Mission-Centric Views

| Mission Type | Primary View | Secondary Panels |
|-------------|-------------|------------------|
| Chat/General | Conversation | Agent Stream |
| Research | Sources + Synthesis | Agent Stream |
| Coding | Files + Diff + Tests | Agent Stream |
| Computer | Actions + Screen | Agent Stream |
| Memory | Knowledge Graph | Search |
| Agents | Hierarchy Tree | Details |

#### 3. Visual Language
- **Colors:** Deep space (#080d16) + Cyan accent (#00d4ff) + Semantic
- **Typography:** SF Pro / system-ui, clear hierarchy
- **Spacing:** 4pt base unit, 8/16/24/32 rhythm
- **Radius:** 8pt (cards), 12pt (panels), 16pt (modals)
- **Shadows:** 3 elevation levels
- **Motion:** Spring (damping 0.8, stiffness 180)

#### 4. Golden Core States
- Idle: Slow cyan pulse, particles drift
- Listening: Bright cyan, particles converge to center
- Thinking: Blue shift, slow rotation, spiral particles
- Planning: Gold accent, expanding rings, orbit particles
- Executing: Green tint, outward pulse, flowing particles
- Verifying: Amber, checkmark pulse, validation particles
- Success: Bright green burst, particles disperse upward
- Error: Red pulse, shake, scatter particles

#### 5. Agent Stream (Peripheral Awareness)
- Right sidebar, always visible but subdued
- Real-time delegation cards
- Auto-scroll, fade older entries
- Click to expand details
- Filter by King/worker

#### 6. Tool Transparency Cards
- Appear in-line during execution
- Show: Tool name, args, status, duration, result, verification
- Collapsible after completion
- Error: expand with recovery actions

---

## Accessibility (WCAG 2.1 AA)

- **Color Contrast:** 4.5:1 normal, 3:1 large text
- **Focus Indicators:** Visible, 3px offset, high contrast
- **Keyboard Navigation:** Full tab order, skip links
- **Screen Readers:** ARIA labels, live regions for agent stream
- **Reduced Motion:** Disable spring animations
- **Scaling:** Support 200% zoom
- **Language:** Declared, simple, consistent

---

## Implementation Priority

1. **Design Tokens** (DONE) - Colors, spacing, typography, motion
2. **Animation System** (DONE) - Spring physics, state transitions
3. **Golden Core State Machine** - Visual state reactions
4. **Contextual Panel System** - Slide panels based on mission
5. **Agent Stream Polish** - Real-time, filterable, accessible
6. **Tool Cards** - Execution transparency
7. **Mission View** - Plan → Execute → Verify → Reflect
8. **Settings Redesign** - Categorized, searchable
9. **Accessibility Audit** - WCAG 2.1 AA compliance
10. **Performance** - 60fps, lazy loading, bundle optimization

---

*Research completed: 2026-07-29*
*Sources: Apple HIG, Nielsen Norman Group, Cognitive Load Theory, Gestalt Principles, Calm Technology, WCAG 2.1*