from fastapi import APIRouter

from app.models import MonthlyCostRequest, MonthlyCostResponse

router = APIRouter(prefix="/calculations", tags=["calculations"])

# Bolånetak 90 % applies from 2026-04-01 (was 85 %).
MAX_LOAN_TO_VALUE = 0.90
INTEREST_DEDUCTION_LIMIT = 100_000
INTEREST_DEDUCTION_LOW = 0.30
INTEREST_DEDUCTION_HIGH = 0.21


def required_amortization_rate(loan_to_value: float) -> float:
    """Swedish amorteringskrav, in percent of the loan per year."""
    if loan_to_value > 0.70:
        return 2.0
    if loan_to_value > 0.50:
        return 1.0
    return 0.0


def interest_deduction(annual_interest: float) -> float:
    low = min(annual_interest, INTEREST_DEDUCTION_LIMIT)
    high = max(annual_interest - INTEREST_DEDUCTION_LIMIT, 0)
    return low * INTEREST_DEDUCTION_LOW + high * INTEREST_DEDUCTION_HIGH


def monthly_cost(req: MonthlyCostRequest) -> MonthlyCostResponse:
    warnings: list[str] = []
    loan = max(req.price - req.down_payment, 0)
    ltv = loan / req.price
    if ltv > MAX_LOAN_TO_VALUE:
        warnings.append(
            f"Loan-to-value {ltv:.0%} exceeds the bolånetak of {MAX_LOAN_TO_VALUE:.0%}; "
            f"minimum down payment is {round(req.price * (1 - MAX_LOAN_TO_VALUE)):,} kr."
        )

    required = required_amortization_rate(ltv)
    amortization_rate = required if req.amortization_rate is None else req.amortization_rate
    if amortization_rate < required:
        warnings.append(
            f"Amortization {amortization_rate}% is below the amorteringskrav of {required}% "
            f"at {ltv:.0%} loan-to-value."
        )

    annual_interest = loan * req.interest_rate / 100
    interest = annual_interest / 12
    interest_net = (annual_interest - interest_deduction(annual_interest)) / 12
    amortization = loan * amortization_rate / 100 / 12
    fixed = req.monthly_fee + req.operating_costs

    return MonthlyCostResponse(
        loan_amount=loan,
        loan_to_value=round(ltv, 4),
        amortization_rate=amortization_rate,
        interest=round(interest),
        interest_after_deduction=round(interest_net),
        amortization=round(amortization),
        monthly_fee=req.monthly_fee,
        operating_costs=req.operating_costs,
        total=round(interest + amortization + fixed),
        total_after_deduction=round(interest_net + amortization + fixed),
        warnings=warnings,
    )


@router.post("/monthly-cost", response_model=MonthlyCostResponse)
def calculate_monthly_cost(req: MonthlyCostRequest):
    return monthly_cost(req)
