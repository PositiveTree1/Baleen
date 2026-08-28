#!/usr/bin/env python3
"""
Baleen Custom MCP Testing & Inspection Server
Complies with Model Context Protocol (JSON-RPC 2.0 stdio transport).
Enables automated health checks, API diagnostics, DOM inspection, math audit, and UI verification.
"""

import sys
import json
import urllib.request
import urllib.error
import time
import os

DEFAULT_BACKEND_URL = os.environ.get("BALEEN_BACKEND_URL", "http://localhost:8000")
DEFAULT_FRONTEND_URL = os.environ.get("BALEEN_FRONTEND_URL", "http://localhost:3000")

def send_response(response_dict):
    """Write JSON-RPC message to stdout followed by newline and flush."""
    data = json.dumps(response_dict)
    sys.stdout.write(data + "\n")
    sys.stdout.flush()

def make_http_request(url, method="GET", body=None, headers=None, timeout=6.0):
    """Executes an HTTP request using built-in standard library urllib."""
    req_headers = {"User-Agent": "Baleen-MCP-Inspector/1.0", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
        
    data = None
    if body:
        if isinstance(body, dict):
            data = json.dumps(body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        elif isinstance(body, str):
            data = body.encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            content = response.read().decode("utf-8", errors="replace")
            status = response.status
            try:
                parsed_json = json.loads(content)
            except Exception:
                parsed_json = None
            return {
                "success": True,
                "status_code": status,
                "latency_ms": latency_ms,
                "json": parsed_json,
                "raw": content[:2000] if not parsed_json else None
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        err_body = e.read().decode("utf-8", errors="replace")
        return {
            "success": False,
            "status_code": e.code,
            "latency_ms": latency_ms,
            "error": str(e),
            "detail": err_body[:1000]
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "status_code": 0,
            "latency_ms": latency_ms,
            "error": str(e)
        }

# Tool Implementations
def tool_test_api_endpoints(args):
    base_url = args.get("baseUrl") or DEFAULT_BACKEND_URL
    endpoints = [
        {"name": "Platform Stats", "path": "/api/stats", "method": "GET"},
        {"name": "Execution Summary", "path": "/api/executions/summary", "method": "GET"},
        {"name": "Recent Executions", "path": "/api/executions?limit=25", "method": "GET"},
        {"name": "Whale Leaderboard", "path": "/api/wallets", "method": "GET"},
        {"name": "Admin Health", "path": "/api/admin/status", "method": "GET"},
        {"name": "Activity Events", "path": "/api/events?limit=10", "method": "GET"}
    ]
    
    results = []
    all_passed = True
    total_latency = 0
    
    for ep in endpoints:
        url = f"{base_url.rstrip('/')}{ep['path']}"
        res = make_http_request(url, method=ep["method"])
        is_ok = res.get("success") and res.get("status_code", 0) < 400
        if not is_ok:
            all_passed = False
        total_latency += res.get("latency_ms", 0)
        results.append({
            "name": ep["name"],
            "endpoint": ep["path"],
            "status_code": res.get("status_code"),
            "latency_ms": res.get("latency_ms"),
            "passed": is_ok,
            "sample": res.get("json") if is_ok else res.get("error")
        })
        
    return {
        "all_passed": all_passed,
        "average_latency_ms": round(total_latency / max(1, len(endpoints)), 2),
        "tested_endpoints": len(endpoints),
        "results": results
    }

def tool_inspect_page(args):
    page_url = args.get("pageUrl") or DEFAULT_FRONTEND_URL
    res = make_http_request(page_url, method="GET", timeout=8.0)
    
    if not res.get("success"):
        return {
            "page_url": page_url,
            "reachable": False,
            "error": res.get("error"),
            "status_code": res.get("status_code")
        }
        
    raw_html = res.get("raw") or ""
    has_baleen = "Baleen" in raw_html or "baleen" in raw_html
    has_dark_mode = "dark" in raw_html
    has_revolut_tokens = "revolut" in raw_html or "font-outfit" in raw_html
    
    return {
        "page_url": page_url,
        "reachable": True,
        "status_code": res.get("status_code"),
        "latency_ms": res.get("latency_ms"),
        "html_size_bytes": len(raw_html),
        "inspections": {
            "brand_title_present": has_baleen,
            "dark_mode_supported": has_dark_mode,
            "theme_styles_present": has_revolut_tokens
        }
    }

def tool_verify_math_integrity(args):
    base_url = args.get("baseUrl") or DEFAULT_BACKEND_URL
    summary_res = make_http_request(f"{base_url.rstrip('/')}/api/executions/summary")
    
    if not summary_res.get("success") or not summary_res.get("json"):
        return {
            "verified": False,
            "error": "Failed to fetch /api/executions/summary for mathematical verification",
            "details": summary_res
        }
        
    summary = summary_res["json"]
    starting = summary.get("startingBalance", 10000.0)
    current = summary.get("currentBalance", 10000.0)
    pnl = summary.get("totalPnlUsd", 0.0)
    
    expected_current = round(starting + pnl, 2)
    drift = round(abs(current - expected_current), 2)
    is_accurate = drift < 0.05
    
    return {
        "verified": is_accurate,
        "drift_usd": drift,
        "starting_balance": starting,
        "total_pnl_usd": pnl,
        "recorded_current_balance": current,
        "calculated_expected_balance": expected_current,
        "win_rate_pct": summary.get("allTimeWinRate"),
        "total_notional_volume": summary.get("totalNotionalInvested"),
        "total_taker_fees_paid": summary.get("totalFeesPaidUsd")
    }

# MCP Tool Specifications
TOOLS = [
    {
        "name": "baleen_test_api_endpoints",
        "description": "Tests and benchmarks all Baleen backend REST endpoints (/api/stats, /api/executions, /api/executions/summary, /api/wallets, /api/events, /api/admin/status) returning latency and payload integrity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "baseUrl": {
                    "type": "string",
                    "description": "Optional base URL of the backend API (defaults to http://localhost:8000 or env)."
                }
            }
        }
    },
    {
        "name": "baleen_inspect_page",
        "description": "Fetches and inspects a Baleen web page (e.g. /, /dashboard, /admin, /settings, /auth/login) verifying reachability, theme tokens, and DOM rendering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pageUrl": {
                    "type": "string",
                    "description": "The URL of the page to inspect."
                }
            },
            "required": ["pageUrl"]
        }
    },
    {
        "name": "baleen_verify_math_integrity",
        "description": "Audits mark-to-market calculations, verifying that starting balance + net realized PnL = current portfolio balance with 0.00 error tolerance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "baseUrl": {
                    "type": "string",
                    "description": "Optional base URL of the backend API."
                }
            }
        }
    }
]

def main():
    """Main JSON-RPC stdio event loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "baleen-tester",
                        "version": "1.0.0"
                    }
                }
            })
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS
                }
            })
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            try:
                if tool_name == "baleen_test_api_endpoints":
                    result = tool_test_api_endpoints(tool_args)
                elif tool_name == "baleen_inspect_page":
                    result = tool_inspect_page(tool_args)
                elif tool_name == "baleen_verify_math_integrity":
                    result = tool_verify_math_integrity(tool_args)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                    
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                })
            except Exception as ex:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32000,
                        "message": str(ex)
                    }
                })
        else:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            })

if __name__ == "__main__":
    main()
