# Component Hierarchy, VisionOS Dynamic Dock, and Interactive Mechanics Survey

## 1. Observation

### 1.1 Scope & Architecture Overview
We surveyed the entire frontend component hierarchy in `frontend/src/` (`package.json`, `app/`, `components/`, `context/`, `public/`, `styles/`).
Key dependency observations:
- `framer-motion`: `^13.1.0` is installed and functional in `frontend/package.json` (line 16).
- `lucide-react`: `^1.31.0` and `@heroicons/react`: `^2.2.0` (lines 12, 17).
- `recharts`: `^3.10.1` (line 22).
- `tailwindcss`: `^3.4.19` (line 36).
- `next`: `16.3.0`, `react`: `19.2.8` (lines 18, 20).
- Production build baseline: `npm run build` in `frontend/` succeeds with exit code 0 and zero TypeScript or lint errors.
- Backend test suite: `pytest` in `backend/` passes 2672 tests (57 skipped) with 100% pass rate.

### 1.2 Complete Component Hierarchy Map

#### A. Layout & Global Styling
- `frontend/src/app/layout.tsx` (lines 1-49):
  - Root layout loading Google fonts: `Plus_Jakarta_Sans`, `Outfit`, `Cinzel`, `Inter`, `Space_Grotesk`.
  - Body container: `bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white`.
  - Wrapped in `<Providers>` (`SessionProvider` and `ThemeProvider`).
- `frontend/src/app/globals.css` (lines 1-517):
  - Base classes for light/dark backgrounds (`#F8F9FB` / `#000000`).
  - `.revolut-canvas`, `.revolut-card` (lines 51-70): white cards with subtle grey borders in light mode; `#16171B` in dark mode.
  - Hardcoded dark theme styles for `.baleen-landing` (line 290): `--metallic-canvas: #07080a`, `background-color: #07080a`.
  - Glass utilities: `.apple-glass`, `.liquid-glass-lens`, `.liquid-chromatic-rim`, `.liquid-dock`, `.liquid-active-lens`, `.liquid-pill-btn` (lines 315-446). All designed against dark/black backdrops rather than the Arctic Glacier palette.
- `frontend/src/context/ThemeContext.tsx` (lines 1-82):
  - Theme toggler managing `'light'` and `'dark'`. Default is `'light'`, stored in `localStorage.getItem('baleen_theme')`.

#### B. Landing Page Components (`frontend/src/app/page.tsx`)
1. `LiquidGlassFilter` (`frontend/src/components/landing/LiquidGlassFilter.tsx`, lines 1-48):
   - Offscreen SVG filter defining `#liquid-goo-metaball`, `#fluid-drop-shadow`, and `#liquid-caustics`.
2. `LiquidParallaxBackground` (`frontend/src/components/landing/LiquidParallaxBackground.tsx`, lines 1-63):
   - Fixed full-screen backdrop with mouse movement parallax tracking. Hardcoded to dark `#060709` background with emerald/cyan/purple caustic orbs.
3. `LiquidGlassHeader` / `LiquidGlassMobileDock` (`frontend/src/components/landing/LiquidGlassDock.tsx`, lines 1-204):
   - Desktop floating navigation dock (`max-w-[1240px]`, `rounded-full`, `fixed top-0` with `pt-3 sm:pt-5`).
   - Links: Architecture (`#advantages`), Sleeve Model (`#simulator`), Telemetry (`#infrastructure`), Sign In (`/auth/login`), Launch Sandbox (`/dashboard`).
   - Active indicator: Convex protruding bubble using Framer Motion (`layoutId="desktop-liquid-lens-bubble"`, `spring` stiffness: 420, damping: 30, mass: 0.8).
   - Mobile bottom dock (`fixed bottom-4 inset-x-3 sm:hidden`, `max-w-[360px]`, `layoutId="mobile-liquid-lens-bubble"`).
