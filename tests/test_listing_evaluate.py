from app.listing_evaluate import evaluate_listing
from app.db import connect, init_db


def _diligens_listing_id(conn) -> int:
    row = conn.execute(
        "SELECT id FROM listings WHERE address = 'Diligensvägen 4'"
    ).fetchone()
    assert row is not None
    return row[0]


def test_evaluate_diligensvagen_seed(client):
    listings = client.get("/listings").json()
    listing = next(l for l in listings if l["address"] == "Diligensvägen 4")
    res = client.post(f"/listings/{listing['id']}/evaluate")
    assert res.status_code == 200
    body = res.json()
    assert body["listing_id"] == listing["id"]
    assert body["criteria_score"] > 0
    assert body["evaluation_id"] is not None
    names = {r["name"]: r["status"] for r in body["criteria_results"]}
    assert names["Minst 65 kvm"] == "pass"
    assert names["Minst 3 rok"] == "pass"
    assert names["Maxpris 3,5 MSEK"] == "pass"
    assert names["Avgift högst 8 000 kr/mån"] == "pass"
    assert names["Inte källarvåning"] == "pass"
    assert names["Diskmaskin"] == "unverified"
    assert "Diskmaskin" in body["unverified"]
    assert body["brf_assessment"] is not None
    assert 0 <= body["brf_assessment"]["economy_score"] <= 100

    ev = client.get(f"/evaluations/{body['evaluation_id']}").json()
    assert ev["criteria_score"] == body["criteria_score"]


def test_evaluate_module_hard_fail(tmp_path):
    init_db(tmp_path / "t.db")
    with connect(tmp_path / "t.db") as conn:
        n_id = conn.execute("SELECT id FROM neighborhoods LIMIT 1").fetchone()[0]
        lid = conn.execute(
            """INSERT INTO listings (address, neighborhood_id, price, rooms, area_sqm, monthly_fee, floor, status)
               VALUES ('Testgatan 1', ?, 5000000, 2, 50, 9000, 2, 'watching')""",
            (n_id,),
        ).lastrowid
        conn.commit()
        result = evaluate_listing(conn, lid)
    failed = [r["name"] for r in result["criteria_results"] if r["status"] == "fail"]
    assert any("Maxpris" in n for n in failed)
    assert result["hard_criteria_met"] is False


def test_unmapped_criteria_reported_unverified(tmp_path):
    init_db(tmp_path / "t2.db")
    with connect(tmp_path / "t2.db") as conn:
        lid = _diligens_listing_id(conn)
        result = evaluate_listing(conn, lid)
    soft_unmapped = [
        r for r in result["criteria_results"]
        if r["kind"] == "soft" and r["status"] == "unverified" and r["field"] not in (
            "area_sqm", "area_name", "commute_odenplan_min"
        )
    ]
    assert len(soft_unmapped) >= 5
