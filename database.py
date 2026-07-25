import json
import sqlite3
import uuid
from utils.text_processor import now_kst_string
from utils.classifier import classify_campus_scope

DB_NAME = "recommendation.db"


def get_db_connection():
    """데이터베이스 연결 객체를 반환합니다."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """SQLite 데이터베이스 스키마 및 마이그레이션을 초기화합니다."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_section TEXT,
            campus_scope TEXT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            activity_category TEXT NOT NULL,
            interest_categories TEXT NOT NULL,
            region_sido TEXT,
            region_sigungu TEXT,
            region_detail TEXT,
            region_status TEXT,
            target TEXT NOT NULL,
            target_raw TEXT,
            reference_date TEXT NOT NULL,
            date_basis TEXT NOT NULL,
            body_text TEXT,
            ocr_text TEXT,
            ocr_used INTEGER DEFAULT 0,
            missing_before_ocr TEXT,
            review_required INTEGER DEFAULT 0,
            first_seen_at TEXT,
            last_seen_at TEXT
        )
        """)

        # campus_scope 컬럼 안전 보장 (마이그레이션)
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(activities)")
        }
        if "campus_scope" not in existing_columns:
            conn.execute("ALTER TABLE activities ADD COLUMN campus_scope TEXT")

        # null_scope 백필(backfill)
        null_scope_rows = conn.execute(
            "SELECT id, source, source_section FROM activities WHERE campus_scope IS NULL"
        ).fetchall()
        for row_id, source, source_section in null_scope_rows:
            conn.execute(
                "UPDATE activities SET campus_scope = ? WHERE id = ?",
                (classify_campus_scope(source, source_section or ""), row_id),
            )

        conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 4),
            interest_categories TEXT NOT NULL,
            region_sido TEXT NOT NULL,
            region_sigungu TEXT,
            email TEXT,
            notify_opt_in INTEGER DEFAULT 1,
            is_international INTEGER DEFAULT 0
        )
        """)

        student_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(students)")
        }
        if "email" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN email TEXT")
        if "notify_opt_in" not in student_columns:
            conn.execute(
                "ALTER TABLE students ADD COLUMN notify_opt_in INTEGER DEFAULT 1"
            )
        if "is_international" not in student_columns:
            conn.execute(
                "ALTER TABLE students ADD COLUMN is_international INTEGER DEFAULT 0"
            )


def create_student(
    department,
    grade,
    interest_categories,
    region_sido,
    region_sigungu="",
    email=None,
    notify_opt_in=1,
    name=None,
    is_international=0,
):
    """프로필 온보딩 및 회원가입 시 학생 정보를 신규 등록합니다."""
    name = name or f"guest-{uuid.uuid4().hex[:8]}"
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(
            """
            INSERT INTO students (
                name, department, grade, interest_categories,
                region_sido, region_sigungu, email, notify_opt_in, is_international
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                department,
                grade,
                json.dumps(interest_categories, ensure_ascii=False),
                region_sido,
                region_sigungu,
                email,
                notify_opt_in,
                int(bool(is_international)),
            ),
        )
        return cursor.lastrowid



def save_activity(item):
    """
    수집된 활동 데이터를 DB에 저장하거나 수정(업소트/upsert)합니다.
    신규 insert 시 True, 수정 UPDATE 시 False를 반환합니다.
    """
    now = now_kst_string()
    with sqlite3.connect(DB_NAME) as conn:
        existing = conn.execute(
            "SELECT id FROM activities WHERE url = ?", (item["url"],)
        ).fetchone()

        serialized = {
            **item,
            "campus_scope": classify_campus_scope(
                item["source"], item.get("source_section", "")
            ),
            "interest_categories": json.dumps(item["interest_categories"], ensure_ascii=False),
            "target": json.dumps(item["target"], ensure_ascii=False),
            "missing_before_ocr": json.dumps(item.get("missing_before_ocr", []), ensure_ascii=False),
        }

        if existing is None:
            conn.execute("""
            INSERT INTO activities (
                source, source_section, campus_scope, title, url, activity_category,
                interest_categories, region_sido, region_sigungu, region_detail,
                region_status, target, target_raw, reference_date, date_basis, body_text,
                ocr_text, ocr_used, missing_before_ocr, review_required,
                first_seen_at, last_seen_at
            ) VALUES (
                :source, :source_section, :campus_scope, :title, :url, :activity_category,
                :interest_categories, :region_sido, :region_sigungu, :region_detail,
                :region_status, :target, :target_raw, :reference_date, :date_basis, :body_text,
                :ocr_text, :ocr_used, :missing_before_ocr, :review_required,
                :first_seen_at, :last_seen_at
            )
            """, {**serialized, "first_seen_at": now, "last_seen_at": now})
            return True

        conn.execute("""
        UPDATE activities SET
            source=:source,
            source_section=:source_section,
            campus_scope=:campus_scope,
            title=:title,
            activity_category=:activity_category,
            interest_categories=:interest_categories,
            region_sido=:region_sido,
            region_sigungu=:region_sigungu,
            region_detail=:region_detail,
            region_status=:region_status,
            target=:target,
            target_raw=:target_raw,
            reference_date=:reference_date,
            date_basis=:date_basis,
            body_text=:body_text,
            ocr_text=:ocr_text,
            ocr_used=:ocr_used,
            missing_before_ocr=:missing_before_ocr,
            review_required=:review_required,
            last_seen_at=:last_seen_at
        WHERE url=:url
        """, {**serialized, "last_seen_at": now})
        return False
