import time
from connectors.common import fetch_response, make_result, save_raw
from pipeline.config import load_config

HF_PAPERS_URL = "https://huggingface.co/api/daily_papers"


# Extract recent papers and community upvote counts from Hugging Face Daily Papers.
def extract(cfg: dict) -> dict:
    start = time.time()
    try:
        resp = fetch_response(HF_PAPERS_URL, params={"limit": 50}, delay=0.5)
        items = resp.json()
        return make_result("hf_papers", "ok" if items else "failed", items, start)
    except Exception as exc:
        return make_result("hf_papers", "failed", [], start, str(exc))


if __name__ == "__main__":
    save_raw(extract(load_config()))