import os
import time
from connectors.common import cutoff_utc, fetch_response, logger, make_result, parse_dt, save_raw
from pipeline.config import load_config

BASE_URL = "https://api.daily.dev/public/v1"
MAX_REQUESTS = 4
PAGE_LIMIT = 50


# Extract recent posts from the official daily.dev Public API (hard cap: 4 requests/run).
def extract(cfg: dict) -> dict:
    start = time.time()
    token = os.getenv("DAILY_DEV_TOKEN", "").strip()
    if not token:
        return make_result("daily_dev", "degraded", [], start, "DAILY_DEV_TOKEN not set")

    cutoff = cutoff_utc(cfg["project"]["lookback_hours"])
    max_snippet = cfg["project"].get("max_snippet_length", 300)
    tags = cfg["sources"]["daily_dev"].get("tags", [])[: MAX_REQUESTS - 1]
    endpoints = [("/feeds/popular", "popular")] + [(f"/feeds/tag/{t}", t) for t in tags]

    headers = {"Authorization": f"Bearer {token}"}
    seen, items, errors = set(), [], []
    requests_used = 0
    degraded = False

    for i, (path, label) in enumerate(endpoints[:MAX_REQUESTS]):
        requests_used += 1
        try:
            resp = fetch_response(
                f"{BASE_URL}{path}",
                params={"limit": PAGE_LIMIT},
                headers=headers,
                timeout=20,
                delay=0.5 if i > 0 else 0.0,
                stop_on_status=(403, 429),
            )
            if resp.status_code in (403, 429):
                degraded = True
                errors.append(f"{label}: HTTP {resp.status_code}")
                break
            posts = resp.json().get("data") or []
            for post in posts:
                url = (post.get("url") or "").strip()
                dt = parse_dt(post.get("publishedAt") or post.get("createdAt"))
                if not url or url in seen or not dt or dt < cutoff:
                    continue
                seen.add(url)
                author_obj = post.get("author") or {}
                source_obj = post.get("source") or {}
                items.append({
                    "id": str(post.get("id") or url),
                    "title": (post.get("title") or "").strip(),
                    "url": url,
                    "summary": (post.get("summary") or "")[:max_snippet],
                    "publishedAt": dt.isoformat(),
                    "author": author_obj.get("name") or author_obj.get("username") or source_obj.get("name") or "",
                    "tags": post.get("tags") or [],
                    "numUpvotes": int(post.get("numUpvotes") or 0),
                    "numComments": int(post.get("numComments") or 0),
                })
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    logger.info("[daily_dev] requests_used=%d/%d items=%d", requests_used, MAX_REQUESTS, len(items))
    if degraded:
        status = "degraded"
    elif items and not errors:
        status = "ok"
    elif items:
        status = "partial"
    else:
        status = "failed"
    return make_result("daily_dev", status, items, start, "; ".join(errors) if errors else None)


if __name__ == "__main__":
    save_raw(extract(load_config()))