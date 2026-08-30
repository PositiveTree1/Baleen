# Comprehensive Codebase Survey: Requirement R2 — Dual-Column Daily Wins & Losses Chart Rendering

## 1. Executive Summary

Requirement R2 mandates the frontend rendering of an authentic, responsive, dual-column daily win/loss chart (`DailyWinLossBarChart.tsx`) within the Baleen whale drawer:
- **Green Bar (`#00D09C`)**: Represents daily gross won profits (`wonUsd`).
- **Red Bar (`#FF453A`)**: Represents daily gross losses (`lostUsd`).
- **Visual Integrity**: Clean visual alignment, zero chart clipping across timeframes (`1W`, `1M`, `YTD`, `ALL`), responsive SVG sizing, zero collision on date ticks, and accurate interactive tooltips with net P&L calculations.

This survey provides an exhaustive review of the frontend charting architecture, data models, API hydration pathways, timeframe filtering mechanisms, Recharts rendering mechanics, build/type/lint configurations, visual edge cases, and concrete recommendations for implementation.

---

## 2. Architecture & Component Inventory

### 2.1 Component Map
| File | Role | Props / State |
|---|---|---|
| `src/components/charts/DailyWinLossBarChart.tsx` | Pure charting component rendering dual-column daily bars | `data: DailyPnLPoint[]` |
| `src/components/charts/CumulativePnLChart.tsx` | Sibling chart component rendering cumulative equity area curve | `data: PnLPoint[]` |
| `src/components/charts/ScoreHistoryChart.tsx` | Sibling chart component rendering whale score history line | `data: { date: string; score: number }[]` |
| `src/components/dashboard/WalletDrawer.tsx` | Drawer container managing whale profile view, timeframe state, and chart sub-tabs | `address: string \| null`, `onClose: () => void` |
| `src/app/dashboard/page.tsx` | Top-level dashboard page controlling `selectedWallet` state | `selectedWallet: string \| null` |
| `src/lib/api-client.ts` | Data hydration layer fetching `/api/wallets/{address}` and mapping daily PnL history | `fetchWallet(address)` |
| `src/types/index.ts` | TypeScript interface definitions for `DailyPnLPoint`, `WalletDetail`, and `Wallet` | `DailyPnLPoint`, `WalletDetail` |
| `src/lib/formatters.ts` | Locale-aware currency and date formatting utilities (`formatFrenchDate`, `formatCompactPnL`, `formatExactPnL`) | Formatting functions |

### 2.2 Trigger & User Journey
1. User interacts with any whale row in `WalletLeaderboard.tsx`, `LiveTape.tsx`, or `TradeLog.tsx`.
2. `DashboardPage` updates `selectedWallet = wallet.address`, mounting `<WalletDrawer address={selectedWallet} onClose={...} />`.
3. `WalletDrawer` invokes `fetchWallet(address)`, receiving `WalletDetail` containing `dailyPnLHistory: DailyPnLPoint[]`.
4. `WalletDrawer` defaults `activeChartTab` to `'winloss'` and `timeframe` to `'ALL'`.
5. `filteredDailyPnLHistory` is computed via `useMemo` based on `timeframe` (`'1W' | '1M' | 'YTD' | 'ALL'`).
6. `<DailyWinLossBarChart data={filteredDailyPnLHistory} />` is mounted inside a responsive container (`h-56 w-full`).

---

## 3. Data Pipeline & Schema Analysis

### 3.1 Data Model (`src/types/index.ts`)
```typescript
export interface DailyPnLPoint {
  date: string;          // ISO date format 'YYYY-MM-DD'
  wonUsd?: number;       // Gross daily profit ($ >= 0)
  lostUsd?: number;      // Gross daily loss ($ <= 0, negative number)
  netPnL?: number;       // Net daily PnL (wonUsd + lostUsd)
  dailyPnL: number;      // Fallback/standard daily PnL
  cumulativePnL: number; // Running cumulative PnL
  tradesCount: number;   // Number of trades resolved on that date
}
```

