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


def _status_contains(status: str, markers: tuple[str, ...]) -> bool:
    return any(marker in status for marker in markers)


def _job_schedule_date(job: dict, tz) -> str | None:
    schedule = job.get("schedule") or {}
    if not isinstance(schedule, dict):
        return None
    return _parse_date_only(
        schedule.get("scheduled_start") or schedule.get("scheduled_end"),
        tz,
    )


def _job_walked_on_day(job: dict, day: str, tz) -> bool:
    timestamps = job.get("work_timestamps") or {}
    if not isinstance(timestamps, dict):
        return False
    for key in ("started_at", "on_my_way_at", "completed_at"):
        if _parse_date_only(timestamps.get(key), tz) == day:
            return True
    return False


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


def fetch_jobs_walked(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Jobs walked on day (on_my_way/started/completed in tz)."""
    session = _session_with_auth(api_key, auth_header)
    all_jobs = _get_paginated(session, base_url, "/jobs", "jobs")
    result = []
    for j in all_jobs:
        if _job_walked_on_day(j, day, tz):
            result.append(j)
    return result


def fetch_jobs_booked(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Jobs booked on day (scheduled_start in tz)."""
    session = _session_with_auth(api_key, auth_header)
    all_jobs = _get_paginated(session, base_url, "/jobs", "jobs")
    result = []
    for j in all_jobs:
        scheduled_date = _job_schedule_date(j, tz)
        if scheduled_date == day:
            result.append(j)
    return result


def fetch_estimates_converted(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Estimates converted to jobs on day (converted/updated date in tz)."""
    session = _session_with_auth(api_key, auth_header)
    all_estimates = _get_paginated(session, base_url, "/estimates", "estimates")
    result = []
    sold_markers = ("created job", "converted")
    for e in all_estimates:
        status = (e.get("status") or e.get("work_status") or "").lower()
        if not _status_contains(status, sold_markers):
            continue
        # Use converted_at or updated_at for "on day"
        date_str = _parse_date_only(
            e.get("converted_at") or e.get("updated_at") or e.get("created_at"),
            tz,
        )
        if date_str == day:
            result.append(e)
    return result


def fetch_invoices_sent(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Invoices sent on day (sent_at). Falls back to jobs with invoices if no /invoices endpoint."""
    session = _session_with_auth(api_key, auth_header)
    try:
        all_invoices = _get_paginated(session, base_url, "/invoices", "invoices")
    except Exception:
        # No dedicated invoices list: derive from jobs (invoices on jobs)
        all_jobs = _get_paginated(session, base_url, "/jobs", "jobs")
        result = []
        for j in all_jobs:
            for inv in j.get("invoices", []) or []:
                sent_date = _parse_date_only(
                    inv.get("sent_at")
                    or inv.get("invoice_date")
                    or inv.get("created_at")
                    or inv.get("service_date"),
                    tz,
                )
                if sent_date == day:
                    result.append(inv)
        return result
    result = []
    for i in all_invoices:
        sent_date = _parse_date_only(
            i.get("sent_at")
            or i.get("invoice_date")
            or i.get("created_at")
            or i.get("service_date"),
            tz,
        )
        if sent_date == day:
            result.append(i)
    return result


def fetch_payments_received(base_url: str, api_key: str, day: str, tz, auth_header: str = "bearer") -> list:
    """Payments received on day (payment date). Exclude refunds/voids."""
    session = _session_with_auth(api_key, auth_header)

    def _is_refund(payment: dict) -> bool:
        kind = (payment.get("type") or payment.get("status") or "").lower()
        return "refund" in kind or "void" in kind

    def _payment_date(payment: dict) -> str | None:
        return _parse_date_only(
            payment.get("paid_at")
            or payment.get("date")
            or payment.get("created_at")
            or payment.get("payment_date"),
            tz,
        )

    def _collect_nested_payments(objects: list, key: str) -> list:
        result: list = []
        for obj in objects:
            for payment in obj.get(key, []) or []:
                if _is_refund(payment):
                    continue
                pay_date = _payment_date(payment)
                if pay_date == day:
                    result.append(payment)
        return result

    try:
        all_payments = _get_paginated(session, base_url, "/payments", "payments")
    except Exception:
        # Try under jobs and invoices: payments nested on objects
        payments: list = []
        try:
            all_jobs = _get_paginated(session, base_url, "/jobs", "jobs")
            payments.extend(_collect_nested_payments(all_jobs, "payments"))
        except Exception:
            pass
        try:
            all_invoices = _get_paginated(session, base_url, "/invoices", "invoices")
            payments.extend(_collect_nested_payments(all_invoices, "payments"))
        except Exception:
            pass
        if not payments:
            return []
        seen_ids: set = set()
        unique: list = []
        for payment in payments:
            payment_id = payment.get("id")
            if payment_id and payment_id in seen_ids:
                continue
            if payment_id:
                seen_ids.add(payment_id)
            unique.append(payment)
        return unique
    result = []
    for p in all_payments:
        if _is_refund(p):
            continue
        pay_date = _payment_date(p)
        if pay_date == day:
            result.append(p)
    return result
