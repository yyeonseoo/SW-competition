import json
import re
import sqlite3

from common import DB_NAME, clean_text, init_db


def load_json(value, default):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def grade_matches(grade, target_raw):
    text = clean_text(target_raw)
    if not text:
        return True

    range_match = re.search(r"([1-4])\s*[~\-–]\s*([1-4])\s*학년", text)
    if range_match:
        start, end = map(int, range_match.groups())
        return start <= grade <= end

    minimum = re.search(r"([1-4])\s*학년\s*이상", text)
    if minimum and grade < int(minimum.group(1)):
        return False

    maximum = re.search(r"([1-4])\s*학년\s*이하", text)
    if maximum and grade > int(maximum.group(1)):
        return False

    excluded = [int(value) for value in re.findall(r"([1-4])\s*학년\s*제외", text)]
    if grade in excluded:
        return False

    explicit = [int(value) for value in re.findall(r"([1-4])\s*학년", text)]
    if explicit and not range_match and not minimum and not maximum:
        return grade in explicit

    return True


def department_matches(department, target_raw):
    text = clean_text(target_raw)
    if not text:
        return True

    major_terms = re.findall(
        r"([가-힣A-Za-z0-9·/\s]{2,35}(?:학과|학부|전공))",
        text,
    )
    if not major_terms:
        return True

    department_compact = re.sub(r"\s+", "", department)
    return any(
        department_compact in re.sub(r"\s+", "", term)
        or re.sub(r"\s+", "", term) in department_compact
        for term in major_terms
    )


def region_matches(student, activity):
    status = activity["region_status"]

    if status == "nationwide":
        return True

    # 모호하거나 복수 지역이면 자동 제외하지 않고 검토 대상으로 노출
    if status in {"ambiguous", "multiple"}:
        return True

    if activity["region_sido"] != student["region_sido"]:
        return False

    if (
        activity["region_sigungu"]
        and activity["region_sigungu"] != student["region_sigungu"]
    ):
        return False

    return True


def interest_matches(student_interests, activity_interests):
    # 기타는 미분류 상태이므로 자동 제외하지 않는다.
    if activity_interests == ["기타"]:
        return True
    return bool(set(student_interests) & set(activity_interests))


def recommend_for_student(student_name):
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM students WHERE name=?", (student_name,)
        ).fetchone()
        if row is None:
            raise ValueError(f"학생 정보 없음: {student_name}")

        student = dict(row)
        student["interest_categories"] = load_json(
            student["interest_categories"], []
        )

        activity_rows = conn.execute("""
        SELECT * FROM activities
        ORDER BY reference_date DESC, id DESC
        """).fetchall()

    results = []
    for row in activity_rows:
        activity = dict(row)
        activity["interest_categories"] = load_json(
            activity["interest_categories"], ["기타"]
        )

        is_scholarship = activity["activity_category"] == "장학·지원"
        is_internship = activity["activity_category"] == "인턴·채용"

        # 장학·지원은 전공 불문: 학과·관심분야 조건을 적용하지 않고 지역·학년만 본다.
        if not is_scholarship:
            if not department_matches(student["department"], activity["target_raw"]):
                continue
            if not interest_matches(
                student["interest_categories"],
                activity["interest_categories"],
            ):
                continue

        if not grade_matches(student["grade"], activity["target_raw"]):
            continue

        # 인턴·채용은 본문에 학년 조건이 없어도 정책상 2학년 이상만 노출한다.
        if is_internship and student["grade"] < 2:
            continue

        if not region_matches(student, activity):
            continue

        results.append(activity)

    return student, results


def main():
    student, results = recommend_for_student("김학생")

    print(
        f"{student['name']} / {student['department']} / "
        f"{student['grade']}학년 / "
        f"{student['region_sido']} {student['region_sigungu']}"
    )
    print(f"추천 결과: {len(results)}개\n")

    for index, item in enumerate(results, start=1):
        review = " [검토 필요]" if item["review_required"] else ""
        print(f"[{index}] [{item['source']}] {item['title']}{review}")
        print(f"    카테고리: {item['activity_category']}")
        print(f"    관심분야: {', '.join(item['interest_categories'])}")
        print(f"    지역: {item['region_detail'] or item['region_sido']}")
        print(f"    모집대상: {item['target_raw'] or '확인 필요'}")
        print(f"    기준일: {item['reference_date']} ({item['date_basis']})")
        print(f"    URL: {item['url']}\n")


if __name__ == "__main__":
    main()
