import argparse
import sqlite3
from collections import defaultdict

from common import (
    DB_NAME,
    _same_notice_content,
    canonical_activity_url,
    clean_text,
    init_db,
)


def main():
    parser = argparse.ArgumentParser(
        description="동일 URL 또는 사실상 동일한 본문의 중복 공고를 정리합니다."
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM activities ORDER BY id").fetchall()
        parent = {row["id"]: row["id"] for row in rows}

        def find(value):
            while parent[value] != value:
                parent[value] = parent[parent[value]]
                value = parent[value]
            return value

        def union(left, right):
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        by_url = defaultdict(list)
        by_title = defaultdict(list)
        for row in rows:
            by_url[canonical_activity_url(row["url"])].append(row)
            by_title[
                (
                    row["source"],
                    row["source_section"] or "",
                    clean_text(row["title"]),
                )
            ].append(row)

        for group in by_url.values():
            for row in group[1:]:
                union(group[0]["id"], row["id"])

        for group in by_title.values():
            if len(group) < 2:
                continue
            for index, left in enumerate(group):
                for right in group[index + 1 :]:
                    if _same_notice_content(left["body_text"], right["body_text"]):
                        union(left["id"], right["id"])

        grouped = defaultdict(list)
        for row in rows:
            grouped[find(row["id"])].append(row)
        duplicates = [group for group in grouped.values() if len(group) > 1]

        print(f"중복 묶음: {len(duplicates)}개")
        print(f"제거 대상: {sum(len(group) - 1 for group in duplicates)}개")
        for group in duplicates:
            # 기존 결과를 보존하기 위해 가장 먼저 저장된 행을 항상 유지한다.
            keeper = min(group, key=lambda row: row["id"])
            removed = [row for row in group if row["id"] != keeper["id"]]
            print(
                f"  유지 [{keeper['id']}] {keeper['title']} / "
                f"제거 {[row['id'] for row in removed]}"
            )
            if not args.apply:
                continue

            first_seen = min(
                (row["first_seen_at"] for row in group if row["first_seen_at"]),
                default=keeper["first_seen_at"],
            )
            last_seen = max(
                (row["last_seen_at"] for row in group if row["last_seen_at"]),
                default=keeper["last_seen_at"],
            )
            for row in removed:
                conn.execute("DELETE FROM activities WHERE id = ?", (row["id"],))
            conn.execute(
                """
                UPDATE activities
                SET url = ?, first_seen_at = ?, last_seen_at = ?
                WHERE id = ?
                """,
                (
                    canonical_activity_url(keeper["url"]),
                    first_seen,
                    last_seen,
                    keeper["id"],
                ),
            )
        if args.apply:
            conn.commit()


if __name__ == "__main__":
    main()
