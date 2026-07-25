# 광운대학교 학생 맞춤형 비교과 활동 추천 시스템

교내(광운대 공지) + 교외(링커리어) 비교과 활동(공모전/대외활동/인턴·채용/교육/장학) 정보를 하나로 모아,
학생 프로필(전공·학년·거주지역·관심분야) 기준으로 개인화 추천하는 시스템입니다.

- 기능 스펙(단일 기준 문서): [`JY_local/notice.md`](JY_local/notice.md)
- UI/UX 기준: [`JY_local/prototype_v2.html`](JY_local/prototype_v2.html) (색상·타이포·간격·카드·뱃지·모달 스타일의 원본)
- 작업 규칙·구현 현황·미해결 이슈: [`CLAUDE.md`](CLAUDE.md)

## 프로젝트 구조

```
main_scheduler.py      1일 1회 수집 -> 분류/저장 -> 메일 알림 통합 스케줄러 (데몬 모드 지원)
crawlers/              크롤러 패키지: 팀원 수집 규칙 완벽 보존 및 2차 노이즈 차단
  ├── kw_crawler.py       광운대학교 공지사항 수집 및 OCR 텍스트 분석
  └── linkareer_crawler.py 링커리어 공고 수집 (Selenium 헤드리스 크롤러)
utils/                 핵심 공통 처리 패키지
  ├── text_processor.py   텍스트/날짜 전처리, D-day 계산 및 대상 정규화
  └── classifier.py       20개 관심분야/교내외 분류, 3단계 노이즈 방어 필터
services/              서비스 패키지
  └── email_notifier.py   SMTP 기반 신규 맞춤형 공고 알림 HTML 메일 발송 모듈
database.py            SQLite DB 초기화, 온보딩 마이그레이션 및 upsert 로직
link.py                crawlers.linkareer_crawler 호환성 실행 래퍼
kw_notice.py           crawlers.kw_crawler 호환성 실행 래퍼
common.py              신규 모듈(database, utils) 호환성 유지 re-export 래퍼
regions.py             제목·본문에서 시·도 → 구/시·군 2단계 지역 추출 (동명 지명 모호성 처리)
departments.py         web/data/departments.json을 읽어 단과대학→학과 조회 함수 제공
ocr_utils.py           NCP CLOVA OCR 연동 (본문에 모집대상·기간이 없을 때만 호출)
recommend.py           학생 프로필-공고 개인화 매칭 (3차 실시간 노이즈 마스킹 적용)
api.py                 FastAPI 서버 — Next.js 프론트엔드 통신용 REST API
web/                   Next.js(React) 프론트엔드 — '광운대 레드' 프리미엄 UI 및 마이크로 애니메이션
recommendation.db      SQLite DB (activities, students 테이블)
```

### 데이터 흐름 및 3단계 노이즈 방어 파이프라인

