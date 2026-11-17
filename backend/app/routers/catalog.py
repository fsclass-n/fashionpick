from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..models import Product, Supplier, User
from ..schemas import ProductOut, ProductRegisterIn, SupplierIn, SupplierOut
from ..security import get_current_user, require_admin
from ..services import catalog

router = APIRouter(prefix="/api", tags=["catalog"])


def _product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "상품을 찾을 수 없습니다.")
    return product


@router.get("/products")
def list_products(status: str | None = None, category: str | None = None, keyword: str | None = None,
                  q: str | None = None, page: int = Query(1, ge=1), size: int = Query(40, ge=1, le=100),
                  db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    query = select(Product)
    if status:
        query = query.where(Product.status == status)
    if category:
        query = query.where(Product.category == category)
    if keyword:
        query = query.where(Product.keyword == keyword)
    if q:
        like = f"%{q}%"
        query = query.where(or_(Product.name.like(like), Product.keyword.like(like), Product.registered_name.like(like)))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Product.sourced_at.desc(), Product.id.desc()).offset((page - 1) * size).limit(size)).all()
    return {"total": total, "page": page, "size": size,
            "items": [ProductOut.model_validate(catalog.product_out(p)) for p in rows]}


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return catalog.product_out(_product(db, product_id))


@router.get("/products/{product_id}/suggest-name")
def suggest_name(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    product = _product(db, product_id)
    return {"name": catalog.suggest_name(db, product), "sale_price": product.sale_price,
            "margin_rate": catalog.margin_rate(product.wholesale_price, product.sale_price)}


@router.post("/products/{product_id}/register", response_model=ProductOut)
def register_product(product_id: int, data: ProductRegisterIn, db: Session = Depends(get_db),
                     _: User = Depends(get_current_user)):
    """원클릭 상품 등록: 이름 미입력 시 트렌드 키워드 기반 추천명 사용."""
    product = _product(db, product_id)
    product.registered_name = data.registered_name or catalog.suggest_name(db, product)
    if data.sale_price:
        if data.sale_price <= product.wholesale_price:
            raise HTTPException(400, "판매가는 도매가보다 높아야 합니다.")
        product.sale_price = data.sale_price
    product.status, product.registered_at = "registered", utcnow()
    db.commit()
    return catalog.product_out(product)


@router.post("/products/{product_id}/unregister", response_model=ProductOut)
def unregister_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    product = _product(db, product_id)
    product.status, product.registered_at = "sourced", None
    db.commit()
    return catalog.product_out(product)


# ---------- 공급처 ----------
@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Supplier).order_by(Supplier.name)).all()


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.scalar(select(Supplier).where(Supplier.name == data.name)):
        raise HTTPException(409, "같은 이름의 공급처가 있습니다.")
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    return supplier


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, data: SupplierIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "공급처를 찾을 수 없습니다.")
    for k, v in data.model_dump().items():
        setattr(supplier, k, v)
    db.commit()
    return supplier


@router.delete("/suppliers/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "공급처를 찾을 수 없습니다.")
    if supplier.products:
        raise HTTPException(400, "상품이 연결된 공급처는 삭제할 수 없습니다.")
    db.delete(supplier)
    db.commit()
