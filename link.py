import json
import re
import time
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


"""
common.py에서 가져올 함수들
"""

from common import (
    INTEREST_CATEGORIES,
    classify_interest_categories,
    clean_text,
    extract_deadline_date,
    init_db,
    is_recent_upload,
    normalize_date,
    normalize_target,
    save_activity,
    today_kst,
)


SOURCE = "링커리어"
BASE_URL = "https://linkareer.com"

LIST_SOURCES = [
    ("대외활동", "https://linkareer.com/list/activity"),
    ("공모전", "https://linkareer.com/list/contest"),
    ("교육", "https://linkareer.com/list/education"),
]

ALLOWED_TARGETS = {
    "대상 제한 없음",
    "대학생",
    "직장인/일반인",
}

SCROLL_COUNT = 2
MAX_DETAILS_PER_SECTION = 15
REQUEST_DELAY = 1.0


"""
크롬 준비
"""
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130 Safari/537.36"
    )
    return webdriver.Chrome(options=options)

"""
링크 정제
"""
def normalize_activity_url(href):
    """
    /activity/숫자 또는 절대 URL을 정규화한다.
    조건에 맞지 않는 링크는 빈 문자열을 반환한다.
    """
    if not href:
        return ""

    href = href.split("?")[0].split("#")[0].strip()
    full_url = urljoin(BASE_URL, href)

    if re.fullmatch(
        r"https://linkareer\.com/activity/\d+/?",
        full_url,
    ):
        return full_url.rstrip("/")

    return ""

"""
    목록 페이지의 실제 카테고리 제목(h1)을 찾는다.
"""
def find_category_heading(soup, category):
    """
    헤더 메뉴에 있는 '교육', '공모전' 등의 링크가 아니라
    본문 제목을 기준으로 수집 시작점을 잡는다.
    """
    for tag in soup.find_all(["h1", "h2"]):
        if clean_text(tag.get_text(" ", strip=True)) == category:
            return tag

    return None


def collect_links(driver, category, list_url):
    """
    현재 페이지의 공고를 수집하고,
    목표 개수에 못 미치면 다음 페이지로 이동한다.

    페이지 번호가 화면에 없으면 > 버튼을 눌러
    다음 페이지 번호 묶음을 연다.
    """

    driver.get(list_url)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "h1")
        )
    )

    links = []
    seen = set()
    current_page = 1

    while len(links) < MAX_DETAILS_PER_SECTION:
        print(
            f"  {category} {current_page}페이지 확인 중"
        )

        # 현재 페이지에서 필요한 내용이 로딩되도록
        # 페이지 아래쪽까지 이동
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(1.5)

        soup = BeautifulSoup(
            driver.page_source,
            "html.parser",
        )

        heading = find_category_heading(
            soup,
            category,
        )

        if heading is None:
            print(
                f"  → {category} 본문 제목을 찾지 못했습니다."
            )
            break

        before_count = len(links)

        # 현재 카테고리 제목 이후의 요소만 확인
        for element in heading.next_elements:
            if not isinstance(element, Tag):
                continue

            if element.name != "a":
                continue

            url = normalize_activity_url(
                element.get("href", "")
            )

            if not url:
                continue

            if url in seen:
                continue

            seen.add(url)
            links.append(url)

            if len(links) >= MAX_DETAILS_PER_SECTION:
                break

        added_count = len(links) - before_count

        print(
            f"  → 현재 페이지에서 "
            f"새 공고 {added_count}개 수집"
        )

        # 목표 개수만큼 모았으면 종료
        if len(links) >= MAX_DETAILS_PER_SECTION:
            break

        next_page = current_page + 1

        # 다음 페이지 번호를 직접 클릭
        clicked = click_page_number(
            driver,
            next_page,
        )

        # 다음 번호가 현재 번호 묶음에 없으면
        # 오른쪽 > 버튼을 눌러 다음 번호 묶음을 연다.
        if not clicked:
            group_moved = click_next_page_group(
                driver
            )

            if not group_moved:
                print(
                    "  → 다음 페이지 번호와 "
                    "> 버튼을 찾지 못했습니다."
                )
                break

            time.sleep(1.5)

            # 새 번호 묶음이 열린 뒤 다시 번호 클릭
            clicked = click_page_number(
                driver,
                next_page,
            )

        if not clicked:
            print(
                f"  → {next_page}페이지를 "
                "클릭하지 못했습니다."
            )
            break

        current_page = next_page
        time.sleep(2)

    return [
        {
            "activity_category": category,
            "source_section": category,
            "url": url,
        }
        for url in links
    ]

