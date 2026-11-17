# Daily Tech & Data Pulse

An end-to-end automated data engineering pipeline and static analytics platform that extracts, deduplicates, enriches, ranks, and publishes technical and data engineering content daily at **$0 hosting cost**.

## Architecture (Medallion Pipeline)

* **Bronze Layer (`connectors/`, `pipeline/extract.py`):** Polite, rate-limited connectors for 7 sources writing raw daily JSON batches and `_run_report.json` to `data/raw/YYYY-MM-DD/`.
* **Silver Layer (`pipeline/normalize.py`, `pipeline/enrich.py`):** HTML stripping, English language filtering, canonical URL normalization, cross-source deduplication, seed-driven topic/tool regex tagging, VADER sentiment scoring, and 90-day rolling Parquet persistence (`data/history/silver_items.parquet`).
* **Gold Layer (`dbt_project/`):** Ephemeral DuckDB rebuild executing 1 staging view, 6 Gold analytical models, and 27 schema and freshness tests via `dbt build`.
* **Static Export & Frontend (`pipeline/export.py`, `site/`):** Compact JSON feeds exported to `site/data/` powering a static Next.js 14 application deployed on Vercel.

## Local Quickstart

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Run unit tests
pytest -v

# 3. Run the full pipeline (Extract -> Normalize -> Enrich -> dbt build -> Export)
python -m pipeline.run

# 4. Run dbt models and data quality tests directly (optional)
dbt build --project-dir dbt_project --profiles-dir dbt_project

# 5. Build and run the static Next.js frontend
cd site
npm install
npm run build
npm run dev
```

## GitHub Actions & Secrets

The production workflow (`.github/workflows/daily_data.yml`) runs daily at `08:17 UTC` (`10:17 AM` Cairo time).

* **`GITHUB_TOKEN`**: Provided automatically by GitHub Actions for higher GitHub Search API rate limits and pushing data commits.
* **`VERCEL_DEPLOY_HOOK_URL`** *(Optional)*: Repository secret containing a Vercel Deploy Hook URL to trigger a static site rebuild after new data commits are pushed.

## Local Airflow Showcase

```powershell
docker compose -f airflow/docker-compose.yml up -d
docker logs pulse_airflow | Select-String "password:"
```

Open `http://localhost:8085`, log in as `admin`, unpause `daily_tech_data_pulse`, and trigger a run. Stop with `docker compose -f airflow/docker-compose.yml down`.

## Limitations

* **Lexicon Sentiment:** VADER sentiment is rule-based and optimized for short text; neutral technical titles typically score near `0.0`.
* **Keyword Tagging:** Topic and tool detection relies on curated regular expressions and context-word guards in `seeds/` rather than LLM classification.
* **Ephemeral History Window:** Git-committed Parquet storage retains a rolling 90-day window to keep the repository lightweight.

## Sources and Attribution

Content metadata (titles, URLs, short snippets, and public engagement counts) is aggregated from public APIs and feeds: Hacker News (Algolia), dev.to, Lobsters, Engineering RSS Blogs, GitHub Search API, arXiv API, and Hugging Face Daily Papers. All links point directly to the original publishers.

## License

Released under the [MIT License](LICENSE).