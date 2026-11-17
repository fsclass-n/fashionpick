"""쇼핑몰(스토어프런트) 공개 API.

도매가·공급처·마진 같은 운영 정보는 노출하지 않고 판매 등록(registered) 상품만 제공한다.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..models import Order, Product, User
from ..schemas import OrderIn, OrderOut, ShopOrderIn
from ..security import get_current_user
from ..services import ordering, trends

router = APIRouter(prefix="/api", tags=["shop"])

NEW_DAYS = 7
SORTS = {"new", "trend", "price_asc", "price_desc"}


def _trend_map(db: Session) -> dict[str, dict]:
    return {k["keyword"]: k for k in trends.latest(db)}


def shop_item(p: Product, tmap: dict[str, dict]) -> dict:
    t = tmap.get(p.keyword)
    return {
        "id": p.id, "name": p.registered_name or p.name, "category": p.category, "keyword": p.keyword,
        "price": p.sale_price, "image_url": p.image_url, "options": p.options or {},
        "in_stock": p.stock > 0, "stock": min(p.stock, 99),
        "is_new": bool(p.registered_at and p.registered_at >= utcnow() - timedelta(days=NEW_DAYS)),
        "trend_rank": t["rank"] if t else None, "trend_surge": bool(t and t["surge"]),
        "registered_at": (p.registered_at or p.sourced_at).isoformat() + "Z",
    }


def _registered(db: Session) -> list[Product]:
    return db.scalars(select(Product).where(Product.status == "registered")).all()


def _sort(items: list[dict], sort: str) -> list[dict]:
    if sort == "price_asc":
        return sorted(items, key=lambda i: i["price"])
    if sort == "price_desc":
        return sorted(items, key=lambda i: -i["price"])
    if sort == "trend":
        return sorted(items, key=lambda i: (i["trend_rank"] or 10**6, i["registered_at"]))
    return sorted(items, key=lambda i: i["registered_at"], reverse=True)


@router.get("/shop/home")
def home(db: Session = Depends(get_db)):
    tmap = _trend_map(db)
    items = [shop_item(p, tmap) for p in _registered(db)]
    by_cat: dict[str, list[dict]] = {}
    for i in _sort(items, "trend"):
        by_cat.setdefault(i["category"], []).append(i)
    return {
        "trend_keywords": [{"keyword": k["keyword"], "category": k["category"], "rank": k["rank"], "surge": k["surge"],
                            "growth": k["growth"]} for k in list(tmap.values())[:10]],
        "new_arrivals": _sort(items, "new")[:8],
        "trend_picks": [i for i in _sort(items, "trend") if i["trend_rank"]][:8],
        "categories": [{"category": c, "count": len(v), "image_url": v[0]["image_url"]} for c, v in by_cat.items()],
        "lookbook": [{"category": c, "items": v[:3]} for c, v in sorted(by_cat.items(), key=lambda kv: -len(kv[1]))[:3]],
    }


@router.get("/shop/products")
def list_products(category: str | None = None, keyword: str | None = None, q: str | None = None,
                  sort: str = Query("new"), page: int = Query(1, ge=1), size: int = Query(24, ge=1, le=60),
                  db: Session = Depends(get_db)):
    tmap = _trend_map(db)
    items = [shop_item(p, tmap) for p in _registered(db)]
    if category:
        items = [i for i in items if i["category"] == category]
    if keyword:
        items = [i for i in items if i["keyword"] == keyword]
    if q:
        needle = q.strip().lower()
        items = [i for i in items if needle in i["name"].lower() or needle in i["keyword"].lower() or needle in i["category"]]
    items = _sort(items, sort if sort in SORTS else "new")
    return {"total": len(items), "page": page, "size": size, "items": items[(page - 1) * size: page * size]}


@router.get("/shop/products/{product_id}")
def product_detail(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or product.status != "registered":
        raise HTTPException(404, "판매 중인 상품이 아닙니다.")
    tmap = _trend_map(db)
    related = [shop_item(p, tmap) for p in _registered(db) if p.category == product.category and p.id != product.id]
    return {**shop_item(product, tmap), "trend": tmap.get(product.keyword) and {
        k: tmap[product.keyword][k] for k in ("rank", "growth", "surge", "rank_change")}, "related": _sort(related, "trend")[:8]}


@router.post("/shop/orders", response_model=OrderOut, status_code=201)
def place_order(data: ShopOrderIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """회원 주문 -> 공급처별 발주서 자동 생성 파이프라인으로 연결."""
    for item in data.items:
        p = db.get(Product, item.product_id)
        if not p or p.status != "registered":
            raise HTTPException(400, "판매 중이 아닌 상품이 포함되어 있습니다.")
    order = ordering.create_order(db, OrderIn(
        customer_name=data.customer_name or user.name, customer_phone=data.customer_phone, address=data.address,
        channel="web", items=data.items), user_id=user.id)
    return ordering.order_out(order)


@router.get("/me/orders", response_model=list[OrderOut])
def my_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(50)).all()
    return [ordering.order_out(o) for o in rows]
