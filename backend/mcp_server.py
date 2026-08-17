import sys
import json
import asyncio
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from app.database import SessionLocal, init_db
from app.models import Wallet, ExecutionLog, User

TOOLS = [
    {
        "name": "baleen_get_status",
        "description": "Returns live status of the Baleen system: server health, database connection, active whale count, gold snipers count, pending discovery queue, and total execution logs.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_list_whales",
        "description": "Lists all tracked Polymarket whales in the basket, with their tiers, all-time PnL, win rates, Baleen alpha scores, AI summaries, and trade frequencies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'active', 'pending', or 'rejected'. Defaults to 'active'."
                },
                "tier": {
                    "type": "string",
                    "description": "Filter by tier: 'gold_sniper' or 'standard'."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of wallets to return (default 50)."
                }
            },
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_list_trades",
        "description": "Lists recent execution audit logs and copy trades, including entry price, live price, size, realized PnL, and consensus indicators.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent trades to return (default 25)."
                }
            },
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_trigger_discovery",
        "description": "Triggers a full Polymarket multi-period discovery scan and Stage 2 deep audit of candidate wallets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "full_refresh": {
                    "type": "boolean",
                    "description": "Whether to purge stale candidate snapshots and re-evaluate from scratch (default false)."
                }
            },
            "additionalProperties": False
        }
    },
    {
        "name": "baleen_trigger_deploy",
        "description": "Triggers a production deployment on Render and/or Vercel using configured deploy hooks or git push.",
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

async def handle_baleen_get_status(args):
    await init_db()
    async with SessionLocal() as db:
        total_wallets = (await db.execute(select(func.count()).select_from(Wallet))).scalar() or 0
        active_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'active'))).scalar() or 0
        gold_snipers = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.tier == 'gold_sniper'))).scalar() or 0
        pending_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'pending'))).scalar() or 0
        rejected_wallets = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == 'rejected'))).scalar() or 0
        total_trades = (await db.execute(select(func.count()).select_from(ExecutionLog))).scalar() or 0
        
        return {
            "status": "ONLINE",
            "database": "CONNECTED",
            "active_whales_in_basket": active_wallets,
            "gold_snipers": gold_snipers,
            "pending_discovery_queue": pending_wallets,
            "rejected_candidates": rejected_wallets,
            "total_wallets_tracked": total_wallets,
            "total_trades_executed": total_trades
        }

async def handle_baleen_list_whales(args):
    await init_db()
    status = args.get("status", "active")
    tier = args.get("tier")
    limit = args.get("limit", 50)
    
    async with SessionLocal() as db:
        stmt = select(Wallet)
        if status:
            stmt = stmt.where(Wallet.status == status)
        if tier:
            stmt = stmt.where(Wallet.tier == tier)
        stmt = stmt.order_by(Wallet.baleen_score.desc().nullslast()).limit(limit)
        
        wallets = (await db.execute(stmt)).scalars().all()
        return [
            {
                "address": w.address,
                "tier": w.tier,
                "status": w.status,
                "baleen_score": w.baleen_score,
                "all_time_pnl_usd": w.all_time_pnl_usd,
                "win_rate_pct": w.win_rate_pct,
                "avg_trades_per_day": w.avg_trades_per_day,
                "ai_style_tag": w.ai_style_tag,
                "ai_summary": w.ai_summary,
                "rejection_reason": w.rejection_reason
            }
            for w in wallets
        ]

async def handle_baleen_list_trades(args):
    await init_db()
    limit = args.get("limit", 25)
    async with SessionLocal() as db:
        stmt = select(ExecutionLog).order_by(ExecutionLog.executed_at.desc()).limit(limit)
        logs = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": str(l.id),
                "wallet": l.source_wallet_address,
                "market": l.market_question,
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

async def handle_baleen_trigger_discovery(args):
    await init_db()
    full_refresh = args.get("full_refresh", False)
    from app.discovery.scanner import scan_for_wallets
    async with SessionLocal() as db:
        count = await scan_for_wallets(db, full_refresh=full_refresh)
        return {
            "status": "completed",
            "evaluated_wallets": count,
            "message": f"Discovery scan completed. Ingested & evaluated {count} wallets."
        }

async def handle_baleen_trigger_deploy(args):
    target = args.get("target", "all").lower()
    import httpx
    results = {}
    
    render_hook = os.environ.get("RENDER_DEPLOY_HOOK_URL")
    vercel_hook = os.environ.get("VERCEL_DEPLOY_HOOK_URL")
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        if (target in ("all", "render")) and render_hook:
            try:
                resp = await client.post(render_hook)
                results["render"] = f"Triggered (HTTP {resp.status_code})"
            except Exception as e:
                results["render"] = f"Error: {e}"
        elif target in ("all", "render"):
            results["render"] = "Set RENDER_DEPLOY_HOOK_URL in environment or git push to deploy."

        if (target in ("all", "vercel")) and vercel_hook:
            try:
                resp = await client.post(vercel_hook)
                results["vercel"] = f"Triggered (HTTP {resp.status_code})"
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
                    "version": "1.0.0"
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
            if tool_name == "baleen_get_status":
                res = await handle_baleen_get_status(args)
            elif tool_name == "baleen_list_whales":
                res = await handle_baleen_list_whales(args)
            elif tool_name == "baleen_list_trades":
                res = await handle_baleen_list_trades(args)
            elif tool_name == "baleen_trigger_discovery":
                res = await handle_baleen_trigger_discovery(args)
            elif tool_name == "baleen_trigger_deploy":
                res = await handle_baleen_trigger_deploy(args)
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
