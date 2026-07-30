import hashlib
import json
import os
import re
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


OpportunityType = Literal[
    "contest",
    "student_activity",
    "student_education",
    "student_internship",
    "scholarship",
    "student_support",
    "academic_notice",
    "military_notice",
    "staff_recruitment",
    "administrative_notice",
    "unknown",
]
RecommendationGroup = Literal[
    "personalized",
    "eligibility_only",
    "essential_notice",
    "excluded",
]
EnrollmentType = Literal[
    "freshman",
    "enrolled",
    "leave_of_absence",
    "expected_graduate",
    "graduate",
    "graduate_student",
    "all_students",
    "unknown",
]
RegionRestriction = Literal["none", "include_only", "unknown"]


class NoticeStructure(BaseModel):
    opportunity_type: OpportunityType
    recommendation_group: RecommendationGroup
    recommendable: bool
    student_eligible: bool = Field(
        description="대학생 또는 해당 학생 프로필이 지원 가능한 공고인지 여부"
    )
    summary: str = Field(description="학생이 이해하기 쉬운 한두 문장 요약")
    eligibility_summary: str = Field(
        description=(
            "실제로 신청 가능한 사람의 자격조건만 한 문장으로 요약. "
            "제출서류, 신청방법, 증빙방법은 포함하지 않으며, "
            "자격조건이 명시되지 않았으면 빈 문자열"
        )
    )
    eligible_statuses: list[str]
    eligible_enrollment_types: list[EnrollmentType] = Field(
        description="지원 가능한 학생 신분. 명시되지 않으면 unknown"
    )
    grade_min: int | None
    grade_max: int | None
    eligible_majors: list[str]
    excluded_majors: list[str]
    major_restriction: Literal["none", "include_only", "exclude_only", "unknown"]
    region_restriction: RegionRestriction = Field(
        description=(
            "지원자의 거주지·주민등록지·소속 대학 소재지를 실제 자격조건으로 "
            "제한하면 include_only, 명시적 제한이 없으면 none, 판단 불가면 unknown"
        )
    )
    regions: list[str] = Field(
        description=(
            "region_restriction이 include_only일 때 지원 가능한 지역만 한국어로 작성. "
            "행사·교육 장소, 기관명, 제출처, 문의처, 주최·주관 주소는 제외"
        )
    )
    region_eligibility_evidence: str | None = Field(
        description="지원 지역 제한을 직접 명시한 원문 근거. 지역 제한이 없으면 null"
    )
    international_student_required: bool
    topics: list[str]
    required_skills: list[str]
    application_start_date: str | None = Field(
        description="모집·신청·접수 시작일 YYYY-MM-DD. 진행 시작일과 구별하며 불명확하면 null"
    )
    application_end_date: str | None = Field(
        description="모집·신청·접수 마감일 YYYY-MM-DD. 진행 종료일과 구별하며 불명확하면 null"
    )
    program_start_date: str | None = Field(
        description="교육·행사·활동 실제 진행 시작일 YYYY-MM-DD, 불명확하면 null"
    )
    program_end_date: str | None = Field(
        description="교육·행사·활동 실제 진행 종료일 YYYY-MM-DD, 불명확하면 null"
    )
    application_method: str | None
    eligibility_evidence: str | None
    application_period_evidence: str | None
    program_period_evidence: str | None
    confidence: float = Field(ge=0, le=1)


INSTRUCTIONS = """
너는 한국 대학생 대상 공고를 구조화하는 분류기다. 제공된 공고 안에 명시된 정보만 사용한다.

분류 규칙:
- 공모전, 대외활동, 학생 교육/인턴은 personalized: 자격 검사를 통과한 뒤 관심 분야와 의미 유사도로 추천한다.
- 장학금과 학생 지원 프로그램은 eligibility_only: 관심 분야와 무관하게 자격으로 추천한다.
- 수강/학사 일정 등 재학생 필수 정보는 essential_notice로 분류한다.
- 교직원·교수·조교 채용, 행정 안내, 군입대/병무 공고는 excluded이며 recommendable=false다.
- 국제학생만 지원 가능한 공고는 international_student_required=true다.
- 대학생이 지원할 수 없고 교원·청소년·기업·직원 등만 가능한 공고는 student_eligible=false다.
- 신입생, 재학생, 휴학생, 졸업예정자, 졸업생, 대학원생을 구분해 eligible_enrollment_types에 넣는다.
- "신입생만", "신·편입생만"이면 freshman만 넣고 enrolled나 all_students를 넣지 않는다.
- "재학생"은 enrolled, "휴학생"은 leave_of_absence, "졸업예정자"는 expected_graduate다.
- 주최 학과명과 지원 가능한 전공을 구별한다. 특정 전공만 가능하다는 문장이 없으면 eligible_majors에 넣지 않는다.
- application_start_date/application_end_date에는 모집·신청·접수 기간만 넣는다.
- program_start_date/program_end_date에는 교육·활동·행사·상담 등 실제 진행 기간만 넣는다.
- 접수기간이 없고 진행기간만 있으면 application 날짜는 반드시 null이다. 진행기간을 접수기간으로 복사하지 않는다.
- "모집 시 마감", "채용 시 마감", "상시 모집"처럼 날짜가 명시되지 않은 마감은 application_end_date=null이다.
- 시작일만 있고 마감일이 날짜로 명시되지 않았으면 시작일을 마감일에 복사하지 않는다.
- 링커리어 상단 정보의 접수기간과 활동기간이 함께 있으면 접수기간 블록만 application 날짜로 사용한다.
- 확실하지 않은 값은 추측하지 말고 빈 배열, null, unknown을 사용한다.
- evidence는 원문에서 판단 근거가 되는 짧은 구절만 적는다.
"""


