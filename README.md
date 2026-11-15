# Daily Tech & Data Pulse

An end-to-end automated data engineering pipeline and static analytics platform that extracts, deduplicates, enriches, ranks, and publishes technical and data engineering content daily at **$0 hosting cost**.

---

## Tech Stack

* **Ingestion & Processing:** Python 3.11 (`requests`, `feedparser`, `beautifulsoup4`, `langdetect`, `vaderSentiment`, `pandas`, `pyarrow`)
* **Storage & History:** DuckDB (local analytical engine) + Apache Parquet (rolling 90-day Silver history snapshot)
* **Transformation & Data Quality:** `dbt-core` + `dbt-duckdb` (1 staging view, 6 Gold tables, 27 automated schema and freshness tests)
* **Frontend:** Next.js 14 Static Export (`output: "export"`) deployed on Vercel
* **Orchestration & CI/CD:** GitHub Actions (daily production schedule + `pytest` CI) & Dockerized Apache Airflow 2.10 (local DAG showcase)

---

## Medallion Architecture

```text
[7 Sources: Hacker News, dev.to, Lobsters, 15 RSS Blogs, GitHub, arXiv, HF Papers]
       │
       ▼
1. Bronze Layer (pipeline/extract.py)
   - Polite rate-limited connectors, retry/backoff, per-source fault isolation
   - Raw JSON batch + _run_report.json written to data/raw/YYYY-MM-DD/
       │
       ▼
2. Silver Layer (pipeline/normalize.py & pipeline/enrich.py)
   - HTML stripping, 300-char snippet cap, UTC normalization, English filter
   - Canonical URL normalization & cross-source deduplication
   - Seed-driven topic & tool tagging (with context-word guards) + VADER sentiment
   - Persisted to 90-day rolling Parquet snapshot (data/history/silver_items.parquet)
       │
       ▼
3. Gold Layer (dbt_project/ with dbt-duckdb)
   - Rebuilds local DuckDB (data/pulse.duckdb) from 90-day Parquet history
   - Builds stg_silver_items + 6 Gold analytical models + 27 data quality tests
       │
       ▼
4. Static Export & Frontend (pipeline/export.py -> site/)
   - Exports compact JSON feeds (<1 MB each) to site/data/
   - Prerendered static Next.js site deployed on Vercel
```

---

## Data Sources & Trust Tiers

| Source | Type | Trust Tier | Weight | Min Score Filter |
|---|---|---|---|---|
| **RSS Feeds (15 Engineering Blogs)** | Official blogs & release notes | Tier 1 | `1.0` | `0` |
| **arXiv (`cs.AI`, `cs.LG`, `cs.DB`)** | Research preprints | Tier 1 | `1.0` | `0` |
| **Hugging Face Daily Papers** | Curated ML papers | Tier 1 | `1.0` | `0` |
| **Hacker News (Algolia API)** | Technical community (relevance-filtered) | Tier 2 | `0.8` | `5` |
| **Lobsters** | Curated computing community | Tier 2 | `0.8` | `2` |
| **GitHub Search API** | Active open-source repositories | Tier 2 | `0.8` | `10` stars |
| **dev.to** | Open developer publishing platform | Tier 3 | `0.6` | `3` reactions |

---

## Ranking Formula

Items in `gold_ranked_items` and `gold_today_feed` are scored using:

$$\text{rank\_score} = \text{engagement\_percentile} \times \text{trust\_weight} \times \text{freshness\_score} \times \text{cross\_source\_bonus}$$

* **Engagement Percentile:** 7-day within-source cumulative distribution (`CUME_DIST`) of `source_score + 2 * comments_count` (sources without native scores like RSS and arXiv receive a neutral `0.7` baseline).
* **Trust Weight:** `1.0` (Tier 1), `0.8` (Tier 2), or `0.6` (Tier 3).
* **Freshness Score:** Exponential decay with an **18-hour half-life** ($0.5^{\Delta t / 18}$).
* **Cross-Source Bonus:** $+0.15$ per additional source mentioning the same canonical URL, capped at $+0.45$ ($1.45\times$).

---

## Repository Structure

```text
daily_tech_data/
├── .github/workflows/
│   └── daily_data.yml           # Daily scheduled GitHub Actions workflow + CI tests
├── airflow/
│   ├── dags/
│   │   └── daily_tech_data_dag.py
│   ├── Dockerfile
│   └── docker-compose.yml       # Local Airflow standalone on port 8085
├── connectors/                  # Modular source extractors (HN, dev.to, RSS, GitHub, etc.)
├── data/
│   └── history/
│       └── silver_items.parquet # Committed 90-day deduplicated Silver history
├── dbt_project/
│   ├── macros/                  # Custom generic test macros (test_between.sql)
│   ├── models/                  # Staging view, 6 Gold SQL models, and schema.yml
│   ├── tests/                   # 36h freshness and 7d median row-count tests
│   ├── dbt_project.yml
│   └── profiles.yml
├── pipeline/
│   ├── config.py                # YAML & environment loader
│   ├── extract.py               # Bronze runner
│   ├── normalize.py             # Silver cleaning, canonical URLs, deduplication
│   ├── enrich.py                # Topic/tool regex tagging & VADER sentiment
│   ├── export.py                # DuckDB Gold -> compact site/data/*.json exporter
│   └── run.py                   # Single-command end-to-end pipeline orchestrator
├── seeds/
│   ├── topics.csv               # 8 core topics and pipe-delimited keywords
│   └── tools.csv                # 32 data/AI tools with aliases & context words
├── site/                        # Next.js 14 static site (Today, Trends, Sentiment, Sources, About)
├── tests/
│   └── test_pipeline.py         # Pytest unit test suite
├── config.yaml                  # Central pipeline configuration
└── requirements.txt             # Pinned Python dependencies
```

---

## Local Quickstart

```powershell
# 1. Create and activate virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Run unit tests
pytest -v

# 3. Run the full end-to-end pipeline (Rebuild -> Extract -> Normalize -> Enrich ->