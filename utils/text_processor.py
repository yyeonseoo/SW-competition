import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

DATE_PATTERN = re.compile(r"(\d{4})[./年\s\-]+(\d{1,2})[./月\s\-]+(\d{1,2})일?")

DEADLINE_LABELS = [
    "마감일", "마감일자", "마감", "접수마감", "모집마감", "지원마감",
    "제출마감", "신청마감"
]

PERIOD_LABELS = [
    "접수기간", "모집기간", "지원기간", "신청기간", "활동기간",
    "접수일시", "모집일시", "신청일시"
]

TARGET_LABELS = [
    "모집대상", "참가대상", "참여대상", "지원대상", "지원자격",
    "모집자격", "신청자격", "대상", "자격 요건", "응모 자격", "응모대상"
]

NEXT_LABELS = [
    "모집 인원", "모집인원", "선발 인원", "선발인원", "모집 기간", "모집기간",
    " 접수 기간", "접수기간", "지원 기간", "지원기간", "활동 기간", "활동기간",
    "장학 혜택", "활동 혜택", "혜택", "접수 방법", "접수방법", "지원 방법",
    "지원방법", "신청 방법", "신청방법", "문의", "문의처", "주관",
    "주최", "일정", "장소", "시상 내역", "시상내역"
]


def today_kst() -> date:
    """서울 시간대(KST) 기준 오늘의 날짜를 반환합니다."""
    return datetime.now(KST).date()


def now_kst_string() -> str:
    """서울 시간대(KST) 기준 현재 시각을 ISO 포맷 문자열로 반환합니다."""
    return datetime.now(KST).isoformat()


def clean_text(text: str) -> str:
    """HTML 및 크롤링 텍스트에서 탭, 개행, 이종 공백 문자를 단일 스페이스로 정리합니다."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def compact_text(text: str) -> str:
    """단어 내 띄어쓰기를 전부 제거하여 노이즈 키워드 매칭이나 정확한 비교를 용이하게 합니다."""
    if not text:
        return ""
    return re.sub(r"\s+", "", clean_text(text))


def normalize_date(raw_date: str) -> str:
    """다양한 형태의 날짜 문자열(예: '2026. 07. 25', '2026-7-25일')을 'YYYY-MM-DD' 표준 포맷으로 변환합니다."""
    if not raw_date:
        return ""
    match = DATE_PATTERN.search(clean_text(raw_date))
    if not match:
        return ""
    year_str, month_str, day_str = match.groups()
    try:
        year = int(year_str)
        month = int(month_str)
        day = int(day_str)
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        pass
    return ""


def is_recent_upload(date_str: str, days_back: int = 3) -> bool:
    """
    해당 날짜가 오늘(KST)을 기준으로 최근 days_back 이내에 작성/게재된 공고인지 확인합니다.
    (예: days_back=14 인 경우 과거 14일까지 허용)
    """
    norm = normalize_date(date_str)
    if not norm:
        return False
    try:
        target_date = date.fromisoformat(norm)
        diff = (today_kst() - target_date).days
        return -1 <= diff <= days_back
    except ValueError:
        return False


def extract_deadline_date(text: str) -> str:
    """
    공고 본문 텍스트에서 마감일 또는 모집 기간의 종료 일자를 자동 추출합니다.
    1단계: '마감일' 관련 키워드 근접 문자열 탐색
    2단계: '모집기간/접수기간' 범위열에서 두 번째(종료) 날짜 추출
    """
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    # 1. 명시적 마감일 레이블 우선 탐색
    deadline_regex = r"(?:" + "|".join(re.escape(k) for k in DEADLINE_LABELS) + r")\s*[:：\-]?\s*([^.~!,;\n]{4,30})"
    match = re.search(deadline_regex, cleaned, flags=re.IGNORECASE)
    if match:
        result = normalize_date(match.group(1))
        if result:
            return result

    # 2. 기간 레이블 탐색 후 마지막 날짜를 마감일로 판단
    period_regex = r"(?:" + "|".join(re.escape(k) for k in PERIOD_LABELS) + r")\s*[:：\-]?\s*(.{8,80})"
    pmatch = re.search(period_regex, cleaned, flags=re.IGNORECASE)
    if pmatch:
        snippet = pmatch.group(1)
        dates_found = DATE_PATTERN.findall(snippet)
        if len(dates_found) >= 2:
            y, m, d = dates_found[-1]
            try:
                if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            except ValueError:
                pass
        elif len(dates_found) == 1:
            y, m, d = dates_found[0]
            try:
                if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            except ValueError:
                pass

    # 3. 레이블 없이 날짜가 2개 연결된 형태 (예: 2026.07.01 ~ 2026.07.25)
    range_matches = re.findall(r"(\d{4}[./\-]\d{1,2}[./\-]\d{1,2})\s*[~～\-–]\s*(\d{4}[./\-]\d{1,2}[./\-]\d{1,2})", cleaned)
    if range_matches:
        last_end = range_matches[0][1]
        norm_end = normalize_date(last_end)
        if norm_end:
            return norm_end

    return ""


def compute_dday(deadline_date: str):
    """
    마감일까지 남은 일자(D-Day)를 계산하여 정수로 반환합니다.
    마감 당일은 0, 마감 전은 양수(예: D-5는 5), 이미 지났으면 음수를 반환합니다.
    """
    if not deadline_date:
        return None
    try:
        dt = date.fromisoformat(deadline_date)
        diff = (dt - today_kst()).days
        return diff
    except ValueError:
        return None


def extract_target_text(text: str) -> str:
    """본문에서 '모집대상' 혹은 '참가자격' 관련 단락을 추출합니다."""
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    start_pattern = "|".join(re.escape(k) for k in TARGET_LABELS)
    end_pattern = "|".join(re.escape(k) for k in NEXT_LABELS)

    match = re.search(
        rf"(?:{start_pattern})\s*[:：\-]?\s*(.{{1,600}}?)(?=(?:{end_pattern})\s*[:：\-]?|$)",
        cleaned,
        flags=re.IGNORECASE
    )
    if match:
        return clean_text(match.group(1))
    return ""


def normalize_target(raw_target: str) -> str:
    """
    다양한 표현의 대상 텍스트를 규격화된 표현('대학생', '대상 제한 없음' 등)으로 매핑합니다.
    """
    text = clean_text(raw_target)
    compact = compact_text(text)
    if not compact:
        return ""

    if "청소년" in compact:
        return "청소년"

    if any(value in compact for value in ["대상제한없음", "제한없음", "누구나", "전국민"]):
        return "대상 제한 없음"

    if any(value in compact for value in ["대학생", "대학(원)생", "대학원생", "재학생", "휴학생", "광운학우", "학부생"]):
        return "대학생"

    if any(value in compact for value in ["직장인/일반인", "직장인", "일반인", "재직자"]):
        return "직장인/일반인"

    return text
