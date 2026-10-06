import sqlite3

from fastapi import APIRouter, Depends

from app.db import fetch_all, fetch_one, get_db, insert
from app.models import Tip, TipCategory, TipCreate

router = APIRouter(prefix="/tips", tags=["tips"])


@router.get("", response_model=list[Tip])
def list_tips(
    category: TipCategory | None = None,
    min_importance: int | None = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    tips = fetch_all(conn, "tips", {"category": category}, order_by="importance DESC, id")
    if min_importance is not None:
        tips = [t for t in tips if t["importance"] >= min_importance]
    return tips


@router.get("/{tip_id}", response_model=Tip)
def get_tip(tip_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "tips", tip_id)


@router.post("", response_model=Tip, status_code=201)
def create_tip(tip: TipCreate, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "tips", insert(conn, "tips", tip.model_dump()))
