# Data Sources Reference (`SOURCES.md`)

*Last verified: November 8, 2026*

This document records the endpoints, authentication, rate limits, returned fields, terms of use, and politeness rules for every source in **Daily Tech & Data Pulse**.

---

## 1. Hacker News (Core — Tier 2, weight 0.8)

- **Endpoints:**
  - **Firebase Official API:**
    - Top stories: `GET https://hacker-news.firebaseio.com/v0/topstories.json`
    - Best stories: `GET https://hacker-news.firebaseio.com/v0/beststories.json`
    - New stories: `GET https://hacker-news.firebaseio.com/v0/newstories.json`
    - Item detail: `GET https://hacker-news.firebaseio.com/v0/item/{id}.json`
  - **Algolia HN Search API (preferred for bulk time-window extraction):**
    - By date: `GET https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>{unix_timestamp}&hitsPerPage=100`
    - By popularity: `GET https://hn.algolia.com/api/v1/search?tags=story&numericFilters=created_at_i>{unix_timestamp},points>=5&hitsPerPage=100`
- **Authentication:** None required.
- **Rate Limits:**
  - Firebase API: No hard published limit for read-only access.
  - Algolia API: 10,000 requests per hour per IP.
- **Fields Returned:** `objectID` / `id`, `title`, `url`, `author` / `by`, `points` / `score`, `num_comments` / `descendants`, `created_at` / `time`, `story_text` (optional).
- **Terms of Use:** Publicly accessible via Y Combinator's API terms for non-abusive use; always attribute and link to original URLs.
- **Politeness Rules:** Prefer Algolia batch queries (`hitsPerPage=100`) over hundreds of individual Firebase item calls; wait 0.5s between paginated requests and send a descriptive `User-Agent`.

---

## 2. dev.to / Forem API (Core — Tier 3, weight 0.6)

- **Endpoints:**
  - By tag: `GET https://dev.to/api/articles?tag={tag}&top=2&per_page=30`
  - Fresh/latest by tag: `GET https://dev.to/api/articles?tag={tag}&state=fresh&per_page=30`
  - Configured tags: `dataengineering`, `data`, `python`, `sql`, `ai`, `machinelearning`, `devops`, `opensource`, `cloud`, `database`.
- **Authentication:** None required for public `GET` reads (optional `api-key` header raises limits).
- **Rate Limits:** Unauthenticated: ~10 requests per 30 seconds (300 requests/day).
- **Fields Returned:** `id`, `title`, `description` (snippet), `url`, `canonical_url`, `published_at` (ISO 8601 UTC), `positive_reactions_count`, `public_reactions_count`, `comments_count`, `tag_list`, `user.name`, `user.username`.
- **Terms of Use:** Forem API v0/v1 public terms; store metadata and short description only, never full `body_markdown`.
- **Politeness Rules:** Sleep 1.0–1.5 seconds between tag requests to stay well below the 10 req / 30s limit.

---

## 3. Lobsters (Core — Tier 2, weight 0.8)

- **Endpoints:**
  - Hottest feed: `GET https://lobste.rs/hottest.json`
  - Newest feed: `GET https://lobste.rs/newest.json`
  - Tag feed: `GET https://lobste.rs/t/{tag}.json`
  - Verified tags: `databases`, `ai`, `programming`, `python`, `security`, `devops` (note: `devops` replaces `cloud`, which is not an active Lobsters tag).
- **Authentication:** None required.
- **Rate Limits:** No official numeric limit, but aggressively blocks rapid automated scraping.
- **Fields Returned:** `short_id`, `title`, `url`, `description_plain` (snippet), `created_at`, `score`, `comment_count`, `tags` (list), `submitter_user`, `comments_url`.
- **Terms of Use:** Public JSON feeds provided for readers and aggregators; link to original URLs.
- **Politeness Rules:** Minimum 1.5s delay between requests; max 8 requests per daily run; always include a custom `User-Agent` with repository contact URL.

---

## 4. Official & Expert RSS Feeds (Core — Tier 1, weight 1.0)

- **Endpoints (15 XML RSS/Atom feeds):**
  1. **Databricks Blog:** `https://www.databricks.com/feed`
  2. **Snowflake Blog:** `https://www.snowflake.com/feed/`
  3. **dbt Labs Blog:** `https://www.getdbt.com/blog/feed.xml`
  4. **Confluent Blog:** `https://www.confluent.io/rss.xml`
  5. **Google Cloud Blog:** `https://cloudblog.withgoogle.com/rss/`
  6. **AWS Big Data Blog:** `https://aws.amazon.com/blogs/big-data/feed/`
  7. **Microsoft Fabric Blog:** `https://blog.fabric.microsoft.com/en-us/blog/feed/`
  8. **Netflix TechBlog:** `https://netflixtechblog.com/feed`
  9. **Airbnb Engineering:** `https://medium.com/feed/airbnb-engineering` *(replaces Uber Engineering, which retired native XML RSS)*
  10. **Cloudflare Blog:** `https://blog.cloudflare.com/rss/`
  11. **GitHub Blog:** `https://github.blog/feed/`
  12. **Hugging Face Blog:** `https://huggingface.co/blog/feed.xml`
  13. **OpenAI News:** `https://openai.com/news/rss.xml`
  14. **Data Engineering Weekly:** `https://www.dataengineeringweekly.com/feed`
  15. **DuckDB Blog:** `https://duckdb.org/feed.xml`
