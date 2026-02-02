"""Housecall Pro API client: jobs, estimates, invoices, payments."""
import time
from datetime import datetime

import requests

# Rate limit backoff (seconds)
_RATE_LIMIT_BACKOFF = 60
_PER_PAGE = 100


def _parse_date_only(iso_str: str | None, tz) -> str | None:
    """Return YYYY-MM-DD in tz for an ISO datetime string, or None."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(tz)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: dict | None = None,
    **kwargs,
) -> requests.Response:
    """GET with 429 retry using RateLimit-Reset header."""
    while True:
        resp = session.request(method, url, params=params, **kwargs)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        reset = resp.headers.get("RateLimit-Reset")
        wait = _RATE_LIMIT_BACKOFF
        if reset:
            try:
                reset_ts = int(reset)
                wait = max(1, reset_ts - int(time.time()))
            except ValueError:
                pass
        time.sleep(min(wait, _RATE_LIMIT_BACKOFF))


def _get_paginated(
    session: requests.Session,
    base_url: str,
    path: str,
    list_key: str,
    params: dict | None = None,
) -> list:
    """Fetch all pages; list_key is the key in response that holds the list (e.g. 'jobs')."""
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    out: list = []
    page = 1
    while True:
        p = dict(params or {}, page=page, per_page=_PER_PAGE)
        resp = _request_with_retry(session, "GET", url, params=p)
        data = resp.json()
        items = data.get(list_key, data.get("data", []))
        if not items:
            break
        out.extend(items)
        if len(items) < _PER_PAGE:
            break
        page += 1
    return out


def _session_with_auth(api_key: str, auth_header: str) -> requests.Session:
    session = requests.Session()
    session.headers["Accept"] = "application/json"
    if (auth_header or "bearer").lower() in ("api_key", "x-api-key", "apikey"):
        session.headers["X-API-Key"] = api_key
    else:
        session.headers["Authorization"] = f"Bearer {api_key}"
    return session


def fetch_completed_jobs(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Jobs with work_status completed and completed_at date = day (YYYY-MM-DD in tz)."""
    session = _session_with_auth(api_key, auth_header)
    all_jobs = _get_paginated(session, base_url, "/jobs", "jobs")
    result = []
    for j in all_jobs:
        status = (j.get("work_status") or j.get("status") or "").lower()
        if "complete" not in status:
            continue
        completed_date = _parse_date_only(j.get("completed_at"), tz)
        if completed_date == day:
            result.append(j)
    return result


def fetch_won_estimates(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Estimates marked Won on day (won date or updated_at in tz)."""
    session = _session_with_auth(api_key, auth_header)
    all_estimates = _get_paginated(session, base_url, "/estimates", "estimates")
    result = []
    for e in all_estimates:
        status = (e.get("status") or e.get("work_status") or "").lower()
        if "won" not in status:
            continue
        # Use won_at, converted_at, or updated_at for "on day"
        date_str = _parse_date_only(
            e.get("won_at") or e.get("converted_at") or e.get("updated_at"), tz
        )
        if date_str == day:
            result.append(e)
    return result


def fetch_invoices_created(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Invoices created on day. Falls back to jobs with invoices if no /invoices endpoint."""
    session = _session_with_auth(api_key, auth_header)
    try:
        all_invoices = _get_paginated(session, base_url, "/invoices", "invoices")
    except Exception:
        # No dedicated invoices list: derive from jobs (invoices on jobs)
        all_jobs = _get_paginated(session, base_url, "/jobs", "jobs")
        result = []
        for j in all_jobs:
            for inv in j.get("invoices", []) or []:
                created = _parse_date_only(inv.get("created_at"), tz)
                if created == day:
                    result.append(inv)
        return result
    result = [i for i in all_invoices if _parse_date_only(i.get("created_at"), tz) == day]
    return result


def fetch_payments_received(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Payments received on day (payment date). Exclude refunds/voids."""
    session = _session_with_auth(api_key, auth_header)
    try:
        all_payments = _get_paginated(session, base_url, "/payments", "payments")
    except Exception:
        # Try under jobs: payments on jobs
        all_jobs = _get_paginated(session, base_url, "/jobs", "jobs")
        result = []
        for j in all_jobs:
            for p in j.get("payments", []) or []:
                pay_date = _parse_date_only(p.get("date") or p.get("created_at") or p.get("payment_date"), tz)
                if pay_date == day:
                    kind = (p.get("type") or p.get("status") or "").lower()
                    if "refund" in kind or "void" in kind:
                        continue
                    result.append(p)
        return result
    result = []
    for p in all_payments:
        kind = (p.get("type") or p.get("status") or "").lower()
        if "refund" in kind or "void" in kind:
            continue
        pay_date = _parse_date_only(p.get("date") or p.get("created_at") or p.get("payment_date"), tz)
        if pay_date == day:
            result.append(p)
    return result
