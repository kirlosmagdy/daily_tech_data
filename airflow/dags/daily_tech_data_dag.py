from datetime import datetime, timedelta, timezone
import time
from airflow import DAG
from airflow.operators.python import PythonOperator # pyright: ignore[reportMissingImports]

from connectors.common import make_result, save_raw
from pipeline.config import load_config
from pipeline.enrich import run_enrich
from pipeline.export import run_export
from pipeline.extract import CONNECTORS
from pipeline.normalize import run_normalize
from pipeline.run import run_dbt_build, sync_history_and_rebuild_duckdb

SOURCES = ["hackernews", "devto", "lobsters", "rss", "github", "arxiv", "hf_papers", "dailydev"]

default_args = {
    "owner": "kirolos",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


# Rebuild DuckDB from the 90-day Parquet history before extraction starts.
def _rebuild_history() -> None:
    cfg = load_config()
    sync_history_and_rebuild_duckdb(cfg["project"]["history_retention_days"])


# Execute a single source connector and save its raw JSON output.
def _extract_single_source(source_name: str) -> None:
    cfg = load_config()
    if not cfg["sources"].get(source_name, {}).get("enabled", False):
        return
    start = time.time()
    try:
        res = CONNECTORS[source_name](cfg)
    except Exception as exc:
        res = make_result(source_name, "failed", [], start, str(exc))
    save_raw(res)


with DAG(
    dag_id="daily_tech_data",
    description="Daily Tech Data medallion pipeline (Bronze -> Silver -> Gold -> Export)",
    default_args=default_args,
    start_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
    schedule="23 5 * * *",
    catchup=False,
    is_paused_upon_creation=True,
    tags=["data-engineering", "duckdb", "dbt"],
) as dag:

    t_rebuild = PythonOperator(
        task_id="rebuild_duckdb_history",
        python_callable=_rebuild_history,
    )

    extract_tasks = [
        PythonOperator(
            task_id=f"extract_{src}",
            python_callable=_extract_single_source,
            op_kwargs={"source_name": src},
        )
        for src in SOURCES
    ]

    t_normalize = PythonOperator(
        task_id="normalize_silver",
        python_callable=run_normalize,
    )

    t_enrich = PythonOperator(
        task_id="enrich_silver",
        python_callable=run_enrich,
        op_kwargs={"sample_size": 5},
    )

    t_dbt = PythonOperator(
        task_id="dbt_build_gold",
        python_callable=run_dbt_build,
    )

    t_export = PythonOperator(
        task_id="export_site_json",
        python_callable=run_export,
    )

    t_rebuild >> extract_tasks >> t_normalize >> t_enrich >> t_dbt >> t_export