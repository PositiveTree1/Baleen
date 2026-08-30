# Adversarial Challenge Analysis — Milestone R3 (Live Polling, Execution Resilience & Stress Bounds)
**Author**: challenger_2 (Adversarial Verifier & Empirical Challenger)
**Date**: 2026-08-30
**Target**: Baleen Whale Copy-Trading Platform (`backend/app/services/live_poller.py`, `backend/app/services/mark_to_market.py`, `backend/app/services/disk_backup.py`, `backend/app/sizing/sleeve_manager.py`, `backend/app/main.py`)

---

## 1. Executive Summary & Verdict

- **Overall Risk Assessment**: **LOW / VERIFIED ROBUST**
- **Verdict**: **APPROVE**
- **Test Results**: 100% Pass across all 409 backend tests (including 50 targeted execution stress and invariant verification tests).
- **Core Invariant Audited**: Zero orphaned trades, zero negative cash balances, strict $1,000 sleeve capacity limits, robust 24/7 overnight resilience, and automated 3-strike anti-arbitrage bot demotion.

---

## 2. Empirical Verification by Objective

### Objective 1: Continuous Live Poller Pacing, Top-10 Whale Roster Selection & Dynamic Legacy Expansion
- **Pacing**: Verified `_poll_loop` paces requests at `2.5s` intervals via `await asyncio.sleep(2.5)`.
- **Top-10 Selection**: Verified `_poll_active_whales()` queries active, non-dormant, non-HFT wallets with `avg_trades_per_day <= 65.0` ordered by `baleen_score.desc()` with `limit(10)`. Disqualified wallets (HFT, dormant, over-traded, rejected) are strictly excluded from the active basket.
- **Dynamic Legacy Expansion**: If a wallet held an active position (status `FILLED`, side `BUY`) and was subsequently demoted or dropped out of the top 10, the poller dynamically adds this legacy wallet to `all_wallets_to_poll`.
  - **Asymmetric Side Handling**: If the demoted legacy wallet submits a new `BUY`, it is rejected (line 228 of `live_poller.py`). If it submits a `SELL` for an open position, the trade is matched and executes to close the position and unlock capital (lines 183-225).
- **Empirical Test**: Passed `test_top_10_active_roster_selection` and `test_dynamic_roster_expansion_for_legacy_open_positions` in `test_challenger_r3_deep_empirical.py`.

### Objective 2: Boundary Price Screening ($0.04 - $0.96) & 3-Strike Anti-Arbitrage Bot Demotion
- **Ingestion Guard**: Poller filters all incoming trades from the `/trades` endpoint outside the $[0.04, 0.96]$ range at line 978 (`if price < 0.04 or price > 0.96: continue`).
- **3-Strike Anti-Arbitrage Bot Demotion**:
  - In `process_trade_fill` (lines 263-292), BUY trades at boundary prices ($p \le 0.02$ or $p \ge 0.98$) are blocked to prevent toxic settlement arbitrage and dust lottery traps.
  - The wallet's strike counter `boundary_snipe_counts[addr]` increments.
  - Upon reaching 3 strikes ($\ge 3$), the wallet is automatically demoted in the database: `status = "rejected"`, `tier = "rejected"`, `rejection_reason = "FLAGGED_ARBITRAGE_BOT: Repeated boundary price sniping (<=0.02 or >=0.98)"`.
  - Future BUY orders from this wallet are instantly rejected.
- **Empirical Test**: Passed `test_boundary_price_3_strike_bot_demotion` in `test_challenger_r3_deep_empirical.py`.

### Objective 3: 24/7 Overnight Resilience & State Persistence
- **Keep-Alive Public Pinging**: `main.py` schedules `keep_alive_job` every 5 minutes (`scheduler.add_job(keep_alive_job, 'interval', minutes=5)`), targeting the `/health` endpoint to prevent cloud host idle spin-down. Updates `last_cron_ping_time`.
- **Periodic 15-Minute Disk Backups**: `DiskBackupService` runs an asynchronous background loop every 900 seconds (15 minutes), after a 30s initial warmup.
  - `export_all_trades_to_disk()` exports all execution logs to `backend/data/backups/baleen_all_trades_backup.json` and `backend/data/backups/baleen_all_trades_backup.csv`.
  - Shutdown hook triggers a final export before process exit.
