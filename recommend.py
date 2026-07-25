import json
import re
import sqlite3

from common import (
    DB_NAME,
    clean_text,
    compute_dday,
    extract_deadline_date,
    init_db,
    today_kst,
)
from departments import COLLEGES, all_departments, college_of

# 긴 이름부터 찾아 부분 문자열 충돌을 줄인다(regions.py의 지역 매칭과 같은 방식).
_ALL_DEPARTMENTS = sorted(all_departments(), key=len, reverse=True)
_ALL_COLLEGES = sorted(COLLEGES.keys(), key=len, reverse=True)


def _find_known_names(text, candidates):
    return [
        name
        for name in candidates
        if re.search(rf"(?<![가-힣]){re.escape(name)}(?![가-힣])", text)
    ]


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
    """공고 텍스트에 실제 존재하는(departments.py 기준) 학과·단과대학 이름이 언급된 경우에만
    지원자격 제한으로 간주한다. 이름이 안 겹치는 임의의 '~학과/학부/전공' 문구(예: 담당부서 표기)에
    낚이지 않도록, 광운대 실제 학과/단과대학 전체 목록과 정확히 대조한다."""
    text = clean_text(target_raw)
    if not text:
        return True

    mentioned_departments = _find_known_names(text, _ALL_DEPARTMENTS)
    mentioned_colleges = _find_known_names(text, _ALL_COLLEGES)

    if not mentioned_departments and not mentioned_colleges:
        return True

    if department in mentioned_departments:
        return True

    student_college = college_of(department)
    return bool(student_college and student_college in mentioned_colleges)


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
    # 관심분야를 하나도 안 골랐으면 관심분야 조건은 적용하지 않는다(학과 정보만으로 추천).
    if not student_interests:
        return True
    # 기타는 미분류 상태이므로 자동 제외하지 않는다.
    if activity_interests == ["기타"]:
        return True
    return bool(set(student_interests) & set(activity_interests))


def _student_from_row(row):
    student = dict(row)
    student["interest_categories"] = load_json(student["interest_categories"], [])
    return student


# [국제학생] 게시판 공지는 유학생 대상 안내(수강신청/장학금/기숙사 등)라 국내 학생에게는
# 노출하지 않는다. [국제교류] 게시판은 KW 재학생의 해외교환·인턴십 등 국내 학생도 볼 대상이라
# 별도로 취급하지 않는다(그대로 노출).
INTERNATIONAL_ONLY_BOARD_CATEGORIES = {"국제학생"}


def _match_activities(student, activity_rows):
    results = []
    for row in activity_rows:
        activity = dict(row)
        activity["interest_categories"] = load_json(
            activity["interest_categories"], ["기타"]
        )

        # 국제학생 전용 게시판은 국제학생으로 표시된 학생에게만 노출한다.
        if (
            activity["source_section"] in INTERNATIONAL_ONLY_BOARD_CATEGORIES
            and not student.get("is_international")
        ):
            continue

        is_scholarship = activity["activity_category"] == "장학·지원"
        is_internship = activity["activity_category"] == "인턴·채용"
        is_internal = activity["campus_scope"] == "교내"

        # 장학·지원은 전공 불문: 학과 조건을 적용하지 않는다.
        if not is_scholarship:
            if not department_matches(student["department"], activity["target_raw"]):
                continue

        # 교내 프로그램은 관심분야를 보지 않는다(학과·지역만 본다). 교외는 기존대로 관심분야를 본다.
        if not is_internal and not is_scholarship:
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

        # 지역: 교내 일반은 지역 무관(온캠퍼스 행사의 "장소" 주소가 거주지 제한으로 잘못
        # 추출되는 사례가 있어 지역을 걸면 정상 공고까지 막힘). 교내 장학·지원과 교외 전체만 확인.
        if (not is_internal or is_scholarship) and not region_matches(student, activity):
            continue

        results.append(activity)

    return results


