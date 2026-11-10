import time
import feedparser
from connectors.common import cutoff_utc, fetch_response, make_result, parse_dt, save_raw
from pipeline.config import load_config

ARXIV_URL = "https://export.arxiv.org/api/query"


# Extract recent arXiv papers in configured categories while respecting the 3-second spacing rule.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff = cutoff_utc(cfg["project"]["lookback_hours"])
    weekend_cutoff = cutoff_utc(96)
    cats = cfg["sources"]["arxiv"]["categories"]
    query = "+OR+".join(f"cat:{c}" for c in cats)
    url = f"{ARXIV_URL}?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results=100"

    items, weekend_items = [], []
    try:
        resp = fetch_response(url, timeout=25, delay=3.0)
        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            pub = parse_dt(entry.get("published") or entry.get("updated"))
            record = {
                "id": entry.get("id"),
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
        if not items:
            items = weekend_items
        return make_result("arxiv", "ok" if items else "failed", items, start, None if items else "No recent papers")
    except Exception as exc:
        return make_result("arxiv", "failed", [], start, str(exc))


if __name__ == "__main__":
    save_raw(extract(load_config()))