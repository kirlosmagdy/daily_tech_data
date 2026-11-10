import json
import time
from connectors import arxiv, devto, github, hackernews, hf_papers, lobsters, rss
from connectors.common import make_result, now_utc, save_raw
from pipeline.config import ROOT_DIR, load_config

CONNECTORS = {
    "hackernews": hackernews.extract,
    "devto": devto.extract,
    "lobsters": lobsters.extract,
    "rss": rss.extract,
    "github": github.extract,
    "arxiv": arxiv.extract,
    "hf_papers": hf_papers.extract,
}


# Run all enabled source connectors, save raw JSON files, and write the daily run report.
def run_extraction() -> dict:
    cfg = load_config()
    day = now_utc().strftime("%Y-%m-%d")
    report_sources = []

    for name, func in CONNECTORS.items():
        src_cfg = cfg["sources"].get(name, {})
        if not src_cfg.get("enabled", False):
            continue
        start = time.time()
        try:
            result = func(cfg)
        except Exception as exc:
            result = make_result(name, "failed", [], start, f"Unhandled crash: {exc}")
        save_raw(result, day)
        report_sources.append({
            "source": name,
            "status": result["status"],
            "count": result["count"],
            "duration_s": result["duration_s"],
            "error": result["error"],
            "collected_at": result["collected_at"],
        })

    ok_count = sum(1 for s in report_sources if s["status"] == "ok")
    report = {
        "date": day,
        "generated_at": now_utc().isoformat(),
        "ok_sources": ok_count,
        "total_enabled": len(report_sources),
        "sources": report_sources,
    }
    report_path = ROOT_DIR / "data" / "raw" / day / "_run_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nRun Report saved -> {report_path.relative_to(ROOT_DIR)} ({ok_count}/{len(report_sources)} sources ok)")
    return report


if __name__ == "__main__":
    run_extraction()