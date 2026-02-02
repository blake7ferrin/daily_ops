"""Daily Ops: fetch HCP, Plaid, and optional Google Reviews (Places API) and send Telegram summary."""
import argparse
import sys
from datetime import date, datetime, timedelta

from .config import load_config
from .hcp_client import (
    fetch_invoices_created,
    fetch_jobs_created,
    fetch_payments_received,
    fetch_won_estimates,
)
from .metrics import compute_metrics
from .notify import format_message, send_telegram
from .places_client import fetch_reviews_summary as places_fetch_reviews_summary
from .plaid_client import fetch_transactions
from .storage import get_snapshot, upsert_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Ops summary")
    parser.add_argument("--date", type=str, default=None, help="YYYY-MM-DD (default: today in TIMEZONE)")
    args = parser.parse_args()
    cfg = load_config()
    tz = cfg["tz"]

    if args.date:
        try:
            day_date = date.fromisoformat(args.date)
        except ValueError:
            print("Invalid --date; use YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
        day = args.date
    else:
        # Use configured timezone for "today" to avoid empty summaries on UTC hosts.
        day_date = datetime.now(tz=tz).date()
        day = day_date.strftime("%Y-%m-%d")

    yesterday_date = day_date - timedelta(days=1)
    yesterday = yesterday_date.strftime("%Y-%m-%d")

    base_url = cfg["hcp_base_url"]
    api_key = cfg["hcp_api_key"]
    hcp_auth = cfg.get("hcp_auth_header") or "bearer"

    try:
        jobs_created = fetch_jobs_created(base_url, api_key, day, tz, hcp_auth)
    except Exception as e:
        print(f"HCP jobs created: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        won_estimates = fetch_won_estimates(base_url, api_key, day, tz, hcp_auth)
    except Exception as e:
        print(f"HCP won estimates: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        invoices_created = fetch_invoices_created(base_url, api_key, day, tz, hcp_auth)
    except Exception as e:
        print(f"HCP invoices: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        payments_received = fetch_payments_received(base_url, api_key, day, tz, hcp_auth)
    except Exception as e:
        print(f"HCP payments: {e}", file=sys.stderr)
        sys.exit(1)

    plaid_txns = None
    if cfg.get("plaid_client_id") and cfg.get("plaid_secret") and cfg.get("plaid_env") and cfg.get("plaid_access_token"):
        try:
            plaid_txns = fetch_transactions(
                cfg["plaid_client_id"],
                cfg["plaid_secret"],
                cfg["plaid_env"],
                cfg["plaid_access_token"],
                day,
                day,
                account_ids=[cfg["plaid_amex_account_id"]] if cfg.get("plaid_amex_account_id") else None,
            )
        except Exception as e:
            print(f"Plaid: {e}", file=sys.stderr)
            sys.exit(1)

    gbp_total_reviews = None
    gbp_avg_rating = None
    gbp_yesterday_total = None
    if cfg.get("places_api_key") and cfg.get("business_name"):
        try:
            gbp_total_reviews, gbp_avg_rating = places_fetch_reviews_summary(
                cfg["places_api_key"],
                cfg["business_name"],
            )
        except Exception as e:
            print(f"Google Places: {e}", file=sys.stderr)
            sys.exit(1)
        prev = get_snapshot(cfg.get("snapshot_db_path"), yesterday)
        gbp_yesterday_total = prev["gbp_total_reviews"] if prev else None

    m = compute_metrics(
        jobs_created,
        won_estimates,
        invoices_created,
        payments_received,
        plaid_txns,
        cfg.get("plaid_amex_account_id"),
        gbp_total_reviews,
        gbp_yesterday_total,
        gbp_avg_rating,
    )

    text = format_message(day, m)
    try:
        send_telegram(cfg["telegram_bot_token"], cfg["telegram_chat_id"], text)
    except Exception as e:
        print(f"Telegram: {e}", file=sys.stderr)
        sys.exit(1)

    if gbp_total_reviews is not None:
        try:
            upsert_snapshot(cfg.get("snapshot_db_path"), day, gbp_total_reviews, gbp_avg_rating)
        except Exception as e:
            print(f"Storage upsert: {e}", file=sys.stderr)
            sys.exit(1)

    print("Sent.", file=sys.stderr)


if __name__ == "__main__":
    main()
