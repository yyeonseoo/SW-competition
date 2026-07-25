import json
import re
import sqlite3
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DB_NAME = "recommendation.db"
KST = ZoneInfo("Asia/Seoul")

ACTIVITY_CATEGORIES = ["대외활동", "공모전", "인턴·채용", "교육", "장학·지원", "기타"]

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

DATE_PATTERN = r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})"

DEADLINE_LABELS = ["마감일", "마감기한", "접수마감", "신청마감", "모집마감", "제출마감"]
PERIOD_LABELS = ["접수기간", "신청기간", "모집기간", "지원기간", "공고기간", "활동기간"]

STAFF_HIRING_KEYWORDS = [
    "기간제", "계약직원", "계약직", "무기계약직", "공무직", "일용직",
    "교직원채용", "직원채용", "행정직원채용",
]

# 수강신청/성적/휴복학 같은 학사·행정 공지, 시설·서비스 안내, 학교 자체 인사 공고 등
# '기회성 프로그램'이 아닌 게시글을 걸러내기 위한 목록. 제목 키워드 기반이라 오분류 가능성은
# notice.md의 다른 키워드 사전들과 동일한 한계를 가진다(사전 튜닝 필요).
NOISE_KEYWORDS = [
    # 학사 행정
    "수강신청", "학사경고", "성적정정", "휴학", "복학", "등록금고지서", "졸업사정",
    "수업계획서", "강의평가", "시간표", "이수 체계도 안내",
    # 시설/서비스 안내 (청소/승강기는 board_category="시설" 통째 제외로 대체 — 아래 참고)
    "복구안내", "중단안내", "서비스복구", "정전", "점검안내", "주차안내", "도서관안내",
    "장소사용", "초빙"
    # 기타 행정
    "상해보험", "단체교섭", "병무", "현역병모집",
    "수상자 발표", "부고", "행복기숙사(빛솔재)", "사무실 이전", "사칭 물품", "셔틀버스", "장소 사용"
]

# 이 게시판 카테고리는 사실상 전부 학사·시설 행정 공지라 통째로 제외한다.
# "시설"(승강기 운행정지/외벽 청소/공사 안내 등)은 실제 수집 데이터로 전부 확인함 —
NOISE_BOARD_CATEGORIES = {"학사", "병무", "시설"}

_TITLE_NOISE_RE = re.compile(r"(신규게시글|Attachment|조회수\s*\d+)")


def strip_title_noise(title):
    """게시판 목록에서 제목과 함께 붙어오는 'NEW'/첨부파일/조회수 표시를 제거한다."""
    return clean_text(_TITLE_NOISE_RE.sub("", title or ""))


def is_noise_notice(text, board_category=""):
    """수강신청 등 학사·행정 공지, 시설 안내처럼 비교과 활동 추천과 무관한 게시글인지 판별한다.
    제목만이 아니라 본문·OCR 텍스트까지 합친 문자열도 넘길 수 있다.

    단순 substring 매칭이다 — compact_text로 공백을 지운 뒤에는 한글 단어 경계를 규칙적으로
    판정할 방법이 없어서(모든 글자가 한글로 붙어버림), 대신 키워드 자체를 다른 단어와 안 겹치게
    구체적으로 고른다(예: "청소"는 "청소년"과 겹쳐서 빼고 board_category="시설" 제외로 대체함)."""
    if board_category in NOISE_BOARD_CATEGORIES:
        return True
    compact = compact_text(text)
    return any(keyword in compact for keyword in NOISE_KEYWORDS)

