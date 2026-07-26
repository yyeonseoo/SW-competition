import json
import re
import sqlite3
from datetime import datetime

from common import (
    DB_NAME,
    clean_text,
    compute_dday,
    extract_deadline_date,
    init_db,
    is_noise_notice,
    today_kst,
)
from departments import COLLEGES, all_departments, college_of
from embedding_utils import cosine_similarity, ensure_student_embedding
from regions import extract_region

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


REGION_ELIGIBILITY_TERMS = (
    "거주",
    "주민등록",
    "주소",
    "소재 대학",
    "소재 학교",
    "관내 대학",
    "관내 학교",
    "재학",
    "출신",
    "지역 우선",
    "우선 선발",
)


def structured_eligibility_regions(structured):
    if structured.get("region_restriction") != "include_only":
        return []

    evidence = clean_text(structured.get("region_eligibility_evidence") or "")
    if not evidence or not any(term in evidence for term in REGION_ELIGIBILITY_TERMS):
        return []

    parsed_regions = []
    for value in structured.get("regions") or []:
        for part in re.split(r"[,/·]", str(value)):
            parsed = extract_region(part.strip())
            if parsed["region_status"] == "resolved":
                parsed_regions.append(parsed)

    return parsed_regions


def structured_region_matches(student, structured):
    parsed_regions = structured_eligibility_regions(structured)

    # 구조화 지역을 표준 지역으로 해석하지 못하면 자동 제외하지 않는다.
    if not parsed_regions:
        return True
    return any(region_matches(student, region) for region in parsed_regions)


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


def structured_eligibility_matches(student, activity):
    """GPT가 구조화한 명시적 자격 조건만 검사한다.

    아직 구조화되지 않은 공고는 기존 규칙으로 처리해 점진적으로 도입할 수 있다.
    """
    structured = load_json(activity.get("structured_data"), None)
    if not structured:
        return True
    if not structured.get("recommendable", True):
        return False
    if structured.get("student_eligible") is False:
        return False
    if (
        structured.get("international_student_required")
        and not student.get("is_international")
    ):
        return False

    grade_min = structured.get("grade_min")
    grade_max = structured.get("grade_max")
    if grade_min is not None and student["grade"] < grade_min:
        return False
    if grade_max is not None and student["grade"] > grade_max:
        return False

    enrollment_types = set(structured.get("eligible_enrollment_types") or [])
    meaningful_types = enrollment_types - {"unknown", "all_students"}
    if meaningful_types:
        # 현재 온보딩 사용자는 학부 재학생이며, 1학년만 신입생으로 판단한다.
        current_types = {"enrolled"}
        if student["grade"] == 1:
            current_types.add("freshman")
        if not current_types & meaningful_types:
            return False

    major_rule = structured.get("major_restriction")
    eligible_majors = structured.get("eligible_majors") or []
    excluded_majors = structured.get("excluded_majors") or []
    # 모델이 "기계", "전기전자", "CAD" 같은 계열·기술명을 전공으로 반환할 수 있다.
    # 실제 학과/단과대학 목록과 정확히 대응되는 값만 하드 필터로 사용하고 나머지는
    # 이후 의미 유사도 점수의 재료로 남긴다.
    known_eligible = [
        major
        for major in eligible_majors
        if major in _ALL_DEPARTMENTS or major in _ALL_COLLEGES
    ]
    known_excluded = [
        major
        for major in excluded_majors
        if major in _ALL_DEPARTMENTS or major in _ALL_COLLEGES
    ]
    student_college = college_of(student["department"])
    if major_rule == "include_only" and known_eligible:
        if (
            student["department"] not in known_eligible
            and student_college not in known_eligible
        ):
            return False
    if major_rule == "exclude_only" and (
        student["department"] in known_excluded
        or student_college in known_excluded
    ):
        return False
    return True


