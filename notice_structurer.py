import hashlib
import json
import os
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


class NoticeStructure(BaseModel):
    opportunity_type: OpportunityType
    recommendation_group: RecommendationGroup
    recommendable: bool
    student_eligible: bool = Field(
        description="대학생 또는 해당 학생 프로필이 지원 가능한 공고인지 여부"
    )
    summary: str = Field(description="학생이 이해하기 쉬운 한두 문장 요약")
    eligible_statuses: list[str]
    eligible_enrollment_types: list[EnrollmentType] = Field(
        description="지원 가능한 학생 신분. 명시되지 않으면 unknown"
    )
    grade_min: int | None
    grade_max: int | None
    eligible_majors: list[str]
    excluded_majors: list[str]
    major_restriction: Literal["none", "include_only", "exclude_only", "unknown"]
    regions: list[str]
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
- 확실하지 않은 값은 추측하지 말고 빈 배열, null, unknown을 사용한다.
- evidence는 원문에서 판단 근거가 되는 짧은 구절만 적는다.
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
