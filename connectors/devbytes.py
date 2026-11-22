from datetime import datetime, timezone
import re
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from connectors.common import cutoff_utc, fetch_response, make_result, save_raw
from pipeline.config import load_config

BASE_URL = "https://devbytes.co.in"
START_URL = f"{BASE_URL}/news"
DATE_RE = re.compile(r"^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}$")
SLUG_RE = re.compile(r"""newsSidebar\([^,]+,\s*["']([^"']+)["']\)""")

# Parse one DevBytes news HTML page into an article dict and the next ("Previous") URL.
def parse_article_page(html: str, page_url: str, max_snippet: int = 300) -> tuple[dict | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""

    prose = soup.find("div", class_="prose")
    snippet = prose.get_text(" ", strip=True)[:max_snippet] if prose else ""

    pub_dt = None
    for p in soup.find_all("p"):
        txt = p.get_text(" ", strip=True)
        if DATE_RE.match(txt):
            pub_dt = datetime.strptime(txt, "%b %d, %Y").replace(tzinfo=timezone.utc)
            break

    prev_url = None
    for a in soup.find_all("a", href=True):
        if a.get_text(" ", strip=True).lower() == "previous" and a["href"].startswith("/news/"):
            prev_url = urljoin(BASE_URL, a["href"])
            break

    if not title or not pub_dt:
        return None, prev_url

    canon_link = soup.find("link", rel="canonical")
    url = canon_link.get("href", "").strip() if canon_link else page_url
    if url.rstrip("/") == START_URL:
        aside = soup.find("aside", attrs={"x-data": True})
        x_data = aside.get("x-data", "") if aside else ""
        match = SLUG_RE.search(x_data) or SLUG_RE.search(html)
        if match:
            url = f"{START_URL}/{match.group(1)}"

    slug = url.rstrip("/").split("/")[-1]
    record = {
        "id": slug,
        "title": title,
        "url": url,
        "snippet": snippet,
        "published_at": pub_dt.isoformat(),
        "author": "DevBytes",
    }
    return record, prev_url


# Extract recent news summaries from devbytes.co.in by following Previous links up to the 48h cutoff.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff_date = cutoff_utc(cfg["project"]["lookback_hours"]).date()
    max_snippet = cfg["project"].get("max_snippet_length", 300)
    src_cfg = cfg["sources"]["devbytes"]
    max_pages = min(int(src_cfg.get("max_pages", 40)), 40)
    delay_s = float(src_cfg.get("delay_seconds", 1.0))

    visited, seen_urls, items, errors = set(), set(), [], []
    url = START_URL

    for page_idx in range(max_pages):
        if not url or url in visited:
            break
        visited.add(url)
        try:
            resp = fetch_response(url, timeout=20, delay=delay_s if page_idx > 0 else 0.0, stop_on_status=(403, 429))
            if resp.status_code in (403, 429):
                errors.append(f"HTTP {resp.status_code} on {url}")
                return make_result("devbytes", "degraded", items, start, "; ".join(errors))
            record, prev_url = parse_article_page(resp.text, url, max_snippet)
            if not record:
                if page_idx == 0:
                    return make_result("devbytes", "skipped", [], start, "Page structure changed or date missing")
                break
            pub_date = datetime.fromisoformat(record["published_at"]).date()
            if pub_date < cutoff_date:
                break
            if record["url"] not in seen_urls:
                seen_urls.add(record["url"])
                items.append(record)
            url = prev_url
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            break

    if items and not errors:
        status = "ok"
    elif items:
        status = "partial"
    else:
        status = "skipped"
    return make_result("devbytes", status, items, start, "; ".join(errors) if errors else None)


if __name__ == "__main__":
    save_raw(extract(load_config()))