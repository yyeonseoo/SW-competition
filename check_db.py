import json
import sqlite3
from common import DB_NAME, init_db

init_db()

with sqlite3.connect(DB_NAME) as conn:
    conn.row_factory = sqlite3.Row

    print("[공고]")
    for row in conn.execute("""
        SELECT source, source_section, title, activity_category,
               interest_categories, region_detail, region_status,
               target_raw, reference_date, date_basis, ocr_used, missing_before_ocr,
               review_required, url
        FROM activities
        ORDER BY reference_date DESC, id DESC
        LIMIT 50
    """):
        item = dict(row)
        for key in ["interest_categories", "missing_before_ocr"]:
            try:
                item[key] = json.loads(item[key])
            except Exception:
                pass
        print(item)

    print("\n[학생]")
    for row in conn.execute("SELECT * FROM students ORDER BY id"):
        print(dict(row))
