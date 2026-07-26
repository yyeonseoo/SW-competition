import json
import re
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from common import (
    classify_activity_category,
    classify_interest_categories,
    clean_text,
    extract_target_text,
    init_db,
    is_noise_notice,
    is_recent_upload,
    is_staff_hiring_notice,
    normalize_date,
    normalize_target,
    save_activity,
    strip_title_noise,
)
from ocr_utils import ocr_page_images
from regions import extract_region

BASE_URL = "https://www.kw.ac.kr"
LIST_URL_TEMPLATE = (
    "https://www.kw.ac.kr/ko/life/notice.jsp"
    "?srCategoryId=&mode=list&searchKey=1&searchVal=&tpage={page}"
)
SOURCE = "광운대학교"
MAX_PAGES = 10
REQUEST_DELAY = 1.0
# 링커리어(link.py)는 팀원 규칙대로 최근 3일(is_recent_upload 기본값)을 유지하고,
# 광운대 공지는 게시물이 뜸해서 30일(한 달)로 넓힌다.
KW_DAYS_BACK = 7

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def request_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def find_notice_row_text(tag):
    parent = tag
    for _ in range(8):
        parent = parent.parent
        if parent is None:
            break
        text = clean_text(parent.get_text(" ", strip=True))
        if ("작성일" in text or "등록일" in text) and "수정일" in text:
            return text
    return ""


def extract_written_date(row_text):
    match = re.search(
        r"작성일\s+(\d{4}[-./]\d{1,2}[-./]\d{1,2})",
        row_text,
    )
    return normalize_date(match.group(1)) if match else ""


def extract_bracket_category(title):
    """제목 맨 앞 '[카테고리]' 표기를 그대로 게시판 카테고리로 쓴다.
    광운대 공지 목록의 실제 태그(학사/일반/학생/국제학생/국제교류/병무 등)를 놓치지 않고 잡아낸다."""
    match = re.match(r"^\s*\[([^\]]+)\]", title)
    return match.group(1) if match else ""


def infer_board_category(title, row_text):
    bracket = extract_bracket_category(title)
    if bracket:
        return bracket

    for category in ["봉사", "등록/장학", "외부", "학생", "학사", "일반"]:
        if category in row_text:
            return category
    return ""


def collect_recent_notices():
    results = []
    seen = set()

    for page in range(1, MAX_PAGES + 1):
        soup = request_soup(LIST_URL_TEMPLATE.format(page=page))
        page_recent_count = 0

        for tag in soup.find_all("a", href=True):
            href = tag.get("href", "")
            if "BoardMode=view" not in href or "DUID=" not in href:
                continue

            url = urljoin(BASE_URL, href)
            if url in seen:
                continue

            title = strip_title_noise(tag.get_text(" ", strip=True))
            row_text = find_notice_row_text(tag)
            written_date = extract_written_date(row_text)

            if not title or not written_date or not is_recent_upload(written_date, days_back=KW_DAYS_BACK):
                continue

            page_recent_count += 1
            seen.add(url)

            board_category = infer_board_category(title, row_text)

            if is_staff_hiring_notice(title):
                print(f"  → 제외(학교 직원 채용 공고): {title}")
                continue

            if is_noise_notice(title, board_category):
                print(f"  → 제외(학사·행정 공지): {title}")
                continue

            results.append({
                "title": title,
                "url": url,
                "reference_date": written_date,
                "date_basis": "작성일",
                "board_category": board_category,
            })

        if page > 1 and page_recent_count == 0:
            break
        time.sleep(REQUEST_DELAY)

    return results


def extract_body_text(soup):
    selectors = [
        ".board_view", ".view_cont", ".view-content", ".board_contents",
        ".editor-content", "article",
    ]
    container = next((soup.select_one(selector) for selector in selectors if soup.select_one(selector)), soup)
    copy = BeautifulSoup(str(container), "html.parser")

    for tag in copy.find_all(["script", "style", "noscript", "svg", "iframe", "nav", "footer"]):
        tag.decompose()
    for tag in copy.find_all("img"):
        tag.decompose()

    return clean_text(copy.get_text(" ", strip=True))


