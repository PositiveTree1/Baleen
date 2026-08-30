import os
import sys
import traceback

if __name__ == "__main__":
    port_str = os.environ.get("PORT", "8000")
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 8000
    
    print(f"?? Starting Baleen Backend on 0.0.0.0:{port} (PORT env={port_str})...", flush=True)
    try:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info", access_log=True)
    except Exception as e:
        print(f"? Fatal error during uvicorn startup: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        sys.exit(1)

