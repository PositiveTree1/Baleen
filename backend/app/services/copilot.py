import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from app.database import SessionLocal
from app.models import Wallet, ExecutionLog, User, SystemEvent, PortfolioSnapshot
from app.analysis.ai_summary import get_groq_client
from app.services.polymarket_fees import calculate_polymarket_fee, classify_market_category
from app.services.mark_to_market import get_consensus, get_live_price

logger = logging.getLogger(__name__)

# --- Tool Definitions for Groq Function Calling ---
COPILOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_overview",
            "description": "Fetch high-level portfolio performance metrics including live balance, total PnL, win rate, total fees paid, active positions count, and total trades executed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "enum": ["all", "1d", "1w", "1m", "ytd"],
                        "description": "Time window for metrics. Default is 'all'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_whales",
            "description": "Retrieve the top-performing Polymarket whale wallets currently tracked by Baleen, including their tier, win rate, total PnL, trading frequency, and AI quantitative summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of whales to return (max 10). Default is 5."
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["pnl", "win_rate", "score"],
                        "description": "Metric to rank whales by. Default is 'pnl'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_trades",
            "description": "Search recent and historical trade execution logs by whale name/address, market question keywords, status (FILLED/CLOSED), or profitability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword to search in prediction market question or whale name/address."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["ALL", "FILLED", "CLOSED"],
                        "description": "Filter by position status. Default is 'ALL'."
                    },
                    "profitable_only": {
                        "type": "boolean",
                        "description": "If true, only returns winning trades. If false, returns all."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max trades to return (default 8, max 20)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_consensus",
            "description": "Get currently active prediction markets where multiple top whales in the basket have aligned on the same outcome (multi-whale consensus).",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fee_analysis",
            "description": "Get an institutional audit of Polymarket quadratic taker fees paid, category fee rates (Sports 3.5%, Crypto 2.5%, Politics 1.5%), and slippage drag analysis.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_events",
            "description": "Retrieve recent engine audit events including trades copied, slippage blocks, EV gate skips, and wallet promotions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent events (default 10)."
                    }
                }
            }
        }
    }
]

# --- Tool Execution Handlers ---

async def _tool_get_portfolio_overview(args: Dict[str, Any]) -> Dict[str, Any]:
    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]),
            ExecutionLog.user_id.is_(None)
        )
        logs = (await db.execute(stmt)).scalars().all()
        
        total_trades = len(logs)
        total_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in logs)
        total_notional = sum(float(l.notional_usd or 0.0) for l in logs)
        total_fees = sum(float(l.fee_usd or 0.0) for l in logs)
        
        wins = sum(1 for l in logs if (l.realized_pnl_usd or 0.0) > 0)
        losses = sum(1 for l in logs if (l.realized_pnl_usd or 0.0) < 0)
        win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0.0
        
        open_positions = sum(1 for l in logs if l.status == "FILLED" and l.side == "BUY")
        closed_positions = sum(1 for l in logs if l.status in ["CLOSED", "RESOLVED"])

        return {
            "starting_balance_usd": 10000.0,
            "current_balance_usd": round(10000.0 + total_pnl, 2),
            "total_net_pnl_usd": round(total_pnl, 2),
            "total_roi_pct": round((total_pnl / 10000.0) * 100, 2),
            "total_trades_executed": total_trades,
            "open_positions_count": open_positions,
            "closed_trades_count": closed_positions,
            "win_count": wins,
            "loss_count": losses,
            "win_rate_pct": win_rate,
            "total_taker_fees_paid_usd": round(total_fees, 2),
            "total_volume_invested_usd": round(total_notional, 2)
        }

async def _tool_get_top_whales(args: Dict[str, Any]) -> Dict[str, Any]:
    limit = min(args.get("limit", 5), 10)
    sort_by = args.get("sort_by", "pnl")
    
    async with SessionLocal() as db:
        stmt = select(Wallet).where(Wallet.status == "active", Wallet.dormant == False)
        if sort_by == "win_rate":
            stmt = stmt.order_by(desc(Wallet.win_rate_pct))
        elif sort_by == "score":
            stmt = stmt.order_by(desc(Wallet.baleen_score))
        else:
            stmt = stmt.order_by(desc(Wallet.all_time_pnl_usd))
        
        stmt = stmt.limit(limit)
        whales = (await db.execute(stmt)).scalars().all()
        
        return {
            "top_whales_count": len(whales),
            "whales": [
                {
                    "name": w.name or w.pseudonym or (w.address[:6] + "..." + w.address[-4:]),
                    "address": w.address,
                    "tier": w.tier or "silver",
                    "win_rate_pct": round(float(w.win_rate_pct or 0.0), 1),
                    "all_time_pnl_usd": round(float(w.all_time_pnl_usd or 0.0), 2),
                    "avg_trades_per_day": round(float(w.avg_trades_per_day or 0.0), 1),
                    "baleen_score": round(float(w.baleen_score or 0.0), 1),
                    "ai_summary": w.ai_summary or "Quantitative prediction market participant."
                }
                for w in whales
            ]
        }