### 3.2 Backend Emission & API Hydration
The backend generates `daily_pnl_history` through three distinct pathways in `backend/app/api/wallets.py` and `backend/app/discovery/scanner.py`:

1. **Direct DB Trade Grouping (`wallets.py:274-305`)**:
   - Groups resolved executions by `executed_at.strftime("%Y-%m-%d")`.
   - `won_usd`: Sum of `realized_pnl_usd` where `pnl >= 0` (positive).
   - `lost_usd`: Sum of `realized_pnl_usd` where `pnl < 0` (negative).
   - `net_pnl = won_usd + lost_usd`.
   - `cumulative_pnl = running sum of net_pnl`.

2. **Cached Daily History (`wallets.py:308-315`)**:
   - Reads `wallet.cached_daily_pnl` serialized JSON array.

3. **Live On-Chain Scanner Calculation (`scanner.py:266-285`)**:
   - Analyzes Polymarket Data API `/positions`, `/activity`, and `/trades`.
   - Calculates daily won and lost amounts:
     - `won_usd = round(d_info["won"], 2)` (>= 0)
     - `lost_usd = round(-abs(d_info["lost"]), 2)` (<= 0)
     - `daily_pnl = round(d_info["net"], 2)`

### 3.3 Frontend Client Normalization (`src/lib/api-client.ts:193-201`)
```typescript
dailyPnLHistory: (data.daily_pnl_history || []).map((d: any) => ({
  date: d.date,
  wonUsd: d.won_usd ?? Math.max(0, d.daily_pnl ?? 0),
  lostUsd: d.lost_usd ?? (d.daily_pnl < 0 ? d.daily_pnl : 0),
  netPnL: d.net_pnl ?? d.daily_pnl ?? 0,
  dailyPnL: d.daily_pnl ?? 0,
  cumulativePnL: d.cumulative_pnl ?? 0,
  tradesCount: d.trades_count ?? 0
}))
```
*Note on sign convention*: `wonUsd` is always positive or zero (`>= 0`), and `lostUsd` is always negative or zero (`<= 0`). This sign structure allows standard Cartesian zero-baseline bar charting.

---

## 4. Timeframe Filtering Analysis

### 4.1 Filter Implementation in `WalletDrawer.tsx`
```typescript
const filteredDailyPnLHistory = useMemo(() => {
  const raw = wallet?.dailyPnLHistory || [];
  if (timeframe === 'ALL' || raw.length === 0) return raw;
  const now = Date.now();
  let cutoff = 0;
  if (timeframe === '1W') cutoff = now - 7 * 24 * 60 * 60 * 1000;
  else if (timeframe === '1M') cutoff = now - 30 * 24 * 60 * 60 * 1000;
  else if (timeframe === 'YTD') cutoff = new Date(new Date().getFullYear(), 0, 1).getTime();

  const filtered = raw.filter(pt => {
    try {
      const t = new Date(pt.date).getTime();
      return !isNaN(t) && t >= cutoff;
    } catch {
      return true;
    }
  });
  return filtered.length > 0 ? filtered : raw;
}, [wallet?.dailyPnLHistory, timeframe]);
```

### 4.2 Behavior Across Timeframes
- **1W (1 Week)**: Filters to the last 7 calendar days. Typically produces 1–7 bars.
- **1M (1 Month)**: Filters to the last 30 calendar days. Typically produces 5–30 bars.
- **YTD (Year-To-Date)**: Filters from January 1st of the current year (`2026-01-01`).
- **ALL**: Returns all historical daily data points without date bounds.

