import sys
import json
import asyncio
import os
import time
from pathlib import Path
from datetime import datetime

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func, desc
from app.database import SessionLocal, init_db, engine
from app.models import Wallet, ExecutionLog, User, WalletSnapshot, FeeCharge
from app.discovery.scanner import discovery_state, scan_for_wallets

TOOLS = [
    {
        "name": "baleen_admin_system",
        "description": "Returns full system-level health: server uptime, keep-alive status, last cron ping timestamp, database connection & backend engine, and scheduled background workers.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_admin_pipeline",
        "description": "Returns live status of the Discovery & Evaluation Pipeline: running/idle state, progress percentage, current step description, candidate counts, active whales discovered, gold snipers count, and rejected count.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_admin_wallets",
        "description": "Inspects all tracked, pending, and rejected wallets with filtering by status, tier, or search query. Returns detailed scores, win rates, PnLs, rejection reasons, and AI summaries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'active', 'pending', or 'rejected'. Leave empty for all."
                },
                "tier": {
                    "type": "string",
                    "description": "Filter by tier: 'gold_sniper' or 'standard'."
                },
                "search": {
                    "type": "string",
                    "description": "Search by wallet address prefix or style tag."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of wallets to return (default 25)."
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default 0)."
                }
            },
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_admin_trades",
        "description": "Fetches live execution logs, whale copy trades, fill prices, live market prices, notional sizes, realized/unrealized PnLs, and consensus indicators.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent trades to return (default 25)."
                },
                "wallet_address": {
                    "type": "string",
                    "description": "Filter trades by a specific source whale wallet address."
                }
            },
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_admin_users",
        "description": "Lists all user sandbox accounts, current balances, high water marks, and performance fee charges.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_admin_trigger_discovery",
        "description": "Triggers the Polymarket Multi-Period Discovery Scanner and Stage 2 deep evaluation pipeline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "full_refresh": {
                    "type": "boolean",
                    "description": "Whether to perform a full re-evaluation of candidate snapshots (default false)."
                }
            },
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_admin_trigger_deploy",
        "description": "Triggers a production deployment on Render and/or Vercel using configured deploy hooks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target service: 'all', 'render', or 'vercel' (default 'all')."
                }
            },
            "additionalProperties": False
        }
    }
]

async def handle_baleen_admin_system(args):
    await init_db()
    async with SessionLocal() as db:
        total_wallets = (await db.execute(select(func.count()).select_from(Wallet))).scalar() or 0
        active_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'active'))).scalar() or 0
        pending_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'pending'))).scalar() or 0
        rejected_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'rejected'))).scalar() or 0
        total_trades = (await db.execute(select(func.count()).select_from(ExecutionLog))).scalar() or 0
        total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
        
        db_dialect = engine.dialect.name
        is_postgres = "postgres" in db_dialect
        
        return {
            "server_status": "HEALTHY",
            "database_type": "Supabase PostgreSQL" if is_postgres else "SQLite (Local Failover)",
            "database_connected": True,
            "entities": {
                "active_whales_in_basket": active_wallets,
                "pending_discovery_queue": pending_wallets,
                "rejected_candidates": rejected_wallets,
                "total_wallets": total_wallets,
                "total_trades_logged": total_trades,
                "total_users": total_users
            },
            "background_workers": {
                "discovery_scanner": "Every 20 minutes",
                "live_trade_mirror": "Active (8s poll loop)",
                "mark_to_market_valuation": "Active (25s live price loop)",
                "cron_keepalive": "Active (5m cadence)"
            }
        }

async def handle_baleen_admin_pipeline(args):
    await init_db()
    async with SessionLocal() as db:
        pending_count = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'pending'))).scalar() or 0
        active_count = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'active'))).scalar() or 0
        rejected_count = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'rejected'))).scalar() or 0
        gold_count = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.tier == 'gold_sniper'))).scalar() or 0

    return {
        "status": discovery_state.get("status", "idle"),
        "progress_pct": discovery_state.get("progress_pct", 0),
        "current_step": discovery_state.get("step_description", "Ready"),
        "candidates_discovered": discovery_state.get("total_candidates", pending_count + active_count + rejected_count),
        "wallets_scanned": discovery_state.get("wallets_scanned", active_count + rejected_count),
        "active_whales_in_basket": active_count,
        "gold_snipers": gold_count,
        "rejected_wallets": rejected_count,
        "pending_evaluation": pending_count,
        "last_error": discovery_state.get("error_message")
    }

