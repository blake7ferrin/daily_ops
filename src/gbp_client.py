"""Google Business Profile API: fetch review summary (totalReviewCount, averageRating)."""
import requests

_GBP_BASE = "https://mybusiness.googleapis.com/v4"


def fetch_reviews_summary(
    account_id: str,
    location_id: str,
    access_token: str,
) -> tuple[int, float | None]:
    """Return (total_review_count, average_rating). average_rating may be None if not in response."""
    url = f"{_GBP_BASE}/accounts/{account_id}/locations/{location_id}/reviews"
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    params = {"pageSize": 1}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    total = data.get("totalReviewCount", 0) or 0
    avg = data.get("averageRating")
    if avg is not None:
        avg = float(avg)
    return (int(total), avg)