### 4.3 Fallback Edge Case
If `filtered.length === 0` (e.g. an inactive whale with no trades in the last 7 days when `1W` is clicked), line 75 currently falls back to `raw` (all history).
- *Observation*: Falling back to `raw` might display 100 days of history even when `1W` is selected.
- *Recommendation*: If `filtered` is empty, passing `[]` allows `DailyWinLossBarChart` to render its designated empty-state message: `"No trade history recorded in selected timeframe"`.

---

## 5. Chart Rendering & Visual Mechanics (`DailyWinLossBarChart.tsx`)

### 5.1 Recharts Layout Architecture
- `<ResponsiveContainer width="100%" height="100%" className="outline-none">`
- `<BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }} stackOffset="sign" className="outline-none">`
- `<CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" vertical={false} />`
- `<ReferenceLine y={0} stroke="rgba(0,0,0,0.18)" strokeWidth={1} />`

### 5.2 Dual-Column Rendering Mechanics
1. **Side-by-Side Dual Columns**:
   - In Recharts, when `stackId` is omitted from `<Bar>`, bars are placed side-by-side in each date slot.
   - `wonUsd` Bar (`fill="#00D09C"`, `name="Gross Won"`, `maxBarSize={18}`, `radius={[4, 4, 0, 0]}`):
     - Values are positive (`>= 0`).
     - Extends upwards from `y=0` to `y=wonUsd`.
     - Top corners are rounded with 4px radius (`radius={[4, 4, 0, 0]}`).
   - `lostUsd` Bar (`fill="#FF453A"`, `name="Gross Lost"`, `maxBarSize={18}`, `radius={[0, 0, 4, 4]}`):
     - Values are negative (`<= 0`).
     - Extends downwards from `y=0` to `y=lostUsd`.
     - Bottom corners are rounded with 4px radius (`radius={[0, 0, 4, 4]}`).
2. **Zero Baseline Alignment**:
   - The `<ReferenceLine y={0} stroke="rgba(0,0,0,0.18)" strokeWidth={1} />` provides a crisp visual axis separating winning profits above from losses below.

### 5.3 Interactive Tooltip Design
```tsx
<Tooltip 
  isAnimationActive={false}
  cursor={{ fill: 'rgba(99, 102, 241, 0.08)' }}
  content={({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const pt = payload[0].payload as DailyPnLPoint;
      const won = pt.wonUsd ?? Math.max(0, pt.dailyPnL);
      const lost = pt.lostUsd ?? (pt.dailyPnL < 0 ? pt.dailyPnL : 0);
      const net = pt.netPnL ?? pt.dailyPnL;
      const trades = pt.tradesCount ?? 1;

      return (
        <div className="bg-white/95 dark:bg-[#1C1D22]/95 backdrop-blur-xl p-3.5 rounded-2xl border border-black/[0.08] dark:border-white/10 shadow-xl text-slate-900 dark:text-white min-w-[170px]">
          <div className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-bold uppercase tracking-wider mb-2 flex items-center justify-between">
            <span>{label}</span>
            <span className="font-mono text-slate-500 dark:text-[#8E8F99]">{trades} trades</span>
          </div>

          <div className="space-y-1.5 font-mono text-xs">
            <div className="flex items-center justify-between text-emerald-600 dark:text-[#00D09C] font-bold">
              <span className="font-sans text-slate-500 dark:text-[#8E8F99] font-medium">Won:</span>
              <span>+${won.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>
            <div className="flex items-center justify-between text-rose-600 dark:text-[#FF453A] font-bold">
              <span className="font-sans text-slate-500 dark:text-[#8E8F99] font-medium">Lost:</span>
              <span>-${Math.abs(lost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>
            <div className="pt-1.5 border-t border-black/[0.06] dark:border-white/10 flex items-center justify-between font-extrabold text-sm">
              <span className="font-sans text-slate-700 dark:text-slate-200 text-xs font-semibold">Net P&L:</span>
              <span className={net >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}>
                {net >= 0 ? '+' : '-'}${Math.abs(net).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  }}
/>
```
- **Tooltip Content**:
  - Header: Date label and number of executed trades.
  - Won Row: `+$XX.XX` in emerald/`#00D09C`.
  - Lost Row: `-$XX.XX` in rose/`#FF453A`.
  - Net P&L Row: `+$XX.XX` or `-$XX.XX` with dynamic color based on sign.

