import time
import feedparser
from connectors.common import cutoff_utc, make_result, parse_datetime_utc, request_with_retry

ARXIV_API_URL = "http://export.arxiv.org/api/query"


# Fetch recent arXiv papers per configured category with deduplication and weekend fallback.
def extract(cfg: dict) -> dict:
    start = time.time()
    src_cfg = cfg["sources"].get("arxiv", {})
    if not src_cfg.get("enabled", True):
        return make_result("arxiv", "ok", [], start)

    categories = src_cfg.get("categories", ["cs.AI", "cs.LG", "cs.DB"])
    lookback_hours = cfg["project"].get("lookback_hours", 36)
    strict_cutoff = cutoff_utc(lookback_hours)
    fallback_cutoff = cutoff_utc(max(lookback_hours, 96))

    raw_entries = []
    seen_ids = set()
    errors = []

    for idx, cat in enumerate(categories):
        if idx > 0:
            time.sleep(3)
        params = {
            "search_query": f"cat:{cat}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": 0,
            "max_results": 40,
        }
        try:
            resp = request_with_retry(ARXIV_API_URL, params=params, timeout=20)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                raw_id = entry.get("id") or entry.get("link") or ""
                base_id = raw_id.split("/abs/")[-1].split("v")[0] if "/abs/" in raw_id else raw_id
                if not base_id or base_id in seen_ids:
                    continue
                seen_ids.add(base_id)
                authors = [a.get("name", "") for a in entry.get("authors", []) if a.get("name")]
                tags = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]
                raw_entries.append({
                    "id": base_id,
                    "url": entry.get("link") or raw_id,
                    "title": " ".join((entry.get("title") or "").split()),
                    "summary": " ".join((entry.get("summary") or "").split()),
                    "author": ", ".join(authors[:3]),
                    "published": entry.get("published") or entry.get("updated"),
                    "tags": tags or [cat],
                })
        except Exception as exc:
            errors.append(f"{cat}: {exc}")

    recent = [
        item for item in raw_entries
        if (dt := parse_datetime_utc(item.get("published"))) and dt >= strict_cutoff
    ]
    if not recent:
        recent = [
            item for item in raw_entries
            if (dt := parse_datetime_utc(item.get("published"))) and dt >= fallback_cutoff
        ] or raw_entries

    status = "ok" if not errors else ("partial" if recent else "failed")
    err_msg = "; ".join(errors) if errors else None
    return make_result("arxiv", status, recent, start, err_msg)