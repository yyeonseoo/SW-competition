# 광운대학교 학생 맞춤형 비교과 활동 추천 시스템

교내(광운대 공지) + 교외(링커리어) 비교과 활동(공모전/대외활동/인턴·채용/교육/장학) 정보를 하나로 모아,
학생 프로필(전공·학년·거주지역·관심분야) 기준으로 개인화 추천하는 시스템입니다.

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

**관심분야를 하나도 선택하지 않은 학생**은 `interest_matches()`가 관심분야 조건 자체를 생략하고
통과시킨다(`if not student_interests: return True`) — 교외에서 "관심분야 미선택 시 학과 정보만으로
추천, 선택하면 그 분야만" 구조를 만들기 위함. 교내는 애초에 관심분야를 안 보므로 이 분기와 무관하게
항상 학과만으로 판단한다.

**화면 표시**: 
`region_matches`/지역 추출(`regions.py::extract_region`)은 본문 전체에서 지역 지명을 찾는 방식이라
위 사례처럼 장소 주소·연락처 등 자격과 무관한 지역 언급까지 집어올 수 있다 — 정밀도 개선 여지가 남아
있다(교외 지역 매칭에는 여전히 이 이슈가 남아 있음).

**국제학생 전용 게시판**: 광운대 공지 게시판 카테고리가 `[국제학생]`(외국인 유학생 대상 수강신청·
장학금·기숙사 등)인 공고는 학생이 프로필에서 "국제학생(유학생)" 토글을 켠 경우에만 보인다

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

