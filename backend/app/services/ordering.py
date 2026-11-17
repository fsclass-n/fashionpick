"""주문 접수 -> 공급처별 발주서 자동 생성 -> 발송 -> 상태 추적."""
import secrets
from collections import defaultdict
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from rpa.purchase_order.dispatcher import notify, send_email, send_webhook
from rpa.purchase_order.generator import build_excel, build_pdf

from ..config import settings
from ..database import utcnow
from ..models import Order, OrderItem, Product, PurchaseOrder
from ..schemas import OrderIn
from .realtime import manager

KST_OFFSET_HOURS = 9


def _code(prefix: str) -> str:
    return f"{prefix}{utcnow():%Y%m%d}-{secrets.token_hex(3).upper()}"


def bot_notify(text: str) -> None:
    notify(text, telegram_token=settings.telegram_bot_token, telegram_chat_id=settings.telegram_chat_id,
           discord_url=settings.discord_webhook_url)


def order_out(order: Order) -> dict:
    return {**{c.name: getattr(order, c.name) for c in Order.__table__.columns}, "items": order.items}


def po_out(po: PurchaseOrder) -> dict:
    return {**{c.name: getattr(po, c.name) for c in PurchaseOrder.__table__.columns},
            "supplier_name": po.supplier.name, "supplier_method": po.supplier.order_method, "items": po.items}


def create_order(db: Session, data: OrderIn) -> Order:
    order = Order(order_no=_code("FP"), customer_name=data.customer_name, customer_phone=data.customer_phone,
                  address=data.address, channel=data.channel)
    for item in data.items:
        product = db.get(Product, item.product_id)
        if not product:
            raise HTTPException(404, f"상품({item.product_id})을 찾을 수 없습니다.")
        order.items.append(OrderItem(product_id=product.id, product_name=product.registered_name or product.name,
                                     option=item.option, quantity=item.quantity, unit_price=product.sale_price,
                                     wholesale_price=product.wholesale_price))
    order.total_amount = sum(i.unit_price * i.quantity for i in order.items)
    db.add(order)
    db.commit()
    manager.publish("order.created", {"id": order.id, "order_no": order.order_no, "customer_name": order.customer_name,
                                      "total_amount": order.total_amount, "items": len(order.items)})
    bot_notify(f"[fashionpick] 신규 주문 {order.order_no} / {order.customer_name} / {order.total_amount:,}원")

    if settings.auto_purchase_order:
        pos = generate_purchase_orders(db, [order])
        if settings.auto_send_purchase_order:
            for po in pos:
                send_purchase_order(db, po)
    db.refresh(order)
    return order


def generate_purchase_orders(db: Session, orders: list[Order] | None = None) -> list[PurchaseOrder]:
    """발주 미배정 주문상품을 공급처별로 묶어, 공급처의 '대기' 발주서에 합치거나 새로 생성."""
    query = select(OrderItem).where(OrderItem.purchase_order_id.is_(None))
    if orders:
        query = query.where(OrderItem.order_id.in_([o.id for o in orders]))
    grouped: dict[int, list[OrderItem]] = defaultdict(list)
    for item in db.scalars(query).all():
        grouped[item.product.supplier_id].append(item)

    touched: list[PurchaseOrder] = []
    for supplier_id, items in grouped.items():
        po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier_id, PurchaseOrder.status == "pending"))
        if not po:
            po = PurchaseOrder(po_no=_code("PO"), supplier_id=supplier_id)
            db.add(po)
            db.flush()
        for item in items:
            item.purchase_order_id = po.id
            item.order.status = "ordering"
        db.flush()
        db.refresh(po)
        po.total_amount = sum(i.wholesale_price * i.quantity for i in po.items)
        touched.append(po)
    db.commit()
    for po in touched:
        manager.publish("po.created", {"id": po.id, "po_no": po.po_no, "supplier_name": po.supplier.name,
                                       "total_amount": po.total_amount, "items": len(po.items)})
    return touched


