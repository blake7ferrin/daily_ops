"""Format and send daily summary to Telegram."""
import requests


def _fmt_money(cents: int | None) -> str:
    if cents is None:
        return "N/A"
    return f"${cents / 100:,.2f}"


def format_message(day: str, m: dict, business_name: str | None = None) -> str:
    """
    Build plain text message:
    Business Name (or Daily Ops Summary with date)
    Reviews TOTAL/+N
    Jobs walked, Jobs Sold, Invoiced, Collected, Spent
    """
    header = business_name.strip() if business_name and business_name.strip() else f"Daily Ops Summary ({day})"
    lines = [header]
    if m.get("gbp_total_reviews") is not None:
        total = m["gbp_total_reviews"]
        new = m.get("gbp_new_reviews")
        if new is None:
            reviews_line = f"Reviews {total}/N/A"
        else:
            reviews_line = f"Reviews {total}/+{new}"
    else:
        reviews_line = "Reviews N/A"
    lines.extend(
        [
            reviews_line,
            f"Jobs walked - {m['jobs_run_count']}",
            f"Jobs Sold - {m['jobs_sold_count']}",
            f"Invoiced - {m['jobs_invoiced_count']}",
            f"Collected - {_fmt_money(m['collected_cents'])}",
            f"Spent - {_fmt_money(m.get('amex_spend_cents'))}",
        ]
    )
    body = "\n".join(lines)
    if len(body) > 4096:
        body = body[:4093] + "..."
    return body


def send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    """POST to Telegram sendMessage. Raises on non-2xx or ok: false."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise SystemExit(f"Telegram API error: {data}")
    return None
