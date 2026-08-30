# Handoff Report — Requirement R2: Dual-Column Daily Wins & Losses Chart Survey

**Agent**: `survey_explorer_2`  
**Date**: 2026-08-30  
**Mission**: Codebase survey for Requirement R2 (Dual-Column Daily Wins & Losses Chart Rendering)  
**Analysis Reference**: `c:\Users\arthu\Documents\Baleen-master\.agents\survey_explorer_2\analysis.md`

---

## 1. Observation

1. **Component Location & Implementation**:
   - `DailyWinLossBarChart.tsx` is located at `c:\Users\arthu\Documents\Baleen-master\frontend\src\components\charts\DailyWinLossBarChart.tsx`.
   - It is imported and rendered inside `WalletDrawer.tsx` (`frontend/src/components/dashboard/WalletDrawer.tsx:10, 284`).
   - The chart renders two `<Bar>` series:
     - `dataKey="wonUsd"` with `fill="#00D09C"`, `name="Gross Won"`, `maxBarSize={18}`, `radius={[4, 4, 0, 0]}`.
     - `dataKey="lostUsd"` with `fill="#FF453A"`, `name="Gross Lost"`, `maxBarSize={18}`, `radius={[0, 0, 4, 4]}`.
   - It includes a `<ReferenceLine y={0} stroke="rgba(0,0,0,0.18)" strokeWidth={1} />` separating positive wins from negative losses.
   - It includes a custom `<Tooltip />` displaying Won (`#00D09C`), Lost (`#FF453A`), Net P&L (color-coded), and trade count.

2. **Data Model & Ingestion Pipeline**:
   - `DailyPnLPoint` interface in `frontend/src/types/index.ts:25-33`:
     ```typescript
     export interface DailyPnLPoint {
       date: string;
       wonUsd?: number;
       lostUsd?: number;
       netPnL?: number;
       dailyPnL: number;
       cumulativePnL: number;
       tradesCount: number;
     }
     ```
   - In `frontend/src/lib/api-client.ts:193-201`, `fetchWallet(address)` maps backend `daily_pnl_history` items:
     - `wonUsd: d.won_usd ?? Math.max(0, d.daily_pnl ?? 0)` (always `>= 0`)
     - `lostUsd: d.lost_usd ?? (d.daily_pnl < 0 ? d.daily_pnl : 0)` (always `<= 0`, negative number)
     - `netPnL: d.net_pnl ?? d.daily_pnl ?? 0`
   - In `backend/app/discovery/scanner.py:277-285` and `backend/app/api/wallets.py:296-304`, the backend computes daily won and lost aggregates, with `won_usd >= 0` and `lost_usd <= 0`.

3. **Timeframe Filtering Logic**:
   - In `WalletDrawer.tsx:58-76`, `timeframe` supports `'1W'`, `'1M'`, `'YTD'`, and `'ALL'`.
   - Data is filtered against timestamps computed from `Date.now()` and current year start.

4. **Build & Lint Verification**:
   - Running `npm run build` (`next build`) in `c:\Users\arthu\Documents\Baleen-master\frontend` exited with code 0 (Turbopack compiled successfully, TypeScript completed with 0 errors, 10/10 routes generated).
   - `DailyWinLossBarChart.tsx` has 0 TypeScript errors and 0 ESLint errors.

---

## 2. Logic Chain

1. **From Requirements to Implementation Scope**:
   - Requirement R2 mandates: (a) green bar (`#00D09C`) for `wonUsd`, (b) red bar (`#FF453A`) for `lostUsd`, (c) clean visual alignment and zero clipping across timeframes (`1W`, `1M`, `YTD`, `ALL`), (d) accurate interactive tooltips.
   - Observation 1 confirms that `DailyWinLossBarChart.tsx` already uses the exact colors `#00D09C` and `#FF453A`.

2. **From Data Structure to Dual-Column Rendering**:
   - Because `wonUsd` is positive and `lostUsd` is negative, and `stackId` is omitted on `<Bar>`, Recharts renders them as two separate side-by-side vertical columns per day: one extending up from `y=0` to `wonUsd`, and one extending down from `y=0` to `lostUsd`.
   - The `<ReferenceLine y={0} />` provides the shared baseline.

3. **From Viewport Responsiveness to Clipping Prevention**:
   - With `margin.left = -10` and large negative dollar values, tick labels could graze container edges on narrow viewports.
   - Constraining `<YAxis width={42} />` and adding `minTickGap={20}` on `<XAxis />` prevents both Y-axis label clipping and X-axis date collision on large datasets (`YTD`, `ALL`).

4. **From Timeframe Handling to UX Consistency**:
   - When filtering by `1W` or `1M` on wallets with older trade history, returning an empty array rather than falling back to full `raw` history ensures the chart displays the appropriate empty-state message: `"No trade history recorded in selected timeframe"`.

---

## 3. Caveats

1. **Node/NPM Execution on Windows**: Running `npm` directly in PowerShell can trigger script execution policy restrictions; `npm.cmd` should always be executed explicitly in command lines on Windows.
2. **ESLint Strict Rules in Other Modules**: While `DailyWinLossBarChart.tsx` has 0 lint issues, peripheral dashboard/modal files have ESLint warnings/errors under ESLint v9 flat config.

---

## 4. Conclusion

Requirement R2 is fundamentally sound and well-structured across the backend data models and frontend components. The chart is fully integrated into `WalletDrawer.tsx`, correctly displays dual-column won/lost gross figures per day with exact branding colors (`#00D09C` and `#FF453A`), and builds with 0 TypeScript errors in Next.js 16 Turbopack.

Key recommendations for final polish:
- Ensure `<XAxis minTickGap={20} />` is set to guarantee zero tick collision on dense timeframes (`YTD`, `ALL`).
- Ensure `<YAxis width={42} />` is specified to guarantee zero clipping on large currency values.
- In `WalletDrawer.tsx`, return `filtered` (even if empty) so the empty-state banner renders appropriately.

---

## 5. Verification Method

To independently verify the frontend chart and build:
1. **Next.js Production Build**:
   ```powershell
   $env:PATH = "C:\Program Files\nodejs;$env:PATH"
   cd c:\Users\arthu\Documents\Baleen-master\frontend
   npm.cmd run build
   ```
   *Expected Result*: Exit code 0, 0 TypeScript errors, 10/10 routes successfully generated.

2. **Inspect Chart Source Code**:
   - Inspect `c:\Users\arthu\Documents\Baleen-master\frontend\src\components\charts\DailyWinLossBarChart.tsx` for bar colors `#00D09C` and `#FF453A`, custom tooltip, and zero reference line.
   - Inspect `c:\Users\arthu\Documents\Baleen-master\frontend\src\components\dashboard\WalletDrawer.tsx` for timeframe state handling (`'1W' | '1M' | 'YTD' | 'ALL'`).
