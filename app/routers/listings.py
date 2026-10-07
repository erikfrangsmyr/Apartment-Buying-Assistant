import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import fetch_all, fetch_one, get_db, insert
from app.listing_evaluate import evaluate_listing
from app.models import Listing, ListingCreate, ListingEvaluateResponse, ListingStatus

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=list[Listing])
def list_listings(
    status: ListingStatus | None = None,
    neighborhood_id: int | None = None,
    association_id: int | None = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    filters = {"status": status, "neighborhood_id": neighborhood_id, "association_id": association_id}
    return fetch_all(conn, "listings", filters, order_by="created_at DESC, id DESC")


@router.get("/{listing_id}", response_model=Listing)
def get_listing(listing_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "listings", listing_id)


@router.post("", response_model=Listing, status_code=201)
def create_listing(listing: ListingCreate, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "listings", insert(conn, "listings", listing.model_dump()))


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
