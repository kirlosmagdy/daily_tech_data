from connectors.common import save_raw
from connectors.rss import run_feeds
from pipeline.config import load_config


# Extract recent articles from configured Medium tag and publication RSS feeds.
def extract(cfg: dict) -> dict:
    src_cfg = cfg["sources"]["medium"]
    feeds = [
        *((f"tag:{t}", f"https://medium.com/feed/tag/{t}") for t in src_cfg.get("tags", [])),
        *((f"pub:{p}", f"https://medium.com/feed/{p}") for p in src_cfg.get("publications", [])),
    ]
    return run_feeds(feeds, "medium", cfg, allow_fallback=False)


if __name__ == "__main__":
    save_raw(extract(load_config()))