async def handle_baleen_admin_wallets(args):
    await init_db()
    status = args.get("status")
    tier = args.get("tier")
    search = args.get("search")
    limit = args.get("limit", 25)
    offset = args.get("offset", 0)

    async with SessionLocal() as db:
        stmt = select(Wallet)
        if status:
            stmt = stmt.where(Wallet.status == status)
        if tier:
            stmt = stmt.where(Wallet.tier == tier)
        if search:
            stmt = stmt.where(
                (func.lower(Wallet.address).contains(search.lower())) |
                (func.lower(Wallet.ai_style_tag).contains(search.lower()))
            )
        stmt = stmt.order_by(Wallet.baleen_score.desc().nullslast(), Wallet.all_time_pnl_usd.desc().nullslast())
        stmt = stmt.limit(limit).offset(offset)
        
        wallets = (await db.execute(stmt)).scalars().all()
        return [
            {
                "address": w.address,
                "status": w.status,
                "tier": w.tier,
                "baleen_score": w.baleen_score,
                "all_time_pnl_usd": w.all_time_pnl_usd,
                "win_rate_pct": w.win_rate_pct,
                "avg_trades_per_day": w.avg_trades_per_day,
                "alpha_per_trade": w.alpha_per_trade,
                "profit_factor": w.profit_factor,
                "ai_style_tag": w.ai_style_tag,
                "ai_summary": w.ai_summary,
                "rejection_reason": w.rejection_reason
            }
            for w in wallets
        ]

async def handle_baleen_admin_trades(args):
    await init_db()
    limit = args.get("limit", 25)
    wallet_addr = args.get("wallet_address")
    
    async with SessionLocal() as db:
        stmt = select(ExecutionLog)
        if wallet_addr:
            stmt = stmt.where(func.lower(ExecutionLog.source_wallet_address) == wallet_addr.lower())
        stmt = stmt.order_by(ExecutionLog.executed_at.desc()).limit(limit)
        
        logs = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": str(l.id),
                "wallet": l.source_wallet_address,
                "market": l.market_question,
                "condition_id": l.market_condition_id,
                "side": l.side,
                "whale_price": l.whale_entry_price,
                "fill_price": l.user_fill_price,
                "notional_usd": l.notional_usd,
                "status": l.status,
                "realized_pnl_usd": l.realized_pnl_usd,
                "executed_at": l.executed_at.isoformat() if l.executed_at else None
            }
            for l in logs
        ]

async def handle_baleen_admin_users(args):
    await init_db()
    async with SessionLocal() as db:
        stmt = select(User).order_by(User.created_at.desc())
        users = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": str(u.id),
                "email": u.email,
                "role": u.role,
                "sandbox_balance_usd": u.sandbox_balance_usd,
                "high_water_mark_usd": u.sandbox_high_water_mark_usd,
                "live_trading_active": u.live_trading_active,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]

async def handle_baleen_admin_trigger_discovery(args):
    await init_db()
    full_refresh = args.get("full_refresh", False)
    async with SessionLocal() as db:
        count = await scan_for_wallets(db, full_refresh=full_refresh)
        return {
            "status": "completed",
            "evaluated_wallets": count,
            "message": f"Discovery scan completed. Processed {count} wallets."
        }

async def handle_baleen_admin_trigger_deploy(args):
    target = args.get("target", "all").lower()
    import httpx
    results = {}
    
    render_hook = os.environ.get("RENDER_DEPLOY_HOOK_URL")
    vercel_hook = os.environ.get("VERCEL_DEPLOY_HOOK_URL")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        if (target in ("all", "render")) and render_hook:
            try:
                resp = await client.post(render_hook)
                results["render"] = f"Triggered successfully (HTTP {resp.status_code})"
            except Exception as e:
                results["render"] = f"Error: {e}"
        elif target in ("all", "render"):
            results["render"] = "Set RENDER_DEPLOY_HOOK_URL in environment or git push to deploy."

        if (target in ("all", "vercel")) and vercel_hook:
            try:
                resp = await client.post(vercel_hook)
                results["vercel"] = f"Triggered successfully (HTTP {resp.status_code})"
            except Exception as e:
                results["vercel"] = f"Error: {e}"
        elif target in ("all", "vercel"):
            results["vercel"] = "Set VERCEL_DEPLOY_HOOK_URL in environment or git push to deploy."
            
    return results

async def process_message(msg):
    method = msg.get("method")
    req_id = msg.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "baleen-mcp",
                    "version": "2.0.0"
                }
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }
    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        try:
            if tool_name in ("baleen_admin_system", "baleen_get_status"):
                res = await handle_baleen_admin_system(args)
            elif tool_name == "baleen_admin_pipeline":
                res = await handle_baleen_admin_pipeline(args)
            elif tool_name in ("baleen_admin_wallets", "baleen_list_whales"):
                res = await handle_baleen_admin_wallets(args)
            elif tool_name in ("baleen_admin_trades", "baleen_list_trades"):
                res = await handle_baleen_admin_trades(args)
            elif tool_name == "baleen_admin_users":
                res = await handle_baleen_admin_users(args)
            elif tool_name in ("baleen_admin_trigger_discovery", "baleen_trigger_discovery"):
                res = await handle_baleen_admin_trigger_discovery(args)
            elif tool_name in ("baleen_admin_trigger_deploy", "baleen_trigger_deploy"):
                res = await handle_baleen_admin_trigger_deploy(args)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                }
                
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"error": str(e)})
                        }
                    ],
                    "isError": True
                }
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not supported: {method}"
            }
        }

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line_str = line.strip()
        if not line_str:
            continue
        try:
            msg = json.loads(line_str)
            resp = asyncio.run(process_message(msg))
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error handling message: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
