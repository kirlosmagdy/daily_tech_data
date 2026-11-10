import time
from connectors.common import cutoff_utc, fetch_response, make_result, parse_dt, save_raw
from pipeline.config import load_config

DEVTO_URL = "https://dev.to/api/articles"


# Extract recent dev.to articles across configured tags within the lookback window.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff = cutoff_utc(cfg["project"]["lookback_hours"])
    tags = cfg["sources"]["devto"]["tags"]
    seen, items, errors = set(), [], []

    for i, tag in enumerate(tags):
        try:
            resp = fetch_response(DEVTO_URL, params={"tag": tag, "per_page": 40}, delay=1.0 if i > 0 else 0.0)
            for art in resp.json():
                aid = art.get("id")
                pub = parse_dt(art.get("published_at") or art.get("created_at"))
                if aid and aid not in seen and pub and pub >= cutoff:
                    seen.add(aid)
                    items.append(art)
        except Exception as exc:
            errors.append(f"{tag}: {exc}")

    status = "ok" if items and not errors else ("partial" if items else "failed")
    return make_result("devto", status, items, start, "; ".join(errors) if errors else None)


if __name__ == "__main__":
    save_raw(extract(load_config()))