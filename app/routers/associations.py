import sqlite3

from fastapi import APIRouter, Depends

from app.db import fetch_all, fetch_one, get_db, insert
from app.brf_assess import assess_brf
from app.models import (
    Association,
    AssociationAssessRequest,
    AssociationAssessResponse,
    AssociationCreate,
    AssociationDetail,
    Renovation,
    RenovationCreate,
)

router = APIRouter(prefix="/associations", tags=["associations"])


@router.post("/assess", response_model=AssociationAssessResponse)
def assess_association(body: AssociationAssessRequest):
    """Rule-based BRF screening from association-like JSON (no database write)."""
    return assess_brf(body)


@router.get("", response_model=list[Association])
def list_associations(neighborhood_id: int | None = None, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_all(conn, "associations", {"neighborhood_id": neighborhood_id}, order_by="name")


@router.get("/{association_id}", response_model=AssociationDetail)
def get_association(association_id: int, conn: sqlite3.Connection = Depends(get_db)):
    association = fetch_one(conn, "associations", association_id)
    association["renovations"] = fetch_all(
        conn, "renovations", {"association_id": association_id}, order_by="year, id"
    )
    return association


@router.post("", response_model=Association, status_code=201)
def create_association(association: AssociationCreate, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "associations", insert(conn, "associations", association.model_dump()))


@router.get("/{association_id}/renovations", response_model=list[Renovation])
def list_renovations(association_id: int, conn: sqlite3.Connection = Depends(get_db)):
    fetch_one(conn, "associations", association_id)
    return fetch_all(conn, "renovations", {"association_id": association_id}, order_by="year, id")


@router.post("/{association_id}/renovations", response_model=Renovation, status_code=201)
def create_renovation(
    association_id: int, renovation: RenovationCreate, conn: sqlite3.Connection = Depends(get_db)
):
    fetch_one(conn, "associations", association_id)
    values = {"association_id": association_id, **renovation.model_dump()}
    return fetch_one(conn, "renovations", insert(conn, "renovations", values))
