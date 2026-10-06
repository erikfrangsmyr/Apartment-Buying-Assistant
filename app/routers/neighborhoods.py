import sqlite3

from fastapi import APIRouter, Depends

from app.db import fetch_all, fetch_one, get_db, insert
from app.models import Neighborhood, NeighborhoodCreate

router = APIRouter(prefix="/neighborhoods", tags=["neighborhoods"])


@router.get("", response_model=list[Neighborhood])
def list_neighborhoods(municipality: str | None = None, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_all(conn, "neighborhoods", {"municipality": municipality}, order_by="name")


@router.get("/{neighborhood_id}", response_model=Neighborhood)
def get_neighborhood(neighborhood_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "neighborhoods", neighborhood_id)


@router.post("", response_model=Neighborhood, status_code=201)
def create_neighborhood(neighborhood: NeighborhoodCreate, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "neighborhoods", insert(conn, "neighborhoods", neighborhood.model_dump()))
