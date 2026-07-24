[전체 프로젝트 흐름]

link.py
링커리어 공고 수집
        ↓
kw_notice.py
광운대학교 공지 수집
        ↓
common.py / regions.py / ocr_utils.py
공통 분류·지역 분석·OCR 지원
        ↓
recommendation.db
공고와 학생 정보 저장
        ↑
insert_student.py
학생 정보 등록
        ↓
recommend.py
학생 조건과 공고를 비교해 추천
        ↓
check_db.py
DB에 저장된 결과 확인

*일단 제가 링커리어 공고 크롤링(link.py)만 구현했습니다 ㅜㅜ!
[link.py 반영 사항]
-  링커리어에서는 지역을 별도로 분석하지 않고 참여대상이 '직장인/일반인, 대상 제한 없음, 대학생'일 경우 공고 추출하는 것으로 설정
- '시작일'이 당일~3일 전인 공고만 수집 (ex. 07/21~07/24)
- 링커리어는 OCR 사용 X
- '교육' 파트는 관심분야가 정해져 있지 않아서 제목+본문 분석 후 키워드로 분류되도록 설정