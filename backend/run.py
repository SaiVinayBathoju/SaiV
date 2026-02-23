#!/usr/bin/env python3
"""
Run the SaiV API. Use this as the Render start command so the app loads correctly.
Usage: python run.py
"""
import os
import sys

# Ensure this directory (backend) is on path so "app" resolves when run from anywhere
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Optional: load .env if present (Render uses env vars from Dashboard)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    try:
        import uvicorn
        from app.main import app
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"Failed to start: {e}", file=sys.stderr)
        sys.exit(1)
