"""Plaid API client: fetch posted transactions for a date range (AMEX spend)."""
from datetime import date

import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions


def _env_to_plaid(env: str):
    e = (env or "").strip().lower()
    if e == "production":
        return plaid.Environment.Production
    if e == "sandbox":
        return plaid.Environment.Sandbox
    return plaid.Environment.Sandbox


def fetch_transactions(
    client_id: str,
    secret: str,
    env: str,
    access_token: str,
    start_date: str,
    end_date: str,
    account_ids: list[str] | None = None,
) -> list[dict]:
    """Fetch all posted transactions for the date range. start_date/end_date are YYYY-MM-DD."""
    configuration = plaid.Configuration(
        host=_env_to_plaid(env),
        api_key={"clientId": client_id, "secret": secret},
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    options = TransactionsGetRequestOptions()
    if account_ids:
        options.account_ids = account_ids
    options.count = 500
    options.offset = 0

    all_txns = []
    while True:
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start,
            end_date=end,
            options=options,
        )
        response = client.transactions_get(request)
        txns = getattr(response, "transactions", None) or []
        total = getattr(response, "total_transactions", None) or 0
        for t in txns:
            all_txns.append(t.to_dict() if hasattr(t, "to_dict") else (t if isinstance(t, dict) else dict(t)))
        if len(all_txns) >= total or len(txns) < 500:
            break
        options.offset = len(all_txns)
    return all_txns
