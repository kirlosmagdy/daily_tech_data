from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import time
import requests
from pipeline.config import ROOT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pulse")

USER_AGENT = "DailyTechDataPulse/1.1 (+https://github.com/kirlosmagdy/daily_tech_data)"


# Return the current UTC timestamp as a timezone-aware datetime.
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# Return the UTC cutoff timestamp for the configured lookback window in hours.
def cutoff_utc(lookback_hours: int = 48) -> datetime:
    return now_utc() - timedelta(hours=lookback_hours)


# Parse an ISO-8601 or RFC-2822 timestamp string into a UTC datetime, or None on failure.
def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None


# Perform an HTTP GET with timeout, 3 retries with increasing waits, custom User-Agent, and polite delay.
def fetch_response(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 15,
    delay: float = 0.5,
) -> requests.Response:
    if delay > 0:
        time.sleep(delay)
    req_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    last_err = None
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=req_headers, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_err = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise RuntimeError(f"Request failed after 3 attempts ({url}): {last_err}")


# Build a standardized connector result dictionary matching the connector contract.
def make_result(source: str, status: str, items: list, start_time: float, error: str | None = None) -> dict:
    return {
        "source": source,
        "status": status,
        "count": len(items),
        "duration_s": round(time.time() - start_time, 2),
        "error": error,
        "collected_at": now_utc().isoformat(),
        "items": items,
    }


# Write the raw connector output to data/raw/YYYY-MM-DD/{source}.json and print a one-line status.
def save_raw(result: dict, date_str: str | None = None) -> None:
    day = date_str or now_utc().strftime("%Y-%m-%d")
    out_dir = ROOT_DIR / "data" / "raw" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{result['source']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    err_note = f" | error={result['error']}" if result.get("error") else ""
    print(f"[{result['source']}] status={result['status']} count={result['count']} duration={result['duration_s']}s -> {out_path.relative_to(ROOT_DIR)}{err_note}")