async def _tool_search_trades(args: Dict[str, Any]) -> Dict[str, Any]:
    query_str = args.get("query", "").strip().lower()
    status_filter = args.get("status", "ALL")
    profitable_only = args.get("profitable_only", False)
    limit = min(args.get("limit", 8), 20)
    
    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]),
            ExecutionLog.user_id.is_(None)
        )
        
        if status_filter == "FILLED":
            stmt = stmt.where(ExecutionLog.status == "FILLED")
        elif status_filter == "CLOSED":
            stmt = stmt.where(ExecutionLog.status.in_(["CLOSED", "RESOLVED"]))
            
        if profitable_only:
            stmt = stmt.where(ExecutionLog.realized_pnl_usd > 0)
            
        stmt = stmt.order_by(desc(ExecutionLog.executed_at)).limit(100)
        logs = (await db.execute(stmt)).scalars().all()
        
        results = []
        for l in logs:
            q = (l.market_question or "").lower()
            addr = (l.source_wallet_address or "").lower()
            if query_str and (query_str not in q and query_str not in addr):
                continue
            
            results.append({
                "id": str(l.id),
                "market_question": l.market_question,
                "outcome": l.resolution_outcome or "Yes",
                "side": l.side,
                "entry_price": float(l.user_fill_price or l.whale_entry_price or 0.5),
                "notional_size_usd": float(l.notional_usd or 0.0),
                "net_pnl_usd": float(l.realized_pnl_usd or 0.0),
                "status": l.status,
                "category": l.market_category or "General",
                "fee_usd": float(l.fee_usd or 0.0),
                "executed_at": l.executed_at.strftime("%Y-%m-%d %H:%M:%S") if l.executed_at else None
            })
            if len(results) >= limit:
                break
                
        return {
            "match_count": len(results),
            "trades": results
        }

async def _tool_get_live_consensus(args: Dict[str, Any]) -> Dict[str, Any]:
    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.status == "FILLED",
            ExecutionLog.side == "BUY",
            ExecutionLog.user_id.is_(None)
        ).order_by(desc(ExecutionLog.executed_at)).limit(100)
        logs = (await db.execute(stmt)).scalars().all()
        
        consensus_items = []
        seen_conditions = set()
        for l in logs:
            cid = l.market_condition_id or ""
            if not cid or cid in seen_conditions:
                continue
            seen_conditions.add(cid)
            cons = get_consensus(cid)
            if cons and cons.get("is_consensus"):
                consensus_items.append({
                    "market_question": l.market_question,
                    "condition_id": cid,
                    "outcome": l.resolution_outcome or "Yes",
                    "aligned_whales_count": cons.get("whale_count", 0),
                    "total_cash_committed_usd": cons.get("total_cash", 0.0),
                    "entry_price": float(l.user_fill_price or 0.5)
                })
                
        return {
            "active_consensus_markets_count": len(consensus_items),
            "consensus_markets": consensus_items[:5]
        }

async def _tool_get_fee_analysis(args: Dict[str, Any]) -> Dict[str, Any]:
    async with SessionLocal() as db:
        stmt = select(ExecutionLog).where(
            ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]),
            ExecutionLog.user_id.is_(None)
        )
        logs = (await db.execute(stmt)).scalars().all()
        
        category_breakdown = {}
        total_fees = 0.0
        for l in logs:
            cat = l.market_category or "General"
            fee = float(l.fee_usd or 0.0)
            total_fees += fee
            if cat not in category_breakdown:
                category_breakdown[cat] = {"count": 0, "fees_usd": 0.0}
            category_breakdown[cat]["count"] += 1
            category_breakdown[cat]["fees_usd"] = round(category_breakdown[cat]["fees_usd"] + fee, 2)
            
        return {
            "total_fees_paid_usd": round(total_fees, 2),
            "fee_model": "Polymarket Quadratic Taker Fee Curve (0% - 7%)",
            "category_rates": {
                "Sports": "3.5% base fee (EV gate requires >65% win rate)",
                "Crypto / Financial": "2.5% base fee",
                "Politics / Macro": "1.5% base fee",
                "General / Culture": "2.0% base fee"
            },
            "category_breakdown": category_breakdown
        }

