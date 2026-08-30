## 2026-08-31T00:30:58Z

You are R2 Sizing Explorer.
Working directory: c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_r2
Original Request: c:\Users\arthu\Documents\Baleen-master\.agents\ORIGINAL_REQUEST.md

Task:
Perform a deep survey and technical investigation for Requirement 2 (R2):
"Sample-Size Damped Dynamic Sleeve Budget Sizing"
- Audit the dynamic sleeve adjustment calculation in `backend/app/sizing/sleeve_manager.py`, `backend/app/sizing/dynamic_sizing.py`, and any Supabase audit views or models.
- Investigate how low-trade-count whales (e.g. `SitsToPee` with N < 15 trades, or N=1, 2, 5) currently have their budget adjusted or slashed.
- Design a Bayesian credibility / sample-size shrinkage prior ($N < 15$ trades) so low-trade-count whales remain anchored near their $1,000 base sleeve (within 10%, i.e. $900-$1,100) and cannot have their budget violently slashed without statistically significant sample evidence.
- Design smooth EMA adjustments that scale over dozens of trades with bounded per-trade adjustment sensitivity.
- Identify all affected files, line numbers, schema/DB queries, and existing tests in `backend/tests/`.

Deliverables:
- Write your complete findings and mathematical specification to `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_r2\analysis.md` and `handoff.md`.
- Send a completion message back to the orchestrator.
