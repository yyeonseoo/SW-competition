import base64
import os
import time
import uuid
from io import BytesIO
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

from common import clean_text

load_dotenv()

CLOVA_OCR_URL = os.getenv("CLOVA_OCR_URL")
CLOVA_OCR_SECRET = os.getenv("CLOVA_OCR_SECRET")

MAX_OCR_IMAGES = 5
MIN_IMAGE_WIDTH = 300
MIN_IMAGE_HEIGHT = 180

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def extract_image_urls(soup, page_url):
    selectors = [
        ".board_view", ".view_cont", ".view-content", ".board_contents",
        ".editor-content", "article",
    ]
    container = next((soup.select_one(selector) for selector in selectors if soup.select_one(selector)), soup)

    urls = []
    excluded = ["logo", "icon", "button", "header", "footer", "arrow", "captcha", "favicon", "sns"]
    for tag in container.find_all("img"):
        src = (
            tag.get("src")
            or tag.get("data-src")
            or tag.get("data-original")
            or tag.get("data-lazy-src")
        )
        if not src or src.startswith("data:image"):
            continue
        url = urljoin(page_url, src)
        if any(word in url.lower() for word in excluded):
            continue
        if url not in urls:
            urls.append(url)
    return urls[:MAX_OCR_IMAGES]


def call_clova_ocr(image_url, referer_url):
    if not CLOVA_OCR_URL or not CLOVA_OCR_SECRET:
        raise RuntimeError("CLOVA OCR URL 또는 Secret이 설정되지 않았습니다.")

    response = requests.get(
        image_url,
        headers={**HEADERS, "Referer": referer_url},
        timeout=40,
    )
    response.raise_for_status()

    try:
        image = Image.open(BytesIO(response.content))
        image.load()
    except UnidentifiedImageError as error:
        raise ValueError("OCR 이미지를 열 수 없습니다.") from error

    width, height = image.size
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        return ""

    image_format = (image.format or "").lower()
    image_bytes = response.content

    if image_format == "jpeg":
        image_format = "jpg"
    elif image_format not in {"jpg", "png", "bmp", "tif", "tiff"}:
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=95)
        image_bytes = output.getvalue()
        image_format = "jpg"

    payload = {
        "version": "V2",
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "lang": "ko",
        "images": [{
            "format": image_format,
            "name": "kw_notice",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }],
    }

    result = requests.post(
        CLOVA_OCR_URL,
        headers={"Content-Type": "application/json", "X-OCR-SECRET": CLOVA_OCR_SECRET},
        json=payload,
        timeout=90,
    )
    result.raise_for_status()

    fields = []
    for image_result in result.json().get("images", []):
        for field in image_result.get("fields", []):
            confidence = float(field.get("inferConfidence", 0))
            text = field.get("inferText", "")
            if text and confidence >= 0.65:
                vertices = field.get("boundingPoly", {}).get("vertices", [])
                y = min((v.get("y", 0) for v in vertices), default=0)
                x = min((v.get("x", 0) for v in vertices), default=0)
                fields.append((y, x, text))

    fields.sort(key=lambda value: (value[0], value[1]))
    return clean_text(" ".join(value[2] for value in fields))


def ocr_page_images(soup, page_url):
    texts = []
    urls = extract_image_urls(soup, page_url)

    for index, image_url in enumerate(urls, start=1):
        try:
            print(f"     OCR {index}/{len(urls)}: {image_url}")
            text = call_clova_ocr(image_url, page_url)
            if text:
                texts.append(text)
        except Exception as error:
            print(f"     OCR 실패: {error}")

    return clean_text(" ".join(texts)), len(texts)
