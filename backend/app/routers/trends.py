from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..models import Order, Product, PurchaseOrder, User
from ..schemas import OrderOut
from ..security import get_current_user
from ..services import ordering, trends

router = APIRouter(prefix="/api", tags=["trends"])


def _ser(items: list[dict]) -> list[dict]:
    return [{**i, "collected_at": i["collected_at"].isoformat() + "Z"} for i in items]


@router.get("/trends/public-top")
def public_top(limit: int = Query(10, le=20), db: Session = Depends(get_db)):
    """로그인 페이지용 실시간 트렌드 TOP N (비로그인 공개)."""
    return _ser(trends.top_keywords(db, limit=limit))


@router.get("/trends/latest")
def latest(category: str | None = None, limit: int | None = Query(None, le=200), db: Session = Depends(get_db),
           _: User = Depends(get_current_user)):
    return _ser(trends.latest(db, category=category, limit=limit))


@router.get("/trends/history")
def history(keywords: str | None = None, batches: int = Query(24, le=168), db: Session = Depends(get_db),
            _: User = Depends(get_current_user)):
    kws = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else [k["keyword"] for k in trends.top_keywords(db, 5)]
    data = trends.history(db, kws, batches)
    for s in data["series"]:
        for p in s["points"]:
            p["at"] = p["at"].isoformat() + "Z"
    return data


@router.get("/trends/categories")
def categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return trends.category_summary(db)


@router.get("/dashboard/summary")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    latest_items = trends.latest(db)
    recent = db.scalars(select(Order).order_by(Order.created_at.desc()).limit(5)).all()
    return {
        "top_keywords": _ser(latest_items[:5]),
        "surge_count": sum(1 for k in latest_items if k["surge"]),
        "products_sourced": db.scalar(select(func.count(Product.id)).where(Product.status == "sourced")),
        "products_registered": db.scalar(select(func.count(Product.id)).where(Product.status == "registered")),
        "orders_today": db.scalar(select(func.count(Order.id)).where(Order.created_at >= today)),
        "revenue_today": db.scalar(select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.created_at >= today)),
        "po_pending": db.scalar(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "pending")),
        "po_sent": db.scalar(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "sent")),
        "recent_orders": [OrderOut.model_validate(ordering.order_out(o)).model_dump(mode="json") for o in recent],
    }