```
[광운대 공지] + [링커리어]
        │
        ▼
  [1차 필터: 목록 제목 기준 행정·학사 공지 걸러내기]
        │
        ▼
  수집 (crawlers.kw_crawler / linkareer_crawler)
        │   └─ 이미지형 공지 → NCP OCR로 텍스트화 (모집대상·모집기간)
        ▼
  [2차 필터: 본문·OCR 텍스트 내 행정·학사 단어 2차 차단]
        │
        ▼
  자동 분류 및 저장 (utils.classifier / database.py, URL 기준 upsert)
        │
        ├──► 하루 1회 신규 매칭 공고 추출 ──► HTML 이메일 맞춤 발송 (services.email_notifier)
        ▼
  학생 프로필 매칭 (recommend.py build_dashboard)
        │
        ▼
  [3차 필터: DB 적재된 과거 노이즈 데이터 실시간 마스킹] ──► web/ 대시보드 표시
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

공고 수집 및 통합 스케줄러 실행:

```
python main_scheduler.py           # 하루 1회 수집 -> DB저장 -> 알림 메일 발송 파이프라인 즉시 실행
python main_scheduler.py --daemon   # 매일 지정 시각(기본 00:00)에 자동 반복 실행하는 데몬 모드
python link.py                      # 링커리어 단독 수집 (crawlers/linkareer_crawler 래퍼)
python kw_notice.py                 # 광운대 공지 단독 수집 (crawlers/kw_crawler 래퍼)
```

이메일 발송 단독 테스트 및 시뮬레이션:

```
python -m services.email_notifier   # SMTP 설정이 없으면 터미널에 콘솔 시뮬레이션으로 안전하게 출력됨
```

API 서버 실행 (프론트엔드 REST API 통신용):

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

| 대상                                 | 학과 조건                        | 관심분야 조건               | 지역 조건       | 학년 조건                           |
| ------------------------------------ | -------------------------------- | --------------------------- | --------------- | ----------------------------------- |
| 교내 일반(대외활동/공모전/교육/기타) | 학과 일치 필요                   | **무관(안 봄)**             | **무관(안 봄)** | 본문 기준                           |
| 교내 장학·지원                       | **무시(전공 불문)**              | 무관                        | 지역 규칙 적용  | 본문 기준                           |
| 교외(전 카테고리)                    | 학과 일치 필요(장학·지원은 무시) | 겹침 필요(장학·지원은 무시) | 지역 규칙 적용  | 본문 기준(인턴·채용은 + 2학년 이상) |

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

`region_matches`/지역 추출(`regions.py::extract_region`)은 본문 전체에서 지역 지명을 찾는 방식이라
위 사례처럼 장소 주소·연락처 등 자격과 무관한 지역 언급까지 집어올 수 있다 — 정밀도 개선 여지가 남아
있다(교외 지역 매칭에는 여전히 이 이슈가 남아 있음).

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

| Method/Path                      | 설명                                                                 |
| -------------------------------- | -------------------------------------------------------------------- |
| `GET /api/meta`                  | 관심분야 20종, 활동카테고리 6종, 지역 목록 — 온보딩/모달의 단일 출처 |
| `POST /api/students`             | 프로필 생성                                                          |
| `GET /api/students/{id}`         | 프로필 조회                                                          |
| `PATCH /api/students/{id}`       | 프로필 수정                                                          |
| `GET /api/dashboard?student_id=` | 교내/교외, 곧 마감, 카드 목록 등 대시보드 전체 데이터                |

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
- 2026-07-25: **전면 아키텍처 리팩토링 및 3단계 노이즈 완벽 방어.**
  - 비대화된 `common.py`를 `database.py`, `utils.text_processor`, `utils.classifier`로 역할 분리하고 크롤러 엔진을 `crawlers/` 패키지로 개조(팀원 수집 규칙 100% 보존 및 하위 호환성 래퍼 지원).
  - 수강신청 등 `NOISE_KEYWORDS`가 지속 노출되던 문제를 3단계 필터링(1차 목록 제목 $\rightarrow$ 2차 본문/OCR 텍스트 $\rightarrow$ 3차 `recommend.py` 호출 시 실시간 마스킹) 구조로 개편하여 완벽하게 해결.
  - 미구현 기능이던 맞춤 알림 메일 발송 서비스(`services/email_notifier.py`, 광운대 상징색 HTML 뉴스레터 제공)와 배치 스케줄러(`main_scheduler.py`) 전면 구축 완료.
  - Next.js 프론트엔드(`web/app/globals.css`)에 광운대 레드를 활용한 현대적인 박스 섀도우 및 반응형 마이크로 애니메이션을 도입하여 시각적 완성도 고도화.
- 2026-07-25: **실시간 사용성 고도화, 스케줄링 다중화 및 개인정보 보호 강화.**
  - **국제학생 프로필 연동 및 노출 차단 고도화**: `students` 테이블 및 API에 `is_international` 컬럼을 정식 등재하고, 국내 학생(is_international=0) 대상 `[국제학생]` 게시판 완전 하드 게이트 차단 구현.
  - **OCR 호출 조건 정교화(보조 수단 전환)**: 지역·관심분야 분리 불명확으로 인한 과다 OCR 호출을 방지하고, ① 본문 텍스트 20자 미만(이미지 공고), ② 모집대상 문구 누락, ③ 모집기간/마감일 누락 시에만 정밀 호출하도록 최적화.
  - **1일 3회 크롤러 스케줄러 및 오전 8시 메일 발송 구성**: `main_scheduler.py`를 개편하여 매일 오전 8시, 오후 12시, 오후 4시 3회 수집을 자동 가동하며, 이메일 알림(`email_notifier`)은 오직 오전 8시 실행 시에만 최근 24시간 내 신규 수집된 맞춤 공고를 모아 발송하도록 개선.
  - **대시보드 및 프로필 편집 UI 정비**: 미구현이던 상단 '알림'·'설정' 탭과 종(🔔) 이모티콘 및 '오늘 새로운 공고 N개' 안내 멘트를 제거하고 개인화 타이틀을 강조. 또한 온보딩 후에도 프로필 편집 창(`ProfileEditModal.tsx`)에서 언제든 새 이메일을 기입 및 변경할 수 있는 입력 창 신설.
  - **민감 데이터 Git 제외 및 보존**: `.gitignore`에 `*.db`, `node_modules/`, `.env*` 등을 정식 보강하고 기존 추적되던 `recommendation.db`의 깃허브 추적을 안전 해제.

미해결 스펙 충돌·확인 필요 항목은 [`CLAUDE.md`](CLAUDE.md)를 참고하세요.

