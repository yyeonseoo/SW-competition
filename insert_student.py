import json
import sqlite3

from common import DB_NAME, init_db

init_db()

student = {
    "name": "김학생",
    "department": "경영학과",
    "grade": 2,
    "interest_categories": [
        "경제/금융",
        "콘텐츠",
        "경영/컨설팅/마케팅",
    ],
    "region_sido": "서울특별시",
    "region_sigungu": "노원구",
}

with sqlite3.connect(DB_NAME) as conn:
    conn.execute("""
    INSERT INTO students (
        name, department, grade, interest_categories,
        region_sido, region_sigungu
    ) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(name) DO UPDATE SET
        department=excluded.department,
        grade=excluded.grade,
        interest_categories=excluded.interest_categories,
        region_sido=excluded.region_sido,
        region_sigungu=excluded.region_sigungu
    """, (
        student["name"],
        student["department"],
        student["grade"],
        json.dumps(student["interest_categories"], ensure_ascii=False),
        student["region_sido"],
        student["region_sigungu"],
    ))

print("학생 정보 저장 완료")
