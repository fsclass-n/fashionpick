import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .config import STORAGE_DIR, settings
from .database import Base, SessionLocal, engine, ensure_schema
from .routers import admin, auth, catalog, orders, realtime, shop, trends
from .security import READ_ONLY_MESSAGE, is_read_only_token
from .services import rpa_jobs
from .services.realtime import manager
from .services.seed import run_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.bind_loop()
    Base.metadata.create_all(engine)
    ensure_schema()
    with SessionLocal() as db:
        run_seed(db)
    scheduler = asyncio.create_task(rpa_jobs.scheduler_loop()) if settings.scheduler_enabled else None
    if settings.sourcing_mode == "crawl" and settings.scheduler_enabled and not rpa_jobs.crawl_coverage_ok():
        rpa_jobs.spawn("product_sourcing", "startup")  # 실제 상품이 부족하거나 빈 카테고리가 있으면 기동 직후 1회 수집
    yield
    if scheduler:
        scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler


app = FastAPI(title="fashionpick API", version="1.0.0", lifespan=lifespan,
              description="RPA 기반 패션 트렌드 키워드 분석 · 도매 상품 소싱 · 발주 자동화 플랫폼")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _token_is_read_only(token: str) -> bool:
    with SessionLocal() as db:
        return is_read_only_token(db, token)


@app.middleware("http")
async def read_only_guard(request: Request, call_next):
    """테스트 관리자(읽기 전용) 토큰의 모든 데이터 변경 요청을 API 진입 전에 차단한다.
    (CORS 미들웨어보다 안쪽에 두어 403 응답에도 CORS 헤더가 붙도록 먼저 등록)"""
    path, auth_header = request.url.path, request.headers.get("authorization", "")
    if (request.method not in SAFE_METHODS and path.startswith("/api/") and not path.startswith("/api/auth/")
            and auth_header.lower().startswith("bearer ")
            and await run_in_threadpool(_token_is_read_only, auth_header[7:].strip())):
        return JSONResponse({"detail": READ_ONLY_MESSAGE, "read_only": True}, status_code=403)
    return await call_next(request)


app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition"])

for r in (auth.router, shop.router, trends.router, catalog.router, orders.router, admin.router, realtime.router):
    app.include_router(r)

(STORAGE_DIR / "images").mkdir(parents=True, exist_ok=True)
app.mount("/media/images", StaticFiles(directory=STORAGE_DIR / "images"), name="images")


@app.get("/", tags=["health"])
def root():
    return {"service": "fashionpick-api", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "rpa_mode": settings.rpa_mode}
