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
notice_structurer.py   OpenAI Structured Outputs로 공고 유형·자격·기간을 JSON 구조화
analyze_notices.py     새 공고만 구조화하는 비용 제한 CLI (본문 해시 캐시)
build_embeddings.py    개인화 대상 공고의 문장 임베딩 생성·캐시
embedding_utils.py     학생/공고 추천 문장 생성, 임베딩 호출, 코사인 유사도
recommend.py           학생 프로필과 공고를 매칭해 추천 목록 생성 (CLI) + API가 쓰는 build_dashboard()
insert_student.py      학생 프로필 등록 dev 스크립트 (테스트용 단일 학생 하드코딩, 웹 앱은 미사용)
check_db.py            recommendation.db 저장 내용 확인용 스크립트
api.py                 FastAPI 서버 — web/ 프론트엔드가 쓰는 REST API
web/                   Next.js(React) 프론트엔드 — prototype_v2.html의 UI/인터랙션 재현
recommendation.db      SQLite DB (실행 시 자동 생성, Git에는 포함하지 않음)
requirements.txt       Python 의존성 목록
.env.example           OCR/OpenAI 환경변수 템플릿 (.env로 복사해서 사용)
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

이미 가상환경과 패키지 설치가 끝난 Windows 개발 환경에서는 프로젝트 루트에서 다음 명령으로
백엔드를 실행한다.

```powershell
cd C:\Users\USER\sw
.\.venv\Scripts\python.exe -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

정상적으로 실행되면 터미널에 `Uvicorn running on http://127.0.0.1:8000`이 표시된다.
해당 터미널을 닫지 않은 상태에서 웹을 실행하며, API 문서는
`http://127.0.0.1:8000/docs`에서 확인할 수 있다. 서버 종료는 터미널에서 `Ctrl+C`를 누른다.

처음 환경을 구성하는 경우에는 아래 순서로 가상환경과 의존성을 설치한다.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell에서는 가상환경 활성화 명령만 다음과 같이 사용한다.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

OCR/OpenAI 자격 증명 설정:

```bash
cp .env.example .env
# .env에 CLOVA_OCR_URL, CLOVA_OCR_SECRET, OPENAI_API_KEY 입력
# OPENAI_MODEL=gpt-5.4-nano
```

`.env`는 Git에서 제외된다. 실제 키를 `.env.example`이나 소스 코드에 입력하지 않는다. OCR을 사용하지
않으면 CLOVA 항목은 비워둘 수 있고, 공고 구조화·임베딩을 실행하지 않으면 OpenAI 키도 비워둘 수 있다.

공고 수집:
```
python link.py         # 링커리어 (카테고리별 최대 15개, 모집 중 우선)
python kw_notice.py    # 광운대학교 공지사항 (최근 7일, 최대 10페이지)
python analyze_notices.py --dry-run       # 과금 없이 다음 구조화 대상 확인
python analyze_notices.py                 # 새/변경 공고만 최대 20개 구조화
python analyze_notices.py --limit 5       # 이번 실행 호출 상한을 5개로 축소
python build_embeddings.py                # 새/변경된 개인화 공고 임베딩 생성
```

`analyze_notices.py`는 공고 내용의 SHA-256 해시와 구조화 결과를 DB에 저장한다. 같은 내용은 다시
호출하지 않으며 실패한 공고만 다음 실행에서 재시도한다. `--force`는 캐시를 무시해 비용이 다시
발생하므로 결과 형식을 바꿔 재분석할 때만 사용한다. API 키가 없는 팀원은 수집·추천·웹 실행만 하고,
키 담당자 한 명만 구조화 명령을 실행하는 방식을 권장한다.

`build_embeddings.py`는 `text-embedding-3-small`을 사용하며 공고 제목·GPT 요약·주제·필요 역량을
합친 추천 문장의 해시를 캐시한다. 같은 공고는 다시 호출하지 않는다. 학생 임베딩은 전공·학년·관심분야·
선호 활동 문장으로 만들며 프로필이 바뀐 경우에만 대시보드 최초 요청에서 갱신한다.

API 서버 실행 (macOS/Linux 또는 가상환경이 이미 활성화된 터미널):

```bash
uvicorn api:app --reload --host 127.0.0.1 --port 8000
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
cp .env.local.example .env.local
npm run dev   # http://localhost:3000
```

