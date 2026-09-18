# Wallet implementation and independent review — September 17, 2026

## September 18 engineering follow-up

Implemented and verified locally; GitHub push, production migrations and the Supabase cutover are left to Gemini. Use [the operational handoff](GEMINI_WALLET_CUTOVER.md).

- Transactional, idempotent statistics reset with archives, preserved addresses/first-seen dates, preserved financial records, and a generation fence. A PostgreSQL concurrency test verifies that an evidence fetch started before reset cannot write afterward. Frontend cache namespaces/generation headers invalidate old wallet cache entries.
- Migrations 20–22 add reset archives, immutable point-in-time wallet observations and forward book observations. Current evidence remains in migration 19's table.
- Production discovery now routes to the verified evidence collector; the legacy heuristic evaluator is no longer the discovery entry point. Metadata refresh cannot overwrite V2 statistics or falsely update the scoring timestamp.
- The account-owned live path already had a persisted fixed `copy_ratio`. It now shares checked share-scaling arithmetic with the new replay, records allocation-limited exits, and rejects ratio changes while source inventory or unresolved orders remain. The legacy paper/backtesting paths are separate and are not thereby converted into faithful copying.
- After statistics cutover, new account-owned BUYs require fresh generation-matching research approval before signing and again at submission. SELL eligibility is preserved. No collector or replay creates execution approval.
- An independent Decimal ledger handles buys, partial sells, reopening, funding, transfers with supplied valuation, binary splits/merges, redemptions, fees and income; missing inventory/marks and conflicting event identities fail explicitly. This is tested accounting machinery, not a claim that every audited wallet's full history has been mapped and reconciled.
- Proportional replay tests cover $20/$100/$1,000 accounts, 1:3:6 entries, partial exits, minimums, depth, cash shortages, precision and missing evidence. Replay consumes explicit observations and reports actual observed delays. It never submits orders or invents a historical fill.
- Current accounting ZIPs are parsed with bounded size, freshness and equity/position reconciliation. Dreamlawn's fresh September 18 observation reports $43.528364 cash plus $14,204.574350 positions = $14,248.102714 equity. This is not lifetime P&L or verified historical strategy capital.
- After cutover, a bounded 30-second job rotates fresh watchlist/research candidates and records source windows, actual books and fee responses without orders. Partial coverage and failures remain explicit; failed wallets do not starve other candidates. Receipt reconciliation is still required before overlapping windows can become a replay input.

Verification: **2,806 full backend tests passed**, including real PostgreSQL integration; **12 listener tests passed**; **Next.js production build passed**. The subsequent metadata-refresh regression/API checks passed separately. See `research/backend-tests-reset-2026-09-18.txt`, `research/listener-tests-reset-2026-09-17.txt`, `research/frontend-build-reset-2026-09-18.txt`, and `research/wallet-api-reset-final-2026-09-18.txt`.

**Not finished:** production replacement of the legacy paper simulator, wallet-history-to-ledger mapping and independent historical reconciliation, account-specific strategy-capital baselines, enough prospective resolved outcomes, and held-out strategy/baseline comparison. Consequently this remains a research-mode deployment; do not describe it as the complete activated trading strategy.

## Decision

Integrate verified provider data and research classification now. Do not declare the proposed trading strategy ready for automatic allocation. No production database reset, deployment, wallet deletion, or liquidation was performed in this work.

Gemini's regression results are useful, but its report maps synthetic software tests to empirical requirements they do not establish:

- `test_dynamic_sizing.py::test_risk_cap_overrides_raw_calculation` explicitly tests clipping, not a fixed multiplier preserving all leader legs.
- `test_sleeve_manager.py::test_conviction_percentile_sizing` tests percentile sizing, which is different from the proposed proportional copying.
- `test_paper_run_isolation.py` tests data separation. It is not a fresh forward trial with measured independent outcomes.
- Engine and adversarial unit tests do not supply a point-in-time wallet population, untouched evaluation sample, or measured comparisons against cash and simpler selection policies.
- Provider component identities and receipt spot checks are useful reconciliation evidence; they are not an independently reconstructed lifetime ledger for every candidate.

