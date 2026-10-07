from app.db import connect, init_db
from app.listing_compare import (
    down_payment_for_price,
    find_default_compare_ids,
    hard_dimension_status,
)
from app.listing_evaluate import infer_fields_from_notes


def test_infer_notes_balcony_and_appliances():
    notes = "Inglasad balkong. Diskmaskin och tvättmaskin i lägenheten."
    inferred = infer_fields_from_notes(notes)
    assert inferred["outdoor_space"] == "balcony"
    assert inferred["has_dishwasher"] is True
    assert inferred["has_washing_machine"] is True
    assert infer_fields_from_notes(notes) == inferred


def test_down_payment_fifteen_percent():
    assert down_payment_for_price(3_495_000) == 524_250


def test_find_default_compare_ids(tmp_path):
    init_db(tmp_path / "cmp.db")
    with connect(tmp_path / "cmp.db") as conn:
        ids = find_default_compare_ids(conn)
        assert len(ids) >= 1
        row = conn.execute("SELECT address FROM listings WHERE id = ?", (ids[0],)).fetchone()
        assert "Diligensvägen" in row[0]


def test_hard_dimension_landavagen_price_pass(tmp_path):
    init_db(tmp_path / "cmp2.db")
    with connect(tmp_path / "cmp2.db") as conn:
        listing = conn.execute(
            "SELECT * FROM listings WHERE address = 'Landåvägen 77'"
        ).fetchone()
        assert listing is not None
        listing_d = dict(listing)
        n = conn.execute(
            "SELECT * FROM neighborhoods WHERE id = ?", (listing_d["neighborhood_id"],)
        ).fetchone()
        status = hard_dimension_status(
            conn, listing_d, dict(n) if n else None, "price", "Maxpris 3,5 MSEK"
        )
    assert status == "pass"


def test_compare_page(client):
    res = client.get("/app/jamfor")
    assert res.status_code == 200
    assert "Jämför objekt" in res.text
    assert "Diligensvägen" in res.text
