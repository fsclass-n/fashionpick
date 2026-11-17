import hmac
import random
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from rpa.purchase_order.generator import build_excel, build_pdf

from ..config import settings
from ..database import get_db
from ..models import Order, Product, PurchaseOrder, User
from ..schemas import OrderIn, OrderItemIn, OrderOut, PurchaseOrderOut, PurchaseOrderStatusIn
from ..security import require_admin, require_admin_read
from ..services import ordering

router = APIRouter(prefix="/api", tags=["orders"])

SIM_CUSTOMERS = ["김하늘", "이서윤", "박지후", "최도윤", "정하린", "강시우", "조예린", "윤서준"]


@router.get("/orders", response_model=list[OrderOut])
def list_orders(status: str | None = None, limit: int = Query(50, le=200), db: Session = Depends(get_db),
                _: User = Depends(require_admin_read)):
    query = select(Order).order_by(Order.created_at.desc()).limit(limit)
    if status:
        query = query.where(Order.status == status)
    return [ordering.order_out(o) for o in db.scalars(query).all()]


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(data: OrderIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ordering.order_out(ordering.create_order(db, data))


@router.post("/orders/simulate", response_model=OrderOut, status_code=201)
def simulate_order(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """시연용: 등록 상품 중 무작위로 주문을 발생시켜 발주 자동화 흐름을 확인."""
    products = db.scalars(select(Product).where(Product.status == "registered")).all()
    if not products:
        raise HTTPException(400, "등록된 판매 상품이 없습니다. 소싱 페이지에서 상품을 먼저 등록하세요.")
    picks = random.sample(products, min(len(products), random.randint(1, 3)))
    data = OrderIn(customer_name=random.choice(SIM_CUSTOMERS), customer_phone="010-0000-0000", address="서울특별시",
                   channel="simulation", items=[OrderItemIn(
                       product_id=p.id, quantity=random.randint(1, 3),
                       option="/".join(filter(None, [random.choice(p.options.get("colors") or [""]),
                                                     random.choice(p.options.get("sizes") or [""])])))
                       for p in picks])
    return ordering.order_out(ordering.create_order(db, data))


@router.post("/orders/webhook", response_model=OrderOut, status_code=201)
def order_webhook(data: OrderIn, x_webhook_secret: str = Header(default=""), db: Session = Depends(get_db)):
    """외부 쇼핑몰(자사몰·오픈마켓 연동 미들웨어)의 주문 수신 웹훅."""
    if not settings.order_webhook_secret or not hmac.compare_digest(x_webhook_secret, settings.order_webhook_secret):
        raise HTTPException(401, "웹훅 인증 실패")
    return ordering.order_out(ordering.create_order(db, data))


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_read)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "주문을 찾을 수 없습니다.")
    return ordering.order_out(order)


# ---------- 발주서 ----------
def _po(db: Session, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(404, "발주서를 찾을 수 없습니다.")
    return po


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_pos(status: str | None = None, limit: int = Query(100, le=300), db: Session = Depends(get_db),
             _: User = Depends(require_admin_read)):
    query = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).limit(limit)
    if status:
        query = query.where(PurchaseOrder.status == status)
    return [ordering.po_out(p) for p in db.scalars(query).all()]


@router.post("/purchase-orders/generate", response_model=list[PurchaseOrderOut])
def generate_pos(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [ordering.po_out(p) for p in ordering.generate_purchase_orders(db)]


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def get_po(po_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_read)):
    return ordering.po_out(_po(db, po_id))


@router.get("/purchase-orders/{po_id}/preview")
def preview_po(po_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin_read)):
    return ordering.po_document(_po(db, po_id))


@router.get("/purchase-orders/{po_id}/{fmt}")
def download_po(po_id: int, fmt: str, db: Session = Depends(get_db), _: User = Depends(require_admin_read)):
    if fmt not in {"excel", "pdf"}:
        raise HTTPException(404, "지원하지 않는 형식입니다.")
    po = _po(db, po_id)
    doc = ordering.po_document(po)
    data, ext, mime = ((build_excel(doc), "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                       if fmt == "excel" else (build_pdf(doc), "pdf", "application/pdf"))
    filename = f"발주서_{po.supplier.name}_{po.po_no}.{ext}"
    return Response(data, media_type=mime, headers={
        "Content-Disposition": f"attachment; filename=\"{po.po_no}.{ext}\"; filename*=UTF-8''{quote(filename)}"})


@router.post("/purchase-orders/{po_id}/send", response_model=PurchaseOrderOut)
def send_po(po_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ordering.po_out(ordering.send_purchase_order(db, _po(db, po_id)))


@router.patch("/purchase-orders/{po_id}/status", response_model=PurchaseOrderOut)
def update_po_status(po_id: int, data: PurchaseOrderStatusIn, db: Session = Depends(get_db),
                     user: User = Depends(require_admin)):
    po = _po(db, po_id)
    labels = {"pending": "대기", "sent": "발송 완료", "received": "입고 확인"}
    return ordering.po_out(ordering.set_status(db, po, data.status, f"상태 변경 -> {labels[data.status]} ({user.name})"))
