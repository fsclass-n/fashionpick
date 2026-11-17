import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = ROOT_DIR / "backend" / "storage"
load_dotenv(ROOT_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _json_list(name: str) -> list:
    try:
        value = json.loads(os.getenv(name) or "[]")
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


class Settings:
    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "development")
        self.secret_key = os.getenv("SECRET_KEY") or "dev-secret-change-me"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

        self.database_url = os.getenv("DATABASE_URL") or f"sqlite:///{(STORAGE_DIR / 'fashionpick.db').as_posix()}"
        self.db_ssl = _bool("DB_SSL", True)

        self.cors_origins = [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        self.backend_public_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")

        self.enable_test_login = _bool("ENABLE_TEST_LOGIN", True)
        self.test_user_email = os.getenv("TEST_USER_EMAIL", "user@fashionpick.dev")
        self.test_admin_email = os.getenv("TEST_ADMIN_EMAIL", "admin@fashionpick.dev")
        self.test_user_password = os.getenv("TEST_USER_PASSWORD", "Fashion!2026")
        self.test_admin_password = os.getenv("TEST_ADMIN_PASSWORD", "Admin!2026pick")

        self.oauth = {
            p: {"client_id": os.getenv(f"{p.upper()}_CLIENT_ID", ""), "client_secret": os.getenv(f"{p.upper()}_CLIENT_SECRET", "")}
            for p in ("google", "naver", "kakao")
        }

        self.rpa_mode = os.getenv("RPA_MODE", "demo")
        self.scheduler_enabled = _bool("SCHEDULER_ENABLED", True)
        self.rpa_headless = _bool("RPA_HEADLESS", True)
        self.rpa_request_delay = float(os.getenv("RPA_REQUEST_DELAY_SEC", "2.0"))
        self.rpa_user_agent = os.getenv("RPA_USER_AGENT", "fashionpick-bot/1.0")
        self.naver_datalab_client_id = os.getenv("NAVER_DATALAB_CLIENT_ID", "")
        self.naver_datalab_client_secret = os.getenv("NAVER_DATALAB_CLIENT_SECRET", "")
        self.trend_scrape_targets = _json_list("TREND_SCRAPE_TARGETS")
        self.wholesale_targets = _json_list("WHOLESALE_TARGETS")

        self.auto_purchase_order = _bool("AUTO_PURCHASE_ORDER", True)
        self.auto_send_purchase_order = _bool("AUTO_SEND_PURCHASE_ORDER", False)
        self.default_markup = float(os.getenv("DEFAULT_MARKUP", "2.2"))
        self.order_webhook_secret = os.getenv("ORDER_WEBHOOK_SECRET", "")
        self.store = {
            "name": os.getenv("STORE_NAME", "fashionpick"),
            "manager": os.getenv("STORE_MANAGER", ""),
            "phone": os.getenv("STORE_PHONE", ""),
            "address": os.getenv("STORE_ADDRESS", ""),
        }

        self.smtp = {
            "host": os.getenv("SMTP_HOST", ""),
            "port": int(os.getenv("SMTP_PORT", "587")),
            "user": os.getenv("SMTP_USER", ""),
            "password": os.getenv("SMTP_PASSWORD", ""),
            "sender": os.getenv("SMTP_FROM", "") or os.getenv("SMTP_USER", ""),
            "use_tls": _bool("SMTP_USE_TLS", True),
        }
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
