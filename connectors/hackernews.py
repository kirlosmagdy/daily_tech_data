import time
from connectors.common import cutoff_utc, fetch_response, make_result, save_raw
from pipeline.config import load_config

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


# Extract Hacker News stories from the last 48 hours using the Algolia HN API.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff_ts = int(cutoff_utc(cfg["project"]["lookback_hours"]).timestamp())
    seen, items, errors = set(), [], []

    for page in range(3):
        try:
            params = {
                "tags": "story",
                "numericFilters": f"created_at_i>{cutoff_ts}",
                "hitsPerPage": 100,
                "page": page,
            }
            resp = fetch_response(ALGOLIA_URL, params=params, delay=0.5 if page > 0 else 0.0)
            hits = resp.json().get("hits", [])
            for h in hits:
                oid = str(h.get("objectID", ""))
                if oid and oid not in seen and h.get("url"):
                    seen.add(oid)
                    items.append(h)
            if len(hits) < 100:
                break
        except Exception as exc:
            errors.append(str(exc))
            break

    status = "ok" if items and not errors else ("partial" if items else "failed")
    return make_result("hackernews", status, items, start, "; ".join(errors) if errors else None)


if __name__ == "__main__":
    save_raw(extract(load_config()))