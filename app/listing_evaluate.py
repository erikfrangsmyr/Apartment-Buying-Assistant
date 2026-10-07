"""Rule-based listing evaluation against stored buying criteria."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Literal

from app.brf_assess import assess_brf
from app.models import (
    AssociationAssessRequest,
    AssociationAssessResponse,
    RenovationAssessInput,
)

CriterionStatus = Literal["pass", "fail", "unverified"]

# Criterion `field` -> key on the merged listing context dict (listing + neighborhood).
FIELD_MAP: dict[str, str] = {
    "area_sqm": "area_sqm",
    "rooms": "rooms",
    "price": "price",
    "monthly_fee": "monthly_fee",
    "commute_odenplan_min": "commute_odenplan_min",
    "area_name": "area_name",
    "is_basement": "is_basement",
}


def _parse_criterion_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compare(operator: str, actual: Any, expected: Any) -> bool:
    if operator == ">=":
        a, e = _coerce_number(actual), _coerce_number(expected)
        return a is not None and e is not None and a >= e
    if operator == "<=":
        a, e = _coerce_number(actual), _coerce_number(expected)
        return a is not None and e is not None and a <= e
    if operator == "=":
        if isinstance(expected, bool) or expected in ("true", "false"):
            exp_bool = expected if isinstance(expected, bool) else expected == "true"
            if isinstance(actual, bool):
                return actual == exp_bool
            if actual in (0, 1):
                return bool(actual) == exp_bool
        if isinstance(expected, str) and isinstance(actual, str):
            return actual.lower() == expected.lower()
        a, e = _coerce_number(actual), _coerce_number(expected)
        if a is not None and e is not None:
            return a == e
        return actual == expected
    if operator == "in":
        if not isinstance(expected, list):
            return False
        if actual is None:
            return False
        actual_str = str(actual)
        return actual_str in expected or actual in expected
    return False


def infer_fields_from_notes(notes: str | None) -> dict[str, Any]:
    """Best-effort flags from mäklare/Booli notes (shared with jämför-vyn)."""
    if not notes:
        return {}
    lower = notes.lower()
    inferred: dict[str, Any] = {}
    if "balkong" in lower:
        inferred["outdoor_space"] = "balcony"
    elif "uteplats" in lower:
        inferred["outdoor_space"] = "patio"
    if "diskmaskin" in lower:
        inferred["has_dishwasher"] = True
    if "tvättmaskin" in lower:
        inferred["has_washing_machine"] = True
    if "förråd" in lower or "vindsförråd" in lower:
        inferred["external_storage_possible"] = True
    return inferred


def listing_context(listing: dict[str, Any], neighborhood: dict[str, Any] | None) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "area_sqm": listing.get("area_sqm"),
        "rooms": listing.get("rooms"),
        "price": listing.get("price"),
        "monthly_fee": listing.get("monthly_fee"),
        "commute_odenplan_min": None,
        "area_name": None,
        "is_basement": None,
    }
    if neighborhood:
        ctx["commute_odenplan_min"] = neighborhood.get("commute_minutes")
        ctx["area_name"] = neighborhood.get("name")
    floor = listing.get("floor")
    if floor is not None:
        ctx["is_basement"] = floor < 1
    for key, value in infer_fields_from_notes(listing.get("notes")).items():
        if ctx.get(key) is None:
            ctx[key] = value
    return ctx


def _listing_context(listing: dict[str, Any], neighborhood: dict[str, Any] | None) -> dict[str, Any]:
    return listing_context(listing, neighborhood)


def criterion_status(
    field: str, operator: str, expected_raw: str, ctx: dict[str, Any]
) -> tuple[CriterionStatus, str | None]:
    if field not in FIELD_MAP:
        return "unverified", f"Inget fält i databasen för «{field}» — verifiera manuellt."

    key = FIELD_MAP[field]
    actual = ctx.get(key)
    if actual is None:
        return "unverified", f"Saknar värde för {field} — verifiera manuellt."

    expected = _parse_criterion_value(expected_raw)
    if _compare(operator, actual, expected):
        return "pass", None
    return "fail", f"Uppfyller inte: {actual!r} mot krav {expected!r} ({operator})."


def _criterion_status(
    field: str, operator: str, expected_raw: str, ctx: dict[str, Any]
) -> tuple[CriterionStatus, str | None]:
    return criterion_status(field, operator, expected_raw, ctx)


def _criteria_score(rows: list[dict[str, Any]]) -> float:
    verified = [r for r in rows if r["status"] != "unverified"]
    if not verified:
        return 0.0
    weight_sum = sum(r["weight"] for r in verified)
    passed = sum(r["weight"] for r in verified if r["status"] == "pass")
    return round(100.0 * passed / weight_sum, 1)


def _load_listing_bundle(
    conn: sqlite3.Connection, listing_id: int
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None] | None:
    listing = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if listing is None:
        return None
    listing_d = dict(listing)
    neighborhood = None
    if listing_d.get("neighborhood_id"):
        row = conn.execute(
            "SELECT * FROM neighborhoods WHERE id = ?", (listing_d["neighborhood_id"],)
        ).fetchone()
        neighborhood = dict(row) if row else None
    association = None
    if listing_d.get("association_id"):
        row = conn.execute(
            "SELECT * FROM associations WHERE id = ?", (listing_d["association_id"],)
        ).fetchone()
        association = dict(row) if row else None
    return listing_d, neighborhood, association


def _management_from_notes(notes: str | None) -> str | None:
    if not notes:
        return None
    lower = notes.lower()
    for brand in ("nabo", "hsb", "riksbyggen", "sbc"):
        if brand in lower:
            return brand.upper() if brand == "hsb" else brand.capitalize()
    return None


def _association_assess_payload(
    association: dict[str, Any], renovations: list[dict[str, Any]]
) -> AssociationAssessRequest | None:
    if association.get("built_year") is None and association.get("debt_per_sqm") is None:
        return None
    reno_inputs = [
        RenovationAssessInput(
            kind=r["kind"],
            year=r.get("year"),
            status=r["status"],
            cost_estimate=r.get("cost_estimate"),
            notes=r.get("notes"),
        )
        for r in renovations
    ]
    return AssociationAssessRequest(
        name=association.get("name"),
        built_year=association.get("built_year"),
        num_apartments=association.get("num_apartments"),
        total_debt=association.get("total_debt"),
        debt_per_sqm=association.get("debt_per_sqm"),
        cash_balance=association.get("cash_balance"),
        owns_land=bool(association["owns_land"]) if association.get("owns_land") is not None else None,
        tomtratt_fee=association.get("tomtratt_fee"),
        is_genuine=bool(association["is_genuine"]) if association.get("is_genuine") is not None else None,
        planned_works=association.get("planned_works"),
        notes=association.get("notes"),
        management_brand=_management_from_notes(association.get("notes")),
        renovations=reno_inputs,
    )


def evaluate_listing(conn: sqlite3.Connection, listing_id: int) -> dict[str, Any]:
    bundle = _load_listing_bundle(conn, listing_id)
    if bundle is None:
        raise LookupError("listing not found")
    listing, neighborhood, association = bundle

    ctx = _listing_context(listing, neighborhood)
    criteria_rows = conn.execute("SELECT * FROM criteria ORDER BY kind, id").fetchall()

    results: list[dict[str, Any]] = []
    unverified: list[str] = []
    hard_failures: list[str] = []

    for row in criteria_rows:
        c = dict(row)
        status, detail = _criterion_status(c["field"], c["operator"], c["value"], ctx)
        entry = {
            "criterion_id": c["id"],
            "name": c["name"],
            "kind": c["kind"],
            "field": c["field"],
            "status": status,
            "detail": detail,
            "weight": c["weight"],
        }
        results.append(entry)
        if status == "unverified":
            unverified.append(c["name"])
        elif status == "fail" and c["kind"] == "hard":
            hard_failures.append(c["name"])

    score = _criteria_score(results)
    hard_verified = [r for r in results if r["kind"] == "hard" and r["status"] != "unverified"]
    hard_pass = all(r["status"] == "pass" for r in hard_verified)

    brf_result: AssociationAssessResponse | None = None
    if association:
        renovations = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM renovations WHERE association_id = ? ORDER BY year, id",
                (association["id"],),
            ).fetchall()
        ]
        payload = _association_assess_payload(association, renovations)
        if payload:
            brf_result = assess_brf(payload)

    if hard_failures:
        summary = (
            f"Kriterier: {score}/100. Hårda missar: {', '.join(hard_failures)}."
            + (f" {brf_result.summary}" if brf_result else "")
        )
    elif unverified:
        summary = (
            f"Kriterier: {score}/100 på verifierade fält; "
            f"{len(unverified)} krav ej kontrollerade i databasen."
            + (f" {brf_result.summary}" if brf_result else "")
        )
    else:
        summary = f"Kriterier: {score}/100 — alla kontrollerbara krav uppfyllda." + (
            f" {brf_result.summary}" if brf_result else ""
        )

    red_flags = list(hard_failures)
    if brf_result:
        red_flags.extend(brf_result.red_flags)

    return {
        "listing_id": listing_id,
        "criteria_score": score,
        "hard_criteria_met": hard_pass,
        "criteria_results": results,
        "unverified": unverified,
        "brf_assessment": brf_result.model_dump() if brf_result else None,
        "summary": summary.strip(),
        "red_flags": red_flags,
    }
