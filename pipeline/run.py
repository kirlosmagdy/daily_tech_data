import argparse
import subprocess
import sys
import time
import duckdb
import pandas as pd
from connectors.common import cutoff_utc
from pipeline.config import ROOT_DIR, load_config
from pipeline.enrich import run_enrich
from pipeline.export import run_export
from pipeline.extract import run_extraction
from pipeline.normalize import DUCKDB_PATH, SILVER_PARQUET_PATH, deduplicate_records, run_normalize


# Prune records older than retention_days from Parquet history and rebuild DuckDB from it.
def sync_history_and_rebuild_duckdb(retention_days: int = 90) -> int:
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SILVER_PARQUET_PATH.exists():
        return 0

    df = pd.read_parquet(SILVER_PARQUET_PATH)
    records = []
    for row in df.to_dict(orient="records"):
        for list_col in ("source_tags", "topics", "tools_mentioned", "mentioned_in_sources"):
            val = row.get(list_col)
            row[list_col] = list(val) if val is not None else []
        records.append(row)

    cutoff_iso = cutoff_utc(retention_days * 24).isoformat()
    retained = [r for r in records if r.get("collected_at", "") >= cutoff_iso]
    deduped = deduplicate_records(retained)

    pd.DataFrame(deduped).to_parquet(SILVER_PARQUET_PATH, index=False)
    with duckdb.connect(str(DUCKDB_PATH)) as con:
        con.execute("CREATE OR REPLACE TABLE silver_items AS SELECT * FROM read_parquet(?)", [str(SILVER_PARQUET_PATH)])
    return len(deduped)


# Execute dbt build against the local DuckDB database and raise on test or model failure.
def run_dbt_build() -> None:
    dbt_dir = ROOT_DIR / "dbt_project"
    cmd = ["dbt", "build", "--project-dir", str(dbt_dir), "--profiles-dir", str(dbt_dir)]
    result = subprocess.run(cmd, cwd=str(ROOT_DIR), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"dbt build failed with exit code {result.returncode}. Aborting export.")


# Run the full pipeline end-to-end: rebuild history, extract, normalize, enrich, dbt build, and export.
def run_pipeline(skip_extract: bool = False) -> None:
    start = time.time()
    cfg = load_config()
    retention_days = cfg["project"]["history_retention_days"]

    print("1/6 Rebuilding DuckDB from 90-day Parquet history...")
    rebuilt_count = sync_history_and_rebuild_duckdb(retention_days)
    print(f"    Loaded {rebuilt_count} historical Silver rows.")

    if not skip_extract:
        print("2/6 Running Bronze extraction...")
        report = run_extraction()
        active_sources = [s for s in report["sources"] if s["status"] in ("ok", "partial") and s["count"] > 0]
        if not active_sources:
            raise RuntimeError("All sources failed during extraction. Stopping without overwriting site data.")
    else:
        print("2/6 Skipping extraction (--skip-extract enabled)...")

    print("3/6 Running Silver normalization & deduplication...")
    run_normalize()

    print("4/6 Running Silver enrichment (topics, tools, VADER sentiment)...")
    run_enrich(sample_size=5)

    print("5/6 Running Gold layer (dbt build)...")
    run_dbt_build()

    print("6/6 Exporting static JSON files to site/data/...")
    meta = run_export()

    elapsed = round(time.time() - start, 2)
    print(f"\n=== Pipeline Completed in {elapsed}s ===")
    print(f"Today feed: {meta['today_count']} items | Total history: {meta['total_history_count']} items")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Daily Tech & Data Pulse pipeline.")
    parser.add_argument("--skip-extract", action="store_true", help="Reuse latest raw files without network calls.")
    args = parser.parse_args()
    try:
        run_pipeline(skip_extract=args.skip_extract)
    except Exception as exc:
        print(f"\n[FATAL] Pipeline aborted: {exc}", file=sys.stderr)
        sys.exit(1)