from typing import Any, Literal

from pydantic import BaseModel, Field

TipCategory = Literal["brf_finance", "renovation", "legal", "viewing", "cost", "negotiation"]
RenovationKind = Literal["roof", "facade", "stambyte", "windows", "elevator", "other"]
ListingStatus = Literal["watching", "viewed", "bid", "rejected"]


class TipCreate(BaseModel):
    category: TipCategory
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    importance: int = Field(default=3, ge=1, le=5)
    source: str | None = None


class Tip(TipCreate):
    id: int
    created_at: str


class CriterionCreate(BaseModel):
    name: str = Field(min_length=1)
    kind: Literal["hard", "soft"]
    field: str = Field(min_length=1, description="e.g. rooms, area_sqm, max_price, max_avgift, area_name")
    operator: Literal[">=", "<=", "=", "in"]
    value: Any = Field(description="Any JSON value; a list for operator 'in'")
    weight: int = Field(default=3, ge=1, le=5)
    notes: str | None = None


class Criterion(CriterionCreate):
    id: int


class NeighborhoodCreate(BaseModel):
    name: str = Field(min_length=1)
    municipality: str = Field(min_length=1)
    commute_minutes: int | None = Field(default=None, ge=0)
    avg_price_per_sqm: int | None = Field(default=None, ge=0)
    notes: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)


class Neighborhood(NeighborhoodCreate):
    id: int


class RenovationCreate(BaseModel):
    kind: RenovationKind
    year: int | None = Field(default=None, ge=1600, le=2100)
    status: Literal["done", "planned"]
    cost_estimate: int | None = Field(default=None, ge=0)
    notes: str | None = None


class Renovation(RenovationCreate):
    id: int
    association_id: int


class AssociationCreate(BaseModel):
    name: str = Field(min_length=1)
    org_number: str | None = Field(default=None, pattern=r"^\d{6}-\d{4}$")
    neighborhood_id: int | None = None
    built_year: int | None = Field(default=None, ge=1600, le=2100)
    num_apartments: int | None = Field(default=None, gt=0)
    total_debt: int | None = Field(default=None, ge=0)
    debt_per_sqm: int | None = Field(default=None, ge=0)
    cash_balance: int | None = None
    owns_land: bool | None = Field(
        default=None,
        description="True = äganderätt till marken; false = tomträtt (hyr marken)",
    )
    tomtratt_fee: int | None = Field(default=None, ge=0)
    is_genuine: bool | None = Field(default=None, description="Äkta förening")
    planned_works: str | None = None
    last_report_year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = None


class Association(AssociationCreate):
    id: int


class AssociationDetail(Association):
    renovations: list[Renovation]


class RenovationAssessInput(BaseModel):
    kind: RenovationKind
    year: int | None = Field(default=None, ge=1600, le=2100)
    status: Literal["done", "planned"]
    cost_estimate: int | None = Field(default=None, ge=0)
    notes: str | None = None


class AssociationAssessRequest(BaseModel):
    """Association-like payload for rule-based BRF screening (not persisted)."""

    name: str | None = None
    built_year: int | None = Field(default=None, ge=1600, le=2100)
    num_apartments: int | None = Field(default=None, gt=0)
    total_debt: int | None = Field(default=None, ge=0)
    debt_per_sqm: int | None = Field(default=None, ge=0)
    cash_balance: int | None = None
    owns_land: bool | None = Field(
        default=None,
        description="True = äganderätt till marken; false = tomträtt (hyr marken)",
    )
    tomtratt_fee: int | None = Field(default=None, ge=0)
    is_genuine: bool | None = Field(default=None, description="Äkta förening")
    planned_works: str | None = None
    notes: str | None = None
    management_brand: str | None = Field(
        default=None, description="Förvaltare, t.ex. HSB, Riksbyggen, SBC"
    )
    rental_units_count: int | None = Field(default=None, ge=0)
    only_bostadsratter: bool | None = None
    renovations: list[RenovationAssessInput] = Field(default_factory=list)


class AssociationAssessResponse(BaseModel):
    economy_score: float = Field(ge=0, le=100)
    red_flags: list[str]
    green_flags: list[str]
    summary: str
    questions_to_ask: list[str]


class ListingCreate(BaseModel):
    association_id: int | None = None
    neighborhood_id: int | None = None
    address: str = Field(min_length=1)
    url: str | None = None
    price: int | None = Field(default=None, ge=0)
    rooms: float | None = Field(default=None, gt=0)
    area_sqm: float | None = Field(default=None, gt=0)
    monthly_fee: int | None = Field(default=None, ge=0, description="Avgift per month")
    floor: int | None = None
    status: ListingStatus = "watching"
    notes: str | None = None


class Listing(ListingCreate):
    id: int
    created_at: str


class EvaluationCreate(BaseModel):
    listing_id: int
    criteria_score: float | None = Field(default=None, ge=0, le=100)
    brf_score: float | None = Field(default=None, ge=0, le=100)
    summary: str | None = None
    red_flags: list[str] = Field(default_factory=list)


class Evaluation(EvaluationCreate):
    id: int
    created_at: str


class CriterionResult(BaseModel):
    criterion_id: int
    name: str
    kind: Literal["hard", "soft"]
    field: str
    status: Literal["pass", "fail", "unverified"]
    detail: str | None = None
    weight: int


class ListingEvaluateResponse(BaseModel):
    listing_id: int
    criteria_score: float = Field(ge=0, le=100)
    hard_criteria_met: bool
    criteria_results: list[CriterionResult]
    unverified: list[str]
    brf_assessment: AssociationAssessResponse | None = None
    summary: str
    red_flags: list[str]
    evaluation_id: int | None = Field(
        default=None, description="Set when the result was persisted to evaluations"
    )


class MonthlyCostRequest(BaseModel):
    price: int = Field(gt=0, description="Purchase price (kr)")
    down_payment: int = Field(ge=0, description="Kontantinsats (kr)")
    interest_rate: float = Field(ge=0, le=25, description="Annual mortgage rate in percent, e.g. 3.5")
    amortization_rate: float | None = Field(
        default=None,
        ge=0,
        le=25,
        description="Annual amortering in percent of the loan; omit to apply the Swedish amorteringskrav",
    )
    monthly_fee: int = Field(default=0, ge=0, description="BRF avgift per month (kr)")
    operating_costs: int = Field(
        default=0, ge=0, description="Other monthly drift: el, försäkring, bredband (kr)"
    )


class MonthlyCostResponse(BaseModel):
    loan_amount: int
    loan_to_value: float
    amortization_rate: float
    interest: int
    interest_after_deduction: int
    amortization: int
    monthly_fee: int
    operating_costs: int
    total: int
    total_after_deduction: int
    warnings: list[str]
