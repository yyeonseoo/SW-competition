import sqlite3
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from common import (
    ACTIVITY_CATEGORIES,
    DB_NAME,
    INTEREST_CATEGORIES,
    PREFERRED_ACTIVITY_TYPES,
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
    department: str = Field(min_length=1)
    grade: int = Field(ge=1, le=4)
    enrollment_status: Literal["freshman", "enrolled", "on_leave", "graduating"]
    region_sido: str = Field(min_length=1)
    region_sigungu: str = Field(min_length=1)
    interest_categories: List[str] = []
    preferred_activity_types: List[str] = []
    email: Optional[str] = None
    notify_opt_in: int = 1
    is_international: int = 0
    preference_text: str = Field(default="", max_length=500)


class StudentPatch(BaseModel):
    department: Optional[str] = None
    grade: Optional[int] = Field(default=None, ge=1, le=4)
    enrollment_status: Optional[
        Literal["freshman", "enrolled", "on_leave", "graduating"]
    ] = None
    region_sido: Optional[str] = None
    region_sigungu: Optional[str] = None
    interest_categories: Optional[List[str]] = None
    preferred_activity_types: Optional[List[str]] = None
    email: Optional[str] = None
    notify_opt_in: Optional[int] = None
    is_international: Optional[int] = None
    preference_text: Optional[str] = Field(default=None, max_length=500)


def _student_response(student_id):
    student = get_student_by_id(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="학생 정보 없음")
    return student


@app.get("/api/meta")
def get_meta():
    return {
        "interest_categories": INTEREST_CATEGORIES,
        "preferred_activity_types": PREFERRED_ACTIVITY_TYPES,
        "activity_categories": ACTIVITY_CATEGORIES,
        "regions": REGIONS,
    }


@app.post("/api/students", status_code=201)
def post_student(body: StudentIn):
    student_id = create_student(
        department=body.department,
        grade=body.grade,
        enrollment_status=body.enrollment_status,
        interest_categories=body.interest_categories,
        preferred_activity_types=body.preferred_activity_types,
        region_sido=body.region_sido,
        region_sigungu=body.region_sigungu,
        email=body.email,
        notify_opt_in=body.notify_opt_in,
        is_international=body.is_international,
        preference_text=body.preference_text,
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

    for list_field in ("interest_categories", "preferred_activity_types"):
        if list_field not in updates:
            continue
        import json

        updates[list_field] = json.dumps(
            updates[list_field], ensure_ascii=False
        )
    if any(
        key in updates
        for key in (
            "department",
            "grade",
            "interest_categories",
            "preferred_activity_types",
            "preference_text",
        )
    ):
        updates["embedding_data"] = None
        updates["embedding_hash"] = None
        updates["embedding_model"] = None
    if "preference_text" in updates:
        updates["preference_embedding_data"] = None
        updates["preference_embedding_hash"] = None
        updates["preference_embedding_model"] = None

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
