# Design Cheatsheet — Talent Agent

**Variant: Top Shelf — Editorial Consulting (gold-on-black, seanyoung.biz-derived).**

This document is the frozen aesthetic spec for the Talent Agent design system. Per HYPHA-DESIGN-CORE.md, surface HYPHAs compose the vocabulary — they do not extend it.

---

## Variant Intent

Top Shelf is an editorial consulting aesthetic. It conveys sophistication, precision, and quiet confidence through:

- **Gold-on-black palette** — derived from seanyoung.biz
- **Serif headlines** — Playfair Display for impact and gravitas
- **Monospace labels** — DM Mono for precision and technical credibility
- **Sans body text** — DM Sans for readability
- **Minimal ornamentation** — borders over shadows, restraint over excess

The aesthetic is intentionally understated. Let content breathe. Use whitespace generously. Avoid visual clutter.

---

## Color Philosophy

### Primary Accent: Gold (`--gold: #C9A227`)

Gold is the signature brand mark. Use it for:

- Primary buttons and CTAs
- Active nav states
- Section labels (`.t-label-gold`)
- Stats and metrics that should draw attention
- Avatar borders
- Interactive element highlights

**Never** use gold for status indicators — status has its own palette.

### Status Colors

Status colors communicate system state. Use the canonical mapping in `StatusBadge.jsx`:

| Color Variable | Semantic Use |
|----------------|--------------|
| `--status-success` | Completed, approved, active, placed |
| `--status-warning` | Reviewing, interviewing, in-progress |
| `--status-error` | Failed, rejected, error states |
| `--status-info` | Discovered, new, informational |
| `--status-pending` | Queued, waiting |
| `--status-hot` | Hot picks, urgent opportunities |

**Rule:** Status-to-color mapping lives ONLY in `StatusBadge.jsx`. No other component duplicates this logic.

### Background Hierarchy

| Variable | Use |
|----------|-----|
| `--bg-primary` | Page background, deepest layer |
| `--bg-secondary` | Sidebar, card backgrounds |
| `--bg-tertiary` | Elevated surfaces, inputs |
| `--bg-elevated` | Dropdowns, modals |

---

## Typography Pairings

### Canonical Type Stack

| Use Case | Class | Font | Weight | Size |
|----------|-------|------|--------|------|
| Page heading | `.t-serif-bold` | Playfair Display | 700 | 48px (clamp) |
| Section heading | `.t-serif` | Playfair Display | 400 | 24-32px |
| Section eyebrow | `.t-label-gold` | DM Mono | 500 | 10px |
| General label | `.t-label` | DM Mono | 500 | 10px |
| Body copy | `.t-body` | DM Sans | 400 | 14px |
| Code/data | `.t-mono` | DM Mono | 400 | 14px |

### Type Rules

1. **Headlines are always Playfair Display.** No mixing with sans for headlines.
2. **Labels are always monospace.** They carry technical precision.
3. **Body text is always DM Sans.** Readable at any size.
4. **Never combine more than two type families in a single component.**

---

## Signature Flourishes

These are the distinctive visual moves that define the Top Shelf aesthetic:

### 1. Gold Top-Border Animation

Cards reveal a gold line from left-to-right on hover. Applied via `.card-hover`:

```css
.card-hover::before {
  height: 2px;
  background: var(--gold);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}
.card-hover:hover::before { transform: scaleX(1); }
```

### 2. Section Label with Dash

The `.section-label` class includes a trailing gold dash:

```html
<div class="section-label">Features</div>
<!-- Renders: FEATURES ——— -->
```

### 3. Stat Treatment

Large serif numbers in gold, monospace labels below:

```html
<div class="stat-num">24/7</div>
<div class="stat-label">Autonomous pipeline</div>
```

### 4. Selection Highlight

Text selection uses gold-faint background with gold text:

```css
::selection {
  background: var(--gold-faint);
  color: var(--gold);
}
```

### 5. Active Nav State

Left border + faint gold background:

```css
.sidebar-link.active {
  border-left-color: var(--gold);
  background: var(--gold-faint);
  color: var(--gold);
}
```

---

## Forbidden Moves

These patterns are explicitly banned:

