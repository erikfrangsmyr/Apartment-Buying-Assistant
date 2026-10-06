from app.brf_assess import assess_brf
from app.models import AssociationAssessRequest, RenovationAssessInput


def test_healthy_brf_scores_high():
    req = AssociationAssessRequest(
        built_year=2005,
        num_apartments=55,
        debt_per_sqm=4_500,
        cash_balance=4_000_000,
        total_debt=20_000_000,
        owns_land=True,
        is_genuine=True,
        management_brand="HSB",
        only_bostadsratter=True,
        renovations=[
            RenovationAssessInput(kind="roof", year=2020, status="done"),
        ],
    )
    res = assess_brf(req)
    assert res.economy_score >= 75
    assert any("Äkta" in f or "äganderätt" in f.lower() for f in res.green_flags)
    assert not any("Oäkta" in f for f in res.red_flags)


def test_oakt_and_tomtratt_heavy_penalty():
    req = AssociationAssessRequest(
        built_year=1960,
        num_apartments=30,
        debt_per_sqm=16_000,
        cash_balance=100_000,
        total_debt=40_000_000,
        owns_land=False,
        tomtratt_fee=600_000,
        is_genuine=False,
        rental_units_count=8,
        renovations=[],
    )
    res = assess_brf(req)
    assert res.economy_score < 40
    assert any("Oäkta" in f for f in res.red_flags)
    assert any("tomträtt" in f.lower() or "äganderätt" in f.lower() for f in res.red_flags)
    assert any("hyres" in f.lower() for f in res.red_flags)
    assert len(res.questions_to_ask) >= 2


def test_old_house_without_stambyte_flags():
    req = AssociationAssessRequest(
        built_year=1963,
        num_apartments=40,
        debt_per_sqm=8_000,
        owns_land=True,
        is_genuine=True,
        renovations=[],
    )
    res = assess_brf(req)
    assert any("stambyte" in f.lower() for f in res.red_flags)
    assert any("stambyte" in q.lower() or "relin" in q.lower() for q in res.questions_to_ask)


def test_api_assess_endpoint(client):
    res = client.post(
        "/associations/assess",
        json={
            "built_year": 1970,
            "num_apartments": 48,
            "debt_per_sqm": 7000,
            "cash_balance": 2_500_000,
            "owns_land": True,
            "is_genuine": True,
            "renovations": [{"kind": "stambyte", "year": 2015, "status": "done"}],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert 0 <= body["economy_score"] <= 100
    assert "summary" in body
    assert isinstance(body["red_flags"], list)
    assert isinstance(body["questions_to_ask"], list)


def test_assess_route_not_captured_as_id(client):
    assert client.get("/associations/assess").status_code == 422
