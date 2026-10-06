"""Run the API server.

Usage: uv run python scripts/serve.py [--port PORT] [--host HOST] [--reload]
Port precedence: --port, then the APP_PORT env var, then 8642.
"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8642


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=int(os.environ.get("APP_PORT", DEFAULT_PORT)))
    parser.add_argument("--host", default=os.environ.get("APP_HOST", "127.0.0.1"))
    parser.add_argument("--reload", action="store_true", help="Restart on code changes")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload, app_dir=str(ROOT))


if __name__ == "__main__":
    main()
