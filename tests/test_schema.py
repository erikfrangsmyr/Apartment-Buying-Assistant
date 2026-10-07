import sqlite3

import pytest

from app.db import connect, init_db

TABLES = {"tips", "criteria", "neighborhoods", "associations", "renovations", "listings", "evaluations"}


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "schema.db"
    init_db(path)
    c = connect(path)
    yield c
    c.close()


def test_all_tables_created(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert TABLES <= names


def test_seed_is_idempotent(tmp_path):
    path = tmp_path / "twice.db"
    init_db(path)
    init_db(path)
    c = connect(path)
    assert c.execute("SELECT COUNT(*) FROM tips").fetchone()[0] >= 15
    assert c.execute("SELECT COUNT(*) FROM neighborhoods").fetchone()[0] == 25
    c.close()


def test_category_constraint(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO tips (category, title, body) VALUES ('bogus', 't', 'b')")


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO renovations (association_id, kind, status) VALUES (999, 'roof', 'done')")


def test_json_columns_validated(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO criteria (name, kind, field, operator, value) VALUES ('x', 'hard', 'rooms', '>=', 'not json')"
        )


def test_renovations_cascade_with_association(conn):
    conn.execute("INSERT INTO associations (id, name) VALUES (9999, 'BRF Test')")
    conn.execute("INSERT INTO renovations (association_id, kind, status) VALUES (9999, 'stambyte', 'done')")
    conn.execute("DELETE FROM associations WHERE id = 9999")
    assert conn.execute(
        "SELECT COUNT(*) FROM renovations WHERE association_id = 9999"
    ).fetchone()[0] == 0