4. `Hero` (`frontend/src/components/landing/Hero.tsx`, lines 1-119):
   - Header badge: `.liquid-glass-lens .liquid-chromatic-rim`.
   - Large typography: `text-3xl sm:text-5xl lg:text-7xl font-black`.
   - Action controls: "Launch $10,000 Sandbox" (solid white pill) + "Interactive Simulator" (`.liquid-pill-btn`).
   - Centerpiece mount: `<LiquidGlassHeroCanvas />` (line 87).
   - Bottom feature strip: `.liquid-glass-lens`.
5. `LiveTicker` (`frontend/src/components/landing/LiveTicker.tsx`, lines 1-139):
   - Marquee ticker streaming live Polymarket fills from `/api/execution-logs`.
   - Infinite horizontal animation using Framer Motion `animate={{ x: ['0%', '-33.333%'] }}`.
6. `AdvantageSection` (`frontend/src/components/landing/AdvantageSection.tsx`, lines 1-120):
   - 4 feature cards using `LiquidGlassCard` (Adaptive Sleeves, $1.00 Floor Sizing, Asymmetric Alpha, Sub-120ms Envio).
7. `LiquidGlassCard` (`frontend/src/components/landing/LiquidGlassCard.tsx`, lines 1-76):
   - Optical glass card with top specular crescent arc highlight, mouse-following radial specular glint, chromatic rainbow dispersion rim, and bottom green refraction line.
8. `LiquidSleeveSimulator` (`frontend/src/components/landing/LiquidSleeveSimulator.tsx`, lines 1-231):
   - Dynamic capital allocation engine ($200 to $20,000).
   - 5 vertical liquid glass vial tubes with animated fluid liquid level and wave meniscus shimmer.
   - Dynamic Kelly sizing metrics and launch simulated portfolio CTA.
9. `InfrastructureSection` (`frontend/src/components/landing/InfrastructureSection.tsx`, lines 1-153):
   - Technical specification cards and optical glass telemetry monitor card.
   - High-impact closing CTA banner with `.liquid-glass-lens .liquid-chromatic-rim`.
10. Footer (`app/page.tsx`, lines 45-80):
    - Dark glass container with BrandLogo, navigation links, copyright, and experimental paper trading disclaimer.

#### C. Dashboard Page Components (`frontend/src/app/dashboard/page.tsx`)
1. Top Bar Navigation (`dashboard/page.tsx`, lines 215-328):
   - Fixed sticky top bar: `border-b border-black/[0.06] dark:border-white/[0.08] bg-white/80 dark:bg-[#000000]/90 backdrop-blur-2xl`.
   - BrandLogo (`/logo.png`).
   - Segmented view mode toggle: `Sandbox (Paper Trading)` vs `Live Trading · Unavailable (Gated)` (lines 222-245).
   - Center command bar: Search trigger for `CommandPalette` (`⌘K`, lines 248-265).
   - Right circular icon controls: Theme toggle (Moon/Sun), Activity Feed bell, Audio toggle, Admin link, Settings link, Sign out button (lines 267-327).
2. Balance Counter & Hero Controls (`frontend/src/components/dashboard/BalanceCounter.tsx`, lines 1-138):
   - Dynamic number animation via Framer Motion `animate(motionVal, balance, { duration: 0.4, ease: [0.16, 1, 0.3, 1] })`.
   - PnL pill badge with positive/negative color tokens.
   - 4-action circular button row: Mirror (`Plus`), Rebalance (`ArrowLeftRight`), Analytics (`BarChart2`), Reset (`RotateCcw`).
   - Risk regime indicator badge (`Balanced`, `Conservative`, `Aggressive`).
3. Portfolio Analytics & Timeframe Module (`frontend/src/components/dashboard/PortfolioAnalytics.tsx`, lines 1-1168):
   - Multi-period area chart / candlestick chart with Recharts.
   - Timeframe pill selectors: `1H`, `6H`, `1D`, `1W`, `1M`, `YTD`, `ALL`.
   - Market attribution cards: Top Alpha markets vs Top Drawdown markets.
   - Sleeve capital allocation breakdown: Progress bars for individual whale sleeves.
   - Execution scorecard metrics: All-time win rate, fee rate drag, total fills count.
