# Token Reference — Talent Agent Design System

> Cross-reference of CSS custom properties to their semantic roles.
> Per HYPHA-DESIGN-CORE.md, this is the single source of truth.

---

## Primary Palette

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--gold` | `#C9A227` | Primary accent, brand mark, CTAs, active states |
| `--gold-dim` | `rgba(201, 162, 39, 0.7)` | Dimmed gold for subtle emphasis |
| `--gold-faint` | `rgba(201, 162, 39, 0.15)` | Background tint for gold elements, active nav states |

---

## Backgrounds

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--bg-primary` | `#0A0A0A` | Page background, deepest layer |
| `--bg-secondary` | `#141414` | Sidebar, card backgrounds, one level above primary |
| `--bg-tertiary` | `#1A1A1A` | Elevated surfaces, input backgrounds |
| `--bg-elevated` | `#1F1F1F` | Dropdowns, modals, highest elevation |

### Legacy Aliases

| Alias | Points To | Notes |
|-------|-----------|-------|
| `--black` | `var(--bg-primary)` | Backwards compatibility |
| `--off-black` | `var(--bg-secondary)` | Backwards compatibility |
| `--surface` | `var(--bg-tertiary)` | Backwards compatibility |

---

## Text Colors

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--text-primary` | `#FAFAFA` | Primary text, headlines, body |
| `--text-secondary` | `#A3A3A3` | Secondary text, labels, muted content |
| `--text-muted` | `#737373` | Disabled states, placeholder text |

### Legacy Aliases

| Alias | Points To | Notes |
|-------|-----------|-------|
| `--white` | `var(--text-primary)` | Backwards compatibility |
| `--muted` | `var(--text-secondary)` | Backwards compatibility |

---

## Borders

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--border` | `rgba(255, 255, 255, 0.08)` | Default border color, dividers |
| `--border-hover` | `rgba(255, 255, 255, 0.15)` | Hover state borders |

---

## Status Colors

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--status-success` | `#22C55E` | Completed, approved, active, placed |
| `--status-warning` | `#EAB308` | Reviewing, in-progress, interviewing |
| `--status-error` | `#EF4444` | Failed, rejected, errors |
| `--status-info` | `#3B82F6` | Discovered, new, informational |
| `--status-pending` | `#A855F7` | Queued, waiting for action |
| `--status-hot` | `#F97316` | Hot picks, urgent opportunities |

### Legacy Aliases

| Alias | Points To | Notes |
|-------|-----------|-------|
| `--emerald` | `var(--status-success)` | Backwards compatibility |
| `--rose` | `var(--status-error)` | Backwards compatibility |
| `--amber` | `var(--status-warning)` | Backwards compatibility |

---

## Semantic Colors

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--accent` | `var(--gold)` | Primary accent alias |
| `--accent-hover` | `#D4AF37` | Accent hover state |
| `--destructive` | `#DC2626` | Destructive actions |
| `--destructive-hover` | `#B91C1C` | Destructive action hover |

---

## Typography — Font Families

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--font-serif` | `'Playfair Display', Georgia, serif` | Headlines, display text |
| `--font-sans` | `'DM Sans', system-ui, sans-serif` | Body text, UI labels |
| `--font-mono` | `'DM Mono', 'Fira Code', monospace` | Labels, code, data |

### Legacy Aliases

| Alias | Points To |
|-------|-----------|
| `--serif` | `var(--font-serif)` |
| `--sans` | `var(--font-sans)` |
| `--mono` | `var(--font-mono)` |

---

## Typography — Font Sizes

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--text-xs` | `0.75rem` (12px) | Small labels, badges |
| `--text-sm` | `0.875rem` (14px) | Body text, inputs |
| `--text-base` | `1rem` (16px) | Default size |
| `--text-lg` | `1.125rem` (18px) | Large body |
| `--text-xl` | `1.25rem` (20px) | Subheadings |
| `--text-2xl` | `1.5rem` (24px) | Section headings |
| `--text-3xl` | `1.875rem` (30px) | Page subheadings |
| `--text-4xl` | `2.25rem` (36px) | Page headings |
| `--text-5xl` | `3rem` (48px) | Hero headings |

