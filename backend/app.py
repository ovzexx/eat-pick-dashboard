from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).parents[1] / "data" / "foods.db"
QUALITY_FILTER = "normalized=1 AND calories>=5 AND calories IS NOT NULL AND protein IS NOT NULL AND sugar IS NOT NULL AND (protein>0 OR sugar>0)"
app = FastAPI(title="EAT-PICK Nutrition API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(503, "데이터베이스가 없습니다. import_data.py를 먼저 실행하세요.")
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@app.get("/api/health")
def health():
    return {"ok": DB_PATH.exists()}


@app.get("/api/meta")
def meta(data_type: str = "가공식품", category_large: str = ""):
    with db() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM foods WHERE data_type=? AND {QUALITY_FILTER}", (data_type,)
        ).fetchone()[0]
        categories = [row[0] for row in connection.execute(
            "SELECT DISTINCT category_large FROM foods WHERE data_type=? AND category_large<>'' ORDER BY category_large",
            (data_type,),
        )]
        params: list[str] = [data_type]
        clause = "data_type=? AND category_medium<>''"
        if category_large:
            clause += " AND category_large=?"
            params.append(category_large)
        medium = [row[0] for row in connection.execute(
            f"SELECT DISTINCT category_medium FROM foods WHERE {clause} ORDER BY category_medium", params
        )]
    return {"total": total, "categories": categories, "mediumCategories": medium}


@app.get("/api/suggest")
def suggest(
    q: str = Query("", max_length=100),
    data_type: str = "가공식품",
):
    if not q:
        return []
    with db() as connection:
        rows = connection.execute(
            f"""SELECT DISTINCT name FROM foods
                WHERE data_type=? AND {QUALITY_FILTER} AND name LIKE ?
                ORDER BY name ASC LIMIT 10""",
            (data_type, f"%{q}%"),
        ).fetchall()
    return [row[0] for row in rows]


@app.get("/api/foods/by-ids")
def foods_by_ids(ids: str = Query(...)):
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    if not id_list:
        return []
    placeholders = ",".join("?" * len(id_list))
    with db() as connection:
        result = connection.execute(
            f"""SELECT id,food_code,name,manufacturer,category_large,category_medium,
                       original_basis,calories,protein,sugar
                FROM foods WHERE id IN ({placeholders})""",
            id_list,
        ).fetchall()
    return [dict(row) for row in result]


@app.get("/api/foods")
def foods(
    data_type: str = "가공식품",
    sort: Literal["calories", "protein", "sugar"] = "calories",
    q: str = Query("", max_length=100),
    category_large: str = "",
    category_medium: str = "",
    min_calories: float | None = None,
    max_calories: float | None = None,
    min_protein: float | None = None,
    max_sugar: float | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
):
    where = ["data_type=?", QUALITY_FILTER]
    if sort == "protein":
        where.append("protein>0")
    params: list[object] = [data_type]
    filters = [
        (q, "name LIKE ?", f"%{q}%"),
        (category_large, "category_large=?", category_large),
        (category_medium, "category_medium=?", category_medium),
        (min_calories is not None, "calories>=?", min_calories),
        (max_calories is not None, "calories<=?", max_calories),
        (min_protein is not None, "protein>=?", min_protein),
        (max_sugar is not None, "sugar<=?", max_sugar),
    ]
    for active, expression, value in filters:
        if active:
            where.append(expression)
            params.append(value)
    condition = " AND ".join(where)
    direction = "DESC" if sort == "protein" else "ASC"
    offset = (page - 1) * page_size
    with db() as connection:
        total = connection.execute(f"SELECT COUNT(*) FROM foods WHERE {condition}", params).fetchone()[0]
        result = connection.execute(
            f"""SELECT id,food_code,name,manufacturer,category_large,category_medium,
                       original_basis,calories,protein,sugar
                FROM foods WHERE {condition}
                ORDER BY {sort} {direction}, name ASC LIMIT ? OFFSET ?""",
            [*params, page_size, offset],
        ).fetchall()
    return {"items": [dict(row) for row in result], "total": total, "page": page, "pageSize": page_size}
