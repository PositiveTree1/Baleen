# Plan: Baleen End-to-End Orchestration

## Objective
Deliver verified implementation and rigorous testing across Baleen codebase:
1. R1: Authentic On-Chain Trade History & Real Classification
2. R2: Dual-Column Daily Wins & Losses Chart Rendering (`DailyWinLossBarChart.tsx`)
3. R3: Overnight Paper Trading Execution & State Machine Invariance (`live_poller.py`)
4. Acceptance: 100% backend pytest pass, Next.js frontend builds with 0 TS/lint errors (`npm run build`), dual-column chart renders properly, live poller executes cleanly with 0 negative balances.

## Strategy & Workflow
1. **Survey (Phase 0)**:
   - Spawn 3 parallel Explorers to analyze backend ingestion, frontend chart component, and live paper-trading state machine.
2. **Decomposition & Project Scope (Phase 1)**:
   - Synthesize survey findings into `PROJECT.md` and feature inventory.
   - Establish `TEST_INFRA.md` for dual-track E2E testing.
3. **Execution (Phase 2)**:
   - Delegate implementation milestones to sub-orchestrators executing the full iteration loop: Explorer -> Worker -> Reviewers (2) -> Challengers (2) -> Forensic Auditor (`teamwork_preview_auditor`).
   - Run parallel E2E Testing Track.
4. **Final Acceptance & Hardening (Phase 3)**:
   - Verify 100% pass of test suite across backend and frontend.
   - Adversarial coverage hardening.
   - Report final verified completion back to parent / Sentinel.
