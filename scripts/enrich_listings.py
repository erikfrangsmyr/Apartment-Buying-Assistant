"""Enrich listings from Booli → mäklare pages (price, rooms, area, avgift).

Usage:
  uv run python scripts/enrich_listings.py --interest love
  uv run python scripts/enrich_listings.py --all-missing
  uv run python scripts/enrich_listings.py --id 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import DEFAULT_DB_PATH, connect  # noqa: E402
from app.listing_enrich import run_enrich_batch, select_listings_for_enrich  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--id", type=int, default=None, help="Enrich a single listing id")
    parser.add_argument("--interest", choices=["love", "interested", "skip"], default=None)
    parser.add_argument("--all-missing", action="store_true", help="All listings where price IS NULL")
    args = parser.parse_args()

    if not args.id and not args.interest and not args.all_missing:
        parser.error("Specify --id, --interest, or --all-missing")

    conn = connect(args.db)
    try:
        listings = select_listings_for_enrich(
            conn,
            listing_id=args.id,
            interest=args.interest,
            all_missing=args.all_missing,
        )
        if not listings:
            print("No matching listings.")
            return

        results = run_enrich_batch(conn, listings)
        ok = sum(1 for r in results if r.ok)
        print(f"Enriched {ok}/{len(results)} listing(s).")
        for r in results:
            status = "OK" if r.ok else "SKIP"
            fields = ", ".join(r.updated_fields) if r.updated_fields else ""
            extra = f" updated=[{fields}]" if fields else ""
            reason = f" ({r.reason})" if r.reason and not r.ok else ""
            print(f"  [{status}] id={r.listing_id}{reason}{extra}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
