import os
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from connectors.common import make_result, save_raw
from pipeline.config import load_config

API_BASE = "https://api.daily.dev/public/v1"


# Keep only the fields needed by the shared pipeline schema.
def map_post(post: dict) -> dict:
    source = post.get("source") or {}
    return {
        "id": str(post.get("id") or ""),
        "title": post.get("title") or "",
        "url": post.get("url") or "",
        "summary": (post.get("summary") or "")[:300],
        "tags": post.get("tags") if isinstance(post.get("tags"), list) else [],
        "author": source.get("name") or "",
        "createdAt": post.get("createdAt"),
        "numUpvotes": int(post.get("numUpvotes") or 0),
        "numComments": int(post.get("numComments") or 0),
    }


# Fetch one popular feed and up to three configured tag feeds within the free monthly quota.
def extract(cfg: dict) -> dict:
    start = time.time()
    load_dotenv()
    token = os.getenv("DAILY_DEV_TOKEN", "").strip()
    if not token:
        result = make_result("dailydev", "degraded", [], start, "DAILY_DEV_TOKEN is not set.")
        result["requests_made"] = 0
        print("[dailydev] API requests=0; DAILY_DEV_TOKEN is not set.")
        return result

    source_cfg = cfg["sources"]["dailydev"]
    max_requests = min(max(int(source_cfg.get("max_requests_per_run", 4)), 1), 4)
    page_size = min(max(int(source_cfg.get("page_size", 25)), 1), 50)
    paths = ["feeds/popular"] + [
        f"feeds/tag/{quote(str(tag), safe='')}" for tag in source_cfg.get("tags", [])
    ]
    paths = paths[:max_requests]

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    items, errors = [], []
    requests_made = 0
    seen = set()
    access_degraded = False

    for path in paths:
        requests_made += 1
        try:
            response = requests.get(
                f"{API_BASE}/{path}",
                headers=headers,
                params={"limit": page_size},
                timeout=20,
            )
            if response.status_code in (401, 403, 429):
                errors.append(f"{path}: HTTP {response.status_code}; stopping daily.dev requests.")
                access_degraded = True
                break
            response.raise_for_status()
            payload = response.json()
            posts = payload.get("data", [])
            if not isinstance(posts, list):
                raise ValueError("API response field 'data' is not a list.")

            for post in posts:
                item = map_post(post)
                if item["id"] and item["url"] and item["id"] not in seen:
                    seen.add(item["id"])
                    items.append(item)
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{path}: {exc}")

    status = "degraded" if access_degraded else ("ok" if items and not errors else ("partial" if items else "degraded"))
    result = make_result("dailydev", status, items, start, "; ".join(errors) if errors else None)
    result["requests_made"] = requests_made
    print(f"[dailydev] API requests={requests_made}/{max_requests}, page_size={page_size}, items={len(items)}")
    return result


if __name__ == "__main__":
    save_raw(extract(load_config()))
