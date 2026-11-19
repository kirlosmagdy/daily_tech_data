from datetime import date, datetime
import json
from pathlib import Path
import duckdb
import numpy as np
from connectors.common import now_utc
from pipeline.config import ROOT_DIR, load_config
from pipeline.normalize import DUCKDB_PATH, resolve_raw_dir

SITE_DATA_DIR = ROOT_DIR / "site" / "data"


# Convert DuckDB/pandas types (timestamps, dates, numpy arrays) into JSON-serializable values.
def _to_serializable(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (float, np.floating)):
        return None if not np.isfinite(val) else float(val)
    return val


# Execute a SQL query on DuckDB and return a list of JSON-ready dictionaries.
def query_records(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> list[dict]:
    df = con.execute(sql, params or []).df()
    records = []
    for row in df.to_dict(orient="records"):
        records.append({k: _to_serializable(v) for k, v in row.items()})
    return records


# Write data as compact JSON to site/data/{filename} and return the file size in KB.
def write_json(filename: str, payload: dict | list) -> float:
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = SITE_DATA_DIR / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    size_kb = round(path.stat().st_size / 1024, 1)
    if size_kb > 1024:
        raise ValueError(f"Exported file {filename} exceeds 1 MB limit ({size_kb} KB)")
    return size_kb


# Export all Gold tables to site/data JSON files for the Next.js static site.
def run_export() -> dict:
    cfg = load_config()
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError("DuckDB file not found. Run normalization and dbt build first.")

    run_report_map = {}
    try:
        _, raw_dir = resolve_raw_dir()
        report_file = raw_dir / "_run_report.json"
        if report_file.exists():
            rep = json.loads(report_file.read_text(encoding="utf-8"))
            run_report_map = {s["source"]: s for s in rep.get("sources", [])}
    except Exception:
        pass

    with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
        today_items = query_records(con, "SELECT * FROM gold_today_feed ORDER BY rank_score DESC")
        all_ranked = query_records(con, "SELECT * FROM gold_ranked_items ORDER BY rank_score DESC")
        trends_30d = query_records(
            con,
            "SELECT * FROM gold_daily_topic_counts WHERE metric_date >= CURRENT_DATE - INTERVAL 30 DAY ORDER BY metric_date ASC, topic ASC",
        )
        tools_trends = query_records(con, "SELECT * FROM gold_tool_trends ORDER BY mentions_last_7d DESC, mentions_delta DESC")
        sentiment_weekly = query_records(con, "SELECT * FROM gold_weekly_tool_sentiment ORDER BY week_start DESC, mentions_count DESC")
        sources_health = query_records(con, "SELECT * FROM gold_source_health ORDER BY trust_weight DESC, source ASC")

    for src in sources_health:
        live = run_report_map.get(src["source"])
        if live:
            src["last_run_status"] = live.get("status", src["status"])
            src["last_run_count"] = live.get("count", 0)
            src["last_run_error"] = live.get("error")
            if live.get("status") in ("partial", "failed"):
                src["status"] = live["status"]
        else:
            src["last_run_status"] = src["status"]
            src["last_run_count"] = src["item_count"]
            src["last_run_error"] = None

    generated_at = now_utc().isoformat()
    meta = {
        "project": cfg["project"]["name"],
        "version": cfg["project"]["version"],
        "generated_at": generated_at,
        "today_count": len(today_items),
        "total_history_count": len(all_ranked),
        "topics_count": len(cfg["topics"]),
        "tools_tracked_count": len(tools_trends),
        "ok_sources_count": sum(1 for s in sources_health if s["status"] == "ok"),
        "total_sources_count": len(sources_health),
    }

    sizes = {
        "today.json": write_json("today.json", today_items),
        "trends.json": write_json("trends.json", trends_30d),
        "tools.json": write_json("tools.json", tools_trends),
        "sentiment.json": write_json("sentiment.json", sentiment_weekly),
        "sources.json": write_json("sources.json", sources_health),
        "meta.json": write_json("meta.json", meta),
    }

    print("\n=== Step 6.1 JSON Export Summary (site/data/) ===")
    for fname, kb in sizes.items():
        print(f"  - {fname:<16}: {kb:>6.1f} KB")
    return meta


if __name__ == "__main__":
    run_export()