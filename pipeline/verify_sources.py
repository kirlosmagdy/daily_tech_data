import json
import time
import feedparser
import requests
from pipeline.config import ROOT_DIR, load_config

FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"
HEADERS = {"User-Agent": "DailyTechDataPulse/1.1 (+https://github.com/kirlosmagdy/daily_tech_data)"}


# Save a trimmed sample payload to tests/fixtures as formatted JSON.
def save_fixture(name: str, data: dict | list) -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURES_DIR / f"{name}_sample.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Saved fixture -> {path.relative_to(ROOT_DIR)}")


# Test core endpoints, verify RSS feeds, and generate trimmed test fixtures.
def main() -> None:
    cfg = load_config()

    print("1. Verifying Hacker News (Algolia API)...")
    r = requests.get("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=2", headers=HEADERS, timeout=15)
    r.raise_for_status()
    save_fixture("hackernews", {"hits": r.json().get("hits", [])[:2]})

    print("2. Verifying dev.to API...")
    r = requests.get("https://dev.to/api/articles?tag=dataengineering&per_page=2", headers=HEADERS, timeout=15)
    r.raise_for_status()
    save_fixture("devto", r.json()[:2])

    print("3. Verifying Lobsters JSON & configured tags...")
    r = requests.get("https://lobste.rs/hottest.json", headers=HEADERS, timeout=15)
    r.raise_for_status()
    save_fixture("lobsters", r.json()[:2])
    for tag in cfg["sources"]["lobsters"]["tags"]:
        time.sleep(1.2)
        tr = requests.get(f"https://lobste.rs/t/{tag}.json", headers=HEADERS, timeout=15)
        items = tr.json() if tr.status_code == 200 else []
        print(f"   - tag '{tag}': HTTP {tr.status_code} ({len(items)} items)")

    print("4. Verifying GitHub Search API...")
    r = requests.get(
        "https://api.github.com/search/repositories?q=topic:duckdb&sort=stars&order=desc&per_page=2",
        headers={**HEADERS, "Accept": "application/vnd.github+json"},
        timeout=15,
    )
    r.raise_for_status()
    save_fixture("github", {"items": r.json().get("items", [])[:2]})

    print("5. Verifying arXiv API...")
    r = requests.get(
        "https://export.arxiv.org/api/query?search_query=cat:cs.DB+OR+cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=2",
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    feed = feedparser.parse(r.text)
    entries = [{"id": e.get("id"), "title": e.get("title"), "summary": e.get("summary"), "published": e.get("published")} for e in feed.entries[:2]]
    save_fixture("arxiv", {"entries": entries, "raw_xml_snippet": r.text[:1500]})

    print("6. Verifying Hugging Face Daily Papers API...")
    r = requests.get("https://huggingface.co/api/daily_papers?limit=2", headers=HEADERS, timeout=15)
    if r.status_code == 200:
        save_fixture("hf_papers", r.json()[:2])

    print("7. Verifying all 15 RSS feeds...")
    sample_saved = False
    for feed_cfg in cfg["sources"]["rss"]["feeds"]:
        name, url = feed_cfg["name"], feed_cfg["url"]
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            parsed = feedparser.parse(resp.content)
            count = len(parsed.entries)
            status = "OK" if resp.status_code == 200 and count > 0 else f"WARN (HTTP {resp.status_code}, {count} items)"
            print(f"   - {name:<26}: {status}")
            if not sample_saved and count > 0:
                e = parsed.entries[0]
                save_fixture("rss", {"feed_name": name, "feed_url": url, "entries": [{"title": e.get("title"), "link": e.get("link"), "summary": e.get("summary", "")[:300], "published": e.get("published", e.get("updated", ""))}]})
                sample_saved = True
        except Exception as exc:
            print(f"   - {name:<26}: FAILED ({exc})")


if __name__ == "__main__":
    main()