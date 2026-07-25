# 광운대학교 학생 맞춤형 비교과 활동 추천 시스템

교내(광운대 공지) + 교외(링커리어) 비교과 활동(공모전/대외활동/인턴·채용/교육/장학) 정보를 하나로 모아,
학생 프로필(전공·학년·거주지역·관심분야) 기준으로 개인화 추천하는 시스템입니다.

- 기능 스펙(단일 기준 문서): [`JY_local/notice.md`](JY_local/notice.md)
- UI/UX 기준: [`JY_local/prototype_v2.html`](JY_local/prototype_v2.html) (색상·타이포·간격·카드·뱃지·모달 스타일의 원본)
- 작업 규칙·구현 현황·미해결 이슈: [`CLAUDE.md`](CLAUDE.md)

## 프로젝트 구조

```
link.py              링커리어 공고 수집 (Selenium)
kw_notice.py          광운대학교 공지사항 수집 (requests + BeautifulSoup)
common.py             공통 유틸: DB 스키마/저장, 활동카테고리·관심분야·교내외 구분 분류,
                       마감일 추출·D-day, 학생 생성, 날짜/대상 정규화
regions.py             제목·본문에서 시·도 → 구/시·군 2단계 지역 추출 (동명 지명 모호성 처리)
departments.py         web/data/departments.json(단일 소스)을 읽어 단과대학→학과 조회 함수 제공(college_of 등)
ocr_utils.py           NCP CLOVA OCR 연동 (본문에 모집대상·기간이 없을 때만 호출)
recommend.py           학생 프로필과 공고를 매칭해 추천 목록 생성 (CLI) + API가 쓰는 build_dashboard()
insert_student.py      학생 프로필 등록 dev 스크립트 (테스트용 단일 학생 하드코딩, 웹 앱은 미사용)
check_db.py            recommendation.db 저장 내용 확인용 스크립트
api.py                 FastAPI 서버 — web/ 프론트엔드가 쓰는 REST API
web/                   Next.js(React) 프론트엔드 — prototype_v2.html의 UI/인터랙션 재현
recommendation.db      SQLite DB (activities, students 테이블)
requirements.txt       Python 의존성 목록
.env.example           NCP OCR 자격 증명 템플릿 (.env로 복사해서 사용)
JY_local/               기획 문서(notice.md)·프로토타입 — 코드 대상 아님, git에도 올리지 않음
```

### 데이터 흐름

```
[광운대 공지] + [링커리어]
        │
        ▼
   수집 (link.py / kw_notice.py)
        │   └─ 이미지형 공지 → NCP OCR로 텍스트화 (모집대상·모집기간)
        ▼
   자동 분류 (common.py: 교내·교외 / 활동카테고리 / 관심분야 / regions.py: 지역)
        │
        ▼
   저장 (recommendation.db, URL 기준 중복 제거)
        │
        ▼
   학생 프로필(웹 온보딩 → api.py POST /api/students)
        │
        ▼
   개인화 매칭(recommend.py build_dashboard) → api.py GET /api/dashboard → web/ 화면
```

## 실행 방법

### 1. 백엔드 (수집 스크립트 + API)

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OCR 자격 증명 설정 (광운대 공지 수집 시 필요):
```
cp .env.example .env
# .env에 CLOVA_OCR_URL, CLOVA_OCR_SECRET 입력
```

공고 수집:
```
python link.py        # 링커리어 (대외활동/공모전/교육, 시작일 최근 3일 + 참여대상 필터)
python kw_notice.py    # 광운대학교 공지사항 (최근 3일 작성글)
```

API 서버 실행 (프론트엔드가 여길 바라봄):
```
uvicorn api:app --reload --port 8000
```

기타 CLI 유틸:
```
python insert_student.py   # dev 전용 테스트 학생 시드
python recommend.py        # CLI로 추천 결과 확인
python check_db.py         # DB 원본 확인
```

### 2. 프론트엔드 (`web/`)

