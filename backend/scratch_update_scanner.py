with open('app/discovery/scanner.py', 'r', encoding='utf-8') as f:
    content = f.read()

prefix = content.split('async def scan_for_wallets')[0]

new_content = prefix + '''async def evaluate_pending_wallets(db: AsyncSession):
    """
    Deep scan for all wallets that were saved with status='pending'.
    """
    global discovery_state
    
    stmt = select(Wallet).where(Wallet.status == 'pending')
    pending_wallets = (await db.execute(stmt)).scalars().all()
    
    if not pending_wallets:
        return 0
        
    discovery_state["status"] = "running"
    total_pending = len(pending_wallets)
    processed_count = 0
    client = PolymarketClient()
    
    try:
        for idx, wallet in enumerate(pending_wallets, 1):
            addr = wallet.address
            discovery_state["wallets_scanned"] += 1
            # Assuming stage 1 was 50%, map this to 50%-90%
            discovery_state["progress_pct"] = 50 + int((idx / max(1, total_pending)) * 40)
            discovery_state["step_description"] = f"Deep evaluation {addr[:6]}...{addr[-4:]} ({idx}/{total_pending})"
            
            try:
                raw_trades = await client.fetch_wallet_trades(addr, max_trades=4000)
                stats = calculate_stats_from_trades_and_entry(raw_trades, None, address=addr)
                
                # Check DB for existing wallet (already exists, but let's score it)
                is_valid, reason = score_wallet(stats)
                baleen_score = compute_baleen_score(stats)
                
                if stats['is_hft']:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = 'High-Frequency Bot detected (TPH >= 50 or automated spam)'
                elif stats['is_dormant']:
                    wallet.status = 'rejected'
                    wallet.tier = 'dormant'
                    wallet.rejection_reason = 'Dormant wallet (Inactive > 21 days)'
                elif is_valid:
                    wallet.status = 'active'
                    if baleen_score >= 82.0 and stats['all_time_pnl_usd'] >= 100000.0:
                        wallet.tier = 'gold_sniper'
                        discovery_state["gold_snipers"] += 1
                    else:
                        wallet.tier = 'standard'
                    discovery_state["active_whales_in_basket"] += 1
                else:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = reason
                    
                # Auto-generate AI summary
                try:
                    ai_summary, ai_style_tag = await generate_summary(stats)
                    wallet.ai_summary = ai_summary
                    wallet.ai_style_tag = ai_style_tag
                except Exception:
                    wallet.ai_summary = f"Institutional Polymarket trader with ${stats['all_time_pnl_usd']:,.0f} all-time PnL and {stats['win_rate_pct']}% win rate."
                    wallet.ai_style_tag = "Alpha Whale"
                    
                wallet.all_time_pnl_usd = stats['all_time_pnl_usd']
                wallet.win_rate_pct = stats['win_rate_pct']
                wallet.total_trades_analyzed = stats['total_trades_analyzed']
                wallet.avg_trades_per_day = stats['avg_trades_per_day']
                wallet.median_inter_trade_gap_hours = stats['median_inter_trade_gap_hours']
                wallet.max_drawdown_pct = stats['max_drawdown_pct']
                wallet.outlier_concentration_pct = stats['outlier_concentration_pct']
                wallet.baleen_score = baleen_score
                wallet.dormant = stats['is_dormant']
                wallet.is_hft = stats['is_hft']
                wallet.trades_per_hour = stats['trades_per_hour']
                wallet.wilson_lb = stats['wilson_lb']
                wallet.alpha_per_trade = stats['alpha_per_trade']
                wallet.profit_factor = stats['profit_factor']
                wallet.first_trade_at = stats['first_trade_dt']
                wallet.last_trade_at = stats['last_trade_dt']
                wallet.cached_daily_pnl = stats['cached_daily_pnl']
                wallet.last_scored_at = datetime.utcnow()
                
                await db.commit()
                processed_count += 1
                await asyncio.sleep(0.04)
                
            except Exception as e:
                logger.warning(f"Failed to evaluate candidate {addr}: {e}")
                await db.rollback()
                continue
                
    finally:
        await client.close()
        
    return processed_count

async def scan_for_wallets(db: AsyncSession, full_refresh: bool = False) -> int:
    global discovery_state
    discovery_state["status"] = "running"
    discovery_state["progress_pct"] = 5
    discovery_state["step_description"] = "Connecting to Polymarket Leaderboard & Trade APIs..."
    discovery_state["wallets_scanned"] = 0
    discovery_state["active_whales_in_basket"] = 0
    discovery_state["gold_snipers"] = 0
    discovery_state["started_at"] = time.time()
    discovery_state["error_message"] = None
    
    client = PolymarketClient()
    processed_count = 0
    
    try:
        if full_refresh:
            discovery_state["step_description"] = "Purging stale test data from database..."
            await db.execute(delete(WalletSnapshot))
            await db.execute(delete(ExecutionLog))
            await db.execute(delete(Wallet))
            await db.commit()
            logger.info("Database completely purged for fresh Polymarket discovery.")

        discovery_state["progress_pct"] = 15
        discovery_state["step_description"] = "Stage 1: Fast Leaderboard Scraping (Saving >$50k wallets)..."
        
        candidates = await client.discover_candidates()
        total_candidates = len(candidates)
        logger.info(f"Discovered {total_candidates} candidate addresses from Polymarket.")
        
        if not candidates:
            discovery_state["step_description"] = "Polymarket API returned 0 candidates. Retrying..."
            discovery_state["status"] = "completed"
            return 0

        # STAGE 1: Fast Filter & Save
        saved_count = 0
        for idx, (addr, meta) in enumerate(candidates.items(), 1):
            pnl = meta.get("profit", 0.0)
            discovery_state["progress_pct"] = min(50, 15 + int((idx / max(1, total_candidates)) * 35))
            
            if pnl >= 50000.0:
                stmt = select(Wallet).where(Wallet.address == addr)
                wallet = (await db.execute(stmt)).scalar_one_or_none()
                if not wallet:
                    wallet = Wallet(
                        address=addr,
                        status="pending",
                        all_time_pnl_usd=pnl,
                        first_seen_at=datetime.utcnow()
                    )
                    db.add(wallet)
                    await db.commit()
                    saved_count += 1

        discovery_state["step_description"] = f"Stage 1 Complete. Saved {saved_count} new whales > $50k."
        await asyncio.sleep(1)

    except Exception as general_err:
        logger.error(f"Error during Stage 1 discovery: {general_err}", exc_info=True)
        discovery_state["status"] = "error"
        discovery_state["error_message"] = str(general_err)
    finally:
        await client.close()
        
    # STAGE 2: Deep Evaluation
    if discovery_state["status"] != "error":
        try:
            discovery_state["step_description"] = "Stage 2: Deep 4,000-trade evaluation..."
            processed_count = await evaluate_pending_wallets(db)
            
            # Post-Evaluation: Live Tape Seeding
            stmt = select(Wallet).where(Wallet.status == 'active').order_by(Wallet.last_scored_at.desc()).limit(10)
            active_wallets = (await db.execute(stmt)).scalars().all()
            
            discovery_state["progress_pct"] = 95
            discovery_state["step_description"] = "Synchronizing live trade execution tape..."
            
            if active_wallets:
                client = PolymarketClient()
                try:
                    for w in active_wallets:
                        raw_trades = await client.fetch_wallet_trades(w.address, max_trades=3)
                        for t in raw_trades:
                            try:
                                ts_raw = t.get("timestamp") or t.get("match_time") or t.get("created_at") or t.get("time")
                                ts_sec = float(ts_raw) / 1000.0 if float(ts_raw) > 1e11 else float(ts_raw)
                                
                                log = ExecutionLog(
                                    source_wallet_address=w.address,
                                    market_condition_id=t.get("conditionId") or t.get("market") or "",
                                    market_question=t.get("title") or "Polymarket Prediction",
                                    side=str(t.get("side") or "BUY").upper(),
                                    whale_entry_price=float(t.get("price") or 0.0),
                                    user_fill_price=float(t.get("price") or 0.0),
                                    notional_usd=min(float(t.get("usdcSize") or (float(t.get("size") or 0) * float(t.get("price") or 0))), 500.0),
                                    active_basket_size_at_trade=discovery_state["active_whales_in_basket"],
                                    is_sandbox=True,
                                    status="FILLED",
                                    executed_at=datetime.fromtimestamp(ts_sec, timezone.utc).replace(tzinfo=None)
                                )
                                db.add(log)
                            except:
                                pass
                    await db.commit()
                finally:
                    await client.close()
                    
            discovery_state["progress_pct"] = 100
            discovery_state["step_description"] = f"Complete: {discovery_state['active_whales_in_basket']} active whales ({discovery_state['gold_snipers']} Gold Snipers) audited."
            discovery_state["status"] = "completed"
            discovery_state["completed_at"] = time.time()
        except Exception as e:
            logger.error(f"Error during Stage 2 deep evaluation: {e}", exc_info=True)
            discovery_state["status"] = "error"
            discovery_state["error_message"] = str(e)

    logger.info(f"Evaluation complete. Processed {processed_count} wallets.")
    return processed_count
'''

with open('app/discovery/scanner.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
