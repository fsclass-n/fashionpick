import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import STORAGE_DIR, settings
from .database import Base, SessionLocal, engine
from .routers import admin, auth, catalog, orders, realtime, trends
from .services import rpa_jobs
from .services.realtime import manager
from .services.seed import run_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.bind_loop()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        run_seed(db)
    scheduler = asyncio.create_task(rpa_jobs.scheduler_loop()) if settings.scheduler_enabled else None
    yield
    if scheduler:
        scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler


app = FastAPI(title="fashionpick API", version="1.0.0", lifespan=lifespan,
              description="RPA 기반 패션 트렌드 키워드 분석 · 도매 상품 소싱 · 발주 자동화 플랫폼")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"])

for r in (auth.router, trends.router, catalog.router, orders.router, admin.router, realtime.router):
    app.include_router(r)

(STORAGE_DIR / "images").mkdir(parents=True, exist_ok=True)
app.mount("/media/images", StaticFiles(directory=STORAGE_DIR / "images"), name="images")


@app.get("/", tags=["health"])
def root():
    return {"service": "fashionpick-api", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "rpa_mode": settings.rpa_mode}
