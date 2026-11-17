"""도매 사이트 상품·이미지 수집기.

- demo: 트렌드 키워드 기반 샘플 도매 상품 생성 (이미지는 백엔드 SVG 플레이스홀더)
- live: WHOLESALE_TARGETS에 등록된 도매 사이트 검색 결과를 Playwright로 수집
        (공급처 이용약관·이미지 사용 허락 범위 내에서만 사용)
"""
import hashlib
import random
from pathlib import Path
from urllib.parse import quote, urljoin

import requests

from ..common import RateLimiter, browser_page, log, parse_price, robots_allowed

DEMO_SUPPLIERS = [
    {"name": "동대문 스튜디오 A동", "contact_name": "김도매", "phone": "02-2200-0001", "email": "order-a@example.com",
     "order_method": "email", "address": "서울 중구 장충단로 263"},
    {"name": "신상 셀렉트 도매", "contact_name": "이신상", "phone": "02-2200-0002", "email": "order-b@example.com",
     "order_method": "email", "address": "서울 중구 마장로 3"},
    {"name": "남대문 잡화 도매", "contact_name": "박잡화", "phone": "02-2200-0003", "email": "",
     "order_method": "manual", "address": "서울 중구 남대문시장4길 21"},
]
SUPPLIER_BY_CATEGORY = {"아우터": 0, "상의": 1, "하의": 0, "원피스": 1, "슈즈": 2, "가방": 2, "액세서리": 2}
PRICE_RANGE = {"아우터": (32000, 89000), "상의": (9000, 32000), "하의": (14000, 38000), "원피스": (18000, 45000),
               "슈즈": (19000, 52000), "가방": (15000, 48000), "액세서리": (3000, 15000)}
ADJECTIVES = ["오버핏", "베이직", "빈티지", "모던", "데일리", "프렌치", "유니섹스", "미니멀", "워싱", "소프트"]
COLORS = ["블랙", "아이보리", "그레이", "네이비", "베이지", "브라운", "카키", "버건디", "스카이블루"]
SIZES = {"슈즈": ["230", "240", "250", "260", "270"], "가방": ["FREE"], "액세서리": ["FREE"]}


def demo_products(keywords: list[dict], per_keyword: int = 3) -> list[dict]:
    items = []
    for kw in keywords:
        keyword, category = kw["keyword"], kw["category"]
        for i in range(per_keyword):
            seed = hashlib.md5(f"{keyword}-{i}".encode()).hexdigest()
            rnd = random.Random(seed)
            low, high = PRICE_RANGE.get(category, (10000, 40000))
            supplier = DEMO_SUPPLIERS[SUPPLIER_BY_CATEGORY.get(category, 0)]
            colors = rnd.sample(COLORS, 3)
            items.append({
                "supplier": supplier["name"],
                "name": f"{rnd.choice(ADJECTIVES)} {keyword} {seed[:4].upper()}",
                "category": category,
                "keyword": keyword,
                "wholesale_price": rnd.randrange(low, high, 500),
                "image_url": f"/media/placeholder/{seed[:12]}.svg?label={quote(keyword)}&color={quote(colors[0])}&cat={quote(category)}",
                "image_ratio": rnd.choice([1.0, 1.25, 1.33, 1.5]),
                "source_url": f"demo://wholesale/{seed[:12]}",
                "options": {"colors": colors, "sizes": SIZES.get(category, ["S", "M", "L", "XL"])},
                "stock": rnd.randint(0, 120),
            })
    return items


def _download_image(url: str, dest_dir: Path, user_agent: str, limiter: RateLimiter) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha1(url.encode()).hexdigest()[:20]
    ext = Path(url.split("?")[0]).suffix.lower()
    path = dest_dir / f"{name}{ext if ext in {'.jpg', '.jpeg', '.png', '.webp', '.gif'} else '.jpg'}"
    if not path.exists():
        limiter.wait(url)
        res = requests.get(url, timeout=20, headers={"User-Agent": user_agent})
        res.raise_for_status()
        path.write_bytes(res.content)
    return f"/media/images/{path.name}"


def live_products(keywords: list[dict], targets: list[dict], *, headless: bool, user_agent: str, delay: float,
                  per_keyword: int = 5, image_dir: Path | None = None) -> list[dict]:
    limiter = RateLimiter(delay)
    items: list[dict] = []
    if not targets:
        raise RuntimeError("live 모드 도매 수집 대상이 없습니다. WHOLESALE_TARGETS를 설정하세요.")
    with browser_page(headless, user_agent) as page:
        for target in targets:
            for kw in keywords:
                url = target["search_url"].format(keyword=quote(kw["keyword"]))
                if not robots_allowed(url, user_agent):
                    log.warning("robots.txt 차단으로 건너뜀: %s", url)
                    continue
                limiter.wait(url)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_selector(target["item_selector"], timeout=15000)
                except Exception as exc:  # noqa: BLE001 - 사이트 하나 실패가 전체 작업을 멈추지 않도록
                    log.warning("수집 실패 %s: %s", url, exc)
                    continue
                for card in page.locator(target["item_selector"]).all()[:per_keyword]:
                    def text(sel: str) -> str:
                        loc = card.locator(sel).first
                        return loc.inner_text().strip() if sel and loc.count() else ""

                    def attr(sel: str, name: str) -> str:
                        loc = card.locator(sel).first
                        return (loc.get_attribute(name) or "") if sel and loc.count() else ""

                    image = urljoin(url, attr(target.get("image_selector", "img"), "src"))
                    if image and image_dir:
                        try:
                            image = _download_image(image, image_dir, user_agent, limiter)
                        except requests.RequestException as exc:
                            log.warning("이미지 다운로드 실패 %s: %s", image, exc)
                    name, price = text(target["name_selector"]), parse_price(text(target["price_selector"]))
                    if not name or not price:
                        continue
                    items.append({
                        "supplier": target.get("supplier") or target["name"],
                        "name": name[:255], "category": kw["category"], "keyword": kw["keyword"],
                        "wholesale_price": price, "image_url": image, "image_ratio": 1.25,
                        "source_url": urljoin(url, attr(target.get("link_selector", "a"), "href")) or url,
                        "options": {"colors": [], "sizes": []}, "stock": 0,
                    })
    return items


def source_products(keywords: list[dict], mode: str, *, targets: list | None = None, headless: bool = True,
                    user_agent: str = "fashionpick-bot", delay: float = 2.0, image_dir: Path | None = None) -> list[dict]:
    if mode != "live":
        return demo_products(keywords)
    return live_products(keywords, targets or [], headless=headless, user_agent=user_agent, delay=delay, image_dir=image_dir)
