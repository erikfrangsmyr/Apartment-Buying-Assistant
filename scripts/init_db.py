"""Create the SQLite database from db/schema.sql and load db/seed.sql.

Usage: uv run python scripts/init_db.py [--db PATH] [--no-seed] [--reset]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import DEFAULT_DB_PATH, connect, init_db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite file path")
    parser.add_argument("--no-seed", action="store_true", help="Create tables only")
    parser.add_argument("--reset", action="store_true", help="Delete the existing database first")
    args = parser.parse_args()

    if args.reset and args.db.exists():
        args.db.unlink()
    init_db(args.db, seed=not args.no_seed)

    conn = connect(args.db)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    )]
    print(f"Initialized {args.db}")
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")
    conn.close()


if __name__ == "__main__":
    main()
