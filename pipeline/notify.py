import html
import json
import os
import requests
from connectors.common import logger, now_utc
from pipeline.config import ROOT_DIR, load_config

TELEGRAM_MAX_LEN = 4096
SITE_URL = "https://daily-tech-data.vercel.app"


# Load canonical URLs present in the existing Silver Parquet history before the current run.
def load_previous_urls() -> set[str]:
    parquet_path = ROOT_DIR / "data" / "history" / "silver_items.parquet"
    if not parquet_path.exists():
        return set()
    try:
        import pandas as pd

        df = pd.read_parquet(parquet_path, columns=["canonical_url"])
        return {str(u) for u in df["canonical_url"].dropna().unique() if u}
    except Exception as exc:
        logger.warning("[notify] Could not read previous history: %s", exc)
        return set()


# Build HTML Telegram message for a successful run, trimmed to fit within 4096 characters.
def build_message(
    today_items: list[dict],
    previous_urls: set[str],
    sources_report: list[dict],
    site_url: str = SITE_URL,
) -> str:
    day = now_utc().strftime("%Y-%m-%d")
    new_items = [
        i
        for i in today_items
        if i.get("canonical_url") and i["canonical_url"] not in previous_urls
    ]

    if not new_items:
        return (
            f"<b>Daily Tech &amp; Data Pulse ({day})</b>\n"
            f"No new items.\n"
            f'<a href="{html.escape(site_url)}">Open site</a>'
        )

    header_lines = [
        f"<b>Daily Tech &amp; Data Pulse ({day}) — {len(new_items)} new</b>",
        *[
            f"• {html.escape(str(s.get('source', '')))}: {html.escape(str(s.get('status', '')))} ({s.get('count', 0)})"
            for s in sources_report
        ],
        "",
        "<b>Newest items:</b>",
    ]
    footer_line = f'\n<a href="{html.escape(site_url)}">View full feed</a>'

    body_lines = []
    for item in new_items[:10]:
        src = html.escape(str(item.get("source") or ""))
        title = html.escape((item.get("title") or "").strip())
        url = html.escape((item.get("canonical_url") or "").strip())
        body_lines.append(f'• [{src}] <a href="{url}">{title}</a>')

    while body_lines:
        msg = "\n".join(header_lines + body_lines) + footer_line
        if len(msg) <= TELEGRAM_MAX_LEN:
            return msg
        body_lines.pop()

    return ("\n".join(header_lines) + footer_line)[:TELEGRAM_MAX_LEN]


# Send a Telegram message via Bot API; log a warning on any error and never raise.
def send_telegram(text: str, token: str | None = None, chat_id: str | None = None) -> bool:
    bot_token = (token if token is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
    target_chat = (chat_id if chat_id is not None else os.getenv("TELEGRAM_CHAT_ID", "")).strip()
    if not bot_token or not target_chat:
        logger.warning("[notify] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing; skipping notification.")
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": target_chat,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("[notify] Telegram send failed: %s", exc)
        return False


# Send a short one-line failure alert if the workflow fails.
def send_failure_alert(run_url: str = "") -> bool:
    line = "Daily Tech &amp; Data Pulse run failed."
    if run_url:
        line += f' <a href="{html.escape(run_url)}">Run log</a>'
    return send_telegram(line)


# Notify from current exported feed and latest run report.
def notify_run(previous_urls: set[str] | None = None) -> bool:
    load_config()
    today_path = ROOT_DIR / "site" / "data" / "today.json"
    today_items = []
    if today_path.exists():
        today_items = json.loads(today_path.read_text(encoding="utf-8"))

    sources_report = []
    raw_root = ROOT_DIR / "data" / "raw"
    if raw_root.exists():
        raw_dirs = sorted([d for d in raw_root.iterdir() if d.is_dir()], reverse=True)
        for d in raw_dirs:
            rep_file = d / "_run_report.json"
            if rep_file.exists():
                sources_report = json.loads(rep_file.read_text(encoding="utf-8")).get("sources", [])
                break

    prev = previous_urls if previous_urls is not None else set()
    msg = build_message(today_items, prev, sources_report)
    return send_telegram(msg)