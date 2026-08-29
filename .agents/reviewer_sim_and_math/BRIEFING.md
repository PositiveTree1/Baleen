# BRIEFING — 2026-08-29T11:11:15Z

## Mission
Independently review, stress-test, and verify all findings related to Paper Trading Simulation and Quantitative Mathematics across the Baleen codebase and survey handoff reports.

## 🔒 My Identity
- Archetype: reviewer_and_adversarial_critic
- Roles: reviewer, critic
- Working directory: c:\Users\arthu\Documents\Baleen-master\.agents\reviewer_sim_and_math\
- Original parent: d751e07b-83a8-45f8-b1a6-dc64b9f42d3b
- Milestone: Simulation & Quantitative Math Review
- Instance: 2 of 3

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Mandatory integrity checking (no fake passes, no facade implementations, verify formulas mathematically)
- Evidence-based verdicts: APPROVE or REQUEST_CHANGES

## Current Parent
- Conversation ID: d751e07b-83a8-45f8-b1a6-dc64b9f42d3b
- Updated: 2026-08-29T11:11:15Z

## Review Scope
- **Files to review**:
  - `backend/app/services/live_poller.py`
  - `backend/app/services/mark_to_market.py`
  - `backend/app/services/polymarket_fees.py`
  - `backend/app/sizing/fill_simulator.py`
  - `backend/app/sizing/slippage.py`
  - `backend/app/sizing/dynamic_sizer.py`
  - `backend/app/discovery/scanner.py`
  - `backend/app/scoring/engine.py`
  - `backend/app/scoring/basket.py`
  - `listener/src/event-processor.ts`
  - `frontend/src/components/landing/ProfitSimulator.tsx`
  - `backend/app/api/execution_logs.py`, `wallets.py`, `signals.py`
- **Interface contracts**: PROJECT.md, ORIGINAL_REQUEST.md, baleen-spec-v2.md
- **Review criteria**: Mathematical soundness, Polymarket 2026 fee schedule, directional slippage realism, PnL accounting integrity, Wilson score bounds, EV gates & Kelly sizing, exponential compounding realism.

## Review Checklist
- **Items reviewed**:
  - User Realized PnL accounting & double-counting bug (VERIFIED - CRITICAL)
  - Fee-Aware EV gate formula & alpha inversion (VERIFIED - CRITICAL)
  - Production bypass of fill simulator, dynamic sizer, and slippage (VERIFIED - HIGH)
  - Listener CTF Exchange parser asset ID 0 & side inversion bug (VERIFIED - HIGH)
  - Synthetic win rate / Wilson lower bound fabrication in scanner (VERIFIED - MEDIUM)
  - Synthetic 45-day PnL timeline generation via MD5 in wallets API (VERIFIED - MEDIUM)
  - Unreachable dead code in `scanner.py` (VERIFIED - MEDIUM)
  - Threshold divergence across scanner, scoring engine, and worker (VERIFIED - MEDIUM)
  - Unconstrained exponential compounding in ProfitSimulator (VERIFIED - MEDIUM)
  - Unrealized MTM gains treated as liquid free cash (VERIFIED - MEDIUM)
- **Verdict**: REQUEST_CHANGES (due to Critical PnL accounting integrity violation, EV gate alpha inversion, simulation bypasses, and synthetic metric fabrication)
- **Unverified claims**: None. All claims mathematically and empirically validated.

## Attack Surface
- **Hypotheses tested**:
  - Mathematical proof of double PnL realization on user trades
  - Proof of EV gate rejecting high-alpha toss-up markets and passing negative-EV favorites
  - Proof of slippage function rejecting favorable price improvements
  - Proof of zero-division / price corruption in fill simulator
  - Proof of scoring engine spec threshold violations causing 3 pytest test failures
- **Vulnerabilities found**: 10 distinct findings (2 Critical, 2 High, 6 Medium)
- **Untested angles**: Live external Polymarket network latency (outside codebase scope)

## Key Decisions Made
- Issue explicit verdict of **REQUEST_CHANGES**.
- Provide complete mathematical derivations, code line citations, and concrete remediation patches for all 10 findings in `handoff.md`.

## Artifact Index
- `.agents/reviewer_sim_and_math/handoff.md` — Comprehensive simulation and quantitative review report
- `.agents/reviewer_sim_and_math/progress.md` — Liveness and progress heartbeat
- `.agents/reviewer_sim_and_math/DISPATCH.md` — Dispatch prompt log