4. Live Tape (`frontend/src/components/dashboard/LiveTape.tsx`, lines 1-219):
   - Real-time scrollable feed of simulated paper executions.
   - Filter pills: `ALL`, `BUY`, `SELL`, `CONSENSUS`.
   - Search input filter.
5. Wallet Leaderboard (`frontend/src/components/dashboard/WalletLeaderboard.tsx`, lines 1-360):
   - Ranked list of discovered Polymarket whales.
   - Tabs: `Copied Whales`, `Top Active (5 Sleeves)`, `All Tracked`.
   - Whale cards displaying tier badges, PnL, win rates, and sleeve sizes.
6. Execution Trade Log (`frontend/src/components/dashboard/TradeLog.tsx`, lines 1-273):
   - Tabbed view: `Holding`, `Closed`, `All`.
   - Audit export modal trigger (`FullHistorySpreadsheetModal`).
   - Interactive transaction list items opening `TradeDrawer`.
7. Live Capital Tab (`dashboard/page.tsx`, lines 412-643):
   - Gated status hero banner with link to Settings.
   - 3 metric cards: pUSD L2 Cash Balance, Unreconciled Live Equity, Unreconciled Exchange PnL.
   - Active Live Positions table (5 columns).
   - Live CLOB Execution Logs table (8 columns).

#### D. Modals and Drawers
1. `CommandPalette` (`frontend/src/components/ui/CommandPalette.tsx`, lines 1-243):
   - Global modal search (Cmd+K) with backdrop blur, keyword filtering across navigation, actions, and whales.
2. `MirrorStrategyModal` (`frontend/src/components/dashboard/MirrorStrategyModal.tsx`, lines 1-194):
   - Modal for adjusting per-whale copy multipliers (1.0x to 2.5x) and sleeve activation toggles.
3. `RebalanceModal` (`frontend/src/components/dashboard/RebalanceModal.tsx`, lines 1-165):
   - Capital rebalancer modal with algorithm selection (Equal weighting, PnL-weighted, WinRate-weighted).
4. `DeepAnalyticsModal` (`frontend/src/components/dashboard/DeepAnalyticsModal.tsx`, lines 1-122):
   - 6-metric quantitative breakdown modal (Net Return, Win Rate, Fees, Profit Factor, Sharpe, Max Drawdown).
5. `ResetSandboxModal` (`frontend/src/components/dashboard/ResetSandboxModal.tsx` & `frontend/src/components/modals/ResetSandboxModal.tsx`):
   - Account balance reset confirmation modal ($10,000 baseline).
6. `FullHistorySpreadsheetModal` (`frontend/src/components/dashboard/FullHistorySpreadsheetModal.tsx`, lines 1-466):
   - Paginated 10-column table of execution history with JSON/CSV export.
7. `TradeDrawer` (`frontend/src/components/dashboard/TradeDrawer.tsx`, lines 1-225):
   - Right-side slide-out drawer displaying trade execution metadata, execution price chart, and Polymarket deep link.
8. `WalletDrawer` (`frontend/src/components/dashboard/WalletDrawer.tsx`, lines 1-456):
   - Right-side slide-out drawer displaying whale profile, historical performance charts (Win/Loss, PnL, Score), AI summary, and recent trades.
9. `ActivityFeed` (`frontend/src/components/dashboard/ActivityFeed.tsx`, lines 1-202):
   - Notification flyout drawer for real-time system events (orders copied, slippage skips, promotions).
10. `Modal` Base (`frontend/src/components/ui/Modal.tsx`, lines 1-375):
    - Accessible portal dialog with scroll lock, focus trap, Escape key handling, and spring animation.

#### E. Settings, Admin, and Auth Pages
- `frontend/src/app/settings/page.tsx` (lines 1-2071):
  - L2 CLOB API credentials, connection test, session key generation and verification, live account baseline initialization, copy policy editor with 11 parameters, risk regime selection, paper run archives.
