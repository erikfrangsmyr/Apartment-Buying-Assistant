import json
import sqlite3

from fastapi import APIRouter, Depends

from app.db import fetch_all, fetch_one, get_db, insert
from app.models import Evaluation, EvaluationCreate

router = APIRouter(prefix="/evaluations", tags=["evaluations"])
JSON_FIELDS = ("red_flags",)


@router.get("", response_model=list[Evaluation])
def list_evaluations(listing_id: int | None = None, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_all(
        conn, "evaluations", {"listing_id": listing_id}, order_by="created_at DESC, id DESC",
        json_fields=JSON_FIELDS,
    )


@router.get("/{evaluation_id}", response_model=Evaluation)
def get_evaluation(evaluation_id: int, conn: sqlite3.Connection = Depends(get_db)):
    return fetch_one(conn, "evaluations", evaluation_id, JSON_FIELDS)


@router.post("", response_model=Evaluation, status_code=201)
def create_evaluation(evaluation: EvaluationCreate, conn: sqlite3.Connection = Depends(get_db)):
    values = evaluation.model_dump()
    values["red_flags"] = json.dumps(values["red_flags"], ensure_ascii=False)
    return fetch_one(conn, "evaluations", insert(conn, "evaluations", values), JSON_FIELDS)