def click_page_number(driver, page_number):
    """
    화면에 표시된 페이지 번호를 찾아 클릭한다.
    """

    page_text = str(page_number)

    xpath_candidates = [
        f"//button[normalize-space(.)='{page_text}']",
        f"//a[normalize-space(.)='{page_text}']",
        (
            f"//*[@role='button' "
            f"and normalize-space(.)='{page_text}']"
        ),
    ]

    for xpath in xpath_candidates:
        elements = driver.find_elements(
            By.XPATH,
            xpath,
        )

        for element in elements:
            try:
                if not element.is_displayed():
                    continue

                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        block: 'center'
                    });
                    """,
                    element,
                )

                time.sleep(0.5)

                driver.execute_script(
                    "arguments[0].click();",
                    element,
                )

                return True

            except Exception:
                continue

    return False

def click_next_page_group(driver):
    """
    페이지 번호 묶음 오른쪽의 > 버튼을 클릭한다.

    예:
    1 2 3 4 5 6 7 8 9 10 >
    에서 >를 누르면
    11 12 13 ... 번호 묶음으로 넘어간다.
    """

    xpath_candidates = [
        "//button[normalize-space(.)='>']",
        "//a[normalize-space(.)='>']",
        (
            "//*[@role='button' "
            "and normalize-space(.)='>']"
        ),

        # 화면에는 >로 보여도 HTML에는 ›로 저장된 경우
        "//button[normalize-space(.)='›']",
        "//a[normalize-space(.)='›']",
        (
            "//*[@role='button' "
            "and normalize-space(.)='›']"
        ),
    ]

    for xpath in xpath_candidates:
        elements = driver.find_elements(
            By.XPATH,
            xpath,
        )

        for element in elements:
            try:
                if not element.is_displayed():
                    continue

                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        block: 'center'
                    });
                    """,
                    element,
                )

                time.sleep(0.5)

                driver.execute_script(
                    "arguments[0].click();",
                    element,
                )

                return True

            except Exception:
                continue

    return False

"""
상단 요약정보에서 특정 항목의 값을 뽑는 함수
"""

def extract_value(text, labels, end_labels):
    text = clean_text(text)

    label_pattern = "|".join(
        re.escape(value) for value in labels
    )
    end_pattern = "|".join(
        re.escape(value) for value in end_labels
    )

    match = re.search(
        rf"(?:{label_pattern})\s*[:：\-]?\s*"
        rf"(.{{1,600}}?)"
        rf"(?=(?:{end_pattern})\s*[:：\-]?|$)",
        text,
        flags=re.IGNORECASE,
    )

    return clean_text(match.group(1)) if match else ""

"""
    상세페이지의 상단 구조화 정보만 추출한다.
"""
def extract_top_summary_text(page_text):

    page_text = clean_text(page_text)

    start_keywords = [
        "기업형태",
        "교육분야",
        "참여대상",
        "접수기간",
    ]
    end_keywords = [
        "공유하기",
        "홈페이지 지원",
        "상세내용",
        "팀원 모집 NEW",
    ]

    start_positions = [
        page_text.find(keyword)
        for keyword in start_keywords
        if page_text.find(keyword) != -1
    ]

    if not start_positions:
        return ""

    start = min(start_positions)
    end = len(page_text)

    for keyword in end_keywords:
        position = page_text.find(keyword, start)
        if position != -1:
            end = min(end, position)

    return clean_text(page_text[start:end])


