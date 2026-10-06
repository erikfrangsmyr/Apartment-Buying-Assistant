import pytest

from app.routers.calculations import interest_deduction, required_amortization_rate


@pytest.mark.parametrize("ltv,expected", [(0.9, 2.0), (0.71, 2.0), (0.7, 1.0), (0.6, 1.0), (0.5, 0.0), (0.0, 0.0)])
def test_amortization_rule(ltv, expected):
    assert required_amortization_rate(ltv) == expected


def test_interest_deduction_brackets():
    assert interest_deduction(50_000) == pytest.approx(15_000)
    assert interest_deduction(150_000) == pytest.approx(30_000 + 10_500)


def test_monthly_cost_typical(client):
    res = client.post("/calculations/monthly-cost", json={
        "price": 4_000_000, "down_payment": 600_000, "interest_rate": 3.5,
        "monthly_fee": 4_000, "operating_costs": 800,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["loan_amount"] == 3_400_000
    assert body["loan_to_value"] == 0.85
    assert body["amortization_rate"] == 2.0
    assert body["interest"] == 9_917
    # 119 000 kr/yr interest: 30 % on the first 100 000, 21 % on the rest.
    assert body["interest_after_deduction"] == 7_084
    assert body["amortization"] == 5_667
    assert body["total"] == 20_383
    assert body["total_after_deduction"] == 17_551
    assert body["warnings"] == []


def test_monthly_cost_warnings(client):
    body = client.post("/calculations/monthly-cost", json={
        "price": 3_000_000, "down_payment": 150_000, "interest_rate": 4, "amortization_rate": 1,
    }).json()
    assert len(body["warnings"]) == 2
    assert "bolånetak" in body["warnings"][0]
    assert "amorteringskrav" in body["warnings"][1]


def test_monthly_cost_no_loan(client):
    body = client.post("/calculations/monthly-cost", json={
        "price": 2_000_000, "down_payment": 2_000_000, "interest_rate": 4, "monthly_fee": 3_000,
    }).json()
    assert body["loan_amount"] == 0
    assert body["total"] == 3_000


def test_monthly_cost_validation(client):
    assert client.post("/calculations/monthly-cost", json={"price": 0, "down_payment": 0, "interest_rate": 3}).status_code == 422
