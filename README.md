# 광운대학교 학생 맞춤형 비교과 활동 추천 시스템

교내(광운대 공지) + 교외(링커리어) 비교과 활동(공모전/대외활동/인턴·채용/교육/장학) 정보를 하나로 모아,
학생 프로필(전공·학년·거주지역·관심분야) 기준으로 개인화 추천하는 시스템입니다.

- 기능 스펙(단일 기준 문서): [`JY_local/notice.md`](JY_local/notice.md)
- 작업 규칙·구현 현황·미해결 이슈: [`CLAUDE.md`](CLAUDE.md)

## 프로젝트 구조

```
link.py              링커리어 공고 수집 (Selenium)
kw_notice.py          광운대학교 공지사항 수집 (requests + BeautifulSoup)
common.py             공통 유틸: DB 스키마/저장, 활동카테고리·관심분야·교내외 구분 분류, 날짜/대상 정규화
regions.py             제목·본문에서 시·도 → 구/시·군 2단계 지역 추출 (동명 지명 모호성 처리)
ocr_utils.py           NCP CLOVA OCR 연동 (본문에 모집대상·기간이 없을 때만 호출)
insert_student.py      학생 프로필 등록 (현재는 테스트용 단일 학생 하드코딩)
recommend.py           학생 프로필과 공고를 매칭해 추천 목록 생성
check_db.py            recommendation.db 저장 내용 확인용 스크립트
recommendation.db      SQLite DB (activities, students 테이블)
requirements.txt       Python 의존성 목록
.env.example           NCP OCR 자격 증명 템플릿 (.env로 복사해서 사용)
JY_local/               기획 문서(notice.md)·프로토타입 스크린샷 — 코드 대상 아님
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
   학생 프로필(insert_student.py) → 개인화 매칭(recommend.py) → 추천 결과
```

## 실행 방법

1. 의존성 설치
   ```
   pip install -r requirements.txt
   ```
   > ⚠️ 알려진 이슈: `link.py`는 `selenium`·`pandas`를, `kw_notice.py`는 `pandas`를 사용하지만
   > 아직 `requirements.txt`에 반영되어 있지 않습니다. 직접 설치해 주세요:
   > `pip install selenium pandas`
   > (Selenium 사용 시 로컬에 Chrome/Chromedriver도 필요합니다.)

2. OCR 자격 증명 설정 (광운대 공지 수집 시 필요)
   ```
   cp .env.example .env
   # .env에 CLOVA_OCR_URL, CLOVA_OCR_SECRET 입력
   ```

3. 공고 수집
   ```
   python link.py        # 링커리어 (대외활동/공모전/교육, 시작일 최근 3일 + 참여대상 필터)
   python kw_notice.py    # 광운대학교 공지사항 (최근 3일 작성글)
   ```

4. 학생 프로필 등록 (현재는 `insert_student.py` 내 하드코딩 값으로 저장되는 테스트용 스크립트)
   ```
   python insert_student.py
   ```

5. 추천 결과 확인
   ```
   python recommend.py
   ```

6. DB 원본 확인
   ```
   python check_db.py
   ```

## 데이터베이스

SQLite (`recommendation.db`), 테이블 2개:

- `activities`: 수집된 공고. `source`(광운대학교/링커리어), `campus_scope`(교내/교외),
  `activity_category`(대외활동/공모전/인턴·채용/교육/장학·지원/기타), `interest_categories`(20개 태그 중 매칭분),
  지역(2단계), 모집대상, 기준일, 본문/OCR 텍스트, 검토 필요 여부 등을 저장.
- `students`: 학생 프로필. 이름, 학과, 학년, 관심분야, 거주지역.

## 개인화 매칭 규칙 (`recommend.py`)

| 대상 | 학과/분야 조건 | 지역 조건 | 학년 조건 |
| --- | --- | --- | --- |
| 일반(대외활동/공모전/교육/기타) | 학과 일치 + 관심분야 겹침 필요 | 지역 규칙 적용 | 본문 기준 |
| 인턴·채용 | 위와 동일 | 지역 규칙 적용 | 본문 기준 + **2학년 이상만** |
| 장학·지원 | **무시(전공 불문)** | 지역 규칙 적용 | 본문 기준 |

## 최근 변경 사항

- 2026-07-25: 활동카테고리에 `인턴·채용`, `장학·지원` 추가 (`common.py` `CATEGORY_RULES`), 광운대 공지
  "등록/장학" 게시판을 `장학·지원`으로 강제 매핑 (`kw_notice.py`).
- 2026-07-25: `recommend.py`에 카테고리별 개인화 규칙 반영 — 장학·지원은 학과/관심분야 조건을 무시하고
  지역·학년만 확인, 인턴·채용은 2학년 이상만 노출.
- 2026-07-25: `activities` 테이블에 `campus_scope`(교내/교외) 컬럼 추가. 판정 로직은 `common.py`의
  `classify_campus_scope()` 한 곳에서만 계산해 `save_activity()` 저장 시점에 채워지며, 기존 DB에도
  `ALTER TABLE`로 안전하게 마이그레이션됨.
- 2026-07-25: `README.txt` → `README.md`로 전환.

## 미구현 (계획 단계)

- 대시보드 UI (Streamlit 예정) — `JY_local/prototype_v2.html` 확보 전까지 작성하지 않음
- 이메일 알림 서비스 (smtplib)
- 수집 스케줄러 (cron/GitHub Actions, 1일 1회)
- 학생 프로필 등록 UI/API (현재는 `insert_student.py` 하드코딩 스크립트로 대체)

미해결 스펙 충돌·확인 필요 항목은 [`CLAUDE.md`](CLAUDE.md)를 참고하세요.