def extract_detail_text(page_text):
    """
    상세내용 이후 실제 공고 본문만 추출한다.
    추천 공고, 합격자료, 후기 등은 제외한다.
    """
    page_text = clean_text(page_text)
    start = page_text.find("상세내용")

    if start == -1:
        return ""

    second_start = page_text.find(
        "상세내용",
        start + len("상세내용"),
    )

    if second_start != -1:
        start = second_start

    start += len("상세내용")
    end = len(page_text)

    stop_keywords = [
        "허위·과장·오류 내용이 있다면 신고해주세요",
        "지원서 다운로드",
        "이 공고를 스크랩한 사용자들이 궁금하다면",
        "이 활동에 관심을 가지는 사용자",
        "팀원 모집 팀원을 모아 공고에 지원해보세요",
        "합격스펙 & 합격자소서",
        "최종합격후기",
        "담당자 Q&A",
        "이 공고 조회자가 많이 본 공고",
    ]

    for keyword in stop_keywords:
        position = page_text.find(keyword, start)
        if position != -1:
            end = min(end, position)

    return clean_text(page_text[start:end])

"""
접수 시작일 추출
"""
def extract_start_date(summary_text):
    patterns = [
        (
            r"접수기간\s*시작일\s*[:：\-]?\s*"
            r"(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2})"
        ),
        (
            r"시작일\s*[:：\-]?\s*"
            r"(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2})"
        ),
        (
            r"접수시작\s*[:：\-]?\s*"
            r"(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2})"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            summary_text,
            flags=re.IGNORECASE,
        )

        if match:
            value = normalize_date(match.group(1))
            if value:
                return value

    return ""


def extract_application_deadline(summary_text):
    """링커리어 상단의 '접수기간' 블록 안에서만 마감일을 읽는다.

    뒤에 이어지는 '활동기간 시작일/마감일'과 섞이지 않도록 접수기간부터
    활동기간 직전까지만 검색한다.
    """
    start = summary_text.find("접수기간")
    if start == -1:
        return ""
    end = summary_text.find("활동기간", start)
    segment = summary_text[start:end if end != -1 else len(summary_text)]
    match = re.search(
        r"마감일\s*[:：\-]?\s*(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2})",
        segment,
        flags=re.IGNORECASE,
    )
    return normalize_date(match.group(1)) if match else ""


def normalize_linkareer_target(raw_target):
    """
    링커리어 상단 참여대상을 표준값으로 정리한다.
    """
    text = clean_text(raw_target)
    compact = re.sub(r"\s+", "", text)

    if not compact:
        return ""

    if "청소년" in compact:
        return "청소년"

    if any(
        value in compact
        for value in [
            "대상제한없음",
            "제한없음",
            "누구나",
            "전국민",
        ]
    ):
        return "대상 제한 없음"

    if any(
        value in compact
        for value in [
            "대학생",
            "대학(원)생",
            "대학원생",
            "재학생",
            "휴학생",
        ]
    ):
        return "대학생"

    if any(
        value in compact
        for value in [
            "직장인/일반인",
            "직장인",
            "일반인",
            "재직자",
        ]
    ):
        return "직장인/일반인"

    return text


def extract_linkareer_target(
    activity_category,
    summary_text,
):
    """
    대외활동·공모전은 상단 참여대상을 사용한다.
    교육은 참여대상 항목이 없으므로 관계없이 대상 제한 없음으로 처리한다.
    """
    if activity_category == "교육":
        return "대상 제한 없음"

    raw_target = extract_value(
        summary_text,
        ["참여대상"],
        [
            "시상규모",
            "접수기간",
            "활동기간",
            "활동지역",
            "관심분야",
            "홈페이지",
            "활동혜택",
            "공모분야",
            "교육분야",
            "추가혜택",
        ],
    )

    return normalize_linkareer_target(raw_target)


def extract_activity_interests(summary_text):
    """
    대외활동은 링커리어 상단 관심분야만 사용한다.
    """
    raw = extract_value(
        summary_text,
        ["관심분야"],
        [
            "활동분야",
            "참여대상",
            "접수기간",
            "활동기간",
            "활동지역",
            "모집인원",
            "홈페이지",
            "활동혜택",
        ],
    )

    found = []

    for category in INTEREST_CATEGORIES:
        if category == "기타":
            continue

        if category in raw:
            found.append(category)

    return list(dict.fromkeys(found))



def detect_category_from_active_tab(
    soup,
    fallback_category,
):
    """
    상세페이지에서 data-active="active"가 붙은
    대외활동·교육·공모전 탭을 찾아 실제 카테고리를 반환한다.
    """

    active_link = soup.select_one(
        'li.nav-menu-item[data-active="active"] '
        'a[href="/list/activity"], '
        'li.nav-menu-item[data-active="active"] '
        'a[href="/list/education"], '
        'li.nav-menu-item[data-active="active"] '
        'a[href="/list/contest"]'
    )

    if active_link is None:
        return fallback_category

    href = active_link.get(
        "href",
        "",
    )

    category_by_href = {
        "/list/activity": "대외활동",
        "/list/education": "교육",
        "/list/contest": "공모전",
    }

    return category_by_href.get(
        href,
        fallback_category,
    )


def parse_detail(driver, seed):
    driver.get(seed["url"])

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )
    time.sleep(0.8)

    soup = BeautifulSoup(
        driver.page_source,
        "html.parser",
    )

    page_text = clean_text(
        soup.get_text(" ", strip=True)
    )

    title_tag = soup.find("h1")
    title = (
        clean_text(
            title_tag.get_text(
                " ",
                strip=True,
            )
        )
        if title_tag
        else ""
    )

    summary_text = extract_top_summary_text(
        page_text
    )
    detail_text = extract_detail_text(
        page_text
    )

    activity_category = (
        detect_category_from_active_tab(
            soup=soup,
            fallback_category=seed[
                "activity_category"
            ],
        )
    )

    print(
    "     [카테고리 확인] "
    f"목록={seed['activity_category']} / "
    f"상세={activity_category}"
)

    start_date = extract_start_date(
        summary_text
    )
    deadline_date = extract_application_deadline(summary_text)

    target_raw = extract_linkareer_target(
        activity_category,
        summary_text,
    )

    if activity_category == "대외활동":
        interests = extract_activity_interests(
            summary_text
        )

        if not interests:
            interests = ["기타"]

    else:
        interests, _ = (
            classify_interest_categories(
                clean_text(
                    f"{title} {detail_text}"
                )
            )
        )

    return {
        "source": SOURCE,
        "source_section": seed[
            "source_section"
        ],
        "title": title,
        "url": seed["url"],
        "activity_category": (
            activity_category
        ),
        "interest_categories": interests,
        "region_sido": "전국/무관",
        "region_sigungu": "",
        "region_detail": "",
        "region_status": "nationwide",
        "target": normalize_target(
            target_raw
        ),
        "target_raw": target_raw,
        "reference_date": start_date or deadline_date,
        "date_basis": "시작일" if start_date else "마감일",
        "application_start_date": start_date,
        "application_end_date": deadline_date,
        "deadline_date": deadline_date,
        "body_text": clean_text(
            f"[링커리어 상단 정보] {summary_text} [상세내용] {detail_text}"
        )[:15000],
        "ocr_text": "",
        "ocr_used": 0,
        "missing_before_ocr": [],
        "review_required": 0,
    }