- `frontend/src/app/admin/page.tsx` (lines 1-594):
  - Admin wallet discovery controls, discovery progress polling, and discovered wallet roster.
- `frontend/src/app/auth/login/page.tsx` & `signup/page.tsx`:
  - Instant guest login provisioning, user credential sign-in.

### 1.3 Identification of Artificial Vector Dumbbells, Static Graphic Placeholders, & Cartoon Art (R2)

We conducted comprehensive literal and regex searches for `dumbbell`, `placeholder`, `watermark`, `mockup`, `cartoon`, `canvas`, `svg`, and raster image assets:
1. **Verbatim Artificial Vector Dumbbell**:
   - Directly found in `frontend/src/components/landing/LiquidGlassHeroCanvas.tsx`:
     - Line 108: `<span className="sm:hidden">Dumbbell</span>`
     - Line 189: `{/* MODE 1: PURE VECTOR WWDC25 LIQUID GLASS DUMBBELL (Zero Watermark, 100% Procedural) */}`
     - Lines 201–322: SVG drawing consisting of two circular/capsule lobes connected by a concave bridge (`d="M 195 64 C 235 64, 255 108, 285 108 C 315 108, 330 48, 365 48 L 415 48 A 84 84 0 0 1 415 216 L 365 216 C 330 216, 315 156, 285 156 C 255 156, 235 200, 195 200 A 68 68 0 0 1 195 64 Z"`).
     - Lines 324–350: Live quantitative telemetry overlaid inside the vector dumbbell art.
     - Mode 2 (lines 355–479): Interactive fluid drag droplet and capsule with dynamic meniscus waist bridge.
   - **Per R2 Requirement**: This artificial vector graphic illustration is explicitly targeted for removal/replacement with genuine functional optical liquid glass UI containers (e.g., real floating glass cards, live telemetry lenses, or dynamic interactive risk sleeve containers).
2. **Unreferenced Heavy Graphic Assets in `frontend/public/images/`**:
   - `public/images/baleen_abyssal_whale.jpg` (709 KB)
   - `public/images/baleen_liquid_glass.jpg` (551 KB)
   - `public/images/bgImage.jpeg` (1.65 MB)
   - `public/images/cta_obsidian_silk.jpg` (398 KB)
   - `public/images/hero-icescape.jpeg` (2.76 MB)
   - `public/images/hero-icescape1.jpg` (708 KB)
   - `public/images/whale_tail_hero.jpg` (483 KB)
   - **Finding**: None of these 7 raster files (totalling ~7.3 MB) are referenced in any `.tsx` or `.css` file across the repository. Only `logo.png` is referenced in `BrandLogo.tsx`.
3. **Orphaned / Legacy Components in `frontend/src/components/`**:
   - `frontend/src/components/landing/FeaturesGrid.tsx` (unreferenced in `page.tsx`).
   - `frontend/src/components/landing/ProfitSimulator.tsx` (unreferenced in `page.tsx`, superseded by `LiquidSleeveSimulator.tsx`).
   - `frontend/src/components/landing/Leaderboard.tsx` (unreferenced in `page.tsx`).
   - `frontend/src/components/landing/ShaderGradientBackground.tsx` (unreferenced in `page.tsx`, superseded by `LiquidParallaxBackground.tsx`).
   - `frontend/src/components/dashboard/BaleenCopilot.tsx` (unreferenced in `dashboard/page.tsx`).

