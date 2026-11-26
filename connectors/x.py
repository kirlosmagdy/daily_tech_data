import os
import time
from connectors.common import cutoff_utc, fetch_response, logger, make_result, parse_dt
from pipeline.config import load_config

X_RECENT_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

DEFAULT_QUERIES = [
    '("data engineering" OR duckdb OR dbt OR airflow OR parquet) lang:en -is:retweet',
    '("ai" OR "llm" OR "machine learning" OR "data science") lang:en -is:retweet',
]


# Extract tweets via X API v2 Recent Search when X_BEARER_TOKEN is configured.
def extract(cfg: dict | None = None) -> dict:
    start = time.time()
    cfg = cfg or load_config()
    src_cfg = cfg["sources"].get("x", {})
    lookback_hours = cfg["project"].get("lookback_hours", 48)
    max_snippet = cfg["project"].get("max_snippet_length", 300)

    token = os.getenv("X_BEARER_TOKEN", "").strip()
    if not token:
        return make_result("x", "degraded", [], start, "X_BEARER_TOKEN not set")

    queries = src_cfg.get("queries") or DEFAULT_QUERIES
    handles = [h.lstrip("@").strip() for h in (src_cfg.get("handles") or []) if str(h).strip()]
    if handles:
        handle_clause = " OR ".join(f"from:{h}" for h in handles[:10])
        queries = [*queries, f"({handle_clause}) lang:en -is:retweet"]

    start_time_iso = cutoff_utc(lookback_hours).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {"Authorization": f"Bearer {token}"}

    items: list[dict] = []
    seen_ids: set[str] = set()
    errors: list[str] = []
    ok_calls = 0

    for query in queries:
        params = {
            "query": query,
            "max_results": 25,
            "start_time": start_time_iso,
            "tweet.fields": "created_at,public_metrics,lang,author_id",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        try:
            resp = fetch_response(
                X_RECENT_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=15,
                delay=0.5,
                stop_on_status=(400, 401, 403, 429),
            )
            if resp.status_code in (401, 403):
                errors.append(f"HTTP {resp.status_code} (check X_BEARER_TOKEN)")
                break
            if resp.status_code in (400, 429):
                errors.append(f"HTTP {resp.status_code} for query")
                continue

            ok_calls += 1
            payload = resp.json()
            users = {
                u.get("id"): u
                for u in (payload.get("includes") or {}).get("users") or []
                if isinstance(u, dict) and u.get("id")
            }

            for tw in payload.get("data") or []:
                if not isinstance(tw, dict):
                    continue
                tid = str(tw.get("id") or "").strip()
                if not tid or tid in seen_ids:
                    continue
                seen_ids.add(tid)

                pub = parse_dt(tw.get("created_at"))
                if not pub or pub < cutoff_utc(lookback_hours):
                    continue

                user = users.get(tw.get("author_id")) or {}
                username = (user.get("username") or "").strip()
                author_name = (user.get("name") or username or "X").strip()
                text = (tw.get("text") or "").strip().replace("\n", " ")
                title = text[:120] + ("..." if len(text) > 120 else "")
                snippet = text[:max_snippet]
                url = (
                    f"https://x.com/{username}/status/{tid}"
                    if username
                    else f"https://x.com/i/web/status/{tid}"
                )
                metrics = tw.get("public_metrics") or {}
                score = (
                    int(metrics.get("like_count") or 0)
                    + int(metrics.get("retweet_count") or 0)
                    + int(metrics.get("reply_count") or 0)
                )

                items.append({
                    "id": tid,
                    "url": url,
                    "title": title,
                    "snippet": snippet,
                    "author": author_name,
                    "username": username,
                    "published_at": pub.isoformat(),
                    "score": score,
                    "comments": int(metrics.get("reply_count") or 0),
                    "tags": ["x", "social"],
                })
        except Exception as exc:
            errors.append(str(exc))
            logger.warning("[x] Query failed: %s", exc)

    if items:
        status = "ok" if not errors else "partial"
    elif ok_calls > 0 and not errors:
        status = "ok"
    elif errors:
        status = "degraded"
    else:
        status = "degraded"

    return make_result("x", status, items, start, "; ".join(errors) if errors else None)