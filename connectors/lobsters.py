import time
from connectors.common import cutoff_utc, fetch_response, make_result, parse_dt, save_raw
from pipeline.config import load_config


# Extract recent stories from Lobsters hottest, newest, and configured tag JSON feeds.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff = cutoff_utc(cfg["project"]["lookback_hours"])
    tags = cfg["sources"]["lobsters"]["tags"]
    urls = ["https://lobste.rs/hottest.json", "https://lobste.rs/newest.json"] + [
        f"https://lobste.rs/t/{t}.json" for t in tags
    ]
    seen, items, errors = set(), [], []

    for i, url in enumerate(urls):
        try:
            resp = fetch_response(url, delay=1.2 if i > 0 else 0.0)
            for story in resp.json():
                sid = story.get("short_id")
                pub = parse_dt(story.get("created_at"))
                if sid and sid not in seen and pub and pub >= cutoff and story.get("url"):
                    seen.add(sid)
                    items.append(story)
        except Exception as exc:
            errors.append(f"{url}: {exc}")

    status = "ok" if items and not errors else ("partial" if items else "failed")
    return make_result("lobsters", status, items, start, "; ".join(errors) if errors else None)


if __name__ == "__main__":
    save_raw(extract(load_config()))