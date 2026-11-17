# fashionpick 설계서

## 1. 시스템 구성

```
┌──────────── Frontend (React · Vite · Tailwind v4) ────────────┐
│  Netlify (staging)  fashionpick.netlify.app                    │
│  Render Static      fashionpick.onrender.com                   │
└───────────────┬───────────────────────────────┬────────────────┘
          REST (JWT Bearer)                WebSocket /ws?token=
┌───────────────▼───────────────────────────────▼────────────────┐
│  FastAPI  fashionpick-api.onrender.com  (Docker + Chromium)     │
│   routers: auth · trends · catalog · orders · admin · realtime  │
│   services: trends · catalog · ordering · rpa_jobs · realtime   │
│   scheduler (asyncio) ──► worker thread ──► rpa/*               │
└───────┬──────────────────────────────┬─────────────────────────┘
        │ SQLAlchemy (PyMySQL + TLS)   │ Playwright / Requests
┌───────▼────────┐      ┌──────────────▼──────────────────────────┐
│ TiDB Cloud     │      │ 네이버 데이터랩 · 랭킹 페이지 · 도매 사이트 │
│ (fashionpick)  │      │ SMTP · Webhook · Telegram · Discord      │
└────────────────┘      └─────────────────────────────────────────┘
```

## 2. RPA 파이프라인

| 작업 (`rpa_jobs`) | 기본 주기 | 모듈 | 내용 |
|---|---|---|---|
| `trend_collect` | 60분 | `rpa/trend/collector.py` | 데이터랩 API(앵커 키워드 정규화) + `TREND_SCRAPE_TARGETS` 랭킹 페이지 수집 → 스냅샷 저장 → 급상승 탐지 (점수 +15% 또는 순위 +5) |
| `product_sourcing` | 180분 | `rpa/sourcing/wholesale.py` | 상위 8개 키워드로 `WHOLESALE_TARGETS` 검색 → 상품명·가격·이미지·링크 수집, 이미지 로컬 저장 → `source_url` 기준 upsert |
| `po_dispatch` | 30분 | `rpa/purchase_order/*` | 발주 미배정 주문상품을 공급처별 '대기' 발주서로 병합, `AUTO_SEND_PURCHASE_ORDER=true` 면 자동 발송 |

- `RPA_MODE=demo`: 외부 접속 없이 샘플 데이터로 전체 흐름을 시연합니다.
- `RPA_MODE=live`: 실제 수집. 수집 전에 robots.txt를 확인하고, 도메인별 요청 간격 제한(`RPA_REQUEST_DELAY_SEC`)을 적용합니다.
- 같은 작업은 동시에 한 번만 실행됩니다. 실행할 때마다 `rpa_logs`에 결과가 기록되고 관리자에게 WebSocket 이벤트가 전송됩니다.

## 3. 데이터 모델

| 테이블 | 주요 컬럼 |
|---|---|
| `users` | email, name, password_hash(PBKDF2-SHA256), role(user/admin), provider(local/google/naver/kakao) |
| `trend_keywords` | batch_id(스냅샷), keyword, category, source, rank, score, collected_at |
| `suppliers` | name, contact_name, phone, email, webhook_url, order_method(email/webhook/manual), template(standard/simple) |
| `products` | supplier_id, name, category, keyword, wholesale_price, sale_price, image_url, options(JSON), stock, status(sourced/registered), registered_name |
| `orders` / `order_items` | order_no, customer, channel, status(received/ordering/ordered/stocked) / product_id, option, quantity, unit_price, wholesale_price, purchase_order_id |
| `purchase_orders` | po_no, supplier_id, status(pending/sent/received), total_amount, send_channel, send_log |
| `rpa_jobs` / `rpa_logs` | name, interval_minutes, enabled, last_status / job_name, status, triggered_by, items_count, message |

## 4. 주요 API

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/auth/register` · `/login` · `/test-login` | 회원가입 / 로그인 / 테스트 간편 로그인 (JWT 발급) |
| GET | `/api/auth/oauth/{google\|naver\|kakao}/login` | 소셜 로그인 (state = 서명된 JWT) |
| GET | `/api/trends/public-top` | 로그인 페이지 실시간 TOP N (공개) |
| GET | `/api/trends/latest` · `/history` · `/categories` | 순위·증감, 시계열, 카테고리 비중 |
| GET | `/api/products` · POST `/api/products/{id}/register` | 소싱 상품 목록 / 원클릭 등록 (추천 상품명) |
| POST | `/api/orders` · `/api/orders/simulate` · `/api/orders/webhook` | 주문 생성 / 시연 주문 / 외부몰 웹훅 (`X-Webhook-Secret`) |
| GET | `/api/purchase-orders/{id}/preview` · `/excel` · `/pdf` | 발주서 미리보기 / 다운로드 |
| POST | `/api/purchase-orders/{id}/send` · PATCH `/status` | 발송 / 상태 변경 |
| GET/PATCH/POST | `/api/admin/rpa/jobs[/{name}[/run]]` · `/rpa/logs` · `/rpa/stats` | RPA 작업 관리 |
| GET/PATCH | `/api/admin/users[/{id}/role]` | 회원 권한 관리 |
| WS | `/ws?token=` | `order.created` · `po.created` · `po.updated` · `po.failed` · `trend.surge` · `rpa.job` · `user.role` |

## 5. 보안

- 비밀번호 규칙: 영문 대문자·소문자, 숫자, 특수문자를 포함한 8~64자. 프런트엔드와 백엔드에서 같은 규칙으로 검사합니다.
- OAuth 계정 연결: 제공자가 이메일 인증을 확인한 경우에만 기존 계정과 연결합니다. 리다이렉트 주소는 `CORS_ORIGINS`에 등록된 주소만 허용합니다.
- 테스트 로그인: 시연용 기능입니다. 운영 환경에서는 `ENABLE_TEST_LOGIN=false`로 끕니다.
