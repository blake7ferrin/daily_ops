"""Compute daily metrics from HCP, Plaid, and GBP data."""
from typing import Any


def _payment_amount_cents(p: dict) -> int:
    """Convert a payment record to cents. HCP may return dollars (float) or cents (int)."""
    amt = p.get("amount") or p.get("total") or 0
    if isinstance(amt, (int, float)):
        if abs(amt) < 1000 and (isinstance(amt, float) or abs(amt) < 100):
            return int(round(amt * 100))
        return int(amt)
    return 0


def compute_metrics(
    created_jobs: list,
    won_estimates: list,
    invoices_created: list,
    payments_received: list,
    plaid_transactions: list[dict] | None,
    amex_account_id: str | None,
    gbp_total_reviews: int | None,
    gbp_yesterday_total: int | None,
    gbp_avg_rating: float | None,
) -> dict[str, Any]:
    """
    Return a single dict with:
    jobs_run_count (jobs created on day), jobs_sold_count, jobs_invoiced_count,
    collected_cents, amex_spend_cents, net_cents,
    gbp_total_reviews, gbp_new_reviews, gbp_avg_rating.
    amex_spend_cents and net_cents are None when Plaid is not used.
    gbp_* are None when Google Reviews (GBP) is not used.
    """
    jobs_run_count = len(created_jobs)
    jobs_sold_count = len(won_estimates)
    jobs_invoiced_count = len(invoices_created)

    collected_cents = sum(_payment_amount_cents(p) for p in payments_received)
    # Exclude negative (refunds) if not already filtered by client
    collected_cents = max(0, collected_cents)

    # Plaid optional: when None, AMEX spend and Net are N/A
    if plaid_transactions is not None:
        amex_spend_cents = 0
        for t in plaid_transactions:
            if t.get("pending") is True:
                continue
            if amex_account_id and t.get("account_id") != amex_account_id:
                continue
            amt = t.get("amount")
            if amt is None:
                continue
            # Plaid: positive = money out for credit cards
            if isinstance(amt, (int, float)) and amt > 0:
                amex_spend_cents += int(round(amt * 100))
        net_cents = collected_cents - amex_spend_cents
    else:
        amex_spend_cents = None
        net_cents = None

    # GBP optional: when gbp_total_reviews is None, all GBP fields N/A
    if gbp_total_reviews is not None:
        if gbp_yesterday_total is not None:
            gbp_new_reviews = max(0, gbp_total_reviews - gbp_yesterday_total)
        else:
            gbp_new_reviews = 0
    else:
        gbp_new_reviews = None

    return {
        "jobs_run_count": jobs_run_count,
        "jobs_sold_count": jobs_sold_count,
        "jobs_invoiced_count": jobs_invoiced_count,
        "collected_cents": collected_cents,
        "amex_spend_cents": amex_spend_cents,
        "net_cents": net_cents,
        "gbp_total_reviews": gbp_total_reviews,
        "gbp_new_reviews": gbp_new_reviews,
        "gbp_avg_rating": gbp_avg_rating,
    }
