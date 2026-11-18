"""도매 수집 상품 저장, 판매가·마진 계산, 트렌드 기반 상품명 추천."""
import math
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import utcnow
from ..models import Product, Supplier
from . import trends


def suggest_sale_price(wholesale: int, markup: float | None = None) -> int:
    """도매가 x 배수를 천 원 단위로 올린 뒤 900원 엔딩 (예: 39,500 x 2.2 = 86,900 -> 86,900)."""
    raw = wholesale * (markup or settings.default_markup)
    return max(int(math.ceil(raw / 1000) * 1000 - 100), wholesale + 1000)


def margin_rate(wholesale: int, sale: int) -> float:
    return round((sale - wholesale) / sale, 4) if sale else 0.0


def season_tag(month: int | None = None) -> str:
    month = month or utcnow().month
    return "SS" if 3 <= month <= 8 else "FW"


def suggest_name(db: Session, product: Product) -> str:
    """상품 원래 키워드 + 같은 카테고리 상위 트렌드 키워드를 조합한 검색 친화형 상품명."""
    related = [k["keyword"] for k in trends.latest(db, category=product.category, limit=3) if k["keyword"] != product.keyword]
    base = " ".join(w for w in product.name.split() if not re.fullmatch(r"[0-9A-F]{4}", w))
    parts = [f"[{season_tag()}]", base]
    if product.keyword and product.keyword not in base:
        parts.append(product.keyword)
    if related:
        parts.append(f"{related[0]} 무드")
    return " ".join(parts)[:255]


def get_or_create_supplier(db: Session, name: str, **fields) -> Supplier:
    supplier = db.scalar(select(Supplier).where(Supplier.name == name))
    if not supplier:
        supplier = Supplier(name=name, **{k: v for k, v in fields.items() if hasattr(Supplier, k)})
        db.add(supplier)
        db.flush()
    return supplier


def save_sourced(db: Session, items: list[dict], markup: float | None = None) -> int:
    """source_url 기준 중복은 가격·재고·이미지만 갱신하고 신규만 추가. 신규 건수 반환."""
    created = 0
    for item in items:
        supplier = get_or_create_supplier(db, item["supplier"])
        product = db.scalar(select(Product).where(Product.supplier_id == supplier.id, Product.source_url == item["source_url"]))
        if product:
            product.wholesale_price, product.stock, product.image_url = item["wholesale_price"], item["stock"], item["image_url"]
            if product.status == "sourced":
                product.sale_price = suggest_sale_price(item["wholesale_price"], markup)
            continue
        db.add(Product(
            supplier_id=supplier.id, name=item["name"], category=item["category"], keyword=item["keyword"],
            wholesale_price=item["wholesale_price"], sale_price=suggest_sale_price(item["wholesale_price"], markup),
            image_url=item["image_url"], image_ratio=item.get("image_ratio", 1.25), source_url=item["source_url"],
            options=item.get("options") or {}, stock=item.get("stock", 0),
        ))
        created += 1
    db.commit()
    return created


def auto_register_crawled(db: Session, limit: int) -> int:
    """크롤링 상품을 카테고리별로 고르게(카테고리당 limit/카테고리 수) 판매 등록한다 (원래 상품명 유지)."""
    real = ~Product.source_url.like("demo://%")
    cats = [c for (c,) in db.execute(select(Product.category).where(real).distinct()).all()]
    if not cats:
        return 0
    per_cat = max(1, -(-limit // len(cats)))
    done = 0
    for cat in cats:
        have = db.scalar(select(func.count(Product.id)).where(real, Product.category == cat, Product.status == "registered")) or 0
        rows = db.scalars(select(Product).where(real, Product.category == cat, Product.status == "sourced")
                          .order_by(Product.sourced_at.desc(), Product.id).limit(max(0, per_cat - have))).all()
        for p in rows:
            p.status, p.registered_at, p.registered_name = "registered", utcnow(), p.name
        done += len(rows)
    db.commit()
    return done


def product_out(p: Product) -> dict:
    return {**{c.name: getattr(p, c.name) for c in Product.__table__.columns},
            "supplier_name": p.supplier.name if p.supplier else "", "margin_rate": margin_rate(p.wholesale_price, p.sale_price)}