### 1. No Drop Shadows on Cards

Editorial aesthetic uses borders exclusively. The `--border` variable is the only edge treatment. Never use `box-shadow` on cards.

**Wrong:**
```jsx
<div style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>
```

**Right:**
```jsx
<div style={{ border: '1px solid var(--border)' }}>
```

### 2. No Hardcoded Hex Colors in JSX

All colors come from CSS variables. Never inline hex values.

**Wrong:**
```jsx
<span style={{ color: '#C9A227' }}>Gold text</span>
```

**Right:**
```jsx
<span style={{ color: 'var(--gold)' }}>Gold text</span>
```

### 3. No Mixing Icon Libraries

All icons are from `lucide-react`. Never import from heroicons, react-icons, or Radix icons.

**Wrong:**
```jsx
import { AiOutlineCheck } from 'react-icons/ai'
```

**Right:**
```jsx
import { Check } from 'lucide-react'
```

### 4. No Inline SVGs for Common Icons

Use Lucide components. Inline SVG is only permitted for custom brand glyphs.

### 5. No Gradients on Backgrounds

Background colors are solid. The only permitted gradient is the radial glow used for decorative hero elements.

### 6. No Bold Sans Headlines

Headlines use `.t-serif-bold` (Playfair Display). DM Sans is never bolded for headlines.

### 7. No Custom Status Color Mappings

Status colors are defined once in `StatusBadge.jsx`. Other components import and use `StatusBadge`, never recreate the mapping.

---

## Motion Language

### Transition Defaults

| Purpose | Duration | Easing |
|---------|----------|--------|
| Micro-interactions | `--duration-fast` (150ms) | `--ease-default` |
| UI state changes | `--duration-normal` (200ms) | `--ease-default` |
| Reveals, entrances | `--duration-slow` (300ms) | `--ease-default` |

### Animation Principles

1. **Subtle over flashy.** Motion should feel natural, not attention-seeking.
2. **Purposeful.** Every animation should communicate state change.
3. **Consistent.** Use the same easing (`--ease-default`) everywhere.

### Standard Animations

| Class | Use |
|-------|-----|
| `.fade-in` | Primary entrance |
| `.fade-in-delay` | Secondary element entrance (150ms delay) |
| `.fade-in-delay2` | Tertiary element entrance (300ms delay) |
| `.spinner` | Loading indicator |

---

## Icon System

- **Library:** `lucide-react` only
- **Default size:** 18×18px
- **Stroke width:** 1.5
- **Color:** Inherit from parent or use `var(--gold)` for accent

### Icon Usage

```jsx
import { Check, X, Loader2 } from 'lucide-react'

<Check className="h-4 w-4" />
<Check style={{ width: 18, height: 18, color: 'var(--gold)', strokeWidth: 1.5 }} />
```

---

## Component Primitives

### StatusBadge

The canonical status-to-color mapping. All status display flows through this component.

```jsx
<StatusBadge status="approved" />
<StatusBadge status="failed" />
```

### StatCard

The primitive card treatment for metrics display.

```jsx
<StatCard label="Active" value={42} change={12} icon={Users} />
```

### Button Variants

| Class | Use |
|-------|-----|
| `.btn-primary` | Primary CTAs, gold background |
| `.btn-ghost` | Secondary actions, bordered |

---

## File Ownership

| File | Owner |
|------|-------|
| `index.css` | design-agent (design-core) |
| `design/CHEATSHEET.md` | design-agent (design-core) |
| `design/tokens.reference.md` | design-agent (design-core) |
| `components/StatusBadge.jsx` | design-agent (design-core) |
| `components/StatCard.jsx` | design-agent (design-core) |

Surface HYPHAs (REVIEW-DASHBOARD, ONBOARDING, etc.) consume these primitives — they never modify them.

---

## Contract Amendment Process

To extend the design vocabulary:

1. Identify the need in your surface HYPHA
2. Document the proposed extension
3. Submit amendment via FRUIT_READY contract-amendment line
4. design-core evaluates and either:
   - Accepts and updates the vocabulary
   - Provides guidance on using existing patterns

**Never silently extend.** The vocabulary stays frozen between amendments.

---

*The network provides. 🍄*
