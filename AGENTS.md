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

## Roles (frontend + backend must stay in sync)
- `user`: storefront (shop, product detail, order, mypage).
- `admin` (real admin): only via `POST /api/auth/admin-login` with `.env` `ADMIN_TOKEN`; full CRUD. Write endpoints use `require_admin`.
- `test_admin`: from "테스트 관리자 로그인"; sees every admin view (`require_admin_read`) but all non-GET `/api/*` (except `/api/auth/*`) are blocked by the `read_only_guard` middleware in `main.py`. Frontend uses `WriteButton` / `useAuth().readOnly` to disable write actions.

## Workflow preferences
- After finishing each task, commit and push to `origin main` (user preference). Never commit `.env` or local DB files.
- Report results to the user in Korean.
- Presentation: edit `docs/presentation.md`, then regenerate `docs/fashionpick_발표자료.pptx` with `.venv/Scripts/python tools/build_presentation.py` (deps: `tools/requirements.txt`).

## Local notes
- The local `.env` may contain the real TiDB `DATABASE_URL`. For local experiments/tests run with `DATABASE_URL=` (empty) so SQLite is used; pytest's conftest already overrides it.
- Ports 8000 / 5173 may be used by other local projects; use `--port 8001` / `--port 5174` and set `CORS_ORIGINS` / `VITE_API_BASE_URL` env accordingly.