---

## 6. Layout & Clipping Prevention Analysis

### 6.1 Left Margin & Y-Axis Label Width
- **Observation**: `margin={{ top: 10, right: 10, left: -10, bottom: 0 }}`.
- **Potential Issue**: Negative left margin (`left: -10`) pulls Y-axis text leftward. For large negative values like `-$1.2M` or `-$450k`, tick strings can get slightly clipped against the left container boundary on small viewport screens.
- **Remedy**: Adjusting `margin={{ top: 10, right: 10, left: -15, bottom: 0 }}` with an explicit `width={45}` on `<YAxis />` ensures zero clipping.

### 6.2 X-Axis Tick Collision on High-Density Timeframes
- **Observation**: For `YTD` or `ALL` with 50–150+ daily data points, French date strings (e.g. `'25 août'`) can collide if tick gap is not constrained.
- **Remedy**: Adding `minTickGap={24}` or `interval="preserveStartEnd"` on `<XAxis />` guarantees clean spacing without label overlap.

### 6.3 Bar Width Scaling (`maxBarSize={18}`)
- Setting `maxBarSize={18}` ensures that when only 2–5 days exist (e.g. `1W` timeframe), bars maintain a slender, modern aesthetic and do not stretch to 100px wide.

---

## 7. Build, Typecheck, and Linter Status

### 7.1 Build Command (`npm run build` / `next build`)
- **Status**: **PASSED (Exit code 0)**.
- **Details**:
  - Turbopack compilation succeeded in 2.4s.
  - TypeScript checking completed in 8.3s with **0 TypeScript errors**.
  - All 10 Next.js routes prerendered / dynamic endpoints verified (`/`, `/admin`, `/auth/login`, `/auth/signup`, `/dashboard`, `/settings`, `/api/auth/[...nextauth]`, `/api/debug-env`, `/_not-found`).

### 7.2 Lint Command (`npm run lint` / `eslint`)
- **Status**: 61 errors, 115 warnings across peripheral components (mainly `@typescript-eslint/no-explicit-any`, `react-hooks/set-state-in-effect`, and `@typescript-eslint/no-unused-vars` in files like `api-client.ts`, `auth.ts`, `TypewriterText.tsx`, `ThemeContext.tsx`, `CommandPalette.tsx`).
- **DailyWinLossBarChart.tsx**: **0 ESLint errors and 0 ESLint warnings**.

---

## 8. Summary of Findings & Concrete Recommendations for R2

| Dimension | Current State | Recommendation for Implementation |
|---|---|---|
| **Bar Series Colors** | Green `#00D09C` for `wonUsd`, Red `#FF453A` for `lostUsd` | Perfectly configured matching R2 spec |
| **Dual-Column Layout** | Rendered as separate side-by-side columns per date | Keep side-by-side grouped rendering with zero-line reference |
| **Tooltip Styling** | Shows Won, Lost, Net P&L, and trade count with dark-mode support | Add `formatFrenchDate(label)` to tooltip header for consistency |
| **Y-Axis Margins** | `margin.left = -10` | Set explicit `width={42}` and `margin={{ top: 10, right: 10, left: -12, bottom: 0 }}` to guarantee zero clipping |
| **X-Axis Tick Density** | Default interval | Add `minTickGap={20}` on `<XAxis />` to avoid overlap on long history (`YTD`, `ALL`) |
| **Timeframe Filter Empty State** | Fallback to `raw` when `filtered.length === 0` | Return empty array so chart displays graceful empty state |
| **Next.js Production Build** | Compiles with 0 errors | Verify build continuously after any modifications |
