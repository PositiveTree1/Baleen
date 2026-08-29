## 2026-08-29T22:29:05Z
You are the M3 Frontend UI Worker for the Baleen codebase.
Working directory for your metadata: c:\Users\arthu\Documents\Baleen-master\.agents\worker_m3
Project root: c:\Users\arthu\Documents\Baleen-master

MANDATORY: Read the original user request at:
c:\Users\arthu\Documents\Baleen-master\.agents\ORIGINAL_REQUEST.md
Also read PROJECT.md at c:\Users\arthu\Documents\Baleen-master\PROJECT.md
Also read survey findings at c:\Users\arthu\Documents\Baleen-master\.agents\explorer_r3_survey\survey_r3.md

Files owned exclusively by you:
- `frontend/src/components/modals/ResetSandboxModal.tsx`
- `frontend/src/components/common/Modal.tsx`
- `frontend/src/components/charts/DailyWinLossBarChart.tsx`
- `frontend/src/components/charts/CumulativePnLChart.tsx`

Tasks:
1. In `frontend/src/components/modals/ResetSandboxModal.tsx`: add dark mode classes (`dark:bg-[#16171B] dark:border-white/10 dark:text-white dark:text-zinc-300 dark:border-zinc-700`) to modal container, header, input, and buttons.
2. In `frontend/src/components/common/Modal.tsx`: ensure dark mode background and border classes are present (`dark:bg-[#16171B] dark:border-white/10 dark:text-white`).
3. In `frontend/src/components/charts/DailyWinLossBarChart.tsx` and `frontend/src/components/charts/CumulativePnLChart.tsx`: ensure empty states support dark theme (`dark:bg-[#1C1D22] dark:text-zinc-400`).
4. In `frontend/`: run production build `npm run build` and `npm run lint` to verify 100% clean compilation, 0 TypeScript errors, and 10/10 generated routes.