- **Authentication:** None required.
- **Rate Limits:** Standard CDN limits per domain (1 request per domain per daily run).
- **Fields Returned:** Standard RSS 2.0 / Atom fields via `feedparser`: `id` / `guid`, `title`, `link`, `summary` / `description`, `published_parsed` / `updated_parsed`, `author`, `tags`.
- **Terms of Use:** Syndication feeds intended for aggregation; store title + <=300-character plain-text snippet only; never store full article HTML.
- **Politeness Rules:** 10s request timeout, standard `User-Agent`, no HTML page scraping.

---

## 5. GitHub Repositories (Core — Tier 2, weight 0.8)

- **Endpoints:**
  - Search repositories: `GET https://api.github.com/search/repositories?q=topic:{topic}+pushed:>={yyyy-mm-dd}&sort=stars&order=desc&per_page=30`
  - Configured topics: `data-engineering`, `duckdb`, `dbt`, `apache-airflow`, `machine-learning`, `llm`, `sql`, `data-science`.
- **Authentication:** Bearer token via `Authorization: Bearer <GITHUB_TOKEN>` (`GITHUB_TOKEN` in GitHub Actions; personal access token with zero scopes in `.env` locally).
- **Rate Limits:**
  - Authenticated Search API: 30 requests per minute.
  - Unauthenticated Search API: 10 requests per minute.
- **Fields Returned:** `id`, `full_name`, `html_url`, `description`, `stargazers_count` (mapped to `source_score`), `forks_count`, `open_issues_count`, `created_at`, `pushed_at`, `updated_at`, `topics`, `owner.login`, `language`.
- **Terms of Use:** GitHub REST API Terms of Service; pass `Accept: application/vnd.github+json` and `X-GitHub-Api-Version: 2022-11-28`.
- **Politeness Rules:** Sleep 2.0s between topic search requests to stay well under 30 requests/minute.

---

## 6. arXiv API (Core — Tier 1, weight 1.0)

- **Endpoints:**
  - Atom query endpoint: `GET https://export.arxiv.org/api/query?search_query=cat:cs.DB+OR+cat:cs.LG+OR+cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=100`
- **Authentication:** None required.
- **Rate Limits:** Strictly **1 request every 3 seconds**; single concurrent connection only.
- **Fields Returned:** Atom XML `<entry>`: `id` (URL), `title`, `summary` (abstract), `published`, `updated`, `author/name`, `arxiv:primary_category`, `category[@term]`.
- **Terms of Use:** arXiv API Terms of Use; metadata and abstracts are CC0 / public domain with attribution to arXiv.org.
- **Politeness Rules:** Combine categories (`cat:cs.DB+OR+cat:cs.LG+OR+cat:cs.AI`) into a single query per run when possible; enforce `time.sleep(3)` before any follow-up call.

---

## 7. Hugging Face Daily Papers (Verified Public Endpoint — Tier 1, weight 1.0)

- **Endpoints:**
  - Daily papers JSON: `GET https://huggingface.co/api/daily_papers?limit=50`
- **Authentication:** None required for read-only access.
- **Rate Limits:** Standard Hugging Face Hub public API rate limits (~100 requests per 5 minutes).
- **Fields Returned:** `paper.id` (arXiv ID), `paper.title`, `paper.summary`, `paper.publishedAt`, `paper.upvotes` (engagement score), `paper.authors`, `numComments`, `publishedAt`.
- **Terms of Use:** Hugging Face Hub API Terms; links back to `https://huggingface.co/papers/{id}` or `https://arxiv.org/abs/{id}`.
- **Politeness Rules:** Single request per daily run (`limit=50`).

---

## 8. Optional & Disabled Sources (Phase 11)

- **Bluesky (Optional — Tier 3, weight 0.6, disabled by default):**
  - Public endpoint: `GET https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={handle}&limit=20` (no auth required for author feeds; App Password required for `app.bsky.feed.searchPosts`).
- **X / Twitter (Optional experimental — Tier 3, weight 0.6, disabled by default):**
  - Cookie-authenticated timeline scraping only for curated handles; strict 200-post cap and fallback to `degraded`/`disabled` if blocked.
- **Reddit (Disabled Stub — Tier 3):**
  - Reddit ended new public API access requests after October 31, 2026, retires RSS feeds on November 13, 2026, and sunsets remaining public API access in March 2027. Maintained only as a disabled stub.