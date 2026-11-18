"""RPA 작업 실행기 + 주기 스케줄러.

작업 목록
- trend_collect    : 트렌드 키워드 수집 (네이버 데이터랩 / 랭킹 페이지 / demo)
- product_sourcing : 상위 트렌드 키워드로 도매 상품·이미지 수집
- po_dispatch      : 발주 미배정 주문 -> 발주서 생성, 대기 발주서 자동 발송
"""
import asyncio
import logging
from collections import Counter
import threading
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select

from rpa.sourcing.price_compare import crawl
from rpa.sourcing.wholesale import source_products
from rpa.trend.collector import collect_trends

from ..config import STORAGE_DIR, settings
from ..database import SessionLocal, utcnow
from ..models import PurchaseOrder, RpaJob, RpaLog
from . import catalog, ordering, trends
from .realtime import manager

log = logging.getLogger("fashionpick.rpa")

JOB_DEFAULTS = {
    "trend_collect": {"label": "트렌드 키워드 수집", "interval_minutes": 60},
    "product_sourcing": {"label": "도매 상품·이미지 수집", "interval_minutes": 180},
    "po_dispatch": {"label": "발주서 생성·자동 발송", "interval_minutes": 30},
}
_running: set[str] = set()
_tasks: set[asyncio.Task] = set()
_lock = threading.Lock()


def _trend_collect(db) -> tuple[int, str]:
    rows = collect_trends(settings.rpa_mode, naver_client_id=settings.naver_datalab_client_id,
                          naver_client_secret=settings.naver_datalab_client_secret, targets=settings.trend_scrape_targets,
                          headless=settings.rpa_headless, user_agent=settings.rpa_user_agent, delay=settings.rpa_request_delay)
    _, surges = trends.save_batch(db, rows)
    for s in surges[:5]:
        manager.publish("trend.surge", {"keyword": s["keyword"], "category": s["category"], "rank": s["rank"],
                                        "growth": s["growth"], "rank_change": s["rank_change"]})
    return len(rows), f"키워드 {len(rows)}건 수집, 급상승 {len(surges)}건"


def _product_sourcing(db) -> tuple[int, str]:
    keywords = trends.top_keywords(db, limit=8)
    if not keywords:
        raise RuntimeError("수집된 트렌드 키워드가 없습니다. 트렌드 수집을 먼저 실행하세요.")
    if settings.sourcing_mode == "crawl":
        keywords = trends.latest(db) or keywords  # 전 카테고리 키워드 (카테고리별로 번갈아 수집)
        db.commit()  # 수집(수 분) 동안 DB 연결을 잡고 있지 않도록 반납 → 저장 시 새 연결(pre_ping)으로 재연결
        items = crawl(keywords, sources=settings.crawl_sources, delay=settings.crawl_delay,
                      max_items=settings.crawl_per_keyword, max_total=settings.crawl_max_total)
        if not items:
            raise RuntimeError("다나와·에누리에서 수집된 상품이 없습니다 (차단·구조 변경 확인 필요).")
        created = catalog.save_sourced(db, items, markup=settings.crawl_markup)
        registered = catalog.auto_register_crawled(db, settings.crawl_auto_register)
        by_cat = Counter(i["category"] for i in items)
        detail = ", ".join(f"{c} {n}" for c, n in by_cat.most_common())
        return len(items), (f"다나와·에누리 키워드 {len({i['keyword'] for i in items})}개로 상품 {len(items)}건 수집 "
                            f"(신규 {created}건, 자동 등록 {registered}건) — {detail}")
    items = source_products(keywords, settings.rpa_mode, targets=settings.wholesale_targets, headless=settings.rpa_headless,
                            user_agent=settings.rpa_user_agent, delay=settings.rpa_request_delay,
                            image_dir=STORAGE_DIR / "images")
    created = catalog.save_sourced(db, items)
    return len(items), f"키워드 {len(keywords)}개로 상품 {len(items)}건 수집 (신규 {created}건)"


