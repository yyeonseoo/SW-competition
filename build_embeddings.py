import argparse
import json
import sqlite3

from common import DB_NAME, init_db
from embedding_utils import (
    activity_recommendation_text,
    embed_texts,
    embedding_model,
    text_hash,
)


def main():
    parser = argparse.ArgumentParser(description="개인화 대상 공고 임베딩을 캐시합니다.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM activities ORDER BY id DESC"
        ).fetchall()
        pending = []
        for row in rows:
            activity = dict(row)
            try:
                structured = json.loads(activity.get("structured_data") or "{}")
            except json.JSONDecodeError:
                structured = {}
            if structured.get("recommendation_group") != "personalized":
                continue
            text = activity_recommendation_text(activity)
            current_hash = text_hash(text)
            if (
                args.force
                or activity.get("embedding_hash") != current_hash
                or activity.get("embedding_model") != embedding_model()
                or not activity.get("embedding_data")
            ):
                pending.append((activity, text, current_hash))
            if len(pending) >= args.limit:
                break

        print(f"임베딩 대상: {len(pending)}개")
        total_tokens = 0
        for offset in range(0, len(pending), 100):
            batch = pending[offset : offset + 100]
            vectors, tokens = embed_texts([item[1] for item in batch])
            total_tokens += tokens
            for (activity, text, current_hash), vector in zip(batch, vectors):
                conn.execute(
                    """
                    UPDATE activities
                    SET recommendation_text=?, embedding_data=?,
                        embedding_hash=?, embedding_model=?
                    WHERE id=?
                    """,
                    (
                        text,
                        json.dumps(vector, separators=(",", ":")),
                        current_hash,
                        embedding_model(),
                        activity["id"],
                    ),
                )
            conn.commit()
            print(f"  {min(offset + len(batch), len(pending))}/{len(pending)} 완료")
        print(f"입력 토큰: {total_tokens}")


if __name__ == "__main__":
    main()