백엔드(`uvicorn api:app --port 8000`)가 먼저 떠 있어야 온보딩/대시보드가 데이터를 받아옵니다.
로그인 없이, 온보딩에서 만든 학생 `id`를 브라우저 `localStorage`(`kwlife_student_id`)에 저장해
"현재 학생"을 식별합니다.

## 데이터베이스

SQLite (`recommendation.db`), 테이블 2개:

`recommendation.db`는 로컬 수집 데이터와 학생 프로필을 포함하므로 Git에 커밋하지 않는다. 저장소를
처음 받은 환경에서는 API 또는 수집 스크립트를 실행할 때 빈 DB와 테이블이 자동 생성된다. 공고 데이터가
필요하면 `link.py`, `kw_notice.py`, `analyze_notices.py`, `build_embeddings.py` 순서로 준비한다.

- `activities`: 수집된 공고. `source`(광운대학교/링커리어), `campus_scope`(교내/교외),
  `activity_category`(대외활동/공모전/인턴·채용/교육/장학·지원/기타), `interest_categories`(20개 태그 중 매칭분),
  지역(2단계), 모집대상, 기준일, 본문/OCR 텍스트, 검토 필요 여부 등을 저장.
- `students`: 학생 프로필. 학과, 학년, 관심분야, 거주지역, 이메일, 알림 수신 여부, `is_international`
  (국제학생 여부, 기본 0). `name`은 온보딩 화면에 입력 필드가 없어 `common.create_student()`가
  내부용 placeholder(`guest-xxxxxxxx`)를 생성한다 — 화면에는 노출되지 않는다.

마감일(`deadline_date`)·D-day·NEW 여부는 스키마에 저장하지 않고 `recommend.build_dashboard()`가
매 요청마다 `body_text`/`target_raw`에서 계산한다(아래 참고).

### "검토 필요" 목록은 어디서 보나

`kw_notice.py` 실행 후 콘솔에 `저장 N개 / 검토 필요 M개 / 본문·OCR 확인 후 제외 K개`가 출력된다.
- **검토 필요(M)**: 활동카테고리·관심분야·지역·모집대상 중 하나라도 제목+본문+OCR로도 못 잡았거나,
  지역이 모호/복수로 잡힌 공고. 저장은 되지만(`activities.review_required=1`) 자동 분류를 못 믿을
  수 있다는 표시다. 실행 후 생성되는 **`kw_review.csv`**를 열어보거나, DB에서
  `SELECT * FROM activities WHERE review_required=1`로 조회하면 목록이 나온다. `check_db.py`도
  이 컬럼을 그대로 보여준다.
- **본문·OCR 확인 후 제외(K)**: 제목만으론 안 걸렸지만 본문/OCR 텍스트에 노이즈 키워드가 있어서
  아예 저장하지 않은 것 — DB에는 안 남고 콘솔 로그에만 남는다(`→ 제외(본문·OCR 확인 후 학사·행정
  공지로 판단)`).

## 개인화 매칭 규칙 (`recommend.py`)

| 대상 | 학과 조건 | 관심분야 조건 | 지역 조건 | 학년 조건 |
| --- | --- | --- | --- | --- |
| 교내 일반(대외활동/공모전/교육/기타) | 학과 일치 필요 | **무관(안 봄)** | **무관(안 봄)** | 본문 기준 |
| 교내 장학·지원 | **무시(전공 불문)** | 무관 | 지역 규칙 적용 | 본문 기준 |
| 교외(전 카테고리) | 학과 일치 필요(장학·지원은 무시) | 겹침 필요(장학·지원은 무시) | 지역 규칙 적용 | 본문 기준(인턴·채용은 + 2학년 이상) |

관심분야는 교내에서는 아예 보지 않고, 교외에서만 겹침을 확인한다(장학·지원 제외). 지역은 교내
장학·지원과 교외 전체만 확인하고, **교내 일반은 지역 무관**이다 — 한때(2026-07-25 중) "교내도
지역을 항상 본다"로 바꿨다가, 실제 데이터에서 문제가 발견돼 되돌렸다: 온캠퍼스 행사 공지 본문의
"장소: 광운대학교 ... 서울특별시 노원구" 같은 주소 문구를 지역 추출기가 참가 자격(거주지 제한)으로
착각해서, 캠퍼스에서 열리는 전체 학생 대상 행사까지 지역이 안 맞는 학생에게는 안 보이는 문제가 있었다.
교내 행사는 원래 거주지와 무관하게 참여 가능하므로(캠퍼스로 통학) 지역 조건을 다시 뺐다.

