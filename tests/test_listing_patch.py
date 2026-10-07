def test_patch_listing_fields(client):
    res = client.post(
        "/listings",
        json={"address": "Testgatan 1", "price": 1_000_000, "rooms": 2, "area_sqm": 45},
    )
    assert res.status_code == 201
    listing_id = res.json()["id"]

    patch = client.patch(
        f"/listings/{listing_id}",
        json={
            "address": "Testgatan 2",
            "price": 2_100_000,
            "monthly_fee": 4500,
            "interest": "love",
            "url": "https://www.lansfast.se/till-salu/example/",
            "notes": "Uppdaterad via API",
        },
    )
    assert patch.status_code == 200
    data = patch.json()
    assert data["address"] == "Testgatan 2"
    assert data["price"] == 2_100_000
    assert data["monthly_fee"] == 4500
    assert data["interest"] == "love"
    assert data["notes"] == "Uppdaterad via API"


def test_patch_listing_validation(client):
    res = client.post("/listings", json={"address": "X"})
    lid = res.json()["id"]
    assert client.patch(f"/listings/{lid}", json={"price": -1}).status_code == 422
    assert client.patch("/listings/99999", json={"address": "Y"}).status_code == 404


def test_enrich_endpoint_uses_mocked_flow(client, monkeypatch):
    from app.listing_enrich import EnrichResult, ListingFacts

    res = client.post("/listings", json={"address": "Booli annons/1 (test)", "url": "https://www.booli.se/annons/1"})
    lid = res.json()["id"]

    def fake_enrich(listing, **kwargs):
        return EnrichResult(
            listing_id=listing["id"],
            ok=True,
            facts=ListingFacts(
                broker_url="https://www.lansfast.se/till-salu/x/",
                price=3_000_000,
                rooms=3,
                area_sqm=70,
            ),
        )

    monkeypatch.setattr("app.routers.listings.enrich_listing_row", fake_enrich)
    out = client.post(f"/listings/{lid}/enrich").json()
    assert out["ok"] is True
    assert out["updated_fields"]
    refreshed = client.get(f"/listings/{lid}").json()
    assert refreshed["price"] == 3_000_000
    assert "lansfast" in refreshed["url"]
