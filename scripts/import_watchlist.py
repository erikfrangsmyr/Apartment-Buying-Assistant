"""Import Erik & Jenny Booli watchlist into listings (watching + url + interest).

Usage:
  uv run python scripts/import_watchlist.py [--db PATH] [--watchlist PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import DEFAULT_DB_PATH, connect  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WATCHLIST = ROOT / "db" / "watchlist.json"

AREA_TO_NEIGHBORHOOD: dict[str, tuple[str, str]] = {
    "jarlaberg": ("Järlaberg", "Nacka"),
    "nacka forum": ("Nacka Forum", "Nacka"),
    "henriksdal": ("Henriksdal", "Nacka"),
    "kärrtorp": ("Kärrtorp", "Stockholm"),
    "enskede dalen": ("Enskede", "Stockholm"),
    "gubbängen": ("Björkhagen", "Stockholm"),
    "årsta": ("Årsta", "Stockholm"),
    "årstaberg": ("Årstaberg", "Stockholm"),
    "hammarbyhöjden": ("Hammarbyhöjden", "Stockholm"),
    "ekudden": ("Nacka Strand", "Nacka"),
    "finntorp": ("Finntorp", "Nacka"),
    "bromma": ("Bromma", "Stockholm"),
    "svedmyra": ("Enskede", "Stockholm"),
}


def booli_url(id_type: str, listing_id: str) -> str:
    if id_type not in ("bostad", "annons"):
        raise ValueError(f"Unknown id_type: {id_type}")
    return f"https://www.booli.se/{id_type}/{listing_id}"


def ensure_interest_column(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(listings)")}
    if "interest" not in cols:
        conn.execute(
            "ALTER TABLE listings ADD COLUMN interest TEXT "
            "CHECK (interest IS NULL OR interest IN ('love', 'interested', 'skip'))"
        )
        conn.commit()


def resolve_neighborhood_id(conn: sqlite3.Connection, area_label: str) -> int | None:
    key = area_label.strip().lower()
    mapped = AREA_TO_NEIGHBORHOOD.get(key)
    if not mapped:
        return None
    name, municipality = mapped
    row = conn.execute(
        "SELECT id FROM neighborhoods WHERE name = ? AND municipality = ?",
        (name, municipality),
    ).fetchone()
    return int(row[0]) if row else None


def placeholder_address(area_label: str, id_type: str, listing_id: str) -> str:
    return f"Booli {id_type}/{listing_id} ({area_label})"


def import_watchlist(
    conn: sqlite3.Connection,
    data: dict,
    dry_run: bool = False,
) -> dict[str, int]:
    ensure_interest_column(conn)
    stats = {"inserted": 0, "updated": 0, "skipped": 0}

    for entry in data.get("listings", []):
        id_type = entry["id_type"]
        listing_id = str(entry["id"])
        interest = entry["interest"]
        area_label = entry["area_label"]
        url = booli_url(id_type, listing_id)
        address = placeholder_address(area_label, id_type, listing_id)
        neighborhood_id = resolve_neighborhood_id(conn, area_label)
        notes = f"Imported from Booli watchlist. Area label: {area_label}."

        existing = conn.execute("SELECT id, interest FROM listings WHERE url = ?", (url,)).fetchone()
        if existing:
            if existing[1] != interest:
                if not dry_run:
                    conn.execute(
                        "UPDATE listings SET interest = ?, notes = COALESCE(notes, '') || ? WHERE id = ?",
                        (interest, f"\n{notes}", existing[0]),
                    )
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
            continue

        if dry_run:
            stats["inserted"] += 1
            continue

        conn.execute(
            """
            INSERT INTO listings (
                association_id, neighborhood_id, address, url, price, rooms, area_sqm,
                monthly_fee, floor, status, interest, notes
            ) VALUES (NULL, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, 'watching', ?, ?)
            """,
            (neighborhood_id, address, url, interest, notes),
        )
        stats["inserted"] += 1

    for match in data.get("address_matches", []):
        address = match["address"]
        interest = match["interest"]
        append = match.get("notes_append", "")
        row = conn.execute(
            "SELECT id, interest, notes FROM listings WHERE address = ?", (address,)
        ).fetchone()
        if not row:
            stats["skipped"] += 1
            continue
        new_notes = (row[2] or "") + (f"\n{append}" if append and append not in (row[2] or "") else "")
        if row[1] == interest and new_notes == (row[2] or ""):
            stats["skipped"] += 1
            continue
        if not dry_run:
            conn.execute(
                "UPDATE listings SET interest = ?, notes = ? WHERE id = ?",
                (interest, new_notes.strip() or None, row[0]),
            )
        stats["updated"] += 1

    if not dry_run:
        conn.commit()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--watchlist", type=Path, default=DEFAULT_WATCHLIST)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = json.loads(args.watchlist.read_text(encoding="utf-8"))
    conn = connect(args.db)
    try:
        stats = import_watchlist(conn, data, dry_run=args.dry_run)
    finally:
        conn.close()

    mode = "dry-run" if args.dry_run else "import"
    print(f"Watchlist {mode} ({args.watchlist.name}): {stats}")


if __name__ == "__main__":
    main()