# [국제학생] 게시판 공지는 유학생 대상 안내(수강신청/장학금/기숙사 등)라 국내 학생에게는
# 노출하지 않는다. [국제교류] 게시판은 KW 재학생의 해외교환·인턴십 등 국내 학생도 볼 대상이라
# 별도로 취급하지 않는다(그대로 노출).
INTERNATIONAL_ONLY_BOARD_CATEGORIES = {"국제학생"}
STRUCTURED_EXCLUDED_TYPES = {
    "staff_recruitment",
    "administrative_notice",
    "military_notice",
}
CLOSED_NOTICE_TITLE_KEYWORDS = {
    "수상자 발표",
    "합격자 발표",
    "경기 결과",
    "모집마감",
}
EMPTY_TARGET_TOKENS = {"및", "또는", "등", "해당", "가능", "-", "·"}
ENROLLMENT_TYPE_LABELS = {
    "freshman": "신입생",
    "enrolled": "재학생",
    "leave_of_absence": "휴학생",
    "expected_graduate": "졸업예정자",
    "graduate": "졸업생",
    "graduate_student": "대학원생",
    "all_students": "전체 학생",
    "unknown": "",
}
CHILD_ONLY_KEYWORDS = {
    "초등학생",
    "중학생",
    "고등학생",
    "초·중·고",
    "초중고",
    "청소년",
    "어린이",
}
STUDENT_OR_ADULT_KEYWORDS = {
    "대학생",
    "대학원생",
    "재학생",
    "휴학생",
    "졸업생",
    "청년",
    "성인",
    "일반인",
    "전 국민",
    "누구나",
}
APPLICATION_EVIDENCE_KEYWORDS = {
    "모집",
    "접수",
    "신청",
    "지원",
    "제출",
    "공모",
    "응모",
    "출품",
    "마감",
    "기한",
    "서류",
    "신고기간",
    "연장기간",
    "application",
    "apply",
    "deadline",
    "close",
}


def is_child_only_notice(activity, structured):
    """미성년 대상만 명시됐을 때 제외하고, 혼합 대상 공고는 보존한다."""
    eligible = " ".join(structured.get("eligible_statuses") or [])
    target_text = clean_text(f"{activity.get('target_raw') or ''} {eligible}")
    has_child_target = any(keyword in target_text for keyword in CHILD_ONLY_KEYWORDS)
    has_student_or_adult = any(
        keyword in target_text for keyword in STUDENT_OR_ADULT_KEYWORDS
    )
    return has_child_target and not has_student_or_adult


def _match_activities(student, activity_rows):
    results = []
    for row in activity_rows:
        activity = dict(row)
        if (
            activity["source"] == "광운대학교"
            and is_noise_notice(
                activity["title"],
                activity.get("source_section", ""),
            )
        ):
            continue
        activity["interest_categories"] = load_json(
            activity["interest_categories"], ["기타"]
        )
        structured = load_json(activity.get("structured_data"), None)

        if not structured_eligibility_matches(student, activity):
            continue
        if structured and structured.get("opportunity_type") in STRUCTURED_EXCLUDED_TYPES:
            continue
        if structured and is_child_only_notice(activity, structured):
            continue
        if any(keyword in activity["title"] for keyword in CLOSED_NOTICE_TITLE_KEYWORDS):
            continue

        # 국제학생 전용 게시판은 국제학생으로 표시된 학생에게만 노출한다.
        if (
            activity["source_section"] in INTERNATIONAL_ONLY_BOARD_CATEGORIES
            and not student.get("is_international")
        ):
            continue

        recommendation_group = (
            structured.get("recommendation_group") if structured else None
        )
        is_scholarship = activity["activity_category"] == "장학·지원"
        is_internship = activity["activity_category"] == "인턴·채용"
        is_internal = activity["campus_scope"] == "교내"

        # 장학·지원은 전공 불문: 학과 조건을 적용하지 않는다.
        if not is_scholarship:
            if not department_matches(student["department"], activity["target_raw"]):
                continue

        # 교내 일반 공고는 관심분야를 보지 않고 학과·학년만 확인한다.
        # 교외 공고는 장학·지원을 제외하고 관심분야가 겹쳐야 한다.
        should_match_interest = (
            not is_internal
            and not is_scholarship
            and (
                recommendation_group == "personalized"
                if recommendation_group
                else True
            )
        )
        if should_match_interest:
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

        # 링커리어는 지역 무관으로 유지한다. 광운대 [외부]와 교내 장학·지원은
        # 구조화 모델이 실제 지원자격으로 확인한 지역 제한만 적용한다.
        if (
            activity["source"] != "링커리어"
            and (not is_internal or is_scholarship)
            and not structured_region_matches(student, structured or {})
        ):
            continue

        results.append(activity)

    return results


