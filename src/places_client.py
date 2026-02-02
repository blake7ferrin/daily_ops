"""Google Places API (Legacy): find place by business name, then get rating and review count."""
import requests

_FIND_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def fetch_reviews_summary(api_key: str, business_name: str) -> tuple[int, float | None]:
    """
    Return (total_review_count, average_rating) for the place matching business_name.
    Uses Find Place from Text to get place_id, then Place Details for rating and user_ratings_total.
    """
    params_find = {
        "input": business_name,
        "inputtype": "textquery",
        "fields": "place_id",
        "key": api_key,
    }
    resp = requests.get(_FIND_URL, params=params_find, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status != "OK":
        raise RuntimeError(f"Places Find Place: status={status}, message={data.get('error_message', '')}")
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Places Find Place: no candidates found for business name")
    place_id = candidates[0].get("place_id")
    if not place_id:
        raise RuntimeError("Places Find Place: no place_id in response")

    params_details = {
        "place_id": place_id,
        "fields": "rating,user_ratings_total",
        "key": api_key,
    }
    resp2 = requests.get(_DETAILS_URL, params=params_details, timeout=15)
    resp2.raise_for_status()
    data2 = resp2.json()
    status2 = data2.get("status")
    if status2 != "OK":
        raise RuntimeError(f"Places Details: status={status2}, message={data2.get('error_message', '')}")
    result = data2.get("result", {})
    total = result.get("user_ratings_total")
    if total is not None:
        total = int(total)
    else:
        total = 0
    rating = result.get("rating")
    if rating is not None:
        rating = float(rating)
    return (total, rating)
