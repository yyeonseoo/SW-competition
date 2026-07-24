import re
from common import clean_text

# 시·도와 시·군·구의 계층관계를 이용한다.
# 상위 지역이 본문에 있으면 '중구'처럼 중복되는 이름도 해당 상위 지역 안에서 결정한다.
REGIONS = {
    "서울특별시": ["종로구","중구","용산구","성동구","광진구","동대문구","중랑구","성북구","강북구","도봉구","노원구","은평구","서대문구","마포구","양천구","강서구","구로구","금천구","영등포구","동작구","관악구","서초구","강남구","송파구","강동구"],
    "부산광역시": ["중구","서구","동구","영도구","부산진구","동래구","남구","북구","해운대구","사하구","금정구","강서구","연제구","수영구","사상구","기장군"],
    "대구광역시": ["중구","동구","서구","남구","북구","수성구","달서구","달성군","군위군"],
    "인천광역시": ["중구","동구","미추홀구","연수구","남동구","부평구","계양구","서구","강화군","옹진군"],
    "광주광역시": ["동구","서구","남구","북구","광산구"],
    "대전광역시": ["동구","중구","서구","유성구","대덕구"],
    "울산광역시": ["중구","남구","동구","북구","울주군"],
    "세종특별자치시": ["세종시"],
    "경기도": ["수원시","성남시","의정부시","안양시","부천시","광명시","평택시","동두천시","안산시","고양시","과천시","구리시","남양주시","오산시","시흥시","군포시","의왕시","하남시","용인시","파주시","이천시","안성시","김포시","화성시","광주시","양주시","포천시","여주시","연천군","가평군","양평군"],
    "강원특별자치도": ["춘천시","원주시","강릉시","동해시","태백시","속초시","삼척시","홍천군","횡성군","영월군","평창군","정선군","철원군","화천군","양구군","인제군","고성군","양양군"],
    "충청북도": ["청주시","충주시","제천시","보은군","옥천군","영동군","증평군","진천군","괴산군","음성군","단양군"],
    "충청남도": ["천안시","공주시","보령시","아산시","서산시","논산시","계룡시","당진시","금산군","부여군","서천군","청양군","홍성군","예산군","태안군"],
    "전북특별자치도": ["전주시","군산시","익산시","정읍시","남원시","김제시","완주군","진안군","무주군","장수군","임실군","순창군","고창군","부안군"],
    "전라남도": ["목포시","여수시","순천시","나주시","광양시","담양군","곡성군","구례군","고흥군","보성군","화순군","장흥군","강진군","해남군","영암군","무안군","함평군","영광군","장성군","완도군","진도군","신안군"],
    "경상북도": ["포항시","경주시","김천시","안동시","구미시","영주시","영천시","상주시","문경시","경산시","의성군","청송군","영양군","영덕군","청도군","고령군","성주군","칠곡군","예천군","봉화군","울진군","울릉군"],
    "경상남도": ["창원시","진주시","통영시","사천시","김해시","밀양시","거제시","양산시","의령군","함안군","창녕군","고성군","남해군","하동군","산청군","함양군","거창군","합천군"],
    "제주특별자치도": ["제주시","서귀포시"],
}

SIDO_ALIASES = {
    "서울특별시": ["서울특별시", "서울시", "서울"],
    "부산광역시": ["부산광역시", "부산시", "부산"],
    "대구광역시": ["대구광역시", "대구시", "대구"],
    "인천광역시": ["인천광역시", "인천시", "인천"],
    "광주광역시": ["광주광역시", "광주광역", "광주"],
    "대전광역시": ["대전광역시", "대전시", "대전"],
    "울산광역시": ["울산광역시", "울산시", "울산"],
    "세종특별자치시": ["세종특별자치시", "세종시", "세종"],
    "경기도": ["경기도", "경기"],
    "강원특별자치도": ["강원특별자치도", "강원도", "강원"],
    "충청북도": ["충청북도", "충북"],
    "충청남도": ["충청남도", "충남"],
    "전북특별자치도": ["전북특별자치도", "전라북도", "전북"],
    "전라남도": ["전라남도", "전남"],
    "경상북도": ["경상북도", "경북"],
    "경상남도": ["경상남도", "경남"],
    "제주특별자치도": ["제주특별자치도", "제주도", "제주"],
}

# 동일 시·군·구명이 어느 시·도에 존재하는지 역색인
PARENTS = {}
for sido, names in REGIONS.items():
    for name in names:
        PARENTS.setdefault(name, []).append(sido)


def extract_region(text):
    """
    제목+본문 전체에서 시·도→시·군·구 계층으로 추출한다.

    반환 status:
    - resolved: 하나의 지역으로 확정
    - nationwide: 지역 표현 없음
    - ambiguous: 중구처럼 상위 지역 없이 여러 후보가 존재
    - multiple: 서로 다른 여러 지역이 함께 언급됨
    """
    text = clean_text(text)

    found_sidos = []
    for official, aliases in SIDO_ALIASES.items():
        if any(alias in text for alias in aliases):
            found_sidos.append(official)

    found_sigungus = []
    # 긴 이름부터 찾아 '광주시'와 '광주' 등의 충돌을 줄임
    all_sigungus = sorted(PARENTS, key=len, reverse=True)
    for name in all_sigungus:
        if re.search(rf"(?<![가-힣]){re.escape(name)}(?![가-힣])", text):
            found_sigungus.append(name)

    found_sidos = list(dict.fromkeys(found_sidos))
    found_sigungus = list(dict.fromkeys(found_sigungus))

    if not found_sidos and not found_sigungus:
        return {
            "region_sido": "전국/무관",
            "region_sigungu": "",
            "region_detail": "",
            "region_status": "nationwide",
            "found": False,
        }

    candidates = []
    for sigungu in found_sigungus:
        parents = PARENTS[sigungu]
        if found_sidos:
            matched_parents = [sido for sido in found_sidos if sido in parents]
            for sido in matched_parents:
                candidates.append((sido, sigungu))
        elif len(parents) == 1:
            candidates.append((parents[0], sigungu))

    candidates = list(dict.fromkeys(candidates))

    if len(candidates) == 1:
        sido, sigungu = candidates[0]
        return {
            "region_sido": sido,
            "region_sigungu": sigungu,
            "region_detail": f"{sido} {sigungu}",
            "region_status": "resolved",
            "found": True,
        }

    if not found_sigungus and len(found_sidos) == 1:
        sido = found_sidos[0]
        return {
            "region_sido": sido,
            "region_sigungu": "",
            "region_detail": sido,
            "region_status": "resolved",
            "found": True,
        }

    if len(candidates) > 1 or len(found_sidos) > 1:
        detail = " / ".join(f"{sido} {sigungu}" for sido, sigungu in candidates)
        return {
            "region_sido": "",
            "region_sigungu": "",
            "region_detail": detail or " / ".join(found_sidos + found_sigungus),
            "region_status": "multiple",
            "found": True,
        }

    # 상위 지역이 없고 동일 이름이 여러 시·도에 존재
    detail_parts = []
    for sigungu in found_sigungus:
        detail_parts.append(f"{sigungu}: {', '.join(PARENTS[sigungu])}")
    return {
        "region_sido": "",
        "region_sigungu": found_sigungus[0] if len(found_sigungus) == 1 else "",
        "region_detail": " / ".join(detail_parts),
        "region_status": "ambiguous",
        "found": True,
    }