INSTRUCTIONS += """

모집대상 표시 규칙:
- eligibility_summary에는 실제 신청 가능한 사람의 자격조건만 한 문장으로 작성한다.
- 제출서류, 신청방법, 증빙방법은 eligibility_summary에 포함하지 않는다.
- 소득, 재학 상태, 학년, 성적, 전공, 연령 등 명시된 자격조건은 빠뜨리지 않는다.
- 자격조건이 명시되지 않았으면 eligibility_summary는 빈 문자열로 둔다.

지원 지역 판정 규칙:
- 지원자의 거주지, 주민등록지 또는 소속 대학 소재지를 제한하는 문장이 있을 때만 region_restriction을 include_only로 둔다.
- 행사 장소, 교육 장소, 기관명, 제출처, 문의처, 주최·주관 기관 주소에 나온 지역명은 지원 지역이 아니다.
- "서울 사랑의열매", "서울특별시 주최", "장소: 서울" 같은 표현만으로 regions를 채우지 않는다.
- 명시적 지원 지역 제한이 없으면 region_restriction은 none, regions는 빈 배열, region_eligibility_evidence는 null이다.
"""


def activity_content(activity) -> str:
    fields = [
        str(activity["title"] or ""),
        str(activity["source_section"] or ""),
        str(activity["target_raw"] or ""),
        str(activity["body_text"] or ""),
        str(activity["ocr_text"] or ""),
    ]
    return "\n".join(fields)


def content_hash(activity) -> str:
    return hashlib.sha256(activity_content(activity).encode("utf-8")).hexdigest()


def build_input(activity, max_chars: int = 12000) -> str:
    body = str(activity["body_text"] or "")
    ocr = str(activity["ocr_text"] or "")
    text = (
        f"출처: {activity['source']}\n"
        f"게시판: {activity['source_section'] or ''}\n"
        f"제목: {activity['title']}\n"
        f"기존 대상 추출: {activity['target_raw'] or ''}\n"
        f"본문:\n{body}\n"
        f"OCR:\n{ocr}"
    )
    return text[:max_chars]


_DATE_VALUE_RE = re.compile(r"\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2}")
_APPLICATION_WORD_RE = re.compile(r"접수|신청|모집|지원|제출")


def _iso_date(value) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"null", "none", "unknown"}:
        return ""
    match = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", text)
    if not match:
        return ""
    try:
        return datetime(
            int(match.group(1)), int(match.group(2)), int(match.group(3))
        ).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _date_appears_in_evidence(date_value: str, evidence: str) -> bool:
    if not date_value or not evidence:
        return False
    compact_evidence = re.sub(r"\D", "", evidence)
    return date_value.replace("-", "") in compact_evidence


def resolve_application_dates(activity, structured: dict) -> tuple[str, str]:
    """명시적인 접수 근거가 있는 날짜만 DB 표시용 값으로 확정한다.

    링커리어 상단의 접수기간은 크롤러가 직접 읽은 값을 최우선으로 사용한다.
    이 블록이 '모집 시 마감'이면 GPT가 활동 종료일을 마감일로 추측했더라도
    마감일을 비워 둔다.
    """
    body = str(activity["body_text"] or "")
    existing_start = _iso_date(activity["application_start_date"])
    existing_end = _iso_date(activity["application_end_date"])

    if activity["source"] == "링커리어" and "접수기간" in body:
        segment = body.split("접수기간", 1)[1].split("활동기간", 1)[0]
        start_match = re.search(
            r"시작일\s*[:：\-]?\s*(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2})",
            segment,
        )
        end_match = re.search(
            r"마감일\s*[:：\-]?\s*(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2})",
            segment,
        )
        start = _iso_date(start_match.group(1)) if start_match else existing_start
        end = _iso_date(end_match.group(1)) if end_match else ""
        return start, end

    evidence = str(structured.get("application_period_evidence") or "")
    if not _APPLICATION_WORD_RE.search(evidence):
        return existing_start, existing_end

    model_start = _iso_date(structured.get("application_start_date"))
    model_end = _iso_date(structured.get("application_end_date"))
    start = existing_start or (
        model_start if _date_appears_in_evidence(model_start, evidence) else ""
    )
    end = existing_end or (
        model_end if _date_appears_in_evidence(model_end, evidence) else ""
    )
    if start and end and end < start:
        end = ""
    return start, end


def structure_activity(activity, client: OpenAI | None = None):
    load_dotenv()
    model = os.getenv("OPENAI_MODEL", "gpt-5.4-nano")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 없습니다.")

    client = client or OpenAI(api_key=api_key, max_retries=2, timeout=45)
    response = client.responses.parse(
        model=model,
        instructions=INSTRUCTIONS,
        input=build_input(activity),
        text_format=NoticeStructure,
        max_output_tokens=1200,
        store=False,
    )
    if response.output_parsed is None:
        raise RuntimeError("모델이 구조화 결과를 반환하지 않았습니다.")
    usage = response.usage
    return {
        "model": model,
        "data": response.output_parsed.model_dump(),
        "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        "structured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def dumps_structure(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