```
cd web
npm install
npm run dev   # http://localhost:3000, NEXT_PUBLIC_API_BASE=http://localhost:8000 (web/.env.local)
```

백엔드(`uvicorn api:app --port 8000`)가 먼저 떠 있어야 온보딩/대시보드가 데이터를 받아옵니다.
로그인 없이, 온보딩에서 만든 학생 `id`를 브라우저 `localStorage`(`kwlife_student_id`)에 저장해
"현재 학생"을 식별합니다.

## 데이터베이스

SQLite (`recommendation.db`), 테이블 2개:

- `activities`: 수집된 공고. `source`(광운대학교/링커리어), `campus_scope`(교내/교외),
  `activity_category`(대외활동/공모전/인턴·채용/교육/장학·지원/기타), `interest_categories`(20개 태그 중 매칭분),
  지역(2단계), 모집대상, 기준일, 본문/OCR 텍스트, 검토 필요 여부 등을 저장.
- `students`: 학생 프로필. 학과, 학년, 관심분야, 거주지역, 이메일, 알림 수신 여부.
  `name`은 온보딩 화면에 입력 필드가 없어 `common.create_student()`가 내부용 placeholder
  (`guest-xxxxxxxx`)를 생성한다 — 화면에는 노출되지 않는다.

마감일(`deadline_date`)·D-day·NEW 여부는 스키마에 저장하지 않고 `recommend.build_dashboard()`가
매 요청마다 `body_text`/`target_raw`에서 계산한다(아래 참고).

## 개인화 매칭 규칙 (`recommend.py`)

| 대상 | 학과/분야 조건 | 지역 조건 | 학년 조건 |
| --- | --- | --- | --- |
| 교내 일반(대외활동/공모전/교육/기타) | 학과 일치 + 관심분야 겹침 필요 | **지역 무관** | 본문 기준 |
| 교내 장학·지원 | **무시(전공 불문)** | 지역 규칙 적용 | 본문 기준 |
| 교외(전 카테고리) | 학과 일치 + 관심분야 겹침 필요(장학·지원은 무시) | 지역 규칙 적용 | 본문 기준(인턴·채용은 + 2학년 이상) |

지역 규칙 게이트는 `recommend.should_apply_region_filter(activity)` 한 곳에서 판정한다 —
교내 일반 활동만 지역 무관, 그 외(교내 장학·지원, 교외 전체)는 기존 `region_matches()`를 적용.

`region_matches`(정밀 지역 매칭)는 지금은 단순 로직이며 개선 여지가 남아 있다.

학과 데이터의 단일 소스는 `web/data/departments.json`(실제 광운대 8개 단과대학·35개 학과)이다.
프론트엔드는 `web/data/departments.ts`가 이 JSON을 직접 import해서 쓰고, 백엔드는 `departments.py`가
같은 JSON 파일을 읽어(`web/data/departments.json`, 상대경로 아님 — `Path(__file__)` 기준이라 실행
위치와 무관) 동일한 조회 함수(`COLLEGES`/`all_departments`/`college_of`)를 제공한다. 학과 목록을
바꿀 땐 그 JSON 하나만 고치면 양쪽에 반영된다. `recommend.py::department_matches`는
공고 `target_raw`에 이 실제 학과/단과대학 이름이 문자 그대로 등장할 때만 지원자격 제한으로 인정하고,
학과명이 아니라 단과대학명만 언급된 경우 `departments.college_of(department)`로 학생의 소속 단과대학을
구해 비교한다(실제로 존재하지 않는 "~학과" 문구에 낚이지 않도록). 온보딩/프로필 편집 화면의 단과대학→학과
선택도 이 목록으로 실제 cascading된다. 다만 학생 프로필에는 여전히 `department`(학과)만 저장하고
단과대학 자체는 저장하지 않는다.

## 마감일 / 곧 마감 / 조기마감 처리

