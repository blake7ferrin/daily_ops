"""Load and validate configuration from environment (Doppler injects vars via doppler run)."""
import os
from zoneinfo import ZoneInfo

_REQUIRED = [
    "HCP_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TIMEZONE",
]


def _get(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None or (isinstance(val, str) and val.strip() == ""):
        raise SystemExit(f"Missing required env var: {key}")
    return val.strip()


def load_config() -> dict:
    """Load and validate config from os.environ. Exits with clear error if any required var is missing."""
    missing = [k for k in _REQUIRED if not (os.environ.get(k) or "").strip()]
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")

    hcp_base = (os.environ.get("HCP_BASE_URL") or "").strip() or "https://api.housecallpro.com"

    return {
        "hcp_api_key": _get("HCP_API_KEY"),
        "hcp_base_url": hcp_base,
        "hcp_auth_header": (os.environ.get("HCP_AUTH_HEADER") or "bearer").strip().lower(),
        "plaid_client_id": (os.environ.get("PLAID_CLIENT_ID") or "").strip() or None,
        "plaid_secret": (os.environ.get("PLAID_SECRET") or "").strip() or None,
        "plaid_env": (os.environ.get("PLAID_ENV") or "").strip() or None,
        "plaid_access_token": (os.environ.get("PLAID_ACCESS_TOKEN") or "").strip() or None,
        "plaid_amex_account_id": (os.environ.get("PLAID_AMEX_ACCOUNT_ID") or "").strip() or None,
        "telegram_bot_token": _get("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": _get("TELEGRAM_CHAT_ID"),
        "timezone": _get("TIMEZONE"),
        "tz": ZoneInfo(_get("TIMEZONE")),
        "places_api_key": (os.environ.get("PLACES_API_KEY") or "").strip() or None,
        "business_name": (os.environ.get("BUSINESS_NAME") or "").strip() or None,
        "snapshot_db_path": (os.environ.get("SNAPSHOT_DB_PATH") or "").strip() or None,
    }