### 1.4 Interactive Mechanics Analysis
1. **Dynamic Dock Current State**:
   - Landing page has `LiquidGlassHeader` and `LiquidGlassMobileDock` in `LiquidGlassDock.tsx`.
   - Mechanics: Uses Framer Motion `<motion.div layoutId="desktop-liquid-lens-bubble">` with spring parameters (`type: 'spring', stiffness: 420, damping: 30, mass: 0.8`).
   - Gap: The dock is hardcoded to dark obsidian colors (`bg-[#08090d]/85`, `bg-black/60`). It only anchors to 3 landing page sections (`#advantages`, `#simulator`, `#infrastructure`).
   - Gap: The Dashboard (`app/dashboard/page.tsx`) uses a flat sticky top bar (`sticky top-0`, `bg-white/80 dark:bg-[#000000]/90`) and has no floating dynamic dock, no morphing pill indicator, and no spring physics.
2. **Tab Selectors Current State**:
   - Dashboard View Mode toggle (Sandbox vs Live) in `dashboard/page.tsx` uses standard CSS classes without Framer Motion `layoutId` or spring morphing.
   - Timeframe pills in `PortfolioAnalytics.tsx` (1H, 6H, 1D, 1W, 1M, YTD, ALL) swap active classes instantly without sliding indicator or spring feedback.
   - Filter pills in `LiveTape.tsx` (ALL, BUY, SELL, CONSENSUS) and `TradeLog.tsx` (Holding, Closed, All) are static button groups.
3. **Sliders Current State**:
   - `LiquidSleeveSimulator.tsx` uses a native HTML range input (`<input type="range">`) with `accent-[#00D09C]`.
   - Lacks tactile glass thumb, haptic/fluid drag feedback, and visionOS specular bubble styling.
4. **Buttons Current State**:
   - `Button.tsx` implements `whileTap={{ scale: 0.98 }}`, but uses flat solid colors (`bg-slate-950 text-white`).
   - `BalanceCounter.tsx` action buttons (Mirror, Rebalance, Analytics, Reset) use flat rounded circles (`bg-[#F1F3F5] dark:bg-[#1C1D22]`) without optical liquid glass lens reflections.

### 1.5 Responsive Layout Bottlenecks (Desktop down to 390px Viewport)
1. **Dashboard Top Navigation Overcrowding**:
   - At 390px viewport width:
     - Left side: BrandLogo (~110px) + Toggle ("Sandbox (Paper Trading)" ~150px + "Live Trading · Unavailable (Gated)" ~190px) = ~450px.
     - Right side: 5 icon buttons (Theme, Bell, Sound, Settings, LogOut) = ~176px.
     - Total required width: >630px.
     - **Defect**: On 390px, this results in severe horizontal overflow or element compression. Button text is not truncated on mobile (e.g. no responsive labels like "Sandbox" / "Live").
2. **Missing Mobile Safe Area Insets**:
   - `LiquidGlassMobileDock.tsx` (line 140): `fixed bottom-4 inset-x-3`.
   - **Defect**: On iOS devices with home indicators (~34px bottom inset), `bottom-4` (16px) causes the dock to overlap the home indicator, triggering unwanted app-switching gestures. It requires `bottom-[calc(1rem+env(safe-area-inset-bottom,0px))]`.
   - Dashboard sticky navigation (`sticky top-0`) lacks `pt-[env(safe-area-inset-top,0px)]` for the iPhone Dynamic Island / notch.
   - Slide-over drawers (`TradeDrawer.tsx`, `WalletDrawer.tsx`, `ActivityFeed.tsx`) lack top and bottom safe-area insets.
3. **Table Horizontal Overflow on Mobile**:
   - `dashboard/page.tsx` Live Capital Positions (5 columns) and Execution Logs (8 columns) have no `min-w` container constraint and no responsive mobile card fallback.
   - `FullHistorySpreadsheetModal.tsx`: 10-column table requires aggressive horizontal scrolling inside a modal dialog on 390px.
4. **Cramped Mobile Card Padding**:
   - Several dashboard cards and settings containers use `p-6 sm:p-8` (24px padding on each side = 48px total). On a 390px viewport, this leaves only 342px for content. Cards inside containers lose an additional 32px-48px, causing text wrapping on numbers and timestamps.
   - Mode 3 in `LiquidGlassHeroCanvas.tsx`: 5-column grid on 390px forces columns into ~60px width, resulting in unreadable 7px text and truncated values.