def analyze_text(title, body_text, board_category):
    combined = clean_text(f"{title} {body_text}")

    # 봉사 게시판은 사용자 확정 규칙에 따라 기타로 고정.
    # 등록/장학 게시판은 활동카테고리 '장학·지원'으로 고정.
    if board_category == "봉사":
        forced = "기타"
    elif board_category == "등록/장학":
        forced = "장학·지원"
    else:
        forced = None
    activity_category, category_found = classify_activity_category(
        combined, forced_category=forced
    )
    interests, interests_found = classify_interest_categories(combined)
    region = extract_region(combined)
    target_raw = extract_target_text(combined)

    missing = []
    if not category_found and forced is None:
        missing.append("활동 카테고리")
    if not interests_found:
        missing.append("관심분야")
    if not region["found"]:
        missing.append("지역")
    if not target_raw:
        missing.append("모집대상")

    return {
        "activity_category": activity_category,
        "interest_categories": interests,
        "region": region,
        "target_raw": target_raw,
        "missing": missing,
    }


def parse_notice(notice):
    soup = request_soup(notice["url"])
    body_text = extract_body_text(soup)

    first = analyze_text(
        notice["title"], body_text, notice.get("board_category", "")
    )

    ocr_text = ""
    ocr_used = 0

    # 네 항목 중 하나라도 제목+본문에서 잡히지 않으면 공지 이미지를 OCR
    if first["missing"]:
        print(f"     OCR 호출 사유: {', '.join(first['missing'])}")
        ocr_text, processed_count = ocr_page_images(soup, notice["url"])
        ocr_used = 1 if processed_count > 0 else 0

    final_body = clean_text(f"{body_text} {ocr_text}")

    # 제목만으로는 못 걸렀지만 본문·OCR까지 합쳐보면 노이즈로 판단되는 경우 여기서 제외한다
    # (예: 포스터 이미지 OCR 결과에 "수강신청"/"행복기숙사(빛솔재)" 등이 나오는 경우).
    combined_for_noise = clean_text(f"{notice['title']} {final_body}")
    board_category = notice.get("board_category", "")
    if is_staff_hiring_notice(combined_for_noise) or is_noise_notice(combined_for_noise, board_category):
        return None

    final = analyze_text(
        notice["title"], final_body, notice.get("board_category", "")
    )

    # OCR 이후에도 지역 표현이 없을 때만 전국/무관으로 최종 확정
    region = final["region"]
    if not region["found"]:
        region = {
            "region_sido": "전국/무관",
            "region_sigungu": "",
            "region_detail": "",
            "region_status": "nationwide",
            "found": False,
        }

    review_required = int(
        bool(final["missing"])
        or region["region_status"] in {"ambiguous", "multiple"}
    )

    return {
        "source": SOURCE,
        "source_section": notice.get("board_category", ""),
        "title": notice["title"],
        "url": notice["url"],
        "activity_category": final["activity_category"],
        "interest_categories": final["interest_categories"],
        "region_sido": region["region_sido"],
        "region_sigungu": region["region_sigungu"],
        "region_detail": region["region_detail"],
        "region_status": region["region_status"],
        "target": normalize_target(final["target_raw"]),
        "target_raw": final["target_raw"],
        "reference_date": notice["reference_date"],
        "date_basis": "작성일",
        "body_text": body_text[:15000],
        "ocr_text": ocr_text[:15000],
        "ocr_used": ocr_used,
        "missing_before_ocr": first["missing"],
        "review_required": review_required,
    }


def main():
    init_db()
    notices = collect_recent_notices()
    print(f"광운대 최근 공지: {len(notices)}개")

    saved, review = [], []
    excluded_after_detail = 0
    for index, notice in enumerate(notices, start=1):
        print(f"[{index}/{len(notices)}] {notice['title']}")
        try:
            item = parse_notice(notice)
            if item is None:
                excluded_after_detail += 1
                print("  → 제외(본문·OCR 확인 후 학사·행정 공지로 판단)")
                continue
            is_new = save_activity(item)
            saved.append(item)
            if item["review_required"]:
                review.append(item)
            print(
                f"  → {'신규' if is_new else '갱신'} / "
                f"{item['activity_category']} / "
                f"{', '.join(item['interest_categories'])} / "
                f"{item['region_detail'] or item['region_sido']} / "
                f"대상: {item['target_raw'] or '확인 필요'}"
            )
        except Exception as error:
            review.append({**notice, "error": str(error)})
            print(f"  → 오류: {error}")
        time.sleep(REQUEST_DELAY)

    pd.DataFrame(saved).to_csv("kw_recent.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(review).to_csv("kw_review.csv", index=False, encoding="utf-8-sig")
    with open("kw_recent.json", "w", encoding="utf-8") as file:
        json.dump(saved, file, ensure_ascii=False, indent=2)

    print(
        f"\n저장 {len(saved)}개 / 검토 필요 {len(review)}개 / "
        f"본문·OCR 확인 후 제외 {excluded_after_detail}개"
    )


if __name__ == "__main__":
    main()