- **MTM Watchdog Gap Recovery**: In `MarkToMarketService._ensure_snapshot_continuity()`, the system checks for snapshot gaps $> 30$ minutes. If detected, it carries forward the last known good balance and total PnL from the previous snapshot, preventing cold-cache zero-valuation collapse upon restart.
- **Async Loop Error Isolation**:
  - `LiveTradeMirrorService._poll_loop()` isolates errors with `try...except Exception as e:` and continues sleeping 2.5s.
  - `MarkToMarketService._valuation_loop()` isolates errors with `try...except Exception as e:` and continues sleeping 5.0s.
  - `DiskBackupService._backup_loop()` isolates errors with `try...except Exception as e:` and continues sleeping 900s.
- **Empirical Test**: Passed `test_mtm_watchdog_restart_gap_recovery`, `test_disk_backup_export_format_and_completeness`, and `test_async_loop_error_isolation` in `test_challenger_r3_deep_empirical.py`.

### Objective 4: Execution Stress & Invariant Test Suite Execution
- **Commands Executed**:
  1. `pytest backend/tests/test_challenger_execution_stress.py backend/tests/test_challenger_a1_stress.py backend/tests/test_live_poller_m_a3.py` -> **44 passed in 2.71s**
  2. `pytest backend/tests/test_challenger_r3_deep_empirical.py` -> **6 passed in 2.84s**
  3. Combined Execution Suite: **50 passed in 4.24s**
  4. Full Backend Regression Suite: **409 passed in 13.91s**

---

## 3. Adversarial Stress Matrix Summary

| Area / Attack Vector | Scenario / Probe | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| **Pacing & Loop** | Continuous execution under slow network / 429 backoff | Sleep 2.5s, isolate errors, no uncaught exceptions | Handled in try/except; sleeps 2.5s | **PASS** |
| **Roster Selection** | Pool with 15 active + 4 disqualified wallets | Select Top 10 by score; exclude dormant/HFT/overtraded | Selected Top 10; excluded all 4 disqualified | **PASS** |
| **Legacy Exit** | Whale demoted after open position is filled | Dynamically polled; blocks new BUYs, executes SELLs | Legacy whale included; BUY blocked, SELL executed | **PASS** |
| **Boundary Screening** | Ingestion trade at $p = 0.01$ or $p = 0.99$ | Dropped at poller boundary check ($0.04 \le p \le 0.96$) | Filtered at line 978 | **PASS** |
| **Anti-Arb 3-Strikes** | Whale submits 3 boundary BUYs ($p \le 0.02$ or $p \ge 0.98$) | Striked 1, 2; on 3rd strike demoted to "rejected" | Demoted in DB, reason FLAGGED_ARBITRAGE_BOT | **PASS** |
| **Restart Gap Recovery**| System restarted after 45-minute outage | Watchdog writes recovery snapshot carrying forward last balance | Last balance ($14.5k) restored, no cold collapse | **PASS** |
| **Disk Backup** | 15-minute periodic trigger & shutdown | Valid JSON & CSV written to `data/backups` | JSON & CSV created with full trade history | **PASS** |
| **Deduplication** | Duplicate signal on-chain (same tx_hash + log_index) | Processed once; duplicate skipped | Database deduplication guard skipped 2nd trade | **PASS** |
| **Out-of-Order SELL** | SELL arrives before lagging BUY | Queued in `pending_out_of_order_sells`, matched on BUY | Matched cleanly; 0 open lots remaining | **PASS** |
| **Binary Resolution** | Market resolved as Winner ($1.00) / Loser ($0.00) | Transition FILLED -> CLOSED with exact PnL | Correct payout, 0 remaining FILLED lots | **PASS** |

---

## 4. Conclusion
All R3 requirements, state machine invariants, resilience hooks, and boundary protections operate strictly within specification. No breaking bugs or invariant violations were identified during stress testing.
