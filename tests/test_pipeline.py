import json
from pathlib import Path
from connectors.common import cutoff_utc, now_utc
from pipeline.config import load_config
from pipeline.enrich import extract_topics_and_tools, load_tools_seed, load_topics_seed
from pipeline.normalize import canonicalize_url, deduplicate_records, map_raw_item


# Verify configuration loads core project settings, sources, and topics.
def test_load_config():
    cfg = load_config()
    assert "project" in cfg
    assert "sources" in cfg
    assert "topics" in cfg
    assert cfg["project"]["history_retention_days"] == 90
    assert cfg["sources"]["rss"]["enabled"] is True


# Verify saved raw fixtures map cleanly into normalized records with titles and canonical URLs.
def test_map_raw_item_fixtures():
    fixtures_dir = Path("tests/fixtures")
    specs = [
        ("hackernews", "hackernews.json", "hits"),
        ("devto", "devto.json", None),
        ("lobsters", "lobsters.json", None),
        ("github", "github.json", "items"),
        ("hf_papers", "hf_papers.json", None),
    ]
    for source, filename, key in specs:
        data = json.loads((fixtures_dir / filename).read_text(encoding="utf-8"))
        rows = data[key] if key else data
        assert len(rows) > 0
        mapped = map_raw_item(rows[0], source, 0.8)
        assert mapped is not None
        assert mapped["canonical_url"]
        assert mapped["title"]


# Verify URL canonicalization strips tracking params, www, trailing slashes, and arXiv version suffixes.
def test_canonicalize_url():
    raw = "HTTPS://www.Example.com/post/?utm_source=hn&utm_medium=social&id=42/"
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