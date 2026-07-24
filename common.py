import json
import re
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DB_NAME = "recommendation.db"
KST = ZoneInfo("Asia/Seoul")

ACTIVITY_CATEGORIES = ["대외활동", "공모전", "교육", "기타"]

INTEREST_CATEGORIES = [
    "여행/호텔/항공",
    "언론/미디어",
    "문화/역사",
    "행사/페스티벌",
    "교육",
    "디자인/사진/예술/영상",
    "경제/금융",
    "경영/컨설팅/마케팅",
    "정치/사회/법률",
    "체육/헬스",
    "의료/보건",
    "뷰티/미용/화장품",
    "과학/공학/기술/IT",
    "요리/식품",
    "창업/자기계발",
    "환경/에너지",
    "콘텐츠",
    "사회공헌/교류",
    "유통/물류",
    "기타",
]

FIELD_KEYWORDS = {
    "여행/호텔/항공": ["여행", "관광", "호텔", "항공", "공항", "해외탐방"],
    "언론/미디어": ["언론", "미디어", "기자", "방송", "신문", "뉴스"],
    "문화/역사": ["문화", "역사", "박물관", "문화유산", "전통", "인문"],
    "행사/페스티벌": ["행사", "축제", "페스티벌", "박람회", "전시회", "포럼", "콘퍼런스"],
    "교육": ["교육", "강의", "특강", "워크숍", "세미나", "아카데미", "부트캠프", "캠프", "실습", "연수", "강좌"],
    "디자인/사진/예술/영상": ["디자인", "사진", "영상", "예술", "미술", "포스터", "웹툰", "일러스트", "영화"],
    "경제/금융": ["경제", "금융", "투자", "은행", "증권", "회계", "재무", "부동산"],
    "경영/컨설팅/마케팅": ["경영", "마케팅", "광고", "홍보", "브랜딩", "기획", "컨설팅"],
    "정치/사회/법률": ["정치", "사회", "법률", "법학", "행정", "정책", "지방자치"],
    "체육/헬스": ["체육", "스포츠", "운동", "헬스", "축구", "농구"],
    "의료/보건": ["의료", "보건", "건강", "병원", "간호", "의약", "바이오"],
    "뷰티/미용/화장품": ["뷰티", "미용", "화장품", "메이크업", "패션"],
    "과학/공학/기술/IT": ["과학", "공학", "기술", "IT", "소프트웨어", "SW", "인공지능", "AI", "데이터", "코딩", "파이썬", "로봇", "반도체", "해커톤", "캡스톤", "빅데이터", "개발"],
    "요리/식품": ["요리", "식품", "음식", "레시피", "외식"],
    "창업/자기계발": ["창업", "스타트업", "자기계발", "진로", "취업역량", "취업"],
    "환경/에너지": ["환경", "에너지", "탄소", "기후", "친환경", "ESG", "넷제로"],
    "콘텐츠": ["콘텐츠", "SNS", "유튜브", "숏폼", "카드뉴스", "블로그", "크리에이터"],
    "사회공헌/교류": ["봉사", "사회공헌", "교류", "멘토링", "국제교류", "서포터즈", "봉사단"],
    "유통/물류": ["유통", "물류", "배송", "무역", "수출입"],
}

TARGET_LABELS = [
    "참여대상", "참가대상", "모집대상", "신청대상", "지원대상",
    "응모대상", "참가자격", "지원자격", "응모자격", "모집자격", "신청자격",
    "지원 조건", "지원조건",
]

NEXT_LABELS = [
    "접수기간", "신청기간", "모집기간", "지원기간", "활동기간",
    "교육기간", "행사기간", "신청방법", "지원방법", "접수방법",
    "제출방법", "활동내용", "교육내용", "활동혜택", "시상내역",
    "문의사항", "문의처", "문의", "장소", "일정", "모집인원",
]

CATEGORY_RULES = {
    "공모전": [
        "공모전", "경진대회", "해커톤", "아이디어대회", "아이디어 대회",
        "작품 공모", "수기 공모", "영상 공모", "챌린지",
    ],
    "대외활동": [
        "대외활동", "서포터즈", "기자단", "홍보대사", "봉사단",
        "멘토단", "체험단", "모니터링단", "기획단", "청년단", "앰버서더",
    ],
    "교육": [
        "교육", "특강", "강연", "워크숍", "세미나", "아카데미",
        "부트캠프", "캠프", "실습", "연수", "강좌", "교육생",
    ],
}


