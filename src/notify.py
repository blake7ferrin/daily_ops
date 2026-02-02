"""Format and send daily summary to Telegram."""
import requests


def _fmt_money(cents: int | None) -> str:
    if cents is None:
        return "N/A"
    return f"${cents / 100:,.2f}"


def format_message(day: str, m: dict) -> str:
    """
    Build plain text message:
    Daily Ops Summary (YYYY-MM-DD)
    Jobs created, Jobs sold, Jobs invoiced, Collected, AMEX spend, Net
    Google Reviews: Total: X (Avg: Y.Y), New since yesterday: +N
    """
    lines = [
        f"Daily Ops Summary ({day})",
        "",
        f"Jobs created: {m['jobs_run_count']}",
        f"Jobs sold: {m['jobs_sold_count']}",
        f"Jobs invoiced: {m['jobs_invoiced_count']}",
        f"Collected: {_fmt_money(m['collected_cents'])}",
        f"AMEX spend: {_fmt_money(m.get('amex_spend_cents'))}",
        f"Net: {_fmt_money(m.get('net_cents'))}",
        "",
    ]
    if m.get("gbp_total_reviews") is not None:
        lines.append("Google Reviews:")
        avg = m.get("gbp_avg_rating")
        if avg is not None:
            lines.append(f"Total: {m['gbp_total_reviews']} (Avg: {avg:.1f})")
        else:
            lines.append(f"Total: {m['gbp_total_reviews']}")
        new = m.get("gbp_new_reviews")
        if new is not None:
            lines.append(f"New since yesterday: +{new}")
        else:
            lines.append("New since yesterday: N/A")
    else:
        lines.append("Google Reviews: N/A")
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