- `common.extract_deadline_date()`가 `DEADLINE_LABELS`(마감일 등) → 실패 시 `PERIOD_LABELS`(접수기간 등)
  구간의 마지막 날짜(종료일)를 최선 노력으로 추출한다. 실패하면 카드에 "모집기간 확인 필요"로 표시하되
  제외하지는 않는다. 스키마에 저장하지 않고 매 요청 시 계산한다(재수집 없이 정규식만 개선하면 되도록).
- 마감일이 확인되고 이미 지났으면 대시보드 응답에서 제외한다(DB 원본은 유지).
- 🔥 곧 마감 섹션: D-day가 0~3인 카드만.
- **조기마감 뱃지(`.badge.early`, `.card.dimmed`)는 실제 데이터에 연결하지 않았다** — notice.md의
  "한계점" 항목에 이미 미구현으로 명시돼 있어 CSS만 이식해두고 가짜 데이터로 채우지 않았다.

## API (`api.py`)

| Method/Path | 설명 |
| --- | --- |
| `GET /api/meta` | 관심분야 20종, 활동카테고리 6종, 지역 목록 — 온보딩/모달의 단일 출처 |
| `POST /api/students` | 프로필 생성 |
| `GET /api/students/{id}` | 프로필 조회 |
| `PATCH /api/students/{id}` | 프로필 수정 |
| `GET /api/dashboard?student_id=` | 교내/교외, 곧 마감, 카드 목록 등 대시보드 전체 데이터 |

## 최근 변경 사항

- 2026-07-25: FastAPI 백엔드(`api.py`)와 Next.js 프론트엔드(`web/`) 신설 — `prototype_v2.html`의
  3단계 온보딩·탭 전환·프로필 편집 모달 인터랙션과 스타일을 재현.
- 2026-07-25: 새 지역 매칭 규칙 반영 — 교내 일반은 지역 무관, 교내 장학·지원과 교외 전체는 지역 매칭.
- 2026-07-25: `common.py`에 마감일 추출(`extract_deadline_date`)·D-day 계산(`compute_dday`)·
  학생 생성(`create_student`) 추가. `students` 테이블에 `email`/`notify_opt_in` 컬럼 추가(안전 마이그레이션).
- 2026-07-25: 활동카테고리에 `인턴·채용`, `장학·지원` 추가, 광운대 공지 "등록/장학" 게시판을
  `장학·지원`으로 강제 매핑.
- 2026-07-25: `activities` 테이블에 `campus_scope`(교내/교외) 컬럼 추가(+기존 22건 백필).
- 2026-07-25: `requirements.txt`에 `selenium`, `pandas`, `fastapi`, `uvicorn` 추가. `README.txt` → `README.md`.
- 2026-07-25: 링커리어 크롤링은 Selenium 유지로 확정(전환 안 함).
- 2026-07-25: `departments.py`(백엔드) 추가, `recommend.py::department_matches`가 광운대 실제
  학과/단과대학 이름만 신뢰하도록 강화(느슨한 정규식 기반 substring 매칭 제거).
- 2026-07-25: `departments.py`가 자체 하드코딩 대신 `web/data/departments.json`을 읽도록 변경 —
  학과 데이터 단일 소스화(프론트·백엔드 모두 같은 JSON을 봄).
- 2026-07-25: `web/data/departments.json`(실제 광운대 단과대학·학과 목록)으로 온보딩/프로필 편집의
  단과대학→학과 선택을 실제 cascading으로 교체.

## 미구현 (계획 단계)

- 이메일 알림 서비스(smtplib) — 온보딩/프로필에서 이메일·수신 동의는 저장하지만 실제 발송 로직은 없음
- 수집 스케줄러 (cron/GitHub Actions, 1일 1회)
- 실제 전공(단과대학→학과) 매핑, 정밀 지역 매칭 — 현재는 단순 placeholder(추후 하드코딩 예정)

미해결 스펙 충돌·확인 필요 항목은 [`CLAUDE.md`](CLAUDE.md)를 참고하세요.
