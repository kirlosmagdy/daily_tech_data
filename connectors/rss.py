from datetime import datetime, timezone
import time
import feedparser
from connectors.common import cutoff_utc, fetch_response, make_result, parse_dt, save_raw
from pipeline.config import load_config


# Parse struct_time from feedparser into a UTC datetime.
def _entry_dt(entry: dict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            return datetime(*st[:6], tzinfo=timezone.utc)
    return parse_dt(entry.get("published") or entry.get("updated"))


# Extract recent entries from all configured official RSS/Atom feeds.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff = cutoff_utc(cfg["project"]["lookback_hours"])
    feeds = cfg["sources"]["rss"]["feeds"]
    seen, items, fallback_items, errors = set(), [], [], []

    for i, feed_cfg in enumerate(feeds):
        name, url = feed_cfg["name"], feed_cfg["url"]
        try:
            resp = fetch_response(url, delay=0.4 if i > 0 else 0.0)
            parsed = feedparser.parse(resp.content)
            for idx, entry in enumerate(parsed.entries):
                link = entry.get("link")
                if not link or link in seen:
                    continue
                dt = _entry_dt(entry)
                record = {
                    "feed_name": name,
                    "feed_url": url,
                    "id": entry.get("id") or link,
                    "title": entry.get("title", ""),
                    "link": link,
                    "summary": (entry.get("summary") or entry.get("description") or "")[:1000],
                    "author": entry.get("author", name),
                    "published_at": dt.isoformat() if dt else None,
                    "tags": [t.get("term", "") for t in entry.get("tags", []) if t.get("term")],
                }
                if dt and dt >= cutoff:
                    seen.add(link)
                    items.append(record)
                elif idx < 2 and dt:
                    fallback_items.append(record)
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if len(items) < 15:
        for r in fallback_items:
            if r["link"] not in seen:
                seen.add(r["link"])
                items.append(r)

    status = "ok" if items and not errors else ("partial" if items else "failed")
    return make_result("rss", status, items, start, "; ".join(errors) if errors else None)


if __name__ == "__main__":
    save_raw(extract(load_config()))