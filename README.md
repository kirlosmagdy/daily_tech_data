# Daily Tech & Data Pulse

Automated daily data pipeline and analytics site that collects, normalizes, enriches, and ranks tech and data engineering content across community, academic, and official engineering sources.

## Architecture

1. **Extract (Bronze):** Python connectors pull daily records into raw JSON.
2. **Normalize & Enrich (Silver):** Deduplication, canonical URL matching, topic/tool tagging, and VADER sentiment stored in Parquet + DuckDB.
3. **Transform (Gold):** `dbt-duckdb` calculates source trust weights, freshness decay, engagement percentiles, and trend aggregations.
4. **Publish:** Static JSON export consumed by a Next.js static site on Vercel, automated via GitHub Actions.

## Quickstart (Local Setup)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m pipeline.config