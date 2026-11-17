# fashionpick API (FastAPI + Playwright Chromium) - Render Docker Web Service
# build context: 저장소 루트  (docker build -t fashionpick-api .)
# Render 기본값(Dockerfile Path ./Dockerfile, Docker Context .)과 일치하도록 루트에 둔다.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY requirements.txt .
# Playwright 드라이버(node)는 slim 이미지에 없는 libatomic1·libstdc++6 이 필요해 먼저 설치한 뒤,
# 빌드 타임에 Chromium 바이너리 + 시스템 종속성(폰트, libnss 등) 설치
RUN apt-get update \
 && apt-get install -y --no-install-recommends libatomic1 libstdc++6 \
 && pip install -r requirements.txt \
 && playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

COPY backend ./backend
COPY rpa ./rpa

RUN useradd --create-home app \
 && mkdir -p backend/storage/images \
 && chown -R app:app /app /ms-playwright
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"8000\")}/health')"

# Render는 PORT 환경변수로 포트를 지정한다
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
