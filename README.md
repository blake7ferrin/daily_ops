# Daily Ops

Daily job that pulls Housecall Pro and optionally Google reviews (via Places API + business name) and Plaid (AMEX) metrics and sends a Telegram summary. Secrets are supplied via **Doppler**; run with `doppler run -- python -m src.main`. Omit Places vars to skip Google Reviews (shows N/A). Omit Plaid vars to skip AMEX spend and Net (shows N/A).

## Doppler setup

1. Install [Doppler CLI](https://docs.doppler.com/docs/install-cli) and run `doppler login`.
2. Create a project (e.g. `daily_ops`) and config (e.g. `dev`, `prd`).
3. In the project directory, run `doppler setup` to link the project.
4. Add the following variables in Doppler (Dashboard or CLI).

### Required variables

| Variable | Description |
| ---------- | ------------- |
| **Housecall Pro** | |
| `HCP_API_KEY` | API key for Housecall Pro |
| `HCP_BASE_URL` | Base URL (optional; default: `https://api.housecallpro.com`) |
| `HCP_AUTH_HEADER` | Optional: `bearer` (default) or `api_key`. Use `api_key` if HCP expects `X-API-Key` header instead of `Authorization: Bearer`. |
| **Telegram** | |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Chat or channel ID to receive messages |
| **Runtime** | |
| `TIMEZONE` | e.g. `America/Phoenix` |

### Optional

| Variable | Description |
| ---------- | ------------- |
| **Google reviews (Places API)** | Omit all to skip; Google Reviews will show N/A |
| `PLACES_API_KEY` | Google Maps Platform API key (Places API enabled) |
| `PLACES_PLACE_ID` | Optional: Place ID (ChIJ...) to pin the listing |
| `PLACES_CID` | Optional: Maps CID (from `https://maps.google.com/?cid=...`) |
| `PLACES_MAPS_URL` | Optional: Google Maps share URL (we'll extract cid/ftid) |
| `BUSINESS_NAME` | Fallback: business name text search (least reliable) |
| `REVIEWS_TOTAL_OVERRIDE` | Optional: override total review count (integer) |
| `REVIEWS_DELTA_OVERRIDE` | Optional: override new reviews since yesterday (integer) |

Places lookup precedence is `PLACES_PLACE_ID` → `PLACES_CID` → `PLACES_MAPS_URL` → `BUSINESS_NAME`.
If `REVIEWS_TOTAL_OVERRIDE` is set, it skips the Places lookup and uses the override value.
| **Plaid (AMEX spend)** | Omit all to skip; AMEX spend and Net will show N/A |
| `PLAID_CLIENT_ID` | Plaid client ID |
| `PLAID_SECRET` | Plaid secret |
| `PLAID_ENV` | `sandbox` or `production` |
| `PLAID_ACCESS_TOKEN` | Plaid access token for linked Item |
| `PLAID_AMEX_ACCOUNT_ID` | Plaid account ID for AMEX (if multiple accounts) |
| `SNAPSHOT_DB_PATH` | Path to SQLite snapshot DB (default: `data/snapshots.db` under project) |

## Run locally

From the `daily_ops` directory (run `doppler setup` there first so Doppler knows the project):

```bash
# Today (in TIMEZONE)
doppler run -- python -m src.main

# Specific date (test run)
doppler run -- python -m src.main --date 2025-02-02
```

Or double‑click **run_daily_ops.bat** (after `doppler setup` in that folder).

## Scheduling

The job uses `TIMEZONE` to determine "today", so schedule it for 7:00 PM local time.

### Windows (Task Scheduler)

A task **Daily Ops** is set to run at **7:00 PM local time** every day. It runs `run_daily_ops.bat`, which runs the job with Doppler. Ensure Doppler CLI is installed and you’ve run `doppler login` and `doppler setup` in `daily_ops` so the task can inject secrets.

To change the time or view the task: **Task Scheduler** → Task Scheduler Library → **Daily Ops**.

### Linux / cron

Example: run daily at 7:00 PM Arizona time:

```bash
0 19 * * * TZ=America/Phoenix cd /path/to/daily_ops && doppler run -- python3 -m src.main >> /var/log/daily_ops.log 2>&1
```

For unattended cron, use a [Doppler service token](https://docs.doppler.com/docs/service-tokens) and set `DOPPLER_TOKEN` in the environment.
