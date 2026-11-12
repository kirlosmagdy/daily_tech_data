import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from bs4 import BeautifulSoup
import duckdb
from langdetect import DetectorFactory, detect
import pandas as pd
from connectors.common import cutoff_utc, now_utc, parse_dt
from pipeline.config import ROOT_DIR, load_config

DetectorFactory.seed = 0

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid", "_hsenc", "_hsmi",
}
DUCKDB_PATH = ROOT_DIR / "data" / "pulse.duckdb"
SILVER_PARQUET_PATH = ROOT_DIR / "data" / "history" / "silver_items.parquet"


# Resolve the raw data folder for the requested date, or fall back to the newest date folder in data/raw.
def resolve_raw_dir(date_str: str | None = None) -> tuple[str, Path]:
    raw_root = ROOT_DIR / "data" / "raw"
    day = date_str or now_utc().strftime("%Y-%m-%d")
    target = raw_root / day
    if target.exists() and any(target.glob("*.json")):
        return day, target
    subdirs = sorted([d for d in raw_root.iterdir() if d.is_dir() and any(d.glob("*.json"))], reverse=True)
    if not subdirs:
        raise FileNotFoundError("No raw JSON files found in data/raw/. Run 'python -m pipeline.extract' first.")
    return subdirs[0].name, subdirs[0]


# Strip HTML tags and collapse whitespace into a clean single-line string.
def clean_text(raw: str | None, max_len: int | None = None) -> str:
    if not raw:
        return ""
    text = BeautifulSoup(str(raw), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len].strip() if max_len else text


# Normalize a URL by lowercasing the host, removing tracking query parameters, and stripping trailing slashes.
def canonicalize_url(url: str | None) -> str:
    if not url or not str(url).strip():
        return ""
    try:
        parts = urlsplit(str(url).strip())
        if parts.scheme not in ("http", "https") or not parts.netloc:
            return ""
        host = parts.netloc.lower().removeprefix("www.")
        path = re.sub(r"/+$", "", parts.path) or "/"
        if host == "arxiv.org" and path.startswith("/abs/"):
            path = re.sub(r"v\d+$", "", path)
        query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in TRACKING_PARAMS])
        return urlunsplit(("https", host, path, query, ""))
    except Exception:
        return ""


# Detect whether text is in English, avoiding false negatives on short ASCII technical titles.
def is_english(title: str, snippet: str) -> bool:
    combined = f"{title} {snippet}".strip()
    if not combined:
        return False
    non_ascii = sum(1 for c in combined if ord(c) > 127)
    if non_ascii / max(len(combined), 1) > 0.15:
        return False
    if len(combined) < 45:
        return True
    try:
        return detect(combined) == "en"
    except Exception:
        return True


