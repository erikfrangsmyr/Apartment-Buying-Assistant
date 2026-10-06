import json
import sqlite3

from fastapi import APIRouter, Depends

from app.db import fetch_all, fetch_one, get_db, insert
from app.models import Criterion, CriterionCreate

router = APIRouter(prefix="/criteria", tags=["criteria"])
JSON_FIELDS = ("value",)


@router.get("", response_model=list[Criterion])
def list_criteria(kind: str | None = None, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_all(conn, "criteria", {"kind": kind}, json_fields=JSON_FIELDS)


@router.get("/{criterion_id}", response_model=Criterion)
def get_criterion(criterion_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "criteria", criterion_id, JSON_FIELDS)


@router.post("", response_model=Criterion, status_code=201)
def create_criterion(criterion: CriterionCreate, conn: sqlite3.Connection = Depends(get_db)):
    values = criterion.model_dump()
    values["value"] = json.dumps(values["value"], ensure_ascii=False)
    return fetch_one(conn, "criteria", insert(conn, "criteria", values), JSON_FIELDS)
