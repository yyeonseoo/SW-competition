import argparse
import json
import sqlite3

from common import DB_NAME, init_db
from notice_structurer import dumps_structure, resolve_application_dates


def main():
    parser = argparse.ArgumentParser(
        description="최근 구조화 공고의 빈 모집기간만 명시적 근거로 보완합니다."
    )
    parser.add_argument("--structured-date", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    init_db()
    changed = 0
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT *
            FROM activities
            WHERE substr(structured_at, 1, 10) = ?
              AND structure_status = 'success'
            ORDER BY id
            """,
            (args.structured_date,),
        ).fetchall()
        for row in rows:
            try:
                structured = json.loads(row["structured_data"] or "{}")
            except json.JSONDecodeError:
                continue
            start, end = resolve_application_dates(row, structured)
            old_start = row["application_start_date"] or ""
            old_end = row["application_end_date"] or ""

            # 링커리어 상단 접수기간은 확정 데이터이므로 GPT의 오추출도 함께 정정한다.
            sanitized_structure = False
            if row["source"] == "링커리어" and "접수기간" in (row["body_text"] or ""):
                if structured.get("application_start_date") != (start or None):
                    structured["application_start_date"] = start or None
                    sanitized_structure = True
                if structured.get("application_end_date") != (end or None):
                    structured["application_end_date"] = end or None
                    sanitized_structure = True

            new_start = old_start or start
            new_end = old_end or end
            if (
                new_start == old_start
                and new_end == old_end
                and not sanitized_structure
            ):
                continue
            changed += 1
            print(
                f"[{row['id']}] {row['title']} / "
                f"{old_start or '-'}~{old_end or '-'} -> "
                f"{new_start or '-'}~{new_end or '-'}"
            )
            if args.apply:
                conn.execute(
                    """
                    UPDATE activities
                    SET application_start_date = ?,
                        application_end_date = ?,
                        structured_data = ?
                    WHERE id = ?
                    """,
                    (
                        new_start,
                        new_end,
                        dumps_structure(structured),
                        row["id"],
                    ),
                )
        if args.apply:
            conn.commit()
    print(f"보완 대상: {changed}개")


if __name__ == "__main__":
    main()
