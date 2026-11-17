# fashionpick 배포 가이드

## 1. 로컬 개발

```bash
# Python 3.11 가상환경
py -3.11 -m venv .venv            # macOS/Linux: python3.11 -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium       # RPA live 모드용

cp .env.example .env              # SECRET_KEY 등 값 입력 (DATABASE_URL 비우면 SQLite)

# 백엔드 (저장소 루트에서)
uvicorn backend.app.main:app --reload --port 8000     # http://localhost:8000/docs

# 프런트엔드 (루트 .env 의 VITE_API_BASE_URL 사용)
cd frontend && npm ci && npm run dev                  # http://localhost:5173

# 테스트
python -m pytest backend/tests -q
```

Docker로 한 번에 실행하려면 `docker compose up --build`를 쓰세요. API는 :8000, 웹은 :5173에서 열립니다.

## 2. TiDB Cloud

1. TiDB Cloud 클러스터에 `fashionpick` 데이터베이스를 준비합니다.
2. `DATABASE_URL=mysql+pymysql://<USER>:<PASSWORD>@<HOST>:4000/fashionpick`와 `DB_SSL=true`를 설정합니다. CA 인증서는 certifi가 제공하는 것을 씁니다.
3. 서버가 처음 기동될 때 테이블 생성, 테스트 계정 생성, RPA 작업 등록이 자동으로 진행됩니다. demo 모드에서는 샘플 데이터도 넣습니다.

## 3. Render

`render.yaml` Blueprint 하나로 두 서비스를 만듭니다.

| 서비스 | 타입 | 주소 |
|---|---|---|
| `fashionpick-api` | Docker Web Service (`backend/Dockerfile`, context `.`) | https://fashionpick-api.onrender.com |
| `fashionpick` | Static Site (`frontend`, `dist`) | https://fashionpick.onrender.com |

- 두 서비스 모두 `autoDeploy: true`로 설정되어 있어, `main`에 푸시하면 Render가 Git 연동으로 자동 배포합니다. Deploy Hook은 쓰지 않습니다.
- `.env.example`에서 **[Render 필수]**로 표시된 값을 Render 대시보드의 Environment에 등록합니다.
- Dockerfile이 빌드할 때 `playwright install --with-deps chromium`을 실행하므로, Chromium과 시스템 종속성이 이미지에 포함됩니다.
- 무료 티어는 15분 동안 요청이 없으면 슬립합니다. 슬립 중에는 스케줄러도 멈추고, 첫 요청 응답에 30초 이상 걸릴 수 있습니다.
- 무료 티어 디스크는 휘발성입니다. live 모드에서 내려받은 이미지(`backend/storage/images`)는 재배포하면 사라지므로, 운영 환경에서는 외부 스토리지를 쓰는 것을 권장합니다.

## 4. Netlify (Staging)

`netlify.toml`의 설정은 다음과 같습니다.

- base: `frontend`
- 빌드 명령: `npm ci && npm run build`
- publish: `dist`
- SPA 리다이렉트 포함
- `VITE_API_BASE_URL=https://fashionpick-api.onrender.com`

## 5. OAuth Redirect URI

각 개발자 콘솔에 아래 주소를 등록합니다.

```
https://fashionpick-api.onrender.com/api/auth/oauth/google/callback
https://fashionpick-api.onrender.com/api/auth/oauth/naver/callback
https://fashionpick-api.onrender.com/api/auth/oauth/kakao/callback
```

로그인이 끝나면 요청을 보낸 프런트엔드 Origin의 `/oauth/callback#token=...`으로 돌아갑니다. Origin은 `CORS_ORIGINS`에 등록되어 있어야 합니다.

## 6. GitHub Actions

| 워크플로 | 트리거 | 내용 |
|---|---|---|
| `ci.yml` | push/PR | 백엔드 pytest, 프런트엔드 빌드 |
| `pages.yml` | `docs/**` 변경 | `docs/` 폴더를 GitHub Pages(https://fsclass-n.github.io/fashionpick/)로 배포 |

Render와 Netlify는 Git 연동으로 자동 배포되므로 별도의 배포 워크플로가 없습니다.

GitHub 저장소의 Settings → Pages에서 Source를 **GitHub Actions**로 설정해야 합니다.