def po_document(po: PurchaseOrder) -> dict:
    created_kst = po.created_at.replace(microsecond=0) + timedelta(hours=KST_OFFSET_HOURS)
    s = po.supplier
    return {
        "po_no": po.po_no, "created_at": f"{created_kst:%Y-%m-%d %H:%M} (KST)",
        "template": s.template, "total_amount": po.total_amount, "store": settings.store,
        "supplier": {"name": s.name, "contact_name": s.contact_name, "phone": s.phone, "email": s.email, "address": s.address},
        "items": [{"order_no": i.order.order_no, "product_name": i.product_name, "option": i.option, "quantity": i.quantity,
                   "wholesale_price": i.wholesale_price, "source_url": i.product.source_url} for i in po.items],
    }


def set_status(db: Session, po: PurchaseOrder, status: str, log_line: str = "") -> PurchaseOrder:
    now = utcnow()
    po.status = status
    if status == "sent" and not po.sent_at:
        po.sent_at = now
    if status == "received":
        po.received_at = now
        po.sent_at = po.sent_at or now
    if log_line:
        po.send_log = (po.send_log + "\n" if po.send_log else "") + f"[{now:%Y-%m-%d %H:%M:%S}Z] {log_line}"
    for order in {i.order for i in po.items}:
        statuses = {i.purchase_order.status if i.purchase_order else "none" for i in order.items}
        order.status = ("stocked" if statuses == {"received"} else
                        "ordered" if statuses <= {"sent", "received"} else "ordering")
    db.commit()
    manager.publish("po.updated", {"id": po.id, "po_no": po.po_no, "status": po.status, "supplier_name": po.supplier.name})
    return po


def send_purchase_order(db: Session, po: PurchaseOrder) -> PurchaseOrder:
    """공급처 수신 방식(email/webhook/manual)에 따라 발송. SMTP 미설정 demo 모드는 시뮬레이션 발송."""
    if po.status != "pending":
        raise HTTPException(400, "대기 상태의 발주서만 발송할 수 있습니다.")
    s = po.supplier
    doc = po_document(po)
    subject = f"[{settings.store['name']}] 발주서 {po.po_no}"
    try:
        if s.order_method == "webhook" and s.webhook_url:
            send_webhook(s.webhook_url, {"type": "purchase_order", **doc})
            po.send_channel = "webhook"
            log_line = f"웹훅 발송 완료 -> {s.webhook_url}"
        elif s.order_method == "email" and s.email and settings.smtp["host"]:
            body = f"{s.name} 담당자님,\n\n첨부한 발주서({po.po_no}) 확인 후 출고 부탁드립니다.\n\n{settings.store['name']} 드림"
            send_email(settings.smtp, s.email, subject, body, [
                (f"{po.po_no}.xlsx", build_excel(doc), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                (f"{po.po_no}.pdf", build_pdf(doc), "application/pdf"),
            ])
            po.send_channel = "email"
            log_line = f"이메일 발송 완료 -> {s.email}"
        elif settings.rpa_mode != "live":
            po.send_channel = "simulation"
            log_line = f"[demo] 시뮬레이션 발송 ({s.order_method}) - SMTP/웹훅 미설정"
        else:
            raise RuntimeError(f"발송 불가: 수신 방식 '{s.order_method}' 설정(이메일/웹훅/SMTP)을 확인하세요. 수동 발주는 상태 변경으로 처리합니다.")
    except Exception as exc:  # noqa: BLE001 - 실패 내역을 발주서 로그에 남기고 대기 상태 유지
        po.send_log = (po.send_log + "\n" if po.send_log else "") + f"[{utcnow():%Y-%m-%d %H:%M:%S}Z] 발송 실패: {exc}"
        db.commit()
        manager.publish("po.failed", {"id": po.id, "po_no": po.po_no, "error": str(exc)})
        raise HTTPException(502, f"발주서 발송 실패: {exc}") from exc
    bot_notify(f"[fashionpick] 발주서 {po.po_no} 발송 ({s.name}, {po.total_amount:,}원)")
    return set_status(db, po, "sent", log_line)
