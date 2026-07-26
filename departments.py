# -*- coding: utf-8 -*-
"""
광운대학교 단과대학 → 학과 데이터.

단일 소스는 web/data/departments.json
학과 목록을 바꿀 땐 그 JSON 하나만 고치면 백엔드·프론트 양쪽에 반영

사용법:
    from departments import COLLEGES, all_departments, college_of

    # 단과대학 목록
    print(list(COLLEGES.keys()))

    # 전체 학과 flat list
    print(all_departments())

    # 특정 학과의 단과대학 찾기
    print(college_of("정보융합학부"))   # → "인공지능융합대학"
"""

import json
from pathlib import Path

_JSON_PATH = Path(__file__).resolve().parent / "web" / "data" / "departments.json"

with open(_JSON_PATH, encoding="utf-8") as _file:
    _DATA = json.load(_file)

COLLEGES: dict[str, list[str]] = {
    college["name"]: college["departments"] for college in _DATA["colleges"]
}

# ── 역인덱스: 학과명 → 단과대학 ──────────────────────────────
_DEPT_TO_COLLEGE: dict[str, str] = {
    dept: college
    for college, depts in COLLEGES.items()
    for dept in depts
}


def all_departments() -> list[str]:
    """전체 학과 flat list (단과대학 순서 유지)."""
    return [dept for depts in COLLEGES.values() for dept in depts]


def college_of(department: str) -> str | None:
    """학과명으로 단과대학을 반환. 없으면 None."""
    return _DEPT_TO_COLLEGE.get(department)


def departments_of(college: str) -> list[str]:
    """단과대학명으로 소속 학과 목록을 반환. 없으면 빈 리스트."""
    return COLLEGES.get(college, [])


# ── 간단 검증 ─────────────────────────────────────────────────
if __name__ == "__main__":
    total = sum(len(v) for v in COLLEGES.values())
    print(f"단과대학: {len(COLLEGES)}개 / 학과: {total}개")
    for college, depts in COLLEGES.items():
        print(f"  {college} ({len(depts)}): {', '.join(depts)}")
    print()
    print("college_of('정보융합학부') →", college_of("정보융합학부"))
    print("college_of('없는학과') →", college_of("없는학과"))