# Map a single raw item from a given source into the unified Silver schema dictionary.
def map_raw_item(source: str, item: dict, collected_at: str, trust_weight: float, max_snippet: int) -> dict:
    if source == "hackernews":
        url = item.get("url") or ""
        title = item.get("title") or ""
        snippet = item.get("story_text") or ""
        item_id = str(item.get("objectID") or item.get("id") or "")
        author = item.get("author") or ""
        pub = parse_dt(item.get("created_at"))
        score = int(item.get("points") or 0)
        comments = int(item.get("num_comments") or 0)
        tags = [t for t in (item.get("_tags") or []) if not t.startswith(("author_", "story_"))]
    elif source == "devto":
        url = item.get("canonical_url") or item.get("url") or ""
        title = item.get("title") or ""
        snippet = item.get("description") or ""
        item_id = str(item.get("id") or "")
        author = (item.get("user") or {}).get("username") or ""
        pub = parse_dt(item.get("published_at") or item.get("created_at"))
        score = int(item.get("public_reactions_count") or item.get("positive_reactions_count") or 0)
        comments = int(item.get("comments_count") or 0)
        tags = item.get("tag_list") if isinstance(item.get("tag_list"), list) else []
    elif source == "lobsters":
        url = item.get("url") or ""
        title = item.get("title") or ""
        snippet = item.get("description_plain") or item.get("description") or ""
        item_id = str(item.get("short_id") or "")
        author = item.get("submitter_user") if isinstance(item.get("submitter_user"), str) else (item.get("submitter_user") or {}).get("username", "")
        pub = parse_dt(item.get("created_at"))
        score = int(item.get("score") or 0)
        comments = int(item.get("comment_count") or 0)
        tags = item.get("tags") or []
    elif source == "rss":
        url = item.get("link") or ""
        title = item.get("title") or ""
        snippet = item.get("summary") or ""
        item_id = str(item.get("id") or url)
        author = item.get("author") or item.get("feed_name") or ""
        pub = parse_dt(item.get("published_at"))
        score = 0
        comments = 0
        tags = item.get("tags") or []
    elif source == "github":
        url = item.get("html_url") or ""
        full_name = item.get("full_name") or ""
        desc = item.get("description") or ""
        title = f"{full_name}: {desc}" if desc else full_name
        snippet = desc
        item_id = str(item.get("id") or "")
        author = item.get("owner_login") or ""
        pub = parse_dt(item.get("pushed_at") or item.get("created_at"))
        score = int(item.get("stargazers_count") or 0)
        comments = int(item.get("open_issues_count") or 0)
        tags = item.get("topics") or ([] if not item.get("language") else [str(item.get("language")).lower()])
    elif source == "arxiv":
        url = item.get("id") or ""
        title = item.get("title") or ""
        snippet = item.get("summary") or ""
        item_id = str(item.get("id") or "").split("/")[-1]
        author = item.get("author") or ""
        pub = parse_dt(item.get("published_at"))
        score = 0
        comments = 0
        tags = item.get("tags") or []
    elif source == "hf_papers":
        paper = item.get("paper") or {}
        pid = str(paper.get("id") or "")
        url = f"https://arxiv.org/abs/{pid}" if pid else ""
        title = paper.get("title") or item.get("title") or ""
        snippet = paper.get("summary") or item.get("summary") or ""
        item_id = pid
        authors = paper.get("authors") or []
        author = ", ".join((a.get("name") or "") for a in authors[:3] if isinstance(a, dict))
        pub = parse_dt(paper.get("publishedAt") or item.get("publishedAt"))
        score = int(paper.get("upvotes") or 0)
        comments = int(item.get("numComments") or 0)
        tags = ["ai", "arxiv"]
    else:
        return {}

    canon = canonicalize_url(url)
    domain = urlsplit(canon).netloc if canon else ""
    pub_iso = (pub or parse_dt(collected_at) or now_utc()).isoformat()

    return {
        "source": source,
        "source_item_id": item_id,
        "canonical_url": canon,
        "title": clean_text(title),
        "snippet": clean_text(snippet, max_len=max_snippet),
        "author": clean_text(author),
        "published_at": pub_iso,
        "collected_at": parse_dt(collected_at).isoformat() if parse_dt(collected_at) else now_utc().isoformat(),
        "source_score": score,
        "comments_count": comments,
        "source_tags": [str(t).lower().strip() for t in tags if str(t).strip()],
        "domain": domain,
        "topics": [],
        "tools_mentioned": [],
        "sentiment": 0.0,
        "trust_weight": float(trust_weight),
        "rank_score": 0.0,
        "mentioned_in_sources": [source],
    }


# Deduplicate records by canonical_url, keeping the highest tier metadata and merging sources and max scores.
def deduplicate_records(records: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for rec in records:
        grouped.setdefault(rec["canonical_url"], []).append(rec)

    deduped = []
    for canon_url, group in grouped.items():
        group.sort(key=lambda r: (r["trust_weight"], r["source_score"], r["published_at"]), reverse=True)
        winner = dict(group[0])
        sources = sorted({s for r in group for s in r.get("mentioned_in_sources", [r["source"]])})
        tags = sorted({t for r in group for t in r.get("source_tags", [])})
        winner["mentioned_in_sources"] = sources
        winner["source_tags"] = tags
        winner["source_score"] = max(r["source_score"] for r in group)
        winner["comments_count"] = max(r["comments_count"] for r in group)
        deduped.append(winner)
    return deduped


# Merge new Silver records with existing 90-day Parquet history and write to Parquet and DuckDB.
def store_silver(new_records: list[dict], retention_days: int = 90) -> int:
    SILVER_PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined = list(new_records)

    if SILVER_PARQUET_PATH.exists():
        try:
            old_df = pd.read_parquet(SILVER_PARQUET_PATH)
            for row in old_df.to_dict(orient="records"):
                for list_col in ("source_tags", "topics", "tools_mentioned", "mentioned_in_sources"):
                    val = row.get(list_col)
                    row[list_col] = list(val) if val is not None else []
                combined.append(row)
        except Exception:
            SILVER_PARQUET_PATH.unlink(missing_ok=True)

    cutoff_iso = cutoff_utc(retention_days * 24).isoformat()
    retained = [r for r in combined if r.get("collected_at", "") >= cutoff_iso]
    final_records = deduplicate_records(retained)
    if not final_records:
        raise ValueError("No valid Silver records to store.")

    df = pd.DataFrame(final_records)
    df.to_parquet(SILVER_PARQUET_PATH, index=False)

    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DUCKDB_PATH)) as con:
        con.execute("CREATE OR REPLACE TABLE silver_items AS SELECT * FROM read_parquet(?)", [str(SILVER_PARQUET_PATH)])
    return len(final_records)