CATEGORY_RULES = {
    "공모전": [
        "공모전", "경진대회", "해커톤", "아이디어대회", "아이디어 대회",
        "작품 공모", "수기 공모", "영상 공모", "챌린지",
    ],
    "대외활동": [
        "대외활동", "서포터즈", "기자단", "홍보대사", "봉사단",
        "멘토단", "체험단", "모니터링단", "기획단", "청년단", "앰버서더",
    ],
    "인턴·채용": [
        "인턴", "인턴십", "채용", "공채", "수시채용", "현장실습",
        "채용연계형", "체험형인턴", "청년인턴", "인턴사원",
    ],
    "교육": [
        "교육", "특강", "강연", "워크숍", "세미나", "아카데미",
        "부트캠프", "캠프", "실습", "연수", "강좌", "교육생",
    ],
    "장학·지원": [
        "장학", "장학금", "장학생", "학자금", "지원금", "생활비 지원",
        "등록금 지원", "근로장학",
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
    match = re.search(DATE_PATTERN, text or "")
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


def extract_deadline_date(text):
    """본문/모집대상 텍스트에서 마감일(종료일)을 최선 노력으로 추출한다.
    라벨을 못 찾거나 날짜 형식이 불명확하면 빈 문자열을 반환한다(추출 실패는 정상 케이스)."""
    text = clean_text(text)
    if not text:
        return ""

    for label in DEADLINE_LABELS:
        pos = text.find(label)
        if pos == -1:
            continue
        value = normalize_date(text[pos:pos + 60])
        if value:
            return value

    stop_labels = NEXT_LABELS + DEADLINE_LABELS
    for label in PERIOD_LABELS:
        pos = text.find(label)
        if pos == -1:
            continue
        end = len(text)
        for stop in stop_labels:
            stop_pos = text.find(stop, pos + len(label))
            if stop_pos != -1:
                end = min(end, stop_pos)

        dates = re.findall(DATE_PATTERN, text[pos:end])
        if dates:
            year, month, day = map(int, dates[-1])
            try:
                return datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                continue

    return ""


def compute_dday(date_str):
    """date_str("YYYY-MM-DD")이 오늘 기준 며칠 남았는지 반환한다. 파싱 불가하면 None."""
    if not date_str:
        return None
    try:
        date_value = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (date_value - today_kst()).days


def classify_activity_category(text, forced_category=None):
    """forced_category는 링커리어 목록 종류처럼 사이트가 이미 보장하는 값."""
    if forced_category in ACTIVITY_CATEGORIES:
        return forced_category, True

    lowered = clean_text(text).lower()
    for category in ("공모전", "인턴·채용", "대외활동", "교육", "장학·지원"):
        if any(keyword.lower() in lowered for keyword in CATEGORY_RULES[category]):
            return category, True
    return "기타", False


def is_staff_hiring_notice(text):
    """학교 자체 직원(기간제/계약직 등) 채용 공고인지 판별한다. 학생 대상 인턴·채용 기회가 아니므로
    수집 단계에서 걸러낸다 — 예: '[일반] 기간제 계약직원 채용 공고(공과대학 교학팀)'."""
    compact = compact_text(text)
    return any(keyword in compact for keyword in STAFF_HIRING_KEYWORDS)


def classify_campus_scope(source, board_category=""):
    """광운대 공지의 [외부] 카테고리만 교외, 그 외 광운대 공지는 교내.
    링커리어 등 학교 밖 소스는 항상 교외."""
    if source == "광운대학교":
        return "교외" if board_category == "외부" else "교내"
    return "교외"


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
            campus_scope TEXT,
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

        # campus_scope는 기존 DB에 없을 수 있으므로 안전하게 추가한다.
        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(activities)")
        }
        if "campus_scope" not in existing_columns:
            conn.execute("ALTER TABLE activities ADD COLUMN campus_scope TEXT")

        # ALTER TABLE은 기존 행을 채워주지 않으므로, 비어있는 campus_scope를 계산해 백필한다.
        null_scope_rows = conn.execute(
            "SELECT id, source, source_section FROM activities WHERE campus_scope IS NULL"
        ).fetchall()
        for row_id, source, source_section in null_scope_rows:
            conn.execute(
                "UPDATE activities SET campus_scope = ? WHERE id = ?",
                (classify_campus_scope(source, source_section or ""), row_id),
            )

        conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 4),
            interest_categories TEXT NOT NULL,
            region_sido TEXT NOT NULL,
            region_sigungu TEXT,
            email TEXT,
            notify_opt_in INTEGER DEFAULT 1,
            is_international INTEGER DEFAULT 0
        )
        """)

        # email/notify_opt_in/is_international은 기존 DB에 없을 수 있으므로 안전하게 추가한다.
        student_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(students)")
        }
        if "email" not in student_columns:
            conn.execute("ALTER TABLE students ADD COLUMN email TEXT")
        if "notify_opt_in" not in student_columns:
            conn.execute(
                "ALTER TABLE students ADD COLUMN notify_opt_in INTEGER DEFAULT 1"
            )
        if "is_international" not in student_columns:
            conn.execute(
                "ALTER TABLE students ADD COLUMN is_international INTEGER DEFAULT 0"
            )


def create_student(
    department,
    grade,
    interest_categories,
    region_sido,
    region_sigungu="",
    email=None,
    notify_opt_in=1,
    is_international=0,
    name=None,
):
    """프로필 온보딩에서 학생을 새로 등록한다. 프로토타입 온보딩 화면에는 이름 입력이
    없으므로, name을 안 주면 화면에 노출되지 않는 내부용 placeholder를 생성한다."""
    name = name or f"guest-{uuid.uuid4().hex[:8]}"
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.execute(
            """
            INSERT INTO students (
                name, department, grade, interest_categories,
                region_sido, region_sigungu, email, notify_opt_in, is_international
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                department,
                grade,
                json.dumps(interest_categories, ensure_ascii=False),
                region_sido,
                region_sigungu,
                email,
                notify_opt_in,
                is_international,
            ),
        )
        return cursor.lastrowid


def save_activity(item):
    now = now_kst_string()
    with sqlite3.connect(DB_NAME) as conn:
        existing = conn.execute(
            "SELECT id FROM activities WHERE url = ?", (item["url"],)
        ).fetchone()

        serialized = {
            **item,
            "campus_scope": classify_campus_scope(
                item["source"], item.get("source_section", "")
            ),
            "interest_categories": json.dumps(item["interest_categories"], ensure_ascii=False),
            "target": json.dumps(item["target"], ensure_ascii=False),
            "missing_before_ocr": json.dumps(item.get("missing_before_ocr", []), ensure_ascii=False),
        }

        if existing is None:
            conn.execute("""
            INSERT INTO activities (
                source, source_section, campus_scope, title, url, activity_category,
                interest_categories, region_sido, region_sigungu, region_detail,
                region_status, target, target_raw, reference_date, date_basis, body_text,
                ocr_text, ocr_used, missing_before_ocr, review_required,
                first_seen_at, last_seen_at
            ) VALUES (
                :source, :source_section, :campus_scope, :title, :url, :activity_category,
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
            campus_scope=:campus_scope,
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
