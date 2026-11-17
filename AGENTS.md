# AGENTS.md - fashionpick

## Commands (run from repo root unless noted)
- Python venv: `.venv/Scripts/python` (Windows). Install: `uv pip install --python .venv/Scripts/python.exe -r requirements.txt` (or pip).
- Backend dev: `.venv/Scripts/python -m uvicorn backend.app.main:app --reload --port 8000`
- Backend tests: `.venv/Scripts/python -m pytest backend/tests -q` (uses temp SQLite, RPA demo mode, scheduler off)
- Frontend (in `frontend/`): `npm ci`, `npm run dev`, `npm run build` (verify build before finishing frontend changes)
- Docker: `docker compose up --build` (API :8000, web :5173)

## Conventions
- Single `.env` at repo root; Vite reads it via `envDir: '..'`. Only `VITE_*` vars reach the frontend.
- Backend imports `rpa.*` as a package -> always run from repo root (Dockerfile copies `backend/` and `rpa/`).
- Starlette 1.x: use `lifespan`, not `on_event`. Sync endpoints run in threadpool; use `manager.publish()` (thread-safe) for WebSocket events.
- Tailwind v4: custom classes are defined with `@utility` in `frontend/src/index.css` (not `@layer components` + `@apply`).
- Semantic colors: `bg-bg`, `bg-surface`, `bg-surface-2`, `text-fg`, `text-muted`, `border-line`, `accent`; dark mode via `.dark` on `<html>`.
- New dependencies: pin versions published >= 7 days ago (`uv pip --exclude-newer`, `npm install --before=<date>`).

## Local notes
- Ports 8000 / 5173 may be used by other local projects; use `--port 8001` / `--port 5174` and set `CORS_ORIGINS` / `VITE_API_BASE_URL` env accordingly.