# Normalize raw files, store Silver data, and print the Step 3.4 threshold profile report.
def run_normalize(date_str: str | None = None) -> dict:
    cfg = load_config()
    day, raw_dir = resolve_raw_dir(date_str)
    min_title_len = cfg["thresholds"]["min_title_length"]
    min_scores = cfg["thresholds"]["min_score"]
    max_snippet = cfg["project"]["max_snippet_length"]

    cleaned_records = []
    profile = []

    for source, src_cfg in cfg["sources"].items():
        if not src_cfg.get("enabled", False):
            continue
        raw_file = raw_dir / f"{source}.json"
        if not raw_file.exists():
            continue

        payload = json.loads(raw_file.read_text(encoding="utf-8"))
        raw_items = payload.get("items", [])
        collected_at = payload.get("collected_at") or now_utc().isoformat()
        trust_weight = cfg["trust_tiers"][src_cfg["tier"]]
        min_score = min_scores.get(source, 0)

        total = len(raw_items)
        drop_invalid, drop_lang, drop_score, kept = 0, 0, 0, 0
        scores = []

        for raw_item in raw_items:
            rec = map_raw_item(source, raw_item, collected_at, trust_weight, max_snippet)
            if not rec.get("canonical_url") or len(rec.get("title", "")) < min_title_len:
                drop_invalid += 1
                continue
            if not is_english(rec["title"], rec["snippet"]):
                drop_lang += 1
                continue
            scores.append(rec["source_score"])
            if rec["source_score"] < min_score:
                drop_score += 1
                continue
            kept += 1
            cleaned_records.append(rec)

        s_series = pd.Series(scores, dtype="float64") if scores else pd.Series([0.0])
        profile.append({
            "source": source,
            "raw": total,
            "drop_invalid_pct": round(100 * drop_invalid / max(total, 1), 1),
            "drop_non_en_pct": round(100 * drop_lang / max(total, 1), 1),
            "drop_score_pct": round(100 * drop_score / max(total, 1), 1),
            "kept": kept,
            "min_score_cfg": min_score,
            "score_p25": round(float(s_series.quantile(0.25)), 1),
            "score_median": round(float(s_series.quantile(0.50)), 1),
            "score_p75": round(float(s_series.quantile(0.75)), 1),
            "score_max": int(s_series.max()),
        })

    deduped_today = deduplicate_records(cleaned_records)
    total_silver = store_silver(deduped_today, cfg["project"]["history_retention_days"])

    print(f"\n=== Step 3.4 Silver Profile & Threshold Report (Raw batch: {day}) ===")
    print(f"{'Source':<12} {'Raw':>5} {'Inv%':>6} {'NonEn%':>7} {'LowScr%':>8} {'Kept':>6} | {'MinCfg':>6} {'P25':>6} {'Med':>6} {'P75':>6} {'Max':>7}")
    print("-" * 88)
    for p in profile:
        print(
            f"{p['source']:<12} {p['raw']:>5} {p['drop_invalid_pct']:>5.1f}% {p['drop_non_en_pct']:>6.1f}% "
            f"{p['drop_score_pct']:>7.1f}% {p['kept']:>6} | {p['min_score_cfg']:>6} {p['score_p25']:>6.1f} "
            f"{p['score_median']:>6.1f} {p['score_p75']:>6.1f} {p['score_max']:>7}"
        )
    print("-" * 88)
    print(f"Cleaned items (pre-dedup): {len(cleaned_records)} | Unique today (post-dedup): {len(deduped_today)} | Total in Silver table: {total_silver}")

    report_out = {
        "date": day,
        "pre_dedup_count": len(cleaned_records),
        "post_dedup_count": len(deduped_today),
        "silver_total_count": total_silver,
        "sources": profile,
    }
    profile_path = raw_dir / "_silver_profile.json"
    profile_path.write_text(json.dumps(report_out, indent=2), encoding="utf-8")
    return report_out


if __name__ == "__main__":
    run_normalize()