import argparse
import sqlite3
import sys

from common import DB_NAME, init_db
from notice_structurer import (
    content_hash,
    dumps_structure,
    resolve_application_dates,
    structure_activity,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def pending_activities(
    conn,
    limit,
    activity_id=None,
    source=None,
    force=False,
    region_sensitive=False,
):
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM activities"
    params = []
    conditions = []
    if activity_id is not None:
        conditions.append("id = ?")
        params.append(activity_id)
    if source:
        conditions.append("source = ?")
        params.append(source)
    if region_sensitive:
        conditions.append(
            "source = '광운대학교' "
            "AND (campus_scope = '교외' OR activity_category = '장학·지원')"
        )
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"

    rows = []
    for row in conn.execute(query, params):
        current_hash = content_hash(row)
        if force or row["structure_status"] != "success" or row["content_hash"] != current_hash:
            rows.append((row, current_hash))
        if len(rows) >= limit:
            break
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="새로 생기거나 내용이 바뀐 공고만 GPT로 구조화합니다."
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--activity-id", type=int)
    parser.add_argument("--source")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--region-sensitive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 500:
        parser.error("--limit은 1~500 사이여야 합니다.")

    init_db()
    success = failed = input_tokens = output_tokens = 0
    with sqlite3.connect(DB_NAME) as conn:
        pending = pending_activities(
            conn,
            args.limit,
            activity_id=args.activity_id,
            source=args.source,
            force=args.force,
            region_sensitive=args.region_sensitive,
        )
        print(f"구조화 대상: {len(pending)}개 (호출 상한 {args.limit}개)")
        if args.dry_run:
            for row, _ in pending:
                print(f"  [{row['id']}] {row['title']}")
            return

        for row, current_hash in pending:
            print(f"[{row['id']}] {row['title']}")
            try:
                result = structure_activity(row)
                data = result["data"]
                application_start_date, application_end_date = (
                    resolve_application_dates(row, data)
                )
                conn.execute(
                    """
                    UPDATE activities
                    SET content_hash = ?, structured_data = ?,
                        structure_status = 'success', structure_confidence = ?,
                        structured_at = ?, structure_model = ?, structure_error = NULL
                        , application_start_date = ?
                        , application_end_date = ?
                        , review_required = CASE
                            WHEN ? < 0.6 THEN 1
                            ELSE review_required
                          END
                    WHERE id = ?
                    """,
                    (
                        current_hash,
                        dumps_structure(data),
                        data["confidence"],
                        result["structured_at"],
                        result["model"],
                        application_start_date,
                        application_end_date,
                        data["confidence"],
                        row["id"],
                    ),
                )
                conn.commit()
                success += 1
                input_tokens += result["input_tokens"]
                output_tokens += result["output_tokens"]
                print(
                    f"  완료: {data['opportunity_type']} / "
                    f"{data['recommendation_group']} / 신뢰도 {data['confidence']:.2f}"
                )
            except Exception as exc:
                conn.execute(
                    """
                    UPDATE activities
                    SET content_hash = ?, structure_status = 'error',
                        structure_error = ?
                    WHERE id = ?
                    """,
                    (current_hash, str(exc)[:500], row["id"]),
                )
                conn.commit()
                failed += 1
                print(f"  실패: {exc}")

    print(
        f"결과: 성공 {success}, 실패 {failed}, "
        f"입력 토큰 {input_tokens}, 출력 토큰 {output_tokens}"
    )


if __name__ == "__main__":
    main()
