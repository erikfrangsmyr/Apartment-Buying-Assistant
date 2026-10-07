import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import fetch_all, fetch_one, get_db, insert, update
from app.listing_enrich import apply_enrich_result, enrich_listing_row
from app.listing_evaluate import evaluate_listing
from app.models import (
    Listing,
    ListingCreate,
    ListingEnrichResponse,
    ListingEvaluateResponse,
    ListingInterest,
    ListingStatus,
    ListingUpdate,
)

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=list[Listing])
def list_listings(
    status: ListingStatus | None = None,
    interest: ListingInterest | None = None,
    neighborhood_id: int | None = None,
    association_id: int | None = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    filters = {
        "status": status,
        "interest": interest,
        "neighborhood_id": neighborhood_id,
        "association_id": association_id,
    }
    return fetch_all(conn, "listings", filters, order_by="created_at DESC, id DESC")


@router.get("/{listing_id}", response_model=Listing)
def get_listing(listing_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "listings", listing_id)


@router.post("", response_model=Listing, status_code=201)
def create_listing(listing: ListingCreate, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "listings", insert(conn, "listings", listing.model_dump()))


@router.patch("/{listing_id}", response_model=Listing)
def patch_listing(
    listing_id: int,
    body: ListingUpdate,
    conn: sqlite3.Connection = Depends(get_db),
):
    fetch_one(conn, "listings", listing_id)
    data = body.model_dump(exclude_unset=True)
    if not data:
        return fetch_one(conn, "listings", listing_id)
    update(conn, "listings", listing_id, data)
    return fetch_one(conn, "listings", listing_id)


@router.post("/{listing_id}/enrich", response_model=ListingEnrichResponse)
def enrich_listing_endpoint(listing_id: int, conn: sqlite3.Connection = Depends(get_db)):
    listing = fetch_one(conn, "listings", listing_id)
    result = enrich_listing_row(listing, only_missing_price=False)
    updated: list[str] = []
    if result.ok:
        updated = apply_enrich_result(conn, listing, result)
    facts = result.facts
    return ListingEnrichResponse(
        listing_id=listing_id,
        ok=result.ok,
        reason=result.reason,
        updated_fields=updated or result.updated_fields,
        facts={
            k: v
            for k, v in {
                "address": facts.address,
                "price": facts.price,
                "rooms": facts.rooms,
                "area_sqm": facts.area_sqm,
                "monthly_fee": facts.monthly_fee,
                "floor": facts.floor,
                "broker_url": facts.broker_url,
            }.items()
            if v is not None
        },
    )


@router.post("/{listing_id}/evaluate", response_model=ListingEvaluateResponse)
def evaluate_listing_endpoint(listing_id: int, conn: sqlite3.Connection = Depends(get_db)):
    fetch_one(conn, "listings", listing_id)
    try:
        result = evaluate_listing(conn, listing_id)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"listings {listing_id} not found") from None

    brf = result.get("brf_assessment")
    eval_id = insert(
        conn,
        "evaluations",
        {
            "listing_id": listing_id,
            "criteria_score": result["criteria_score"],
            "brf_score": brf["economy_score"] if brf else None,
            "summary": result["summary"],
            "red_flags": json.dumps(result["red_flags"], ensure_ascii=False),
        },
    )
    result["evaluation_id"] = eval_id
    return result