def recommend_for_student(student_name):
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM students WHERE name=?", (student_name,)
        ).fetchone()
        if row is None:
            raise ValueError(f"학생 정보 없음: {student_name}")

        student = _student_from_row(row)
        activity_rows = conn.execute("""
        SELECT * FROM activities
        ORDER BY reference_date DESC, id DESC
        """).fetchall()

    return student, _match_activities(student, activity_rows)


def get_student_by_id(student_id):
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM students WHERE id=?", (student_id,)
        ).fetchone()
        return _student_from_row(row) if row else None


def recommend_for_student_id(student_id):
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM students WHERE id=?", (student_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"학생 정보 없음: id={student_id}")

        student = _student_from_row(row)
        activity_rows = conn.execute("""
        SELECT * FROM activities
        ORDER BY reference_date DESC, id DESC
        """).fetchall()

    return student, _match_activities(student, activity_rows)


def _card_from_activity(activity):
    combined = clean_text(
        f"{activity.get('target_raw') or ''} "
        f"{activity.get('body_text') or ''} {activity.get('ocr_text') or ''}"
    )
    deadline_date = extract_deadline_date(combined)
    dday = compute_dday(deadline_date)
    first_seen = (activity.get("first_seen_at") or "")[:10]

    # 지역 뱃지는 실제로 지역 조건이 적용되는 경우에만 보여준다(교내 장학·지원, 교외 전체).
    is_internal = activity["campus_scope"] == "교내"
    is_scholarship = activity["activity_category"] == "장학·지원"
    region_relevant = (
        (not is_internal or is_scholarship) and activity["region_status"] == "resolved"
    )

    return {
        **activity,
        "target": load_json(activity.get("target"), []),
        "missing_before_ocr": load_json(activity.get("missing_before_ocr"), []),
        "deadline_date": deadline_date,
        "dday": dday,
        "is_new": first_seen == today_kst().isoformat(),
        "region_relevant": region_relevant,
    }


def _split_urgent(cards):
    """마감 3일 이내(0~3일 남음) 카드를 곧 마감 섹션으로 분리한다."""
    urgent = sorted(
        (card for card in cards if card["dday"] is not None and 0 <= card["dday"] <= 3),
        key=lambda card: card["dday"],
    )
    urgent_ids = {card["id"] for card in urgent}
    rest = [card for card in cards if card["id"] not in urgent_ids]
    return urgent, rest


def build_dashboard(student_id):
    """API가 그대로 내려줄 수 있는 형태(교내/교외, 곧 마감, D-day)로 매칭 결과를 가공한다."""
    student, matched = recommend_for_student_id(student_id)

    cards = [_card_from_activity(activity) for activity in matched]
    # 마감일이 확인되고 이미 지난 공고는 개인화 화면에서 제외한다(DB 원본은 그대로 둔다).
    cards = [card for card in cards if not (card["dday"] is not None and card["dday"] < 0)]

    internal_cards = [card for card in cards if card["campus_scope"] == "교내"]
    external_cards = [card for card in cards if card["campus_scope"] == "교외"]

    internal_urgent, internal_rest = _split_urgent(internal_cards)
    external_urgent, external_rest = _split_urgent(external_cards)

    kw_external_cards = [card for card in external_rest if card["source"] == "광운대학교"]
    # 링커리어는 notice.md 스펙대로 최대 6개만 노출한다.
    linkareer_cards = [card for card in external_rest if card["source"] == "링커리어"][:6]

    return {
        "student": student,
        "new_today_count": sum(1 for card in cards if card["is_new"]),
        "internal": {
            "count": len(internal_cards),
            "urgent": internal_urgent,
            "cards": internal_rest,
        },
        "external": {
            "count": len(external_cards),
            "urgent": external_urgent,
            "kw_external_cards": kw_external_cards,
            "linkareer_cards": linkareer_cards,
        },
    }


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
