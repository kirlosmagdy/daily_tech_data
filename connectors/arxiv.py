import time
import feedparser
from connectors.common import cutoff_utc, fetch_response, make_result, parse_dt, save_raw
from pipeline.config import load_config

ARXIV_URL = "https://export.arxiv.org/api/query"


# Extract recent arXiv papers per category with 3s spacing, ID deduplication, and weekend fallback.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff = cutoff_utc(cfg["project"]["lookback_hours"])
    weekend_cutoff = cutoff_utc(96)
    cats = cfg["sources"]["arxiv"]["categories"]

    items, weekend_items = [], []
    seen_ids = set()
    errors = []

    for idx, cat in enumerate(cats):
        url = f"{ARXIV_URL}?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&max_results=40"
        try:
            resp = fetch_response(url, timeout=25, delay=3.0 if idx > 0 else 0.0)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                entry_id = entry.get("id")
                if not entry_id or entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)
                pub = parse_dt(entry.get("published") or entry.get("updated"))
                record = {
                    "id": entry_id,
                    "title": " ".join((entry.get("title") or "").split()),
                    "summary": " ".join((entry.get("summary") or "").split()),
                    "author": ", ".join(a.get("name", "") for a in entry.get("authors", [])[:3]),
                    "published_at": pub.isoformat() if pub else None,
                    "tags": [t.get("term", "") for t in entry.get("tags", []) if t.get("term")],
                }
                if pub and pub >= cutoff:
                    items.append(record)
                elif pub and pub >= weekend_cutoff:
                    weekend_items.append(record)
        except Exception as exc:
            errors.append(f"{cat}: {exc}")

    if not items:
        items = weekend_items
    status = "ok" if (items and not errors) else ("partial" if items else "failed")
    err = "; ".join(errors) if errors else (None if items else "No recent papers")
    return make_result("arxiv", status, items, start, err)


if __name__ == "__main__":
    save_raw(extract(load_config()))