def _apply_personalization_scores(student, activities):
    vector_activities = [
        activity
        for activity in activities
        if activity.get("embedding_data")
        and (load_json(activity.get("structured_data"), {}) or {}).get(
            "recommendation_group"
        )
        == "personalized"
    ]
    if not vector_activities:
        return activities
    try:
        student_vector = ensure_student_embedding(student)
    except Exception as exc:
        print(f"임베딩 점수 계산 생략: {exc}")
        return activities

    student_interests = set(student.get("interest_categories") or [])
    preference = clean_text(student.get("preference_text") or "")
    for activity in activities:
        activity["recommendation_score"] = None
        activity["recommendation_reason"] = ""
        activity["eligibility_uncertain"] = False
        if activity not in vector_activities:
            structured = load_json(activity.get("structured_data"), {}) or {}
            if structured.get("recommendation_group") == "eligibility_only":
                activity["recommendation_reason"] = "추가 지원자격 확인이 필요해요"
                activity["eligibility_uncertain"] = True
            elif structured.get("recommendation_group") == "essential_notice":
                activity["recommendation_reason"] = "학생에게 필요한 안내일 수 있어요"
            continue

        activity_vector = load_json(activity.get("embedding_data"), [])
        similarity = max(0.0, min(1.0, cosine_similarity(student_vector, activity_vector)))
        activity_interests = set(activity.get("interest_categories") or [])
        overlap = student_interests & activity_interests
        interest_score = 1.0 if overlap else (0.5 if not student_interests else 0.0)
        score = 0.8 * similarity + 0.2 * interest_score
        activity["recommendation_score"] = round(score * 100, 1)

        if overlap:
            activity["recommendation_reason"] = (
                f"{', '.join(sorted(overlap)[:2])} 관심분야와 관련 있어요"
            )
        elif preference:
            activity["recommendation_reason"] = "선호 활동 내용과 유사해요"
        else:
            activity["recommendation_reason"] = "전공·학년 정보와 관련된 활동이에요"
    return activities


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

    matched = _match_activities(student, activity_rows)
    return student, _apply_personalization_scores(student, matched)


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

    matched = _match_activities(student, activity_rows)
    return student, _apply_personalization_scores(student, matched)


