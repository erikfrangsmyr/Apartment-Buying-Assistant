import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "db" / "schema.sql"
SEED_PATH = ROOT / "db" / "seed.sql"
DEFAULT_DB_PATH = Path(os.environ.get("APARTMENT_DB", ROOT / "data" / "apartment.db"))


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path, seed: bool = True) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if seed:
            conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
    conn.close()


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row, json_fields: tuple[str, ...] = ()) -> dict[str, Any]:
    data = dict(row)
    for field in json_fields:
        if data.get(field) is not None:
            data[field] = json.loads(data[field])
    return data


def insert(conn: sqlite3.Connection, table: str, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    try:
        cur = conn.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", list(values.values())
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail=f"Constraint failed: {exc}") from exc
    return cur.lastrowid


def fetch_one(
    conn: sqlite3.Connection, table: str, row_id: int, json_fields: tuple[str, ...] = ()
) -> dict[str, Any]:
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{table} {row_id} not found")
    return row_to_dict(row, json_fields)


def update(
    conn: sqlite3.Connection,
    table: str,
    row_id: int,
    values: dict[str, Any],
) -> None:
    if not values:
        return
    columns = ", ".join(f"{k} = ?" for k in values)
    try:
        cur = conn.execute(
            f"UPDATE {table} SET {columns} WHERE id = ?",
            list(values.values()) + [row_id],
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail=f"Constraint failed: {exc}") from exc
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"{table} {row_id} not found")


def fetch_all(
    conn: sqlite3.Connection,
    table: str,
    filters: dict[str, Any] | None = None,
    order_by: str = "id",
    json_fields: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    active = {k: v for k, v in (filters or {}).items() if v is not None}
    where = " AND ".join(f"{k} = ?" for k in active)
    sql = f"SELECT * FROM {table}" + (f" WHERE {where}" if where else "") + f" ORDER BY {order_by}"
    return [row_to_dict(r, json_fields) for r in conn.execute(sql, list(active.values()))]