async def _tool_get_system_events(args: Dict[str, Any]) -> Dict[str, Any]:
    limit = min(args.get("limit", 10), 20)
    async with SessionLocal() as db:
        try:
            stmt = select(SystemEvent).order_by(desc(SystemEvent.created_at)).limit(limit)
            events = (await db.execute(stmt)).scalars().all()
            return {
                "events_count": len(events),
                "events": [
                    {
                        "event_type": e.event_type,
                        "severity": e.severity,
                        "title": e.title,
                        "detail": e.detail,
                        "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else None
                    }
                    for e in events
                ]
            }
        except Exception:
            return {"events_count": 0, "events": []}

TOOL_HANDLERS = {
    "get_portfolio_overview": _tool_get_portfolio_overview,
    "get_top_whales": _tool_get_top_whales,
    "search_trades": _tool_search_trades,
    "get_live_consensus": _tool_get_live_consensus,
    "get_fee_analysis": _tool_get_fee_analysis,
    "get_system_events": _tool_get_system_events,
}

# --- Main Copilot Reasoning Agent ---

SYSTEM_PROMPT = """You are the **Baleen Copilot**, an institutional quantitative AI assistant integrated into the Baleen autonomous Polymarket whale copy-trading engine.

### Your Capabilities & Knowledge:
1. You have direct access to real-time portfolio statistics, whale basket analytics, trade execution history, multi-whale consensus signals, and fee structures via built-in tools.
2. ALWAYS use the provided tools to query real data when the user asks about performance, specific whales, trades, balances, fees, or events.
3. NEVER make up statistics or hallucinate trade figures. Use tool results as the single source of truth.
4. Format all responses cleanly using GitHub Markdown:
   - Use bold numbers and currency formatting (e.g. **$11,842.58**, **+18.4% ROI**).
   - Use bullet points, concise tables, and clear visual hierarchy.
   - Maintain a sophisticated, sharp, institutional hedge-fund tone (confident, precise, quantitative).
"""

async def execute_copilot_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Executes a multi-turn chat interaction with tool calling enabled using Groq.
    """
    client = get_groq_client()
    if not client:
        return {
            "message": "Groq AI client is currently unavailable. Please verify that `GROQ_API_KEY_1` is configured in the environment.",
            "tool_calls_executed": []
        }

    # Prepare chat message history
    formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages[-8:]:  # keep last 8 turns for context hygiene
        role = msg.get("role", "user")
        if role in ["user", "assistant", "system"]:
            formatted_messages.append({"role": role, "content": msg.get("content", "")})

    tools_executed = []

    # Try candidate models with tool-calling capabilities in order of capability
    CANDIDATE_MODELS = [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "mixtral-8x7b-32768",
        "groq/compound-mini"
    ]

    for model_name in CANDIDATE_MODELS:
        try:
            # Step 1: Initial LLM inference with tool calling
            response = await client.chat.completions.create(
                model=model_name,
                messages=formatted_messages,
                tools=COPILOT_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1024,
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # Step 2: Handle tool calls if requested
            if tool_calls:
                # Make a working copy of messages for tool execution
                turn_messages = list(formatted_messages)
                turn_messages.append(response_message)
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    handler = TOOL_HANDLERS.get(function_name)
                    
                    try:
                        function_args = json.loads(tool_call.function.arguments or "{}")
                    except Exception:
                        function_args = {}

                    if handler:
                        tool_result = await handler(function_args)
                        tools_executed.append({
                            "name": function_name,
                            "args": function_args,
                            "summary": f"Executed {function_name}"
                        })
                    else:
                        tool_result = {"error": f"Tool '{function_name}' not recognized."}

                    turn_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(tool_result),
                    })

                # Step 3: Second call to generate synthesized final response from tool outputs
                second_response = await client.chat.completions.create(
                    model=model_name,
                    messages=turn_messages,
                    temperature=0.3,
                    max_tokens=1024,
                )
                final_content = second_response.choices[0].message.content or ""
            else:
                final_content = response_message.content or ""

            if final_content:
                return {
                    "message": final_content,
                    "tool_calls_executed": tools_executed
                }

        except Exception as e:
            logger.warning(f"Groq Copilot inference with model {model_name} failed: {e}")
            continue

    return {
        "message": "Quantitative AI Copilot is temporarily initializing live price models. Please try your question again in a moment.",
        "tool_calls_executed": tools_executed
    }

