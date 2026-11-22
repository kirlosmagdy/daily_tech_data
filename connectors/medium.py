import re
import time
from bs4 import BeautifulSoup
import feedparser
from connectors.common import cutoff_utc, fetch_response, make_result, save_raw
from connectors.rss import _entry_dt
from pipeline.config import load_config


# Strip HTML from a Medium RSS entry and keep at most max_len characters (never store full text).
def _make_snippet(entry: dict, max_len: int = 300) -> str:
    raw = entry.get("summary") or entry.get("description") or ""
    if not raw:
        return ""
    text = BeautifulSoup(str(raw), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()[:max_len].strip()


# Extract recent articles from Medium topic and publication RSS feeds.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff = cutoff_utc(cfg["project"]["lookback_hours"])
    max_snippet = cfg["project"].get("max_snippet_length", 300)
    src_cfg = cfg["sources"]["medium"]

    feeds = [
        *((f"tag:{t}", f"https://medium.com/feed/tag/{t}") for t in src_cfg.get("tags", [])),
        *((f"pub:{p}", f"https://medium.com/feed/{p}") for p in src_cfg.get("publications", [])),
    ]

    seen, items, errors = set(), [], []
    degraded = False

    for i, (feed_name, url) in enumerate(feeds):
        try:
            resp = fetch_response(url, timeout=20, delay=0.5 if i > 0 else 0.0, stop_on_status=(403, 429))
            if resp.status_code in (403, 429):
                degraded = True
                errors.append(f"{feed_name}: HTTP {resp.status_code}")
                break
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries:
                link = (entry.get("link") or "").split("?")[0]
                dt = _entry_dt(entry)
                if not link or link in seen or not dt or dt < cutoff:
                    continue
                seen.add(link)
                items.append({
                    "id": entry.get("id") or link,
                    "feed_name": feed_name,
                    "title": (entry.get("title") or "").strip(),
                    "link": link,
                    "author": (entry.get("author") or feed_name).strip(),
                    "published_at": dt.isoformat(),
                    "snippet": _make_snippet(entry, max_snippet),
                    "tags": [t.get("term", "") for t in entry.get("tags", []) if t.get("term")],
                })
        except Exception as exc:
            errors.append(f"{feed_name}: {exc}")

    if degraded:
        status = "degraded"
    elif items and not errors:
        status = "ok"
    elif items:
        status = "partial"
    else:
        status = "failed"
    return make_result("medium", status, items, start, "; ".join(errors) if errors else None)


if __name__ == "__main__":
    save_raw(extract(load_config()))