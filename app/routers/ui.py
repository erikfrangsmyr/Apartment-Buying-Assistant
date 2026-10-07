import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import fetch_all, fetch_one, get_db

ROOT = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))

router = APIRouter(tags=["ui"])

STATUS_LABELS = {
    "watching": "Bevakar",
    "viewed": "Besökt",
    "bid": "Bud",
    "rejected": "Avvisad",
}


def _format_sek(amount: int | float | None) -> str:
    if amount is None:
        return "—"
    return f"{int(amount):,}".replace(",", " ") + " kr"


@router.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"health": {"status": "ok"}},
    )


@router.get("/ui")
def ui_alias():
    return RedirectResponse(url="/app", status_code=302)


@router.get("/app")
def app_listings(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    listings = fetch_all(conn, "listings", {}, order_by="created_at DESC, id DESC")
    for row in listings:
        row["status_label"] = STATUS_LABELS.get(row.get("status"), row.get("status"))
        row["price_fmt"] = _format_sek(row.get("price"))
        row["fee_fmt"] = _format_sek(row.get("monthly_fee"))
    return templates.TemplateResponse(request, "listings.html", {"listings": listings})


@router.get("/app/listings/{listing_id}")
def app_listing_detail(
    listing_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    listing = fetch_one(conn, "listings", listing_id)
    listing["status_label"] = STATUS_LABELS.get(listing.get("status"), listing.get("status"))
    listing["price_fmt"] = _format_sek(listing.get("price"))
    listing["fee_fmt"] = _format_sek(listing.get("monthly_fee"))
    return templates.TemplateResponse(request, "listing_detail.html", {"listing": listing})


@router.get("/app/kostnad")
def monthly_cost_page(request: Request):
    defaults = {
        "price": 3_495_000,
        "down_payment": 524_250,
        "interest_rate": 3.5,
        "monthly_fee": 5_927,
        "operating_costs": 800,
    }
    return templates.TemplateResponse(request, "monthly_cost.html", {"defaults": defaults})
