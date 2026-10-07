"""Helpers for side-by-side listing comparison in the web UI."""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

from app.listing_evaluate import CriterionStatus, criterion_status, listing_context

INTEREST_BADGE: dict[str, str] = {
    "love": "❤",
    "interested": "👍",
    "skip": "👎",
}

INTEREST_LABEL: dict[str, str] = {
    "love": "Älskar",
    "interested": "Intressant",
    "skip": "Hoppa över",
}

STATUS_LABEL: dict[CriterionStatus, str] = {
    "pass": "✓",
    "fail": "✗",
    "unverified": "?",
}

# Rows shown in jämför-tabellen (criterion name in DB, or synthetic key).
COMPARE_ROWS: list[tuple[str, str, str | None]] = [
    ("area_sqm", "Boarea (m²)", "Minst 65 kvm"),
    ("rooms", "Rum", "Minst 3 rok"),
    ("price", "Pris", "Maxpris 3,5 MSEK"),
    ("monthly_fee", "Avgift/mån", "Avgift högst 8 000 kr/mån"),
    ("outdoor", "Balkong/uteplats", "Balkong eller uteplats"),
    ("floor", "Våning", "Inte källarvåning"),
    ("interest", "Intresse", None),
    ("brf_score", "BRF-poäng", None),
    ("monthly_cost", "Månadskostnad (ca)", None),
]

MAX_COMPARE = 4

MONTHLY_COST_DEFAULTS = {
    "down_payment_ratio": 0.15,
    "interest_rate": 3.5,
    "operating_costs": 800,
}


def interest_display(interest: str | None) -> str:
    if not interest:
        return "—"
    badge = INTEREST_BADGE.get(interest, "")
    label = INTEREST_LABEL.get(interest, interest)
    return f"{badge} {label}".strip()


def status_cell(status: CriterionStatus, detail: str | None = None, value: str | None = None) -> dict[str, Any]:
    text = value if value is not None else STATUS_LABEL[status]
    return {"status": status, "text": text, "detail": detail}


def down_payment_for_price(price: int | float | None) -> int:
    if price is None:
        return 0
    return int(round(price * MONTHLY_COST_DEFAULTS["down_payment_ratio"]))


def find_default_compare_ids(conn: sqlite3.Connection) -> list[int]:
    """Pre-select Diligensvägen 4 and Landåvägen 77 (Booli 6252361) when present."""
    ids: list[int] = []
    diligens = conn.execute(
        "SELECT id FROM listings WHERE address LIKE 'Diligensvägen%' ORDER BY id LIMIT 1"
    ).fetchone()
    if diligens:
        ids.append(int(diligens[0]))
    landa = conn.execute(
        "SELECT id FROM listings WHERE address LIKE 'Landåvägen%' OR url LIKE '%6252361%' OR notes LIKE '%6252361%' ORDER BY id LIMIT 1"
    ).fetchone()
    if landa and int(landa[0]) not in ids:
        ids.append(int(landa[0]))
    return ids


def criterion_by_name(evaluate_result: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if not evaluate_result:
        return None
    for row in evaluate_result.get("criteria_results", []):
        if row.get("name") == name:
            return row
    return None


def build_compare_row_cells(
    listing: dict[str, Any],
    neighborhood: dict[str, Any] | None,
    evaluate_result: dict[str, Any] | None,
    monthly_total: int | None,
) -> list[dict[str, Any]]:
    ctx = listing_context(listing, neighborhood)
    cells: list[dict[str, Any]] = []

    for _key, label, criterion_name in COMPARE_ROWS:
        if _key == "interest":
            cells.append(
                {
                    "label": label,
                    **status_cell(
                        "pass" if listing.get("interest") == "love" else "unverified",
                        value=interest_display(listing.get("interest")),
                    ),
                }
            )
            continue
        if _key == "brf_score":
            brf = (evaluate_result or {}).get("brf_assessment")
            if brf and brf.get("economy_score") is not None:
                score = brf["economy_score"]
                cells.append(
                    {
                        "label": label,
                        **status_cell("pass", value=f"{score:.0f}/100"),
                    }
                )
            else:
                cells.append({"label": label, **status_cell("unverified", value="—")})
            continue
        if _key == "monthly_cost":
            if monthly_total is not None:
                cells.append(
                    {
                        "label": label,
                        **status_cell("unverified", value=f"{monthly_total:,}".replace(",", " ") + " kr/mån"),
                    }
                )
            else:
                cells.append({"label": label, **status_cell("unverified", value="—")})
            continue
        if _key == "floor":
            floor = listing.get("floor")
            floor_text = str(floor) if floor is not None else "?"
            crit = criterion_by_name(evaluate_result, "Inte källarvåning")
            if crit:
                cells.append(
                    {
                        "label": label,
                        **status_cell(crit["status"], crit.get("detail"), value=floor_text),
                    }
                )
            else:
                st: CriterionStatus = "unverified"
                if ctx.get("is_basement") is True:
                    st = "fail"
                elif ctx.get("is_basement") is False:
                    st = "pass"
                cells.append({"label": label, **status_cell(st, value=floor_text)})
            continue
        if _key == "outdoor":
            crit = criterion_by_name(evaluate_result, criterion_name or "")
            if crit:
                cells.append({"label": label, **status_cell(crit["status"], crit.get("detail"))})
            elif ctx.get("outdoor_space"):
                cells.append({"label": label, **status_cell("pass", value=str(ctx["outdoor_space"]))})
            else:
                cells.append({"label": label, **status_cell("unverified")})
            continue

        if criterion_name:
            crit = criterion_by_name(evaluate_result, criterion_name)
            if crit:
                raw = listing.get(_key)
                display = str(raw) if raw is not None else "?"
                cells.append(
                    {
                        "label": label,
                        **status_cell(crit["status"], crit.get("detail"), value=display),
                    }
                )
                continue

        cells.append({"label": label, **status_cell("unverified")})

    return cells


def hard_dimension_status(
    conn: sqlite3.Connection,
    listing: dict[str, Any],
    neighborhood: dict[str, Any] | None,
    field: str,
    criterion_name: str,
) -> CriterionStatus:
    """Evaluate one hard dimension without full evaluate_listing (for unit tests)."""
    row = conn.execute("SELECT * FROM criteria WHERE name = ?", (criterion_name,)).fetchone()
    if row is None:
        return "unverified"
    c = dict(row)
    ctx = listing_context(listing, neighborhood)
    status, _ = criterion_status(c["field"], c["operator"], c["value"], ctx)
    return status
