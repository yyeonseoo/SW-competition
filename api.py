import sqlite3
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from common import (
    ACTIVITY_CATEGORIES,
    DB_NAME,
    INTEREST_CATEGORIES,
    create_student,
    init_db,
)
from recommend import build_dashboard, get_student_by_id
from regions import REGIONS

app = FastAPI(title="KW-LIFE API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


class StudentIn(BaseModel):
    department: str
    grade: int = Field(ge=1, le=4)
    region_sido: str
    region_sigungu: str = ""
    interest_categories: List[str] = []
    email: Optional[str] = None
    notify_opt_in: int = 1
    is_international: int = 0


class StudentPatch(BaseModel):
    department: Optional[str] = None
    grade: Optional[int] = Field(default=None, ge=1, le=4)
    region_sido: Optional[str] = None
    region_sigungu: Optional[str] = None
    interest_categories: Optional[List[str]] = None
    email: Optional[str] = None
    notify_opt_in: Optional[int] = None
    is_international: Optional[int] = None


def _student_response(student_id):
    student = get_student_by_id(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="학생 정보 없음")
    return student


@app.get("/api/meta")
def get_meta():
    return {
        "interest_categories": INTEREST_CATEGORIES,
        "activity_categories": ACTIVITY_CATEGORIES,
        "regions": REGIONS,
    }


@app.post("/api/students", status_code=201)
def post_student(body: StudentIn):
    student_id = create_student(
        department=body.department,
        grade=body.grade,
        interest_categories=body.interest_categories,
        region_sido=body.region_sido,
        region_sigungu=body.region_sigungu,
        email=body.email,
        notify_opt_in=body.notify_opt_in,
        is_international=body.is_international,
    )
    return _student_response(student_id)


@app.get("/api/students/{student_id}")
def get_student(student_id: int):
    return _student_response(student_id)


@app.patch("/api/students/{student_id}")
def patch_student(student_id: int, body: StudentPatch):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return _student_response(student_id)

    if "interest_categories" in updates:
        import json

        updates["interest_categories"] = json.dumps(
            updates["interest_categories"], ensure_ascii=False
        )

    with sqlite3.connect(DB_NAME) as conn:
        existing = conn.execute(
            "SELECT id FROM students WHERE id=?", (student_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="학생 정보 없음")

        columns = ", ".join(f"{key}=?" for key in updates)
        conn.execute(
            f"UPDATE students SET {columns} WHERE id=?",
            (*updates.values(), student_id),
        )

    return _student_response(student_id)


@app.get("/api/dashboard")
def get_dashboard(student_id: int):
    if get_student_by_id(student_id) is None:
        raise HTTPException(status_code=404, detail="학생 정보 없음")
    return build_dashboard(student_id)
