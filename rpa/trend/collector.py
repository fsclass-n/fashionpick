"""트렌드 키워드 수집기.

- demo: 시간에 따라 변하는 샘플 트렌드 데이터 (외부 접속 없음)
- live: 네이버 데이터랩 쇼핑인사이트 API + Playwright 랭킹 페이지 수집 (TREND_SCRAPE_TARGETS)
"""
import hashlib
import math
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

from ..common import CATEGORIES, RateLimiter, browser_page, log, robots_allowed

SEED_KEYWORDS: dict[str, list[str]] = {
    "아우터": ["바시티 자켓", "숏패딩", "트렌치코트", "레더 자켓", "발마칸 코트", "플리스 집업", "윈드브레이커"],
    "상의": ["크롭 니트", "오버핏 셔츠", "스트라이프 셔츠", "꽈배기 니트", "후드 티셔츠", "카라 니트", "레이어드 티"],
    "하의": ["와이드 데님", "카고 팬츠", "벌룬 팬츠", "롱 스커트", "버뮤다 팬츠", "부츠컷 데님", "트랙 팬츠"],
    "원피스": ["셔링 원피스", "니트 원피스", "셔츠 원피스", "슬립 원피스", "플리츠 원피스"],
    "슈즈": ["메리제인", "로퍼", "스웨이드 스니커즈", "발레리나 플랫", "어글리 슈즈", "첼시 부츠"],
    "가방": ["스웨이드 숄더백", "버킷백", "미니 크로스백", "토트백", "백팩"],
    "액세서리": ["볼캡", "실버 링", "헤어 클립", "바라클라바", "레그워머", "스카프"],
}

NAVER_CATEGORY_CODE = {"아우터": "50000000", "상의": "50000000", "하의": "50000000", "원피스": "50000000",
                       "슈즈": "50000001", "가방": "50000001", "액세서리": "50000001"}
NAVER_KEYWORD_API = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"


def _stable_noise(text: str) -> float:
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def collect_demo(now: float | None = None) -> list[dict]:
    """키워드별 고유 주기를 갖는 사인파 + 노이즈로 순위가 자연스럽게 변동하는 샘플 데이터."""
    t = (now or time.time()) / 3600
    rng = np.random.default_rng(int(t * 10))
    rows = []
    for category, keywords in SEED_KEYWORDS.items():
        for kw in keywords:
            base = 35 + _stable_noise(kw) * 45
            wave = 18 * math.sin(t / (3 + _stable_noise(kw + "p") * 9) + _stable_noise(kw + "o") * 6)
            rows.append({"keyword": kw, "category": category, "source": "demo",
                         "score": round(float(np.clip(base + wave + rng.normal(0, 3), 1, 100)), 2)})
    return rows


def collect_naver_datalab(client_id: str, client_secret: str, limiter: RateLimiter, days: int = 14) -> list[dict]:
    """쇼핑인사이트 키워드 API는 요청 단위로 정규화(최대 100)되므로,
    카테고리 첫 키워드를 기준(anchor)으로 매 요청에 포함시켜 요청 간 점수를 비교 가능하게 맞춘다."""
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret, "Content-Type": "application/json"}
    end = date.today() - timedelta(days=1)
    rows = []
    for category, keywords in SEED_KEYWORDS.items():
        anchor, others = keywords[0], keywords[1:]
        scores: dict[str, float] = {}
        for i in range(0, max(len(others), 1), 4):
            group = [anchor, *others[i:i + 4]]
            body = {
                "startDate": (end - timedelta(days=days)).isoformat(), "endDate": end.isoformat(), "timeUnit": "date",
                "category": NAVER_CATEGORY_CODE[category],
                "keyword": [{"name": kw, "param": [kw]} for kw in group],
            }
            limiter.wait(NAVER_KEYWORD_API)
            res = requests.post(NAVER_KEYWORD_API, json=body, headers=headers, timeout=15)
            res.raise_for_status()
            means = {r["title"]: float(np.mean([d["ratio"] for d in r["data"][-7:]] or [0])) for r in res.json()["results"]}
            anchor_value = means.get(anchor) or 1.0
            for kw, value in means.items():
                scores[kw] = value / anchor_value * 50
        rows += [{"keyword": kw, "category": category, "source": "naver_datalab", "score": round(min(s, 100), 2)}
                 for kw, s in scores.items()]
    return rows


def collect_ranking_pages(targets: list[dict], headless: bool, user_agent: str, limiter: RateLimiter) -> list[dict]:
    """TREND_SCRAPE_TARGETS에 등록된 랭킹 페이지에서 순위 키워드를 Playwright로 수집."""
    rows = []
    if not targets:
        return rows
    with browser_page(headless, user_agent) as page:
        for target in targets:
            url = target["url"]
            if not robots_allowed(url, user_agent):
                log.warning("robots.txt 차단으로 건너뜀: %s", url)
                continue
            limiter.wait(url)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector(target["item_selector"], timeout=15000)
            texts = [t.strip() for t in page.locator(target["item_selector"]).all_inner_texts() if t.strip()]
            for rank, kw in enumerate(texts[:30], start=1):
                rows.append({"keyword": kw[:100], "category": target.get("category", "상의"),
                             "source": target.get("name", "ranking"), "score": round(100 - (rank - 1) * 3, 2)})
    return rows


def collect_trends(mode: str, *, naver_client_id: str = "", naver_client_secret: str = "", targets: list | None = None,
                   headless: bool = True, user_agent: str = "fashionpick-bot", delay: float = 2.0) -> list[dict]:
    """수집 결과를 (keyword, category) 기준으로 병합하고 점수순 rank를 부여해 반환."""
    if mode != "live":
        rows = collect_demo()
    else:
        limiter = RateLimiter(delay)
        rows = []
        if naver_client_id and naver_client_secret:
            rows += collect_naver_datalab(naver_client_id, naver_client_secret, limiter)
        rows += collect_ranking_pages(targets or [], headless, user_agent, limiter)
        if not rows:
            raise RuntimeError("live 모드 수집 소스가 없습니다. NAVER_DATALAB_* 또는 TREND_SCRAPE_TARGETS를 설정하세요.")

    df = pd.DataFrame(rows)
    df = df[df["category"].isin(CATEGORIES)] if not df.empty else df
    df = (df.groupby(["keyword", "category"], as_index=False)
            .agg(score=("score", "max"), source=("source", lambda s: ",".join(sorted(set(s))))))
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df.to_dict("records")
