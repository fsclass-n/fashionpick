"""최초 실행 시 테스트 계정·공급처·RPA 작업·데모 데이터 초기화 (기존 데이터는 유지)."""
import random
import time
import uuid
from datetime import timedelta

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rpa.sourcing.wholesale import DEMO_SUPPLIERS, demo_products
from rpa.trend.collector import collect_demo

from ..config import settings
from ..database import utcnow
from ..models import Order, Product, TrendKeyword, User
from ..schemas import OrderIn, OrderItemIn
from ..security import TEST_ADMIN, hash_password
from . import catalog, ordering, trends
from .rpa_jobs import ensure_jobs


def seed_users(db: Session) -> None:
    """테스트 계정 보장. 테스트 관리자 계정은 비밀번호가 공개되어 있으므로 매 기동 시 읽기 전용 권한으로 고정."""
    for email, name, role, password in (
        (settings.test_user_email, "테스트 회원", "user", settings.test_user_password),
        (settings.test_admin_email, "테스트 관리자", TEST_ADMIN, settings.test_admin_password),
    ):
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            db.add(User(email=email, name=name, role=role, password_hash=hash_password(password)))
        else:
            user.name = name
            if role == TEST_ADMIN:
                user.role = TEST_ADMIN
    db.commit()


def seed_demo_data(db: Session) -> None:
    if not db.scalar(select(func.count(TrendKeyword.id))):
        now, base = time.time(), utcnow()
        for h in range(24, 0, -1):
            df = pd.DataFrame(collect_demo(now - h * 3600)).sort_values("score", ascending=False).reset_index(drop=True)
            batch, at = uuid.uuid4().hex, base - timedelta(hours=h)
            db.add_all(TrendKeyword(batch_id=batch, collected_at=at, keyword=r.keyword, category=r.category,
                                    source=r.source, rank=i + 1, score=float(r.score)) for i, r in enumerate(df.itertuples()))
        db.commit()

    if not db.scalar(select(func.count(Product.id))):
        for s in DEMO_SUPPLIERS:
            catalog.get_or_create_supplier(db, **s)
        db.commit()
        catalog.save_sourced(db, demo_products(trends.top_keywords(db, limit=16)))
        rnd = random.Random(7)
        for p in rnd.sample(db.scalars(select(Product)).all(), 12):
            p.status, p.registered_at, p.registered_name = "registered", utcnow(), catalog.suggest_name(db, p)
        db.commit()

    if not db.scalar(select(func.count(Order.id))):
        registered = db.scalars(select(Product).where(Product.status == "registered")).all()
        rnd = random.Random(11)
        for name in ("김하늘", "이서윤", "박지후", "최도윤"):
            picks = rnd.sample(registered, 2)
            ordering.create_order(db, OrderIn(customer_name=name, customer_phone="010-0000-0000", address="서울특별시 성동구",
                                              channel="simulation", items=[
                OrderItemIn(product_id=p.id, quantity=rnd.randint(1, 3),
                            option=f"{(p.options.get('colors') or ['-'])[0]}/{(p.options.get('sizes') or ['FREE'])[0]}")
                for p in picks]))


def run_seed(db: Session) -> None:
    seed_users(db)
    ensure_jobs(db)
    if settings.rpa_mode != "live":
        seed_demo_data(db)
