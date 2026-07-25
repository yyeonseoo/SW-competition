import re
from utils.text_processor import clean_text, compact_text

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

STAFF_HIRING_KEYWORDS = [
    "기간제", "계약직원", "계약직", "무기계약직", "공무직", "일용직",
    "교직원채용", "직원채용", "행정직원채용",
]

NOISE_KEYWORDS = [
    # 학사 행정
    "수강신청", "학사경고", "성적정정", "휴학", "복학", "등록금고지서", "졸업사정",
    "수업계획서", "강의평가", "시간표", "이수 체계도 안내",
    # 시설/서비스 안내 (청소/승강기는 board_category="시설" 통째 제외로 대체 — 아래 참고)
    "복구안내", "중단안내", "서비스복구", "정전", "점검안내", "주차안내", "도서관안내",
    "장소사용", "초빙 교수", "초빙교수", "초빙",
    # 기타 행정
    "상해보험", "단체교섭", "병무", "현역병모집", "승강기", "수상자 발표", "부고",
    "행복기숙사(빛솔재)", "사무실 이전", "사칭 물품", "셔틀버스", "장소 사용", "청소"
]

NOISE_BOARD_CATEGORIES = {"학사", "병무"}

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

_TITLE_NOISE_RE = re.compile(r"(신규게시글|Attachment|조회수\s*\d+)")


def strip_title_noise(title):
    """게시판 목록에서 제목과 함께 붙어오는 'NEW'/첨부파일/조회수 표시를 제거합니다."""
    return clean_text(_TITLE_NOISE_RE.sub("", title or ""))


def is_noise_notice(title, board_category="", body_text="", ocr_text="", activity_category=None):
    """
    수강신청 등 학사·행정 공지, 시설 안내처럼 비교과 활동 추천과 무관한 게시글인지 판별합니다.
    제목뿐 아니라 본문 및 OCR 텍스트까지 2차 검증하여 노이즈를 명확히 걸러냅니다.
    """
    if board_category in NOISE_BOARD_CATEGORIES:
        return True

    compact_title = compact_text(title)
    # 1. 제목에 노이즈 단어가 있으면 명백한 노이즈로 즉시 차단
    if any(keyword in compact_title for keyword in NOISE_KEYWORDS):
        return True

    # 2. 본문 + OCR 텍스트 결합 검증
    # 명확한 비교과 활동('공모전', '대외활동' 등)으로 분류되지 못한 상태('기타' 또는 미지정)에서
    # 본문이나 OCR 텍스트에 학사/행정 노이즈 키워드가 등장하는 경우 확실하게 필터링
    if body_text or ocr_text:
        combined_compact = compact_text(f"{body_text} {ocr_text}")
        if activity_category in (None, "", "기타"):
            if any(keyword in combined_compact for keyword in NOISE_KEYWORDS):
                return True

    return False


def classify_activity_category(text, forced_category=None):
    """forced_category는 링커리어 목록 종류처럼 사이트가 이미 보장하는 값입니다."""
    if forced_category in ACTIVITY_CATEGORIES:
        return forced_category, True

    lowered = clean_text(text).lower()
    for category in ("공모전", "인턴·채용", "대외활동", "교육", "장학·지원"):
        if any(keyword.lower() in lowered for keyword in CATEGORY_RULES[category]):
            return category, True
    return "기타", False


def is_staff_hiring_notice(text):
    """학교 자체 직원(기간제/계약직 등) 채용 공고인지 판별합니다. 학생 대상 인턴·채용 기회가 아니므로 수집 단계에서 제외합니다."""
    return any(keyword in compact_text(text) for keyword in STAFF_HIRING_KEYWORDS)


def classify_campus_scope(source, board_category=""):
    """
    광운대 공지의 [외부] 카테고리만 교외, 그 외 광운대 공지는 교내.
    링커리어 등 학교 밖 소스는 항상 교외.
    """
    if source == "광운대학교":
        return "교외" if board_category == "외부" else "교내"
    return "교외"


def classify_interest_categories(text):
    """공고 텍스트를 기반으로 20개 관심분야 중 일치하는 항목을 반환합니다."""
    title_body = clean_text(text)
    lowered = title_body.lower()
    scores = {}
    for category, keywords in FIELD_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in lowered)
        scores[category] = score

    found = [category for category, score in scores.items() if score > 0]
    return (found, True) if found else (["기타"], False)