def _card_from_activity(activity):
    structured = load_json(activity.get("structured_data"), None) or {}
    combined = clean_text(
        f"{activity.get('target_raw') or ''} "
        f"{activity.get('body_text') or ''} {activity.get('ocr_text') or ''}"
    )
    legacy_deadline = extract_deadline_date(combined)
    direct_application_start = activity.get("application_start_date") or ""
    direct_application_end = activity.get("application_end_date") or ""
    has_separated_periods = "application_period_evidence" in structured
    application_evidence = clean_text(
        structured.get("application_period_evidence") or ""
    ).lower()
    trusted_application_period = bool(application_evidence) and any(
        keyword in application_evidence
        for keyword in APPLICATION_EVIDENCE_KEYWORDS
    )
    if has_separated_periods and trusted_application_period:
        structured_start = structured.get("application_start_date") or ""
        structured_deadline = structured.get("application_end_date") or ""
    elif has_separated_periods:
        structured_start = ""
        structured_deadline = ""
    else:
        structured_start = structured.get("start_date") or ""
        structured_deadline = structured.get("end_date") or ""

    # 구조화 날짜가 기존 수집 기준일과 다른 연도라면 모델이 연도를 추정한 것으로 보고 쓰지 않는다.
    reference_year = str(activity.get("reference_date") or "")[:4]
    if structured_start and reference_year and structured_start[:4] != reference_year:
        structured_start = ""
    if structured_deadline and reference_year and structured_deadline[:4] != reference_year:
        structured_deadline = ""

    # 새 날짜 스키마가 있으면 기존 정규식 결과로 보충하지 않는다.
    # 기존 정규식은 프로그램 진행기간을 모집기간으로 오인할 수 있기 때문이다.
    deadline_date = direct_application_end or (
        structured_deadline
        if has_separated_periods
        else structured_deadline or legacy_deadline
    )
    dday = compute_dday(deadline_date)
    first_seen = (activity.get("first_seen_at") or "")[:10]
    reference_date = (
        direct_application_start
        or structured_start
        or activity.get("reference_date")
        or ""
    )
    reference_age_days = None
    try:
        reference_age_days = (
            today_kst() - datetime.strptime(reference_date, "%Y-%m-%d").date()
        ).days
    except (TypeError, ValueError):
        pass
    stale_without_deadline = (
        not deadline_date
        and reference_age_days is not None
        and reference_age_days > 30
    )
    eligible_statuses = [
        value.strip()
        for value in (structured.get("eligible_statuses") or [])
        if value
        and value.strip() not in EMPTY_TARGET_TOKENS
        and value.strip() not in ENROLLMENT_TYPE_LABELS
    ]
    structured_target = ", ".join(eligible_statuses)
    eligibility_summary = clean_text(
        structured.get("eligibility_summary") or ""
    ).strip('“”"')
    if len(eligibility_summary) > 200:
        eligibility_summary = ""
    enrollment_target = ", ".join(
        dict.fromkeys(
            ENROLLMENT_TYPE_LABELS.get(value, "")
            for value in (structured.get("eligible_enrollment_types") or [])
            if ENROLLMENT_TYPE_LABELS.get(value, "")
        )
    )
    legacy_target = clean_text(activity.get("target_raw") or "")
    if legacy_target in EMPTY_TARGET_TOKENS:
        legacy_target = ""

    # 지역 뱃지는 실제 지원자격에 지역 제한이 확인된 광운대 공고에만 보여준다.
    is_internal = activity["campus_scope"] == "교내"
    is_scholarship = activity["activity_category"] == "장학·지원"
    parsed_structured_regions = structured_eligibility_regions(structured)
    structured_regions = list(
        dict.fromkeys(
            region["region_detail"]
            for region in parsed_structured_regions
            if region.get("region_detail")
        )
    )
    region_relevant = (
        activity["source"] != "링커리어"
        and (not is_internal or is_scholarship)
        and bool(structured_regions)
    )

    return {
        **activity,
        "target_raw": (
            eligibility_summary
            or structured_target
            or legacy_target
            or enrollment_target
        ),
        "target": load_json(activity.get("target"), []),
        "reference_date": reference_date,
        "date_basis": (
            "링커리어 접수 시작일"
            if direct_application_start
            else "GPT 구조화 시작일"
            if structured_start
            else activity.get("date_basis")
        ),
        "missing_before_ocr": load_json(activity.get("missing_before_ocr"), []),
        "region_detail": " / ".join(structured_regions) if region_relevant else "",
        "deadline_date": deadline_date,
        "dday": dday,
        "is_new": first_seen == today_kst().isoformat(),
        "region_relevant": region_relevant,
        "recommendation_score": activity.get("recommendation_score"),
        "recommendation_reason": activity.get("recommendation_reason") or "",
        "eligibility_uncertain": bool(activity.get("eligibility_uncertain")),
        "reference_age_days": reference_age_days,
        "stale_without_deadline": stale_without_deadline,
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
    cards.sort(
        key=lambda card: (
            not card["stale_without_deadline"],
            card["recommendation_score"] is not None,
            card["recommendation_score"] or 0,
            card["reference_date"],
        ),
        reverse=True,
    )
    # 마감일이 확인되고 이미 지난 공고는 개인화 화면에서 제외한다(DB 원본은 그대로 둔다).
    cards = [card for card in cards if not (card["dday"] is not None and card["dday"] < 0)]

    internal_cards = [card for card in cards if card["campus_scope"] == "교내"]
    external_cards = [card for card in cards if card["campus_scope"] == "교외"]

    internal_urgent, internal_rest = _split_urgent(internal_cards)
    external_urgent, external_rest = _split_urgent(external_cards)

    kw_external_cards = [card for card in external_rest if card["source"] == "광운대학교"]
    # 출처·카테고리 하위 탭에서 탐색하므로 조건을 통과한 링커리어 공고를 모두 제공한다.
    linkareer_cards = [card for card in external_rest if card["source"] == "링커리어"]

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
