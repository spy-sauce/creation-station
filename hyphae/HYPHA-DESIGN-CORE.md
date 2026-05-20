# HYPHA-DESIGN-CORE

> HYPHA tag: `TA/DESIGN`
> Status: **DRAFT** — pending freeze

## Goal

Own the single source of truth for the Talent Agent design language: the variant pick, the token vocabulary (color, type, spacing, motion), the primitive components that encode the aesthetic, and the cheatsheet that tells every other HYPHA what "production-grade" means in this repo. Every frontend-touching HYPHA reads from these definitions; only design-core writes them.

Mirrors the role of HYPHA-SCHEMA-CORE: schema-core is the upstream NUTRIENT for data; design-core is the upstream NUTRIENT for aesthetic. Without it, each surface HYPHA invents its own taste at execution time and the system drifts.

## Scope

### In Scope

- **Variant declaration**: one canonical aesthetic identity. For this repo: **Top Shelf — Editorial Consulting** (gold-on-black, derived from seanyoung.biz). Not cellar / not back-of-house. Frozen by this HYPHA; surface HYPHAs do not re-pick.
- `frontend/src/index.css` — CSS custom properties (palette, type stack, status colors, transition curves, scrollbar treatment, selection treatment)
- `frontend/src/index.css` — typography utility classes (`.t-serif`, `.t-serif-bold`, `.t-label`, `.t-label-gold`, `.t-body`) and any section-label / divider primitives
- `frontend/src/design/CHEATSHEET.md` — prose aesthetic spec: variant intent, signature flourishes, what's forbidden, when to use each token, motion language, icon system
- `frontend/src/components/StatusBadge.jsx` — status-to-color map (the canonical status palette lives here)
- `frontend/src/components/StatCard.jsx` — the primitive card treatment (border, padding, label-over-value composition)
- Tailwind v4 `@import "tailwindcss"` entrypoint and any theme extensions
- Icon system declaration: **lucide-react only**, no mixing
- Font loading strategy: Playfair Display (serif), DM Sans (sans), DM Mono (mono)

### Out of Scope

- Feature components (Sidebar's nav structure, TopBar's content, page-specific layouts) — those belong to the surface HYPHA that owns the route (REVIEW-DASHBOARD, ONBOARDING, etc.)
- Routes, pages, API wiring (REVIEW-DASHBOARD owns)
- Auth UI flows (AUTH / ONBOARDING own)
- Multi-theme switching, dark/light toggling — single dark editorial variant only
- Mobile-first responsive design — desktop-first, table breakpoints only (mirrors REVIEW-DASHBOARD scope)
- A11y audit pass — best-effort, not a freeze criterion
- Cellar / back-of-house variants — not used in this repo; reserved for future Mycelium-cultivated repos where back-of-house is the right call

## Inputs

- Repo CLAUDE.md (no hex literals in JSX; Tailwind classes scoped per design tokens)
- Brief §"Polish bar" (Review Queue is highest-leverage surface; production-grade)
- seanyoung.biz consulting site — the source aesthetic this design language is derived from
- `frontend-design` skill — referenced when extending the vocabulary (not when consuming it)
- Existing `frontend/src/index.css` at HEAD — the implicit aesthetic this HYPHA makes explicit
- Existing `frontend/src/components/{StatusBadge,StatCard,Sidebar,TopBar}.jsx` — codify the primitive treatments already in place

## Outputs (Deliverables)

Existing files codified by this HYPHA (already at HEAD, locked by freeze):

- `frontend/src/index.css` — token vocabulary and typography utilities
- `frontend/src/components/StatusBadge.jsx` — canonical status-to-color map
- `frontend/src/components/StatCard.jsx` — primitive card treatment

New files produced by this HYPHA's freeze:

- `frontend/src/design/CHEATSHEET.md` — prose aesthetic spec (variant intent, signature flourishes, forbidden moves, token-usage rules, motion language, icon rule)
- `frontend/src/design/tokens.reference.md` — short table cross-referencing CSS custom properties to their semantic role (e.g. `--gold` = primary accent + brand mark; never used for status)

## Acceptance Criteria

- [ ] CHEATSHEET.md exists and declares the variant in its first line: "Variant: Top Shelf — Editorial Consulting (gold-on-black, seanyoung.biz-derived)."
- [ ] Every CSS custom property in `index.css` is documented in `tokens.reference.md` with a one-line semantic role
- [ ] `grep -rE "#[0-9a-fA-F]{3,8}" frontend/src/ --include="*.jsx" --include="*.tsx"` returns zero matches outside `frontend/src/design/`
- [ ] Every JSX color, border, or shadow value resolves to a `var(--token)` or a Tailwind class bound to a token — never an inline hex
- [ ] `StatusBadge`'s status-to-color map is the only place status colors are mapped; no other component duplicates the mapping
- [ ] CHEATSHEET.md lists the canonical type pairings (e.g. "page heading: `.t-serif-bold` 48px / section eyebrow: `.t-label-gold` / body: `.t-body`") so surface HYPHAs don't invent new combinations
- [ ] CHEATSHEET.md lists at least three "forbidden moves" (e.g. "no drop shadows on cards; the border at `--border` is the only edge treatment")
- [ ] Lucide-react is the only icon import; `grep -r "heroicons\|react-icons\|@radix-ui/react-icons" frontend/src/` returns zero matches
- [ ] `npm run build` produces a clean `dist/` with no warnings about unresolved CSS vars
- [ ] When `frontend-design` skill is invoked during a surface HYPHA execution, it is invoked WITH the frozen variant + tokens as context — never asked to pick a variant

## Notes

- **DESIGN-CORE is upstream of every frontend HYPHA.** REVIEW-DASHBOARD, ONBOARDING, and any future surface HYPHA must list `design-core` in their Inputs. The contract enforces: surface HYPHAs compose the vocabulary; they don't extend it.
- **Variant pick is the most expensive decision.** It's frozen once at DESIGN-CORE freeze and never re-litigated in surface HYPHAs. If a future cultivation wants to introduce a cellar variant for an admin sub-surface, that's a new DESIGN-CORE-V2 freeze, not an ad-hoc surface decision.
- **Cellar is reserved for other repos.** This codebase chose top-shelf intentionally — single-candidate MVP, operator IS the customer, polish matters more than patina. Future Mycelium-cultivated repos where back-of-house is the right call will freeze a different DESIGN-CORE pointing at one of the six cellar variants.
- **Retrofit question for REVIEW-DASHBOARD (frozen at `26143cd`):** REVIEW-DASHBOARD currently lists `schema-core` and `auth` as Inputs but not `design-core`. Two options when DESIGN-CORE freezes:
  1. Add `design-core` to REVIEW-DASHBOARD's Inputs via amendment (re-freeze REVIEW-DASHBOARD at the new HEAD)
  2. Apply the dependency going forward only — REVIEW-DASHBOARD stays at `26143cd`; the next surface HYPHA cultivated lists `design-core` from day one
  Operator decides at freeze time.
- **When `frontend-design` skill applies vs. this HYPHA**: the skill is invoked to *generate* aesthetic decisions when none exist. Once those decisions are frozen here, the skill becomes a consumer — it must receive the variant + tokens as upstream context and produce code that conforms, not code that re-picks. Same relationship `cellar-design` would have with a cellar-variant DESIGN-CORE in a different repo.
- **No design tokens in component files.** Status colors map in `StatusBadge`; primitive treatments encode in their component file; everything else flows from CSS custom properties via `var(--token)` or Tailwind classes bound to tokens. A component referencing a hex literal directly is a contract violation.
