"""Google OAuth2: exchange refresh token for access token (for GBP API)."""
import os
import requests

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CACHED_ACCESS_TOKEN: str | None = None


def get_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str:
    """Return a valid access token. Cached in memory for the run."""
    global _CACHED_ACCESS_TOKEN
    if _CACHED_ACCESS_TOKEN:
        return _CACHED_ACCESS_TOKEN
    body = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    resp = requests.post(_TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise SystemExit("Google OAuth: no access_token in response")
    _CACHED_ACCESS_TOKEN = token
    return token
