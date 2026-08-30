# Baleen Design System Specification (DESIGN.md)

## 1. Visual Theme & Atmosphere
- **Archetype:** Institutional High-Frequency FinTech & Autonomous Prediction Market Terminal.
- **Mood:** Cold Obsidian, Surgical Precision, Kinetic Haptics, High Data Density, Authoritative.
- **Color Philosophy:**
  - Light Canvas: Cold Pristine Slate (`#F8F9FB`) with luminous pure white elevated surfaces.
  - Dark Canvas: Pitch Black (`#000000`) with deep obsidian surfaces (`#0A0D12` / `#16171B`).
  - Signal Won (Profit): Pure Emerald (`#00D09C` / `#059669`).
  - Signal Loss (Risk): High-Voltage Crimson (`#FF453A` / `#E11D48`).
  - Accents: Electric Blue (`#2563EB` / `#38BDF8`) and Amber Gold (`#F59E0B` / `#D97706`) for Gold Sniper tiering.

---

## 2. Color Palette & Token Roles
| Semantic Token | Light Mode Value | Dark Mode Value | Usage |
|---|---|---|---|
| `canvas` | `#F8F9FB` | `#000000` | Page root background |
| `surface` | `#FFFFFF` | `#16171B` | Primary cards and drawers |
| `surface-sub` | `#F1F3F5` | `#1C1D22` | Inset containers, filters, pill badges |
| `border-subtle` | `rgba(0, 0, 0, 0.06)` | `rgba(255, 255, 255, 0.08)` | Card boundaries, dividers |
| `border-hover` | `rgba(0, 0, 0, 0.14)` | `rgba(255, 255, 255, 0.18)` | Interactive hover boundaries |
| `text-primary` | `#0F172A` (Slate-950) | `#FFFFFF` | Primary headlines, metrics, titles |
| `text-secondary` | `#475569` (Slate-600) | `#8E8F99` | Subtitles, helper text, timestamps |
| `text-muted` | `#94A3B8` (Slate-400) | `#52535A` | Labels, disabled states, grid lines |
| `brand-won` | `#00D09C` | `#00D09C` | Positive PnL, gross profits, wins |
| `brand-lost` | `#FF453A` | `#FF453A` | Negative PnL, gross losses, drawdowns |

---

## 3. Typography Rules & Scales
- **Display / Headers:** Outfit (`var(--font-outfit)`) with tracking `-0.03em` to `-0.04em`.
- **Body:** Plus Jakarta Sans (`var(--font-jakarta)`) / Inter.
- **Financial Metrics & Telemetry:** Monospace (`font-mono`) with `font-variant-numeric: tabular-nums` (`tabular-nums`).
- **Headline Balance:** Always apply `text-wrap: balance` (`text-balance`) to multi-line titles.

---

## 4. Component Stylings
- **Buttons:**
  - Primary: High-contrast solid (`bg-slate-950 text-white dark:bg-white dark:text-black`), rounded-full, `active:scale-[0.98]`, `focus-visible:ring-2`.
  - Secondary / Pill: Subtle surface (`bg-[#F1F3F5] dark:bg-[#1C1D22]`), hairline border, `active:scale-[0.98]`.
  - Circle Actions: 48px to 56px rounded-full with centered icon and tactile hover elevation.
- **Cards & Surfaces:**
  - Smooth 24px to 28px border radius (`rounded-[26px]`).
  - Hairline border with semi-transparent specular shadow.
  - Interactive cards apply `hover:-translate-y-0.5 hover:shadow-md transition-all duration-200`.
- **Badges:**
  - Pill shape (`rounded-full`), `text-xs font-semibold`, explicit contrast in both light and dark modes.

---

## 5. Layout & Spatial Rhythm
- **Modular Scale:** 4px / 8px spatial grid (`gap-2`, `gap-3.5`, `gap-6`, `p-6`, `p-8`, `py-14 sm:py-24`).
- **Container Max-Width:** `max-w-7xl mx-auto` with `px-4 sm:px-6 lg:px-12`.
- **Viewport Stability:** Full hero sections use `min-h-[80vh] sm:min-h-[84vh]` with `overflow-hidden`.

---

## 6. Depth & Elevation
- **Specular Highlights:** `box-shadow: inset 0 1px 0 rgba(255, 255, 255, 1), 0 2px 8px -2px rgba(0, 0, 0, 0.04)`.
- **Obsidian Dark Elevation:** `box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 16px 36px -8px rgba(0, 0, 0, 0.5)`.

---

## 7. Do's and Don'ts
- **DO:**
  - Use `tabular-nums` on all numbers, dollar amounts, win rates, and timestamps.
  - Provide visible focus rings (`focus-visible:ring-2 focus-visible:ring-[#00D09C]`) on all interactive controls.
  - Provide informative `aria-label` on all icon-only buttons.
  - Use non-breaking spaces `&nbsp;` between currency symbols and figures.
  - Respect `prefers-reduced-motion`.
- **DON'T:**
  - Never use AI purple glows or generic multicolored gradient slops.
  - Never leave bare `outline-none` without a `focus-visible` ring replacement.
  - Never use straight quotes in prose when curved quotes belong.
  - Never wrap button text to multiple lines on desktop.

---

## 8. Responsive Behavior
- **Desktop (>= 1024px):** Multi-column telemetry grids, expanded navigation, detailed tooltips.
- **Tablet (768px - 1023px):** 2-column bento grids, sticky top bars.
- **Mobile (< 768px):** Single-column vertical stacks, bottom-sheet drawers, touch-friendly 44px+ hit targets.

---

## 9. Agent Prompt Guide
When generating or modifying frontend code for Baleen:
- Strictly adhere to these design tokens and principles.
- Check WCAG AA contrast in both light and dark themes.
- Test keyboard navigation and ARIA attributes before completion.
