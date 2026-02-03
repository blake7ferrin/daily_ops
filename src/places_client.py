"""Google Places API (Legacy): find place and get rating/review count."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import requests

_FIND_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def _fetch_details(api_key: str, params_details: dict) -> tuple[int, float | None]:
    resp = requests.get(_DETAILS_URL, params=params_details, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status != "OK":
        raise RuntimeError(f"Places Details: status={status}, message={data.get('error_message', '')}")
    result = data.get("result", {})
    total = result.get("user_ratings_total")
    if total is not None:
        total = int(total)
    else:
        total = 0
    rating = result.get("rating")
    if rating is not None:
        rating = float(rating)
    return (total, rating)


def _extract_cids_from_url(maps_url: str) -> list[str]:
    if not maps_url:
        return []
    resolved_url = maps_url
    try:
        resp = requests.get(maps_url, allow_redirects=True, timeout=10)
        resp.raise_for_status()
        resolved_url = resp.url
    except requests.RequestException:
        resolved_url = maps_url
    parsed = urlparse(resolved_url)
    qs = parse_qs(parsed.query)
    cids: list[str] = []
    for value in qs.get("cid", []):
        if value and value.isdigit():
            cids.append(value)
    for value in qs.get("ftid", []):
        match = re.match(r"0x([0-9a-fA-F]+):0x([0-9a-fA-F]+)", value or "")
        if match:
            for part in match.groups():
                cids.append(str(int(part, 16)))
    return cids


def fetch_reviews_summary(
    api_key: str,
    business_name: str | None = None,
    *,
    place_id: str | None = None,
    cid: str | None = None,
    maps_url: str | None = None,
) -> tuple[int, float | None]:
    """
    Return (total_review_count, average_rating) for the place.
    Priority: place_id, cid, maps_url (cid/ftid), then business_name text search.
    """
    if place_id:
        return _fetch_details(
            api_key,
            {
                "place_id": place_id,
                "fields": "rating,user_ratings_total",
                "key": api_key,
            },
        )
    if cid:
        return _fetch_details(
            api_key,
            {
                "cid": cid,
                "fields": "rating,user_ratings_total",
                "key": api_key,
            },
        )
    if maps_url:
        cids = _extract_cids_from_url(maps_url)
        last_error: RuntimeError | None = None
        for candidate_cid in cids:
            try:
                return _fetch_details(
                    api_key,
                    {
                        "cid": candidate_cid,
                        "fields": "rating,user_ratings_total",
                        "key": api_key,
                    },
                )
            except RuntimeError as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Places Maps URL: no cid/ftid found in URL")
    if not business_name:
        raise RuntimeError("Places: missing business_name, place_id, cid, or maps_url")

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

    return _fetch_details(
        api_key,
        {
            "place_id": place_id,
            "fields": "rating,user_ratings_total",
            "key": api_key,
        },
    )
