"""다나와 · 에누리 패션 검색 결과 수집기 (requests + BeautifulSoup, Playwright 미사용 — Render 무료 인스턴스 자원 고려).

수집 한계(의도적으로 제한)
- robots.txt 를 확인하고 Crawl-delay 를 지킨다 (search.danawa.com 10초, price.enuri.com 1초) — 설정 간격과 비교해 더 긴 값 사용
- 1회 실행당 키워드 최대 MAX_KEYWORDS 개, 키워드·사이트당 상품 최대 MAX_ITEMS 개
- 검색 결과 HTML 1페이지만 읽고 상세 페이지·API(/api/*, /list/ajax/)는 호출하지 않는다
- 이미지는 내려받지 않고 원본 URL 과 출처 링크만 저장한다 (화면에 출처 표시)
"""
import re
from urllib.parse import quote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from ..common import RateLimiter, log

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 fashionpick-bot/1.0"
MAX_KEYWORDS, MAX_ITEMS, TIMEOUT = 6, 5, 15
SOURCES = {
    "danawa": {"label": "다나와", "search": "https://search.danawa.com/?query={q}"},
    "enuri": {"label": "에누리", "search": "https://price.enuri.com/search?keyword={q}"},
}
PRICE_RE = re.compile(r"([\d]{1,3}(?:,\d{3})+|\d{4,})\s*원")
_robots: dict[str, RobotFileParser] = {}


def _robot(url: str) -> RobotFileParser:
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    if base not in _robots:
        rp = RobotFileParser()
        try:
            res = requests.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=TIMEOUT)
            rp.parse(res.text.splitlines() if res.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[base] = rp
    return _robots[base]


def _price(text: str) -> int:
    nums = [int(m.replace(",", "")) for m in PRICE_RE.findall(text)]
    nums = [n for n in nums if 1000 <= n <= 5_000_000]
    return min(nums) if nums else 0


def _img(tag) -> str:
    img = tag.find("img") if tag else None
    if not img:
        return ""
    src = img.get("data-src") or img.get("data-original") or img.get("src") or ""
    if src.startswith("//"):
        src = "https:" + src
    return "" if src.startswith("data:") else src


SKIP_NAMES = {"이미지 보기", "상품 보기", "가격비교", "최저가", "리뷰"}


def parse_danawa(html: str, base: str) -> list[dict]:
    soup, items, seen = BeautifulSoup(html, "html.parser"), [], set()
    names: dict[str, str] = {}
    for a in soup.select("a[href*='prod.danawa.com/info/?pcode=']"):
        m = re.search(r"pcode=(\d+)", a["href"])
        t = a.get_text(" ", strip=True)
        if m and t not in SKIP_NAMES and len(t) > len(names.get(m.group(1), "")):
            names[m.group(1)] = t
    for a in soup.select("a[href*='prod.danawa.com/info/?pcode=']"):
        pcode = re.search(r"pcode=(\d+)", a["href"])
        if not pcode or pcode.group(1) in seen:
            continue
        card = a
        for _ in range(6):  # 상품 이름·가격·이미지를 함께 가진 가장 가까운 조상
            card = card.parent
            if card is None:
                break
            if card.find("img") and PRICE_RE.search(card.get_text(" ", strip=True)):
                break
        if card is None:
            continue
        img = card.find("img")
        name = (names.get(pcode.group(1)) or (img.get("alt", "") if img else "")).strip()
        price, image = _price(card.get_text(" ", strip=True)), _img(card)
        if len(name) < 4 or not price or not image:
            continue
        seen.add(pcode.group(1))
        items.append({"name": name[:200], "price": price, "image_url": image, "source_url": urljoin(base, a["href"].split("&keyword")[0])})
    return items


def parse_enuri(html: str, base: str) -> list[dict]:
    soup, items = BeautifulSoup(html, "html.parser"), []
    for card in soup.select("[class*='productCard']"):
        name_el = card.select_one("[class*='productName']") or card.select_one("[class*='productTitle']")
        link = card.find("a", href=True)
        name = name_el.get_text(" ", strip=True) if name_el else ""
        price, image = _price(card.get_text(" ", strip=True)), _img(card)
        if len(name) < 4 or not price or not image or not link:
            continue
        items.append({"name": name[:200], "price": price, "image_url": image, "source_url": urljoin(base, link["href"])})
    return items


PARSERS = {"danawa": parse_danawa, "enuri": parse_enuri}


def crawl(keywords: list[dict], sources=("danawa", "enuri"), delay: float = 3.0, max_keywords=MAX_KEYWORDS,
          max_items=MAX_ITEMS) -> list[dict]:
    """keywords: [{keyword, category}] → 공통 상품 dict 목록 (wholesale.py 와 같은 형식)."""
    limiter, out = RateLimiter(delay), []
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    for kw in keywords[:max_keywords]:
        for src in sources:
            conf = SOURCES[src]
            url = conf["search"].format(q=quote(kw["keyword"]))
            rp = _robot(url)
            if not rp.can_fetch(UA, url):
                log.warning("robots.txt 차단으로 건너뜀: %s", url)
                continue
            limiter.delay = max(delay, float(rp.crawl_delay(UA) or 0))
            limiter.wait(url)
            try:
                res = session.get(url, timeout=TIMEOUT, allow_redirects=True)
                res.raise_for_status()
            except requests.RequestException as exc:
                log.warning("%s 수집 실패 (%s): %s", conf["label"], kw["keyword"], exc)
                continue
            for it in PARSERS[src](res.text, res.url)[:max_items]:
                out.append({
                    "supplier": conf["label"], "name": it["name"], "category": kw["category"], "keyword": kw["keyword"],
                    "wholesale_price": it["price"], "image_url": it["image_url"], "image_ratio": 1.0,
                    "source_url": it["source_url"], "options": {"colors": [], "sizes": ["FREE"]}, "stock": 10,
                })
    return out