def _po_dispatch(db) -> tuple[int, str]:
    created = ordering.generate_purchase_orders(db)
    sent, failed = 0, 0
    if settings.auto_send_purchase_order:
        pending = db.scalars(select(PurchaseOrder).where(PurchaseOrder.status == "pending")).all()
        for po in pending:
            if po.supplier.order_method == "manual":
                continue
            try:
                ordering.send_purchase_order(db, po)
                sent += 1
            except HTTPException:
                failed += 1
    if failed:
        raise RuntimeError(f"발주서 생성 {len(created)}건, 발송 {sent}건, 발송 실패 {failed}건")
    return len(created) + sent, f"발주서 생성/갱신 {len(created)}건, 자동 발송 {sent}건"


RUNNERS = {"trend_collect": _trend_collect, "product_sourcing": _product_sourcing, "po_dispatch": _po_dispatch}


def ensure_jobs(db) -> None:
    for name, cfg in JOB_DEFAULTS.items():
        if not db.scalar(select(RpaJob).where(RpaJob.name == name)):
            db.add(RpaJob(name=name, **cfg))
    db.commit()


def run_job(name: str, triggered_by: str = "scheduler") -> RpaLog:
    """작업을 동기 실행하고 로그를 남김 (스레드에서 호출). 같은 작업 중복 실행은 막는다."""
    if name not in RUNNERS:
        raise HTTPException(404, "알 수 없는 RPA 작업입니다.")
    with _lock:
        if name in _running:
            raise HTTPException(409, "이미 실행 중인 작업입니다.")
        _running.add(name)
    db = SessionLocal()
    try:
        job = db.scalar(select(RpaJob).where(RpaJob.name == name))
        entry = RpaLog(job_name=name, triggered_by=triggered_by)
        db.add(entry)
        job.last_status, job.last_run_at = "running", utcnow()
        db.commit()
        manager.publish("rpa.job", {"job": name, "status": "running", "log_id": entry.id}, admin_only=True)
        try:
            count, message = RUNNERS[name](db)
            entry.status, entry.items_count, entry.message = "success", count, message
        except Exception as exc:  # noqa: BLE001 - 실패 로그 기록이 목적
            db.rollback()
            log.exception("RPA 작업 실패: %s", name)
            entry.status, entry.message = "failed", f"{type(exc).__name__}: {exc}"[:2000]
        entry.finished_at = utcnow()
        job = db.scalar(select(RpaJob).where(RpaJob.name == name))
        job.last_status = entry.status
        db.commit()
        manager.publish("rpa.job", {"job": name, "label": job.label, "status": entry.status, "message": entry.message,
                                    "items_count": entry.items_count}, admin_only=True)
        if entry.status == "failed":
            ordering.bot_notify(f"[fashionpick] RPA 작업 실패: {job.label} - {entry.message}")
        return entry
    finally:
        db.close()
        with _lock:
            _running.discard(name)


def crawl_coverage_ok(min_items: int = 200, min_categories: int = 7) -> bool:
    """실제 수집 상품이 충분하고 모든 카테고리가 채워졌는지 (아니면 기동 직후 1회 수집)."""
    from sqlalchemy import func

    from ..models import Product
    real = ~Product.source_url.like("demo://%")
    with SessionLocal() as db:
        total = db.scalar(select(func.count(Product.id)).where(real)) or 0
        cats = db.scalar(select(func.count(func.distinct(Product.category))).where(real)) or 0
    return total >= min_items and cats >= min_categories


def is_running(name: str) -> bool:
    return name in _running


async def scheduler_loop(poll_seconds: int = 30) -> None:
    """주기가 도래한 활성 작업을 백그라운드 스레드에서 실행."""
    while True:
        try:
            db = SessionLocal()
            try:
                now = utcnow()
                due = [j.name for j in db.scalars(select(RpaJob).where(RpaJob.enabled.is_(True))).all()
                       if not is_running(j.name)
                       and (j.last_run_at is None or j.last_run_at + timedelta(minutes=j.interval_minutes) <= now)]
            finally:
                db.close()
            for name in due:
                spawn(name, "scheduler")
        except Exception:  # noqa: BLE001 - 스케줄러 루프는 멈추지 않음
            log.exception("스케줄러 오류")
        await asyncio.sleep(poll_seconds)


def spawn(name: str, triggered_by: str) -> None:
    """이벤트 루프를 막지 않도록 작업을 워커 스레드에서 실행 (실행 중 중복은 무시)."""
    def _run() -> None:
        try:
            run_job(name, triggered_by)
        except HTTPException:
            pass

    task = asyncio.create_task(asyncio.to_thread(_run))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
