import json
import sqlite3

import pytest

from app.db import connect, init_db
from scripts.import_watchlist import booli_url, import_watchlist


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "import.db"
    init_db(path)
    c = connect(path)
    yield c
    c.close()


def test_booli_url():
    assert booli_url("bostad", "348073") == "https://www.booli.se/bostad/348073"
    assert booli_url("annons", "6252361") == "https://www.booli.se/annons/6252361"


def test_import_watchlist_inserts_and_is_idempotent(conn: sqlite3.Connection, tmp_path):
    watchlist = {
        "listings": [
            {
                "area_label": "Kärrtorp",
                "id_type": "bostad",
                "id": "348073",
                "interest": "love",
            },
            {
                "area_label": "Jarlaberg",
                "id_type": "annons",
                "id": "6252361",
                "interest": "love",
            },
        ],
        "address_matches": [],
    }
    path = tmp_path / "watchlist.json"
    path.write_text(json.dumps(watchlist), encoding="utf-8")

    stats1 = import_watchlist(conn, watchlist)
    assert stats1["inserted"] == 2
    assert stats1["updated"] == 0

    rows = conn.execute(
        "SELECT interest, neighborhood_id FROM listings WHERE url = ?",
        (booli_url("bostad", "348073"),),
    ).fetchone()
    assert rows[0] == "love"
    assert rows[1] is not None

    stats2 = import_watchlist(conn, watchlist)
    assert stats2["inserted"] == 0
    assert stats2["skipped"] == 2


def test_import_updates_diligens_interest(conn: sqlite3.Connection):
    conn.execute(
        "INSERT INTO listings (address, status, interest) VALUES ('Diligensvägen 4', 'watching', NULL)"
    )
    conn.commit()
    data = {
        "listings": [],
        "address_matches": [
            {"address": "Diligensvägen 4", "interest": "interested", "notes_append": "watchlist"},
        ],
    }
    stats = import_watchlist(conn, data)
    assert stats["updated"] == 1
    row = conn.execute(
        "SELECT interest, notes FROM listings WHERE address = 'Diligensvägen 4'"
    ).fetchone()
    assert row[0] == "interested"
    assert "watchlist" in (row[1] or "")
