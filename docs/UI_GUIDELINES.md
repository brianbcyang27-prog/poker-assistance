# JARVIS UI Guidelines v7.0

> **Design Philosophy**: Calm. Elegant. Fast. Premium. Alive.

---

## Design Tokens

### Shadows
```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.1);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.15);
--shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.2);
--shadow-xl: 0 16px 48px rgba(0, 0, 0, 0.3);
```

### Spacing
```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
```

### Typography
```css
--font-size-xs: 12px;
--font-size-sm: 13px;
--font-size-base: 14px;
--font-size-md: 15px;
--font-size-lg: 18px;
--font-size-xl: 20px;
--font-size-2xl: 24px;
--font-size-3xl: 28px;
```

### Border Radius
```css
--radius-sm: 6px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
--radius-2xl: 20px;
--radius-full: 9999px;
```

### Transitions
```css
--transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
--transition-base: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
--transition-slow: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
--transition-spring: 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
```

### Glass Effects
```css
--glass-bg: rgba(20, 20, 25, 0.7);
--glass-border: rgba(255, 255, 255, 0.06);
--glass-blur: blur(20px);
--glass-blur-heavy: blur(40px);
```

---

## Component Patterns

### Buttons
- **Primary**: `var(--gold)` background, dark text, hover scales to 1.02
- **Secondary**: Glass background, light border, hover brightens
- **Ghost**: No background, text only, hover adds subtle glass
- All buttons: `border-radius: var(--radius-lg)`, `transition: var(--transition-base)`

### Cards
- Glass background with `backdrop-filter: blur(20px)`
- Subtle border: `1px solid var(--glass-border)`
- Hover: slight lift with shadow increase
- Padding: `var(--space-5)` to `var(--space-6)`

### Navigation
- Top bar with glass effect
- 5 primary items: Home, Chat, Memory, Projects, Settings
- Active state: gold background pill, scale(1.02)
- Hover: subtle glow, scale(1.02)
- Developer items hidden by default, toggle with `Cmd+Shift+D`

### Inputs
- Glass background, subtle border
- Focus: gold border glow, slight scale
- Placeholder: `var(--text-muted)`
- Padding: `var(--space-3)` vertical, `var(--space-4)` horizontal

### Panels
- Glass background with heavy blur
- Smooth transitions between states
- No layout jumps — use `display: none/flex/block` with transitions
- Consistent padding: `var(--space-5)` to `var(--space-6)`

---

## Motion Principles

1. **Spring Easing**: Use `cubic-bezier(0.34, 1.56, 0.64, 1)` for natural, bouncy motion
2. **Subtle Scale**: Buttons/cards scale to 1.02 on hover, not 1.1
3. **Gold Glow**: Use `box-shadow` with gold color for active/focus states
4. **Smooth Transitions**: 0.15s–0.3s for most interactions
5. **No Flashing**: Use opacity/transform transitions instead of display changes

---

## Color Usage

| Element | Color | Usage |
|---------|-------|-------|
| `--gold` | `#FFD700` | Primary accent, active states, CTAs |
| `--gold-dim` | `#CC9900` | Muted gold, secondary accents |
| `--bg-primary` | `#0A0A0F` | Main background |
| `--bg-secondary` | `#111118` | Card/panel backgrounds |
| `--bg-tertiary` | `#1A1A24` | Elevated surfaces |
| `--text-primary` | `#F0F0F5` | Headings, primary text |
| `--text-secondary` | `#A0A0B0` | Body text |
| `--text-muted` | `#606070` | Placeholders, labels |
| `--success` | `#10B981` | Success states |
| `--warning` | `#F59E0B` | Warning states |
| `--error` | `#EF4444` | Error states |

---

## Workspace Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Logo   Home   Chat   Memory   Projects   [···]   ⚙   👤  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    [Active Workspace]                       │
│                                                             │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- **Home**: Neural Core visualization, AI presence, quick actions
- **Chat**: Single message input, conversation history
- **Memory**: Memory Galaxy, knowledge graph
- **Projects**: Project cards, workspace management
- **Settings**: User preferences, model config, secrets
- **Developer** (hidden): Metrics, Logs, Engineering, Computer

---

## Anti-Patterns

1. **Don't** use `display: block/none` for transitions — use opacity + transform
2. **Don't** mix different border-radius values — stick to the token scale
3. **Don't** use hardcoded colors — always use CSS variables
4. **Don't** add comments unless absolutely necessary
5. **Don't** create new workspaces — use overlays/drawers instead
6. **Don't** show developer info by default — hide behind Dev Mode
7. **Don't** use static "Ready" text — use dynamic AI presence messages
