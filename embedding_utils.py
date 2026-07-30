import hashlib
import json
import math
import os
import sqlite3

from dotenv import load_dotenv
from openai import OpenAI

from common import DB_NAME
from departments import college_of


DEFAULT_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 512


def embedding_model():
    load_dotenv()
    return os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_MODEL)


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def student_recommendation_text(student):
    interests = student.get("interest_categories") or []
    if isinstance(interests, str):
        try:
            interests = json.loads(interests)
        except json.JSONDecodeError:
            interests = []
    college = college_of(student["department"])
    affiliation = (
        f"{college} {student['department']}"
        if college
        else student["department"]
    )
    parts = [f"광운대학교 {affiliation} {student['grade']}학년 재학생"]
    if interests:
        parts.append(f"관심 분야: {', '.join(interests)}")
    activity_types = student.get("preferred_activity_types") or []
    if isinstance(activity_types, str):
        try:
            activity_types = json.loads(activity_types)
        except json.JSONDecodeError:
            activity_types = []
    if activity_types:
        parts.append(f"선호 활동 유형: {', '.join(activity_types)}")
    preference = (student.get("preference_text") or "").strip()
    if preference:
        parts.append(f"선호 활동: {preference}")
    elif interests or activity_types:
        parts.append("선택한 관심 주제와 활동 유형에 관련된 대학생 활동을 선호함")
    else:
        parts.append("전공과 직접 관련된 대학생 활동을 선호함")
    return ". ".join(parts)


def activity_recommendation_text(activity):
    structured = {}
    try:
        structured = json.loads(activity.get("structured_data") or "{}")
    except json.JSONDecodeError:
        pass
    topics = structured.get("topics") or []
    skills = structured.get("required_skills") or []
    parts = [
        activity.get("title") or "",
        f"활동 유형: {activity.get('activity_category') or ''}",
        structured.get("summary") or "",
    ]
    if topics:
        parts.append(f"주제: {', '.join(topics)}")
    if skills:
        parts.append(f"필요 역량: {', '.join(skills)}")
    return ". ".join(part for part in parts if part)


def embed_texts(texts, client=None):
    if not texts:
        return [], 0
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 없습니다.")
    client = client or OpenAI(api_key=api_key, max_retries=2, timeout=60)
    response = client.embeddings.create(
        model=embedding_model(),
        input=texts,
        dimensions=EMBEDDING_DIMENSIONS,
        encoding_format="float",
    )
    vectors = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
    tokens = getattr(response.usage, "prompt_tokens", 0) if response.usage else 0
    return vectors, tokens


def ensure_student_embedding(student):
    text = student_recommendation_text(student)
    current_hash = text_hash(text)
    model = embedding_model()
    if (
        student.get("embedding_data")
        and student.get("embedding_hash") == current_hash
        and student.get("embedding_model") == model
    ):
        return json.loads(student["embedding_data"])

    vectors, _ = embed_texts([text])
    vector = vectors[0]
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            UPDATE students
            SET embedding_data=?, embedding_hash=?, embedding_model=?
            WHERE id=?
            """,
            (json.dumps(vector, separators=(",", ":")), current_hash, model, student["id"]),
        )
    return vector


def ensure_preference_embedding(student):
    """선호 활동 문장만 별도로 임베딩하고, 문장이 바뀔 때만 다시 생성한다."""
    preference = (student.get("preference_text") or "").strip()
    if not preference:
        return None

    text = f"대학생이 선호하는 활동: {preference}"
    current_hash = text_hash(text)
    model = embedding_model()
    if (
        student.get("preference_embedding_data")
        and student.get("preference_embedding_hash") == current_hash
        and student.get("preference_embedding_model") == model
    ):
        return json.loads(student["preference_embedding_data"])

    vectors, _ = embed_texts([text])
    vector = vectors[0]
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            """
            UPDATE students
            SET preference_embedding_data=?,
                preference_embedding_hash=?,
                preference_embedding_model=?
            WHERE id=?
            """,
            (
                json.dumps(vector, separators=(",", ":")),
                current_hash,
                model,
                student["id"],
            ),
        )
    return vector


def cosine_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0
