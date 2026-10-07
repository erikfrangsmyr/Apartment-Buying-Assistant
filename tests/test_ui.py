def test_app_listings_page(client):
    res = client.get("/app")
    assert res.status_code == 200
    assert "Diligensvägen 4" in res.text
    assert "Sparade objekt" in res.text


def test_listing_detail_edit_form(client):
    listings = client.get("/listings").json()
    diligens = next(l for l in listings if l["address"] == "Diligensvägen 4")
    res = client.get(f"/app/listings/{diligens['id']}")
    assert res.status_code == 200
    assert "Redigera objekt" in res.text
    assert 'id="listing-edit-form"' in res.text


def test_dashboard(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Bostadsköp" in res.text
    assert "ok" in res.text.lower()


def test_ui_redirect(client):
    assert client.get("/ui", follow_redirects=False).status_code == 302
    assert client.get("/ui", follow_redirects=True).url.path == "/app"
