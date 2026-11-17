import uuid

import pandas as pd
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..models import TrendKeyword

SURGE_THRESHOLD = 0.15


def batch_ids(db: Session, limit: int) -> list[str]:
    rows = db.execute(
        select(TrendKeyword.batch_id, func.max(TrendKeyword.collected_at).label("at"))
        .group_by(TrendKeyword.batch_id).order_by(desc("at")).limit(limit)
    ).all()
    return [r.batch_id for r in rows]


def save_batch(db: Session, rows: list[dict]) -> tuple[str, list[dict]]:
    """수집 결과를 하나의 스냅샷(batch)으로 저장하고 급상승 키워드 목록을 반환."""
    batch_id, now = uuid.uuid4().hex, utcnow()
    db.add_all(TrendKeyword(batch_id=batch_id, collected_at=now, keyword=r["keyword"], category=r["category"],
                            source=r["source"], rank=int(r["rank"]), score=float(r["score"])) for r in rows)
    db.commit()
    surges = [k for k in latest(db) if k["surge"]]
    return batch_id, surges


def _frame(db: Session, ids: list[str]) -> pd.DataFrame:
    if not ids:
        return pd.DataFrame(columns=["batch_id", "keyword", "category", "source", "rank", "score", "collected_at"])
    rows = db.scalars(select(TrendKeyword).where(TrendKeyword.batch_id.in_(ids))).all()
    return pd.DataFrame([{c: getattr(r, c) for c in ("batch_id", "keyword", "category", "source", "rank", "score",
                                                    "collected_at")} for r in rows])


def latest(db: Session, category: str | None = None, limit: int | None = None) -> list[dict]:
    """최신 스냅샷 + 직전 스냅샷 대비 순위 변동/점수 증감률/급상승 여부."""
    ids = batch_ids(db, 2)
    df = _frame(db, ids)
    if df.empty:
        return []
    cur = df[df.batch_id == ids[0]].copy()
    prev = df[df.batch_id == ids[1]][["keyword", "category", "rank", "score"]] if len(ids) > 1 else None
    if prev is not None and not prev.empty:
        cur = cur.merge(prev, on=["keyword", "category"], how="left", suffixes=("", "_prev"))
    else:
        cur["rank_prev"], cur["score_prev"] = float("nan"), float("nan")
    cur["rank_change"] = (cur["rank_prev"] - cur["rank"]).fillna(0).astype(int)
    cur["growth"] = ((cur["score"] - cur["score_prev"]) / cur["score_prev"]).fillna(0).round(4)
    cur["is_new"] = cur["rank_prev"].isna() & (len(ids) > 1)
    cur["surge"] = (cur["growth"] >= SURGE_THRESHOLD) | (cur["rank_change"] >= 5)
    if category:
        cur = cur[cur.category == category]
    cur = cur.sort_values("rank")
    if limit:
        cur = cur.head(limit)
    return [{"keyword": r.keyword, "category": r.category, "source": r.source, "rank": int(r.rank),
             "score": float(r.score), "rank_change": int(r.rank_change), "growth": float(r.growth),
             "is_new": bool(r.is_new), "surge": bool(r.surge), "collected_at": r.collected_at}
            for r in cur.itertuples()]


def history(db: Session, keywords: list[str], batches: int = 24) -> dict:
    df = _frame(db, batch_ids(db, batches))
    if df.empty:
        return {"series": []}
    df = df[df.keyword.isin(keywords)].sort_values("collected_at")
    return {"series": [{"keyword": kw, "points": [{"at": r.collected_at, "score": float(r.score), "rank": int(r.rank)}
                                                 for r in g.itertuples()]} for kw, g in df.groupby("keyword", sort=False)]}


def category_summary(db: Session) -> list[dict]:
    items = latest(db)
    if not items:
        return []
    df = pd.DataFrame(items)
    g = df.groupby("category").agg(score=("score", "sum"), keywords=("keyword", "count"),
                                   surges=("surge", "sum")).reset_index()
    g["share"] = (g["score"] / g["score"].sum()).round(4)
    return [{"category": r.category, "score": round(float(r.score), 2), "share": float(r.share),
             "keywords": int(r.keywords), "surges": int(r.surges)} for r in g.sort_values("score", ascending=False).itertuples()]


def top_keywords(db: Session, limit: int = 10) -> list[dict]:
    return latest(db, limit=limit)