The original report is retained with a review notice. `WALLET_STRATEGY_LOGIC.md` remains the authoritative strategy proposal.

## Implemented in the application

- V2 cursor collection with explicit terminal coverage, fixed windows, maker and taker fills, identity and timestamp validation, bounded page budgets, and failure reasons. Identical diagnostic fill keys are preserved because separate fills can share them.
- Thirty full UTC days of fill counts, 7/30-day averages, daily peaks, active days, and provider trade/economic P&L. Lifetime distinct markets are explicitly separate from fill counts.
- Activity/trade multiset reconciliation; open and closed position cursor coverage; marked open-position value and unrealized P&L. Position value is not labelled total strategy capital. Source timestamps, block, fidelity, observation time and limitations accompany evidence.
- Classifications: needs data, excluded, watchlist, research candidate. The 2–30/day target uses full calendar windows; a daily burst above 30 also fails this conservative raw-fill screen. Sparse wallets remain in the registry.
- A versioned `wallet_evidence` table (migration 19), 24-hour evidence refresh and bounded batches of 25 retained wallets, independent of whether a wallet trades during discovery. Oldest missing/stale evidence is processed first.
- Discovery revisits retained identities even when absent from leaderboards and recent trades. The existing multi-period leaderboard path found the niche chart examples; low views are not a qualification factor.
- A read-only `/api/wallets/{address}/research` route returns cached or freshly collected evidence, with a 45-second request budget. It does not insert arbitrary addresses into the registry.
- Wallet details use the provider's V2 economic P&L curve, or a labelled evidence cache. Partial closed-position reconstructions cannot substitute. The first observed cumulative point is not booked as one day's profit. Unknown fill counts and equity drawdown are not invented. Daily chart labels describe P&L changes rather than realized wins/losses.
- On-demand wallet registration requires verified ALL-time P&L >= $50,000 and no longer assigns fabricated win rate, score, activity or trade count.
- Legacy heuristic scores alone cannot promote the proposed roster. Research collection never sets execution approval. Basket refresh demotes unvalidated entries to tracked; existing trade rows are preserved and the poller separately follows sources of open positions for exits.

## Fresh Dreamlawn check

The production collector returned 78 views, 30 fills across 30 full UTC days, 15 fills in the last seven full days, and an eight-fill daily peak. Its classification is **watchlist**, because its 30-day activity is below two/day. This differs from a conclusion based only on the profitable chart or recent week. See `research/dreamlawn-production-evidence-2026-09-17.json` for source times, coverage and values.

## Still required before activation

1. Independent ledger/accounting reconstruction across transfers, inventory, settlement and income; historical strategy capital and reliable equity drawdown.
2. Persisted fixed sizing multipliers and account replay preserving entries, partial exits and relative sizes. The existing live percentile/risk sizing is not represented as satisfying this requirement.
3. Point-in-time discovery cohorts and held-out evaluation, with failed and rejected candidates retained in the research sample.
4. Fresh shadow order-book observations and enough independent resolved events to assess outcomes, delays, minimum orders, missed legs, fees and capacity.
5. Measured comparison of core-only, core plus intermittent candidates, and cash. A profitable chart or a passing software suite is insufficient.

The new policy intentionally has no automatic approval path yet. Deploying this patch would pause new roster allocations as basket refresh runs; it does not reset balances or close positions. Existing live execution and sizing have not been replaced or activated by this local work.

## Validation

Final verification: **2,784 backend tests passed**, including PostgreSQL integration against a disposable database, and the **Next.js production build passed**. A focused follow-up after retiring unsupported display metrics also passed (3 tests). The temporary PostgreSQL database was removed after verification. The fresh Dreamlawn API collection exhausted trade, activity, open-position and closed-position cursors and reconciled the trade/activity multisets.

New cursor and classification tests cover empty history, 1/499/500/501/4000/4001 fills, preserved duplicate-looking fills, cursor loops, missing pages, wrong wallets, out-of-window rows, empty midstream pages, page budgets, bursts hidden by weekly averages, unknown data and recorded Dreamlawn history. Integration tests verify retained positions, refresh caching and prevention of legacy-score promotion. Build and full-suite results are recorded in `docs/research/*-evidence-2026-09-17.txt`.
