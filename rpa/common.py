"""RPA 공통 유틸: 요청 간격 제한, robots.txt 확인, Playwright 브라우저 헬퍼."""
import logging
import re
import threading
import time
from contextlib import contextmanager
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

log = logging.getLogger("fashionpick.rpa")

CATEGORIES = ["아우터", "상의", "하의", "원피스", "슈즈", "가방", "액세서리"]


class RateLimiter:
    """같은 도메인에 대해 최소 delay 초 간격으로만 요청하도록 보장."""

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, url: str) -> None:
        host = urlparse(url).netloc
        with self._lock:
            elapsed = time.monotonic() - self._last.get(host, 0)
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self._last[host] = time.monotonic()


_robots_cache: dict[str, RobotFileParser | None] = {}


def robots_allowed(url: str, user_agent: str) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        try:
            res = requests.get(f"{base}/robots.txt", timeout=10, headers={"User-Agent": user_agent})
            parser = RobotFileParser()
            parser.parse(res.text.splitlines() if res.status_code == 200 else [])
            _robots_cache[base] = parser
        except requests.RequestException:
            _robots_cache[base] = None
    parser = _robots_cache[base]
    return True if parser is None else parser.can_fetch(user_agent, url)


@contextmanager
def browser_page(headless: bool, user_agent: str):
    """Playwright Chromium 페이지 (Render Docker 컨테이너에서도 동작하도록 sandbox 옵션 포함)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            context = browser.new_context(user_agent=user_agent, locale="ko-KR")
            yield context.new_page()
        finally:
            browser.close()


def parse_price(text: str | None) -> int:
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else 0
