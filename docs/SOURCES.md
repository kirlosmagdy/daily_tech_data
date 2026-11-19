# Data Sources & Extraction Specification

All connectors live in `connectors/` and follow the contract in `docs/CONNECTOR_CONTRACT.md`.

| Source | Endpoint / Method | Key Parameters | Rate Limit / Timeout | Trust Tier (Weight) | Min Score |
|---|---|---|---|---|---|
| **Hacker News** | Algolia `search_by_date` API | `tags=story`, `numericFilters=created_at_i>...`, `hitsPerPage=100` | `0.5s` page delay, `15s` timeout | Tier 2 (`0.8`) | `5` points |
| **dev.to** | Forem REST API (`/api/articles`) | `per_page=40` (no `top` param; filtered by lookback cutoff) | `0.5s` delay, `15s` timeout | Tier 3 (`0.6`) | `3` reactions |
| **Lobsters** | `hottest.json` & `newest.json` | Deduplicated by `short_id` | `1.2s` delay between requests, `15s` timeout | Tier 2 (`0.8`) | `2` score |
| **RSS Blogs** | `feedparser` over 15 engineering blogs | Custom `User-Agent`, per-feed isolation | `30s` HTTP timeout per feed | Tier 1 (`1.0`) | `0` |
| **GitHub** | REST Search API (`/search/repositories`) | `q=topic:<t> created:>=YYYY-MM-DD`, `sort=stars`, `per_page=25` | `2.0s` delay between topics, `15s` timeout | Tier 2 (`0.8`) | `10` stars |
| **arXiv** | Atom API (`/api/query`) | 1 request per category (`cs.AI`, `cs.LG`, `cs.DB`, `cs.CL`, `cs.SE`, `stat.ML`), `max_results=40` each, deduplicated by ID | `3.0s` delay between categories, `20s` timeout | Tier 1 (`1.0`) | `0` |
| **HF Papers** | Hugging Face `/api/daily_papers` | JSON API with 96h weekend fallback | `15s` timeout | Tier 1 (`1.0`) | `0` |

## Timestamp Mapping (`published_at`)

* **GitHub:** Uses `created_at` first, falling back to `pushed_at`.
* **arXiv:** Uses `published` (falling back to `updated`), with a 96-hour weekend fallback when no papers fall within the 36-hour window.