---

## 2. Logic Chain

1. **Premise**: Requirement R2 mandates the elimination of artificial vector dumbbells, static graphic placeholders, cartoon canvas art, or watermarked mockups, replacing them with authentic Apple Liquid Glass across real UI containers.
   - **Evidence**: `frontend/src/components/landing/LiquidGlassHeroCanvas.tsx` lines 108 & 189 explicitly define a procedural "Dumbbell" SVG illustration.
   - **Inference**: The hero centerpiece must be transformed from an artificial vector dumbbell illustration into a genuine functional UI centerpiece (e.g., an authentic floating Liquid Glass Telemetry & Execution Cockpit or real interactive risk-sleeve container) with optical glass refraction, crystalline cyan highlights, and live execution data.
2. **Premise**: Requirement R1 requires an Arctic Glacier Blue (`#F0F7FF`, `#E0F2FE`), crisp white (`#FFFFFF`), and crystalline cyan (`#0284C7`, `#38BDF8`) palette with high-contrast typography (`#0F172A`, `#1E293B`).
   - **Evidence**: The landing page (`app/page.tsx`) is currently hardcoded to pitch black `#060709` (`.baleen-landing`), and its glass cards/docks use dark gradients (`bg-[#08090d]/85`, `linear-gradient(140deg, rgba(28, 32, 42, 0.65)...)`).
   - **Inference**: The landing page and dashboard must share the Arctic Glacier design tokens. The glass material classes (`.liquid-dock`, `.liquid-glass-card`, `.liquid-glass-lens`, `.apple-glass`) must be adapted with luminous white/ice tints, multi-pass blur, specular rim highlights, and high-contrast slate text.
3. **Premise**: Requirement R3 requires fluid morphing micro-interactions and a visionOS dynamic dock with smooth spring physics.
   - **Evidence**: While `LiquidGlassDock.tsx` on the landing page implements Framer Motion `layoutId="desktop-liquid-lens-bubble"` with spring physics, the Dashboard (`app/dashboard/page.tsx`) lacks a dynamic dock entirely—it uses a traditional sticky top bar with flat static buttons.
   - **Inference**: The visionOS Dynamic Dock architecture should be unified and extended to the Dashboard. On the Dashboard, it should provide a floating glass dock for primary view modes (Sandbox vs Live Capital), quick filters, and actions, featuring fluid pill morphing, tactile hover feedback, and spring physics (`stiffness: 400, damping: 30`).
4. **Premise**: Requirement R4 requires 100% fluid responsiveness across mobile (specifically 390px) and desktop without horizontal overflow or cramped text.
   - **Evidence**: The Dashboard top bar currently requires >630px of horizontal space for full-text buttons ("Sandbox (Paper Trading)" + "Live Trading · Unavailable (Gated)") and 5 circular action buttons. Mobile bottom docks lack `env(safe-area-inset-bottom)`.
   - **Inference**: Mobile navigation must use condensed labels ("Sandbox", "Live (Gated)"), collapse secondary controls into a tactile drawer/menu or bottom dock, incorporate safe-area insets (`env(safe-area-inset-bottom)` and `env(safe-area-inset-top)`), and use responsive card padding (`p-4 sm:p-6`) to prevent cramped layouts.

---

## 3. Caveats

1. **Backend Integration**: This investigation focused exclusively on the frontend component hierarchy (`frontend/src/`). Backend services in `backend/app/` were tested for baseline pass rate (2672 passed, 100%), but API endpoints were not modified.
2. **Third-Party Canvas Libraries**: `ShaderGradientBackground.tsx` and dependencies (`shadergradient`, `three`, `@react-three/fiber`) are currently present in `package.json` but not mounted in `page.tsx`. If 3D WebGL scenes are desired in future milestones, care must be taken to ensure they don't reintroduce dark themes or performance overhead on mobile.
3. **Authentication State Dependency**: Certain dashboard views (e.g. Live Capital configurations, API key settings) depend on session tokens. All interactive state transitions must preserve NextAuth session resilience as documented in `DashboardPage.tsx` (`lastUserIdRef`).

