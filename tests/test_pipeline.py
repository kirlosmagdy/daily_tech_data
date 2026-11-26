import json
from pathlib import Path
from connectors.common import cutoff_utc, now_utc
from pipeline.config import load_config
from pipeline.enrich import extract_topics_and_tools, load_tools_seed, load_topics_seed
from pipeline.normalize import canonicalize_url, deduplicate_records, map_raw_item
from connectors.devbytes import parse_article_page


# Verify configuration loads core project settings, sources, and the 8 topic names.
def test_load_config():
    cfg = load_config()
    assert "project" in cfg
    assert "sources" in cfg
    assert isinstance(cfg["topics"], list)
    assert len(cfg["topics"]) == 8
    assert cfg["project"]["history_retention_days"] == 90
    assert cfg["sources"]["medium"]["enabled"] is True
    assert cfg["sources"]["daily_dev"]["enabled"] is True
    assert cfg["sources"]["devbytes"]["enabled"] is True
    assert cfg["sources"]["rss"]["enabled"] is False


# Verify saved raw fixtures map cleanly into normalized records with non-empty canonical_url and title.
def test_map_raw_item_fixtures():
    fixtures_dir = Path("tests/fixtures")
    specs = [
        ("medium", "medium_sample.json", "items"),
        ("daily_dev", "daily_dev_sample.json", "items"),
        ("devbytes", "devbytes_sample.json", "items"),
        ("hackernews", "hackernews_sample.json", "hits"),
        ("devto", "devto_sample.json", None),
        ("lobsters", "lobsters_sample.json", None),
        ("github", "github_sample.json", "items"),
        ("hf_papers", "hf_papers_sample.json", None),
    ]
    for source, filename, key in specs:
        path = fixtures_dir / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data[key] if (key and isinstance(data, dict) and key in data) else (data.get("items", []) if isinstance(data, dict) else data)
        assert len(rows) > 0
        mapped = map_raw_item(source, rows[0], "2026-11-21T00:00:00+00:00", 0.6, 300)
        assert mapped["canonical_url"]
        assert mapped["title"]
        assert len(mapped["snippet"]) <= 300


# Verify DevBytes HTML parser extracts title, snippet, date, canonical slug URL, and Previous link.
def test_devbytes_parse_article_page():
    html = Path("tests/fixtures/devbytes_page.html").read_text(encoding="utf-8")
    record, prev_url = parse_article_page(html, "https://devbytes.co.in/news")
    assert record is not None
    assert record["title"]
    assert record["url"].startswith("https://devbytes.co.in/news/")
    assert record["published_at"].endswith("+00:00")
    assert len(record["snippet"]) <= 300
    assert prev_url and prev_url.startswith("https://devbytes.co.in/news/")

# Verify URL canonicalization strips utm_* params, lowercases host, removes www/trailing slash, and strips arXiv versions.
def test_canonicalize_url():
    raw = "HTTPS://www.Example.com/post/?utm_source=hn&utm_medium=social&id=42"
    assert canonicalize_url(raw) == "https://example.com/post?id=42"
    assert canonicalize_url("https://arxiv.org/abs/2401.12345v3/") == "https://arxiv.org/abs/2401.12345"


# Verify cross-source deduplication merges sources, keeps highest trust tier, and preserves max score.
def test_deduplicate_records_cross_source():
    records = [
        {
            "source": "devto",
            "source_item_id": "1",
            "canonical_url": "https://example.com/duckdb-guide",
            "title": "DuckDB Guide (Dev.to)",
            "snippet": "Short snippet",
            "author": "alice",
            "published_at": "2026-11-15T08:00:00+00:00",
            "collected_at": "2026-11-15T09:00:00+00:00",
            "source_score": 25,
            "comments_count": 4,
            "source_tags": ["duckdb"],
            "domain": "example.com",
            "trust_weight": 0.6,
            "mentioned_in_sources": ["devto"],
        },
        {
            "source": "hackernews",
            "source_item_id": "2",
            "canonical_url": "https://example.com/duckdb-guide",
            "title": "DuckDB Guide (HN)",
            "snippet": "Detailed engineering guide to DuckDB",
            "author": "bob",
            "published_at": "2026-11-15T07:30:00+00:00",
            "collected_at": "2026-11-15T09:05:00+00:00",
            "source_score": 180,
            "comments_count": 62,
            "source_tags": ["data"],
            "domain": "example.com",
            "trust_weight": 0.8,
            "mentioned_in_sources": ["hackernews"],
        },
    ]
    deduped = deduplicate_records(records)
    assert len(deduped) == 1
    assert deduped[0]["source"] == "hackernews"
    assert deduped[0]["source_score"] == 180
    assert set(deduped[0]["mentioned_in_sources"]) == {"devto", "hackernews"}


# Verify topic and tool extraction identifies unambiguous tools and topics.
def test_extract_topics_and_tools_match():
    topics, tools = extract_topics_and_tools(
        title="Building ELT pipelines with dbt and DuckDB on PostgreSQL",
        snippet="How to model a star schema for analytics engineering.",
        tags=["data-engineering"],
        topic_rules=load_topics_seed(),
        tool_rules=load_tools_seed(),
    )
    assert "data_engineering" in topics
    assert "dbt" in tools
    assert "DuckDB" in tools


# Verify context-word rules block false positives for ambiguous tool names like Spark and Ray.
def test_extract_tools_context_word_guard():
    topic_rules = load_topics_seed()
    tool_rules = load_tools_seed()
    _, tools_false = extract_topics_and_tools(
        title="A bright spark of creativity and a ray of sunshine",
        snippet="General design thoughts about painting and photography.",
        tags=[],
        topic_rules=topic_rules,
        tool_rules=tool_rules,
    )
    assert "Spark" not in tools_false
    assert "Ray" not in tools_false

    _, tools_true = extract_topics_and_tools(
        title="Scaling Apache Spark streaming jobs with PySpark dataframe",
        snippet="Distributed ETL pipeline tuning.",
        tags=[],
        topic_rules=topic_rules,
        tool_rules=tool_rules,
    )
    assert "Spark" in tools_true


# Verify UTC time utilities produce timezone-aware timestamps in the expected order.
def test_utc_time_helpers():
    current = now_utc()
    past = cutoff_utc(24)
    assert current.tzinfo is not None
    assert past < current


# Verify items missing published_at produce an empty date so normalization drops them.
def test_map_raw_item_missing_date():
    raw = {"title": "No Date Post", "link": "https://medium.com/p/abc123", "snippet": "Test"}
    mapped = map_raw_item("medium", raw, "2026-11-22T00:00:00+00:00", 0.6, 300)
    assert mapped["published_at"] == ""


# Verify X connector degrades cleanly without a token and maps tweet records properly.
def test_x_connector_and_normalization(monkeypatch):
    from connectors import x as x_connector

    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    res = x_connector.extract({"project": {"lookback_hours": 48, "max_snippet_length": 300}, "sources": {"x": {}}})
    assert res["status"] == "degraded"
    assert res["count"] == 0

    tweet_item = {
        "id": "1860000000000000000",
        "url": "https://x.com/dataeng/status/1860000000000000000?s=20",
        "title": "DuckDB and dbt local lakehouse workflow",
        "snippet": "Testing DuckDB and dbt pipelines on local Parquet files.",
        "author": "Data Eng",
        "published_at": now_utc().isoformat(),
        "score": 18,
        "comments": 3,
        "tags": ["x", "duckdb"],
    }
    mapped = map_raw_item("x", tweet_item, now_utc().isoformat(), 0.6, 300)
    assert mapped["source"] == "x"
    assert mapped["source_score"] == 18
    assert mapped["canonical_url"] == canonicalize_url(tweet_item["url"])
    assert mapped["canonical_url"].startswith("https://x.com/dataeng/status/1860000000000000000")