**관심분야를 하나도 선택하지 않은 학생**은 `interest_matches()`가 관심분야 조건 자체를 생략하고
통과시킨다(`if not student_interests: return True`) — 교외에서 "관심분야 미선택 시 학과 정보만으로
추천, 선택하면 그 분야만" 구조를 만들기 위함. 교내는 애초에 관심분야를 안 보므로 이 분기와 무관하게
항상 학과만으로 판단한다.

**화면 표시**: `web/components/dashboard/ActivityCard.tsx`/`UrgentCard.tsx`는 `campus_scope === "교외"`
일 때만 관심분야 뱃지를 그린다 — 교내는 필터링에 관심분야를 안 쓰므로 뱃지도 안 보여준다(카테고리
뱃지 하나 + OCR/NEW/지역 뱃지만). `web/lib/badges.ts`가 `common.ACTIVITY_CATEGORIES`의 6개 값
(대외활동/공모전/인턴·채용/교육/장학·지원/기타)만 카테고리 뱃지로 매핑한다.

링커리어 공고는 지역 조건을 적용하지 않는다. 광운대 `[외부]` 공고와 교내 장학·지원 공고만
구조화 결과의 `region_restriction === "include_only"`인 경우 지역을 확인하며, `regions`와 함께
`region_eligibility_evidence`에 거주·주민등록·주소·소재 학교·출신·지역 우선 선발 같은 지원자격
표현이 있어야 실제 제한으로 인정한다. 행사 장소, 주최기관명, 제출처·연락처에 포함된 지역명은
필터와 지역 뱃지에 사용하지 않는다.

**국제학생 전용 게시판**: 광운대 공지 게시판 카테고리가 `[국제학생]`(외국인 유학생 대상 수강신청·
장학금·기숙사 등)인 공고는 학생이 프로필에서 "국제학생(유학생)" 토글을 켠 경우에만 보인다
(`recommend.INTERNATIONAL_ONLY_BOARD_CATEGORIES`, `students.is_international` 컬럼). 이 체크는
`_match_activities`의 다른 조건(학과/관심분야/지역/학년)보다 먼저 적용되는 하드 게이트다. `[국제교류]`
게시판(재학생의 해외교환·인턴십 등)은 국내 학생도 보는 대상이라 별도 취급하지 않는다. 온보딩
2단계(거주지역)와 프로필 편집 모달에 토글이 있다.

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
- 2026-07-25: 교내 프로그램 매칭 규칙 변경 — 관심분야는 더 이상 보지 않고, 학과·지역만 확인(지역은
  이제 교내에도 항상 적용). 교외는 기존대로 관심분야까지 확인.
- 2026-07-25: `kw_notice.py`가 학교 자체 직원 채용 공고("기간제 계약직원" 등, `common.is_staff_hiring_notice`)를
  수집 단계에서 제외하도록 변경. 기존에 이미 저장돼 있던 동일 유형 3건도 DB에서 정리.
- 2026-07-25: 학사·행정 공지(수강신청/학사경고/병무/단체교섭/초빙교수 등) 필터 추가 —
  `common.is_noise_notice()` + `NOISE_KEYWORDS`/`NOISE_BOARD_CATEGORIES`("학사"/"병무" 게시판 전체
  제외). `kw_notice.py`가 제목 맨 앞 `[카테고리]` 표기를 그대로 게시판 카테고리로 추출하도록 개선
  (`extract_bracket_category`, 기존 방식보다 정확하고 "국제학생"/"국제교류"/"병무" 같은 카테고리도
  놓치지 않음). 제목의 "신규게시글"/"Attachment"/"조회수 N" 잡음도 제거(`strip_title_noise`).
  기존 DB에서 같은 기준에 걸리는 7건 삭제, 남은 행 제목의 잡음 텍스트도 정리.
  (참고: `/Users/jiyeon/Downloads/1112`에 있던 예전 테스트용 프로토타입 코드를 검토해서 아이디어를
  가져옴 — 다만 그 코드의 노이즈 키워드 목록도 "수강신청"은 못 걸렀어서, 실제 우리 DB를 분석해 원인
  (게시판 카테고리가 "학사"인 공지들)을 찾아 더 정확한 기준으로 새로 만들었다.)
- 2026-07-25: **교내 일반 활동의 지역 조건을 다시 제거.** 위에서 "교내도 지역을 본다"로 바꾼 지
  얼마 안 돼, 실제로는 온캠퍼스 행사의 "장소" 주소가 거주지 제한으로 오인돼 대부분의 교내 행사가
  안 보이는 문제를 발견해서 되돌림. 최종적으로 교내 일반은 학과만, 교내 장학·지원/교외는 기존대로
  지역까지 확인.
- 2026-07-25: 관심분야를 하나도 선택하지 않은 학생은 `interest_matches()`가 관심분야 조건을 생략하고
  통과시키도록 수정(과거엔 관심분야 미선택 시 "기타" 태그 공고 외엔 거의 안 뜨는 버그가 있었음) —
  교외에서 "미선택 시 학과 기반 추천, 선택 시 그 분야만" 구조 완성.
- 2026-07-25: 교내 카드에서 관심분야 뱃지를 더 이상 표시하지 않음(카테고리 뱃지만, `ActivityCard.tsx`/
  `UrgentCard.tsx`) — 교내는 관심분야로 필터링하지 않으므로 뱃지도 안 보여주는 게 맞음.
- 2026-07-25: 기존 DB에서 게시판이 "등록/장학"인데 `activity_category`가 "기타"로 남아있던 행 2건을
  "장학·지원"으로 수정. 코드는 이미 이 매핑을 강제하도록 돼 있었지만(이전 세션), 그 코드 수정 전에
  저장된 옛 행에는 소급 적용이 안 돼 있었던 것 — 앞으로 크롤링되는 등록/장학 공지는 처음부터 올바르게
  분류된다.
- 2026-07-25: `kw_notice.py`의 수집 기간·페이지 수를 3일→30일(`KW_DAYS_BACK`), 5→20페이지(`MAX_PAGES`)로
  확대. 링커리어(`link.py`)는 팀원 규칙대로 3일 그대로 유지 — 광운대 공지만 늘어난 것. 실제로 재크롤링해서
  약 190건 수집 확인.
- 2026-07-25: `common.NOISE_KEYWORDS`에 학사·행정 노이즈 키워드 다수 추가(장소사용/승강기/부고/
  사무실 이전/사칭 물품/셔틀버스 등) — 실제 재크롤링한 데이터를 보며 계속 튜닝.
- 2026-07-25: **국제학생 전용 공지 필터링 추가.** `[국제학생]` 게시판(외국인 유학생 대상 수강신청·
  장학금·기숙사 공지 등)이 국내 학생에게도 노출되던 문제 수정 — `students.is_international` 컬럼
  신설, 온보딩 2단계와 프로필 편집 모달에 "국제학생(유학생)" 토글 추가. `recommend._match_activities`
  최상단에서 하드 게이트로 적용(국제학생으로 표시 안 된 학생에게는 아예 안 보임). `[국제교류]` 게시판은
  재학생의 해외교환·인턴십 등이라 그대로 노출(국제학생 전용 취급 안 함). 실제 재크롤링 데이터로 검증:
  국내 학생 76건(국제학생 게시판 0건 포함), 국제학생 토글 켠 학생 97건(21건 추가) — 브라우저로 확인.
- 2026-07-25: **"청소"가 "청소년"까지 걸리던 오탐 수정.** `compact_text`(공백 제거)로 비교하는 방식이라
  한글 단어 경계를 정규식으로 판정할 수 없다는 걸 확인(모든 글자가 붙어버림) — 대신 승강기·청소·공사
  관련 공지가 실제로 전부 `[시설]` 게시판이었던 걸 확인하고 `NOISE_BOARD_CATEGORIES`에 `"시설"`을
  추가해 게시판째로 제외, `NOISE_KEYWORDS`에서 애매한 "청소" 단독 키워드는 제거.
- 2026-07-25: **OCR 이후 텍스트에도 노이즈/직원채용 필터 적용.** 이전엔 `is_noise_notice`/
  `is_staff_hiring_notice`가 목록 단계에서 제목만 보고 판단했는데, 제목엔 안 걸려도 본문이나 포스터
  이미지 OCR 결과에 노이즈 키워드가 있으면 여전히 저장되고 있었다. `kw_notice.py::parse_notice`가
  본문+OCR을 합친 뒤 다시 한번 필터를 적용하도록 수정 — 걸리면 저장하지 않고 `None`을 반환, `main()`이
  이를 "본문·OCR 확인 후 제외"로 별도 집계한다(실행 결과 요약에 새 줄로 표시됨).