---

## Typography — Line Heights

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--leading-tight` | `1.25` | Headlines, compact text |
| `--leading-normal` | `1.5` | Standard line height |
| `--leading-relaxed` | `1.75` | Body text, readable content |

---

## Typography — Font Weights

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--font-normal` | `400` | Body text, default |
| `--font-medium` | `500` | Labels, emphasis |
| `--font-semibold` | `600` | Strong emphasis |
| `--font-bold` | `700` | Headlines, strong |

---

## Spacing Scale

| Token | Value | Use Case |
|-------|-------|----------|
| `--space-0` | `0` | No spacing |
| `--space-1` | `0.25rem` (4px) | Tight gaps |
| `--space-2` | `0.5rem` (8px) | Icon gaps, inline elements |
| `--space-3` | `0.75rem` (12px) | Small padding |
| `--space-4` | `1rem` (16px) | Standard padding |
| `--space-5` | `1.25rem` (20px) | Medium padding |
| `--space-6` | `1.5rem` (24px) | Card padding |
| `--space-8` | `2rem` (32px) | Section gaps |
| `--space-10` | `2.5rem` (40px) | Large section gaps |
| `--space-12` | `3rem` (48px) | Section dividers |
| `--space-16` | `4rem` (64px) | Page sections |
| `--space-20` | `5rem` (80px) | Large page sections |
| `--space-24` | `6rem` (96px) | Hero sections |

---

## Border Radii

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--radius-none` | `0` | Sharp corners (default) |
| `--radius-sm` | `0.125rem` (2px) | Subtle rounding |
| `--radius-md` | `0.375rem` (6px) | Inputs, small cards |
| `--radius-lg` | `0.5rem` (8px) | Cards, buttons |
| `--radius-xl` | `0.75rem` (12px) | Large elements |
| `--radius-full` | `9999px` | Pills, avatars, badges |

---

## Shadows

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.4)` | Subtle elevation (rarely used) |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.4)` | Medium elevation (rarely used) |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.5)` | High elevation (rarely used) |
| `--glow-gold` | `0 0 20px rgba(201,162,39,0.3)` | Gold accent glow |

**Note:** Editorial aesthetic prefers borders over shadows. Use shadows sparingly.

---

## Motion — Durations

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--duration-fast` | `150ms` | Micro-interactions, hovers |
| `--duration-normal` | `200ms` | UI state changes |
| `--duration-slow` | `300ms` | Reveals, entrances |

---

## Motion — Easing

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--ease-default` | `cubic-bezier(0.4, 0, 0.2, 1)` | Standard easing |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Entrance emphasis |
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Exit de-emphasis |
| `--ease-bounce` | `cubic-bezier(0.68, -0.55, 0.265, 1.55)` | Playful (rarely used) |

---

## Navigation

| Token | Value | Semantic Role |
|-------|-------|---------------|
| `--nav-bg` | `rgba(10, 10, 10, 0.95)` | Nav bar background with blur |
| `--transition-theme` | `background 0.35s ease, ...` | Theme transition timing |

---

## Usage Examples

### Background Layer

```css
.page { background: var(--bg-primary); }
.card { background: var(--bg-secondary); }
.input { background: var(--bg-tertiary); }
.dropdown { background: var(--bg-elevated); }
```

### Status Badge

```jsx
const statusColors = {
  approved: 'var(--status-success)',
  failed: 'var(--status-error)',
  reviewing: 'var(--status-warning)',
}
```

### Button

```css
.btn-primary {
  background: var(--gold);
  color: var(--bg-primary);
  transition: background var(--duration-normal) var(--ease-default);
}
.btn-primary:hover { background: var(--accent-hover); }
```

### Typography

```jsx
<h1 style={{ fontFamily: 'var(--font-serif)', fontWeight: 'var(--font-bold)' }}>
  Headline
</h1>
<p style={{ fontFamily: 'var(--font-sans)', color: 'var(--text-secondary)' }}>
  Body text
</p>
```

---

*Per HYPHA-DESIGN-CORE.md — amendments via FRUIT_READY contract-amendment line only.*