def clean_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def compact_text(text):
    return re.sub(r"\s+", "", clean_text(text))


def today_kst():
    return datetime.now(KST).date()


def now_kst_string():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def normalize_date(text):
    match = re.search(
        r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})",
        text or "",
    )
    if not match:
        return ""
    year, month, day = map(int, match.groups())
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def is_recent_upload(uploaded_date, days_back=3):
    value = normalize_date(uploaded_date)
    if not value:
        return False
    date_value = datetime.strptime(value, "%Y-%m-%d").date()
    return today_kst() - timedelta(days=days_back) <= date_value <= today_kst()


def classify_activity_category(text, forced_category=None):
    """forced_category는 링커리어 목록 종류처럼 사이트가 이미 보장하는 값."""
    if forced_category in ACTIVITY_CATEGORIES:
        return forced_category, True

    lowered = clean_text(text).lower()
    for category in ("공모전", "대외활동", "교육"):
        if any(keyword.lower() in lowered for keyword in CATEGORY_RULES[category]):
            return category, True
    return "기타", False


def classify_interest_categories(text):
    title_body = clean_text(text)
    lowered = title_body.lower()
    scores = {}
    for category, keywords in FIELD_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in lowered)
        scores[category] = score

    found = [category for category, score in scores.items() if score > 0]
    return (found, True) if found else (["기타"], False)


def extract_target_text(text):
    text = clean_text(text)
    if not text:
        return ""

    target_pattern = "|".join(re.escape(value) for value in TARGET_LABELS)
    next_pattern = "|".join(re.escape(value) for value in NEXT_LABELS)
    pattern = (
        rf"(?:{target_pattern})\s*[:：\-]?\s*"
        rf"(.{{1,500}}?)"
        rf"(?=(?:{next_pattern})\s*[:：\-]?|$)"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return clean_text(match.group(1)) if match else ""


def normalize_target(target_raw):
    raw = clean_text(target_raw)
    if not raw:
        return ["확인 필요"]

    compact = compact_text(raw)
    result = []
    if any(value in compact for value in ["누구나", "전국민", "제한없음", "자격제한없음"]):
        return ["전체"]
    if any(value in compact for value in ["광운대생", "대학생", "학부생", "재학생", "대학(원)생"]):
        result.append("대학생")
    if "대학원생" in compact:
        result.append("대학원생")
    if "휴학생" in compact:
        result.append("휴학생")
    if "청년" in compact:
        result.append("청년")
    if any(value in compact for value in ["교원", "교사", "교직원"]):
        result.append("교원/교사")
    if any(value in compact for value in ["직장인", "재직자"]):
        result.append("직장인")
    return list(dict.fromkeys(result)) or [raw[:200]]


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_section TEXT,
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
        conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 4),
            interest_categories TEXT NOT NULL,
            region_sido TEXT NOT NULL,
            region_sigungu TEXT
        )
        """)


def save_activity(item):
    now = now_kst_string()
    with sqlite3.connect(DB_NAME) as conn:
        existing = conn.execute(
            "SELECT id FROM activities WHERE url = ?", (item["url"],)
        ).fetchone()

        serialized = {
            **item,
            "interest_categories": json.dumps(item["interest_categories"], ensure_ascii=False),
            "target": json.dumps(item["target"], ensure_ascii=False),
            "missing_before_ocr": json.dumps(item.get("missing_before_ocr", []), ensure_ascii=False),
        }

        if existing is None:
            conn.execute("""
            INSERT INTO activities (
                source, source_section, title, url, activity_category,
                interest_categories, region_sido, region_sigungu, region_detail,
                region_status, target, target_raw, reference_date, date_basis, body_text,
                ocr_text, ocr_used, missing_before_ocr, review_required,
                first_seen_at, last_seen_at
            ) VALUES (
                :source, :source_section, :title, :url, :activity_category,
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