---

## 4. Conclusion

1. **Component Inventory**: The Baleen frontend comprises 44 React `.tsx` components across charts, landing, dashboard, and shared UI, plus 7 page routes (`/`, `/dashboard`, `/settings`, `/admin`, `/auth/login`, `/auth/signup`, `/_not-found`).
2. **R2 Compliance Targets**:
   - Eliminate the artificial vector dumbbell illustration in `LiquidGlassHeroCanvas.tsx` (lines 108, 189, 201-322).
   - Clean up or archive the 7 unused raster mockups (~7.3 MB) in `public/images/`.
   - Prune orphaned legacy components (`FeaturesGrid.tsx`, `ProfitSimulator.tsx`, `Leaderboard.tsx`, `ShaderGradientBackground.tsx`).
3. **Dynamic Dock & Interactive Architecture (R3)**:
   - Re-engineer the floating dock with genuine Arctic Liquid Glass: `backdrop-filter: blur(24px) saturate(190%)`, white specular crescent arcs, crystalline cyan borders, and fluid pill morphing via Framer Motion `layoutId`.
   - Introduce a unified visionOS dynamic dock experience to the Dashboard for view switching (Sandbox / Live Capital) and view controls.
   - Upgrade interactive controls (timeframe pills, filter pills, balance action buttons, and risk sleeve sliders) with tactile spring physics and liquid glass feedback.
4. **Responsive Layout Fixes (R4 & 390px Viewport)**:
   - Add responsive text truncation and collapsible icon clusters to the Dashboard top navigation.
   - Implement `env(safe-area-inset-bottom)` on mobile floating docks and `env(safe-area-inset-top)` on sticky headers and drawers.
   - Ensure tables in Live Capital and audit modals support horizontal scrolling with proper container min-widths (`min-w-[600px]`) and mobile touch targets.
   - Standardize mobile padding from `p-6`/`p-8` down to `p-4 sm:p-6` to maximize usable screen real estate.

---

## 5. Verification Method

### 5.1 Independent Verification Commands
1. **Frontend Production Build Verification**:
   ```bash
   cd c:\Users\arthu\repos\Baleen\frontend
   npm run build
   ```
   *Expected result*: Exit code 0, all 10 routes compiled statically or dynamically, zero TypeScript errors.
2. **Backend Regression Verification**:
   ```bash
   cd c:\Users\arthu\repos\Baleen\backend
   pytest
   ```
   *Expected result*: Exit code 0, 2672 passed, 57 skipped.
3. **Inspection of Vector Dumbbell Artifact**:
   Inspect `c:\Users\arthu\repos\Baleen\frontend\src\components\landing\LiquidGlassHeroCanvas.tsx` at line 108 and lines 201–322 to confirm the presence of the vector dumbbell SVG path and mode switcher.
4. **Inspection of Unreferenced Images**:
   Inspect `c:\Users\arthu\repos\Baleen\frontend\public\images` to verify the 7 unreferenced raster files.
5. **Responsive Viewport Verification (390px)**:
   In Chrome DevTools or Edge DevTools, set responsive emulation to 390px × 844px (iPhone 12/13/14/15/16). Check both `/` (landing) and `/dashboard`:
   - Verify zero horizontal document overflow (`document.documentElement.scrollWidth === window.innerWidth`).
   - Verify no clipping in the navigation dock or header buttons.
   - Verify mobile bottom dock clears the iOS home indicator safe area.

### 5.2 Invalidation Conditions
This report's findings would be invalidated if:
- `LiquidGlassHeroCanvas.tsx` is shown to be a required institutional financial widget rather than a placeholder illustration.
- The user explicitly requests a pitch-black matte metallic theme instead of the Arctic Glacier Blue & crisp white palette specified in the 2026-09-14T11:52:24Z update.
