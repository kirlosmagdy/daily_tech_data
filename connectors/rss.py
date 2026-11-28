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


# Fetch entries from RSS/Atom feeds and keep only items within the lookback window.
def run_feeds(feeds: list[tuple[str, str]], source_name: str, cfg: dict, allow_fallback: bool = False) -> dict:
    start = time.time()
    cutoff = cutoff_utc(cfg["project"]["lookback_hours"])
    seen, items, fallback_items, errors = set(), [], [], []
    degraded = False

    for i, (name, url) in enumerate(feeds):
        try:
            resp = fetch_response(url, timeout=20 if source_name == "medium" else 30, delay=0.5 if (source_name == "medium" and i > 0) else (0.4 if i > 0 else 0.0), stop_on_status=(403, 429) if source_name == "medium" else ())
            if source_name == "medium" and resp.status_code in (403, 429):
                degraded = True
                errors.append(f"{name}: HTTP {resp.status_code}")
                break
            parsed = feedparser.parse(resp.content)
            for idx, entry in enumerate(parsed.entries):
                link = (entry.get("link") or "").split("?")[0] if source_name == "medium" else entry.get("link")
                if not link or link in seen:
                    continue
                dt = _entry_dt(entry)
                if not dt:
                    continue
                record = {
                    "feed_name": name,
                    "feed_url": url,
                    "id": entry.get("id") or link,
                    "title": (entry.get("title") or "").strip() if source_name == "medium" else entry.get("title", ""),
                    "link": link,
                    "summary": (entry.get("summary") or entry.get("description") or "")[:300 if source_name == "medium" else 1000],
                    "snippet": (entry.get("summary") or entry.get("description") or "")[:300],
                    "author": (entry.get("author") or name).strip() if source_name == "medium" else entry.get("author", name),
                    "published_at": dt.isoformat(),
                    "tags": [t.get("term", "") for t in entry.get("tags", []) if t.get("term")],
                }
                if dt >= cutoff:
                    seen.add(link)
                    items.append(record)
                elif allow_fallback and idx < 2:
                    fallback_items.append(record)
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if allow_fallback and len(items) < 15:
        for r in fallback_items:
            if r["link"] not in seen:
                seen.add(r["link"])
                items.append(r)

    if degraded:
        status = "degraded"
    elif items and not errors:
        status = "ok"
    elif items:
        status = "partial"
    else:
        status = "failed"
    return make_result(source_name, status, items, start, "; ".join(errors) if errors else None)


# Extract recent entries from configured RSS/Atom feeds.
def extract(cfg: dict) -> dict:
    feeds = [(f["name"], f["url"]) for f in cfg["sources"]["rss"]["feeds"]]
    return run_feeds(feeds, "rss", cfg, allow_fallback=True)


if __name__ == "__main__":
    save_raw(extract(load_config()))