import csv
import random
import re
import duckdb
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from pipeline.config import ROOT_DIR
from pipeline.normalize import DUCKDB_PATH, SILVER_PARQUET_PATH

SEEDS_DIR = ROOT_DIR / "seeds"

SOURCE_DEFAULT_TOPIC = {
    "arxiv": "ai_and_ml",
    "hf_papers": "ai_and_ml",
    "github": "programming_and_devtools",
    "lobsters": "programming_and_devtools",
    "devto": "programming_and_devtools",
    "rss": "data_engineering",
}


# Load topic keyword regex patterns from seeds/topics.csv.
def load_topics_seed() -> dict[str, list[re.Pattern]]:
    topics: dict[str, list[re.Pattern]] = {}
    with open(SEEDS_DIR / "topics.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kw_list = [k.strip() for k in row["keywords"].split("|") if k.strip()]
            topics[row["topic"].strip()] = [
                re.compile(rf"(?<!\w){re.escape(kw)}(?!\w)", re.IGNORECASE) for kw in kw_list
            ]
    return topics


# Load tool alias and context regex patterns from seeds/tools.csv.
def load_tools_seed() -> list[dict]:
    tools = []
    with open(SEEDS_DIR / "tools.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            aliases = [a.strip() for a in row["aliases"].split("|") if a.strip()]
            ctx = [c.strip() for c in (row.get("context_words") or "").split("|") if c.strip()]
            tools.append({
                "tool": row["tool"].strip(),
                "alias_patterns": [re.compile(rf"(?<!\w){re.escape(a)}(?!\w)", re.IGNORECASE) for a in aliases],
                "ctx_patterns": [re.compile(rf"(?<!\w){re.escape(c)}(?!\w)", re.IGNORECASE) for c in ctx],
            })
    return tools


# Match topics and tool mentions in an item's title, snippet, and source_tags.
def extract_topics_and_tools(
    title: str,
    snippet: str,
    tags: list[str],
    topic_rules: dict[str, list[re.Pattern]],
    tool_rules: list[dict],
) -> tuple[list[str], list[str]]:
    tag_str = " ".join(tags)
    full_text = f"{title} {snippet} {tag_str}"

    matched_topics = [
        topic for topic, patterns in topic_rules.items() if any(p.search(full_text) for p in patterns)
    ]

    matched_tools = []
    for rule in tool_rules:
        if any(p.search(full_text) for p in rule["alias_patterns"]):
            if not rule["ctx_patterns"] or any(cp.search(full_text) for cp in rule["ctx_patterns"]):
                matched_tools.append(rule["tool"])

    return matched_topics, matched_tools


# Enrich Silver items with topics, tools_mentioned, VADER sentiment, and apply the HN relevance filter.
def run_enrich(sample_size: int = 30) -> None:
    if not SILVER_PARQUET_PATH.exists():
        raise FileNotFoundError("silver_items.parquet not found. Run 'python -m pipeline.normalize' first.")

    topic_rules = load_topics_seed()
    tool_rules = load_tools_seed()
    analyzer = SentimentIntensityAnalyzer()

    df = pd.read_parquet(SILVER_PARQUET_PATH)
    records = df.to_dict(orient="records")

    kept_records = []
    hn_dropped = 0

    for rec in records:
        for col in ("source_tags", "mentioned_in_sources"):
            val = rec.get(col)
            rec[col] = list(val) if val is not None else []

        title = rec.get("title") or ""
        snippet = rec.get("snippet") or ""
        tags = rec["source_tags"]

        topics, tools = extract_topics_and_tools(title, snippet, tags, topic_rules, tool_rules)

        # Hacker News relevance filter: drop HN-only items that match zero topic keywords.
        if rec["source"] == "hackernews" and rec["mentioned_in_sources"] == ["hackernews"] and not topics:
            hn_dropped += 1
            continue

        if not topics:
            topics = [SOURCE_DEFAULT_TOPIC.get(rec["source"], "programming_and_devtools")]

        sentiment_text = f"{title}. {snippet}".strip()
        compound = analyzer.polarity_scores(sentiment_text)["compound"]

        rec["topics"] = topics
        rec["tools_mentioned"] = tools
        rec["sentiment"] = round(float(compound), 4)
        kept_records.append(rec)

    out_df = pd.DataFrame(kept_records)
    out_df.to_parquet(SILVER_PARQUET_PATH, index=False)

    with duckdb.connect(str(DUCKDB_PATH)) as con:
        con.execute("CREATE OR REPLACE TABLE silver_items AS SELECT * FROM read_parquet(?)", [str(SILVER_PARQUET_PATH)])

    with_tools = sum(1 for r in kept_records if r["tools_mentioned"])
    print("\n=== Phase 4 Enrichment Summary ===")
    print(f"Input Silver rows     : {len(records)}")
    print(f"HN irrelevant dropped : {hn_dropped}")
    print(f"Enriched Silver rows  : {len(kept_records)}")
    print(f"Items with >=1 topic  : {len(kept_records)} (100.0%)")
    print(f"Items with >=1 tool   : {with_tools} ({round(100 * with_tools / max(len(kept_records), 1), 1)}%)")

    rng = random.Random(42)
    sample = rng.sample(kept_records, min(sample_size, len(kept_records)))
    print(f"\n=== Step 4.4 Spot Check ({len(sample)} Random Items) ===")
    for idx, item in enumerate(sample, 1):
        t_str = ", ".join(item["topics"])
        tl_str = ", ".join(item["tools_mentioned"]) or "-"
        print(f"{idx:>2}. [{item['source']:<10}] (sent={item['sentiment']:+.2f}) {item['title'][:75]}")
        print(f"    Topics: {t_str} | Tools: {tl_str}")


if __name__ == "__main__":
    run_enrich()