def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_tips_seeded_and_filterable(client):
    tips = client.get("/tips").json()
    assert len(tips) >= 15
    assert tips[0]["importance"] == 5

    legal = client.get("/tips", params={"category": "legal"}).json()
    assert legal and all(t["category"] == "legal" for t in legal)
    assert any("Tomträtt" in t["title"] for t in legal)

    important = client.get("/tips", params={"min_importance": 5}).json()
    assert important and all(t["importance"] == 5 for t in important)


def test_tips_invalid_category_rejected(client):
    assert client.get("/tips", params={"category": "nope"}).status_code == 422


def test_create_and_get_tip(client):
    res = client.post("/tips", json={"category": "viewing", "title": "Kolla förrådet", "body": "Finns det?"})
    assert res.status_code == 201
    tip = res.json()
    assert tip["importance"] == 3
    assert client.get(f"/tips/{tip['id']}").json()["title"] == "Kolla förrådet"


def test_duplicate_tip_title_conflicts(client):
    payload = {"category": "cost", "title": "Dubblett", "body": "x"}
    assert client.post("/tips", json=payload).status_code == 201
    assert client.post("/tips", json=payload).status_code == 409


def test_missing_resource_404(client):
    for path in ("/tips/9999", "/criteria/9999", "/neighborhoods/9999", "/associations/9999",
                 "/listings/9999", "/evaluations/9999"):
        assert client.get(path).status_code == 404, path


def test_criteria_json_value_roundtrip(client):
    seeded = client.get("/criteria").json()
    areas = next(c for c in seeded if c["operator"] == "in")
    assert isinstance(areas["value"], list)

    res = client.post("/criteria", json={
        "name": "Balkong", "kind": "soft", "field": "has_balcony", "operator": "=", "value": True,
    })
    assert res.status_code == 201
    assert res.json()["value"] is True
    assert len(client.get("/criteria", params={"kind": "soft"}).json()) == 4


def test_neighborhoods(client):
    assert len(client.get("/neighborhoods").json()) == 2
    res = client.post("/neighborhoods", json={"name": "Aspudden", "municipality": "Stockholm", "rating": 5})
    assert res.status_code == 201
    assert client.post("/neighborhoods", json={"name": "X", "municipality": "Y", "rating": 9}).status_code == 422
    assert len(client.get("/neighborhoods", params={"municipality": "Stockholm"}).json()) == 2


def make_association(client, **overrides):
    payload = {
        "name": "BRF Eken",
        "org_number": "769600-1234",
        "neighborhood_id": 1,
        "built_year": 1962,
        "num_apartments": 48,
        "total_debt": 24_000_000,
        "debt_per_sqm": 8_000,
        "cash_balance": 1_500_000,
        "owns_land": False,
        "tomtratt_fee": 420_000,
        "is_genuine": True,
        **overrides,
    }
    res = client.post("/associations", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def test_association_with_renovations(client):
    brf = make_association(client)
    assert brf["owns_land"] is False and brf["is_genuine"] is True

    res = client.post(f"/associations/{brf['id']}/renovations",
                      json={"kind": "stambyte", "year": 2019, "status": "done", "cost_estimate": 18_000_000})
    assert res.status_code == 201
    client.post(f"/associations/{brf['id']}/renovations", json={"kind": "roof", "year": 2028, "status": "planned"})

    detail = client.get(f"/associations/{brf['id']}").json()
    assert [r["kind"] for r in detail["renovations"]] == ["stambyte", "roof"]
    assert len(client.get(f"/associations/{brf['id']}/renovations").json()) == 2
    assert len(client.get("/associations", params={"neighborhood_id": 1}).json()) == 1


def test_association_validation(client):
    assert client.post("/associations", json={"name": "BRF", "org_number": "123"}).status_code == 422
    assert client.post("/associations/999/renovations", json={"kind": "roof", "status": "done"}).status_code == 404
    assert client.post("/associations", json={"name": "BRF", "neighborhood_id": 999}).status_code == 409


def test_listings_and_evaluations(client):
    brf = make_association(client)
    res = client.post("/listings", json={
        "association_id": brf["id"], "neighborhood_id": 1, "address": "Eksätravägen 12",
        "price": 3_950_000, "rooms": 2.5, "area_sqm": 62, "monthly_fee": 4_100, "floor": 3,
    })
    assert res.status_code == 201
    listing = res.json()
    assert listing["status"] == "watching"
    assert client.post("/listings", json={"address": "X", "status": "sold"}).status_code == 422
    assert len(client.get("/listings", params={"status": "watching"}).json()) == 1
    assert client.get("/listings", params={"status": "bid"}).json() == []

    res = client.post("/evaluations", json={
        "listing_id": listing["id"], "criteria_score": 82, "brf_score": 64,
        "summary": "Bra läge, men tomträtt.", "red_flags": ["Tomträtt – omreglering 2029"],
    })
    assert res.status_code == 201
    assert res.json()["red_flags"] == ["Tomträtt – omreglering 2029"]
    assert len(client.get("/evaluations", params={"listing_id": listing["id"]}).json()) == 1
    assert client.post("/evaluations", json={"listing_id": 999}).status_code == 409