- 2026-07-26: `common.extract_target_text()`가 `모집 대상`처럼 띄어 쓴 라벨도 인식하도록 개선하고, OCR 표에서
  `참가자격 신청방법`처럼 라벨이 연속될 때 다음 항목의 내용을 모집대상으로 잘못 가져오지 않도록 수정. 추출값 끝의
  `○`, `5.` 같은 항목 구분 기호도 제거.
- 2026-07-26: GPT 구조화 스키마에 화면 표시 전용 `eligibility_summary`를 추가. 실제 신청 가능한 사람의
  재학·학년·성적·소득·전공·연령 조건만 요약하고 제출서류·신청방법·증빙방법은 포함하지 않도록 프롬프트를 강화.
  카드의 모집대상 선택 순서는 `eligibility_summary` → `structured_target` → 기존 `target_raw` →
  `enrollment_target`으로 확정.
- 2026-07-26: 기존 공고 227건을 새 구조화 스키마로 전면 재분석(성공 227건, 실패 0건, 필드 누락 0건).
  구리시 청년성장프로젝트, DDM Union 청년 창업 챌린지, 사랑나눔장학생, 매치업 수강후기 공모전,
  기초학력 클리닉 튜터링 등에서 잘못 표시되던 모집대상을 원문의 실제 지원자격으로 교정.
- 2026-07-26: 개인화 매칭 정책을 최종 정리. 교내 일반 공고는 관심분야와 지역을 보지 않고 학과·학년 조건만
  적용하며, 교내 장학·지원은 전공과 관심분야를 무시하고 지역·학년 조건을 적용. 교외 공고는 장학·지원을 제외하고
  학생이 선택한 관심분야와 공고의 `interest_categories`가 겹쳐야 하며, 관심분야 미설정 시 해당 조건을 생략.
- 2026-07-26: 수집 필터 적용 전에 DB에 남아 있던 `[학생] 장소사용 신청 안내` 7월·8월 공고를 삭제하고,
  `recommend._match_activities()`에서도 광운대학교 공고의 제목에 `is_noise_notice()`를 재적용하도록 방어 로직 추가.
  본문 전체가 아닌 제목만 검사해 정상 장학·활동 공고의 오탐을 방지.
- 2026-07-26: 지역 매칭을 지원자격 근거 기반으로 변경 — 링커리어는 지역 무관으로 유지하고, 광운대
  `[외부]` 및 교내 장학·지원 공고만 구조화된 `region_restriction`/`regions`/
  `region_eligibility_evidence`를 확인. `include_only`이면서 근거 문장에 거주·주민등록·주소·소재
  학교·출신·지역 우선 선발 같은 **지원자격 표현이 있을 때만** 지역 제한과 지역 뱃지를 적용한다.
  행사 개최 장소, 주최기관명, 제출처·연락처에 포함된 지역명은 적용하지 않는다. 관련 공고 72건을
  새 기준으로 재구조화(성공 72, 실패 0).
- 2026-07-26: 대시보드 카드에서 추천 유사도 점수와 이미지 OCR 배지를 제거하고, 헤더의 알림·설정 메뉴와
  종 모양 알림 버튼, “오늘 새로운 공고 N개가 도착했어요” 안내 문구를 제거. 헤더 메뉴는 대시보드만 유지.
- 2026-07-26: 기존 색상 체계는 유지하면서 대시보드를 학교 포털형 UI로 개편. 카드 그림자와 과도한 둥근 모서리를
  줄이고 얇은 테두리·좌측 강조선·조밀한 타이포그래피를 적용했으며, 탭과 카테고리 버튼 및 마감 임박 카드를
  평평하고 정돈된 형태로 변경. 모바일 한 열 레이아웃도 함께 보완.
- 2026-07-26: 학생이 선택한 학과·학년, 지역, 관심분야를 공고 목록 위의 독립 프로필 카드로 구성하고 세 정보
  영역과 프로필 수정 버튼을 카드 안에 배치. 모바일에서는 정보 영역이 세로로 쌓이도록 반응형 처리.
- 2026-07-27: '최신순'을 '추천순'으로 변경.

## 미구현 (계획 단계)

- 이메일 알림 서비스(smtplib) — 온보딩/프로필에서 이메일·수신 동의는 저장하지만 실제 발송 로직은 없음
- 수집 스케줄러 (cron/GitHub Actions, 1일 1회)
- 실제 전공(단과대학→학과) 매핑, 정밀 지역 매칭 — 현재는 단순 placeholder(추후 하드코딩 예정)

미해결 스펙 충돌·확인 필요 항목은 [`CLAUDE.md`](CLAUDE.md)를 참고하세요.
