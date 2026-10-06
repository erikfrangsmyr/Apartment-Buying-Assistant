import sqlite3

from fastapi import APIRouter, Depends

from app.db import fetch_all, fetch_one, get_db, insert
from app.models import Listing, ListingCreate, ListingStatus

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