def deduplicate_seeds(seeds):
    """
    같은 URL은 하나만 남긴다.
    실제 카테고리는 상세페이지에서 확인한다.
    """

    unique = {}

    for seed in seeds:
        url = seed["url"]

        if url not in unique:
            unique[url] = seed

    return list(unique.values())


def main():
    init_db()
    driver = setup_driver()
    seeds = []

    saved = []
    old_count = 0
    excluded_target_count = 0
    no_start_date_count = 0
    error_count = 0

    try:
        for category, list_url in LIST_SOURCES:
            section_links = collect_links(
                driver,
                category,
                list_url,
            )

            print(
                f"{category}: 실제 목록 공고 "
                f"{len(section_links)}개"
            )

            seeds.extend(section_links)

        seeds = deduplicate_seeds(seeds)

        print(
            f"\n검사할 중복 제거 링크: "
            f"{len(seeds)}개\n"
        )

        for index, seed in enumerate(
            seeds,
            start=1,
        ):
            print(
                f"[{index}/{len(seeds)}] "
                f"[{seed['activity_category']}] "
                f"{seed['url']}"
            )

            try:
                item = parse_detail(
                    driver,
                    seed,
                )

                if (
                    item["activity_category"]
                    != seed["activity_category"]
                ):
                    print(
                        "  → 상세페이지 기준 카테고리 수정: "
                        f"{seed['activity_category']} "
                        f"→ {item['activity_category']}"
                    )

                # 교육은 반드시 전체 참여 가능으로 고정한다.
                if item["activity_category"] == "교육":
                    item["target_raw"] = "대상 제한 없음"
                    item["target"] = normalize_target(
                        "대상 제한 없음"
                    )

                if item["target_raw"] not in ALLOWED_TARGETS:
                    excluded_target_count += 1
                    print(
                        "  → 참여대상 제외: "
                        f"{item['target_raw'] or '추출 실패'}"
                    )
                    continue

                if not item["reference_date"]:
                    no_start_date_count += 1
                    print(
                        "  → 제외: 시작일 추출 실패"
                    )
                    continue

                deadline_date = item.get("deadline_date") or ""
                is_active = (
                    deadline_date >= today_kst().isoformat()
                    if deadline_date
                    else is_recent_upload(item["reference_date"], days_back=14)
                )
                if not is_active:
                    old_count += 1
                    print(
                        "  → 기간 제외(기준일): "
                        f"{item['reference_date']}"
                    )
                    continue

                is_new = save_activity(item)
                saved.append(item)

                print(
                    f"  → "
                    f"{'신규 저장' if is_new else '기존 공고 갱신'}"
                )
                print(
                    f"     제목: {item['title']}"
                )
                print(
                    f"     카테고리: "
                    f"{item['activity_category']}"
                )
                print(
                    f"     참여대상: "
                    f"{item['target_raw']}"
                )
                print(
                    f"     관심분야: "
                    f"{', '.join(item['interest_categories'])}"
                )
                print(
                    f"     시작일: "
                    f"{item['reference_date']}"
                )

            except Exception as error:
                error_count += 1
                print(
                    f"  → 오류: {error}"
                )

            time.sleep(REQUEST_DELAY)

    finally:
        driver.quit()

    pd.DataFrame(saved).to_csv(
        "linkareer_recent.csv",
        index=False,
        encoding="utf-8-sig",
    )

    with open(
        "linkareer_recent.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            saved,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("\n===== 실행 결과 =====")
    print(
        f"최근 시작 공고 저장: {len(saved)}개"
    )
    print(
        f"참여대상 제외: "
        f"{excluded_target_count}개"
    )
    print(
        f"기간 제외: {old_count}개"
    )
    print(
        f"시작일 추출 실패: "
        f"{no_start_date_count}개"
    )
    print(
        f"기타 오류: {error_count}개"
    )
    print(
        "생성 파일: "
        "linkareer_recent.csv, "
        "linkareer_recent.json, "
        "recommendation.db"
    )


if __name__ == "__main__":
    main()
