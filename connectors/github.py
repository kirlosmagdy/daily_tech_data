import os
import time
from dotenv import load_dotenv
from connectors.common import cutoff_utc, fetch_response, make_result, save_raw
from pipeline.config import load_config

load_dotenv()
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


# Extract active GitHub repositories pushed within the lookback window across configured topics.
def extract(cfg: dict) -> dict:
    start = time.time()
    cutoff_date = cutoff_utc(cfg["project"]["lookback_hours"]).strftime("%Y-%m-%d")
    topics = cfg["sources"]["github"]["topics"]
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    seen, items, errors = set(), [], []
    for i, topic in enumerate(topics):
        try:
            params = {
                "q": f"topic:{topic} pushed:>={cutoff_date}",
                "sort": "stars",
                "order": "desc",
                "per_page": 25,
            }
            resp = fetch_response(GITHUB_SEARCH_URL, params=params, headers=headers, delay=2.0 if i > 0 else 0.0)
            for repo in resp.json().get("items", []):
                rid = repo.get("id")
                if rid and rid not in seen:
                    seen.add(rid)
                    items.append({
                        "id": rid,
                        "full_name": repo.get("full_name"),
                        "html_url": repo.get("html_url"),
                        "description": repo.get("description") or "",
                        "stargazers_count": repo.get("stargazers_count", 0),
                        "forks_count": repo.get("forks_count", 0),
                        "open_issues_count": repo.get("open_issues_count", 0),
                        "created_at": repo.get("created_at"),
                        "pushed_at": repo.get("pushed_at"),
                        "topics": repo.get("topics", []),
                        "owner_login": (repo.get("owner") or {}).get("login", ""),
                        "language": repo.get("language"),
                    })
        except Exception as exc:
            errors.append(f"{topic}: {exc}")

    status = "ok" if items and not errors else ("partial" if items else "failed")
    return make_result("github", status, items, start, "; ".join(errors) if errors else None)


if __name__ == "__main__":
    save_raw(extract(load_config()))