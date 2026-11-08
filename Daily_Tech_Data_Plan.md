# Daily Tech & Data Pulse — Project Plan

*Implementation plan · November 8, 2026 · Version 1.1 (the project name is a placeholder)*

## 1. How to use this document

This is a manager’s plan, not code. Give the whole document to the AI that will build the project. Rules for the implementing AI:

- Work one phase at a time. At the end of each phase, report what was produced and compare it with the “Expected output”. Do not start the next phase until the human confirms.
- Keep everything simple, with no over-engineering. Write the least code that does the job: short plain functions, clear names, and no extra classes, layers, abstractions or features beyond this plan. The code must still look professional: readable, consistent and easy to follow. Comments must be 1 or 2 lines at most and only explain the main purpose of the function or block.
- Before writing any connector, open the source’s official documentation or endpoint and confirm how it works today. This plan was researched in November 2026 and external services change often.
- Never put passwords, tokens or cookies in the repository. Use GitHub Secrets for automation and a local environment file (excluded from git) for development.
- Pin dependency versions, and choose versions that were released at least two weeks ago.
- If something in this plan conflicts with reality (an API changed, a feed is dead, a limit is different), stop and ask the human instead of guessing.
- Steps marked **[Human]** cannot be done by an AI (creating accounts, copying cookies, approving choices). Steps marked **[AI]** are for the implementing AI.

## 2. Goal and scope

**Goal:** a free website that, every day and automatically, collects the newest and most relevant tech and data content from several trustworthy sources, merges it into one clean dataset, and shows it as (a) a daily ranked feed and (b) an analytics dashboard of trends and sentiment. It serves two purposes: a daily reading tool for the owner and a portfolio-grade data engineering project.

**Topics covered:** data engineering, analytics and BI, databases and data warehouses, AI and machine learning, programming and developer tools, cloud, security, open source.

**Success criteria:**

1. The pipeline runs every day with no human action.
2. The website shows data refreshed within the last 24 hours, with a visible “last updated” time.
3. At least five independent sources work on launch day.
4. If one source fails, the run and the website still work.
5. The Today page scores 90 or more on mobile Lighthouse performance.
6. Total cost is zero.
7. The repository is portfolio-ready: README, architecture diagram, tests, data model documentation.

**Out of scope for version 1:** user accounts, comments, email newsletters, paid APIs, storing full article text, AI-written summaries, Arabic content.

## 3. Locked decisions

| Area | Decision |
|---|---|
| Language of data and site | English |
| Core sources | Hacker News, dev.to, Lobsters, RSS feeds of official company and expert blogs, GitHub, arXiv |
| Optional sources (after launch) | Bluesky, X (by scraping only, no paid API), Reddit |
| Programming language | Python 3.11 or newer |
| Storage | Parquet files plus DuckDB (no database server) |
| Transformations | dbt-core with the DuckDB adapter |
| Sentiment | VADER (rule-based, local, free) |
| Daily automation (production) | GitHub Actions |
| Orchestration showcase | Apache Airflow in Docker, local only |
| Website | Next.js in static export mode |
| Hosting | Vercel Hobby plan (personal and non-commercial: no ads, no payments) |
| Repository | Public on GitHub (unlimited free Actions minutes) |
| Content policy | Store the title, a snippet of at most 300 characters, metadata and the link. Never store or display full articles. Always show the source and link to the original. |

## 4. Architecture

The daily flow, in order:

1. **Extract:** one connector per source pulls recent items and saves raw JSON files (Bronze).
2. **Normalize:** map everything to one schema, clean it, remove duplicates (Silver).
3. **Enrich:** add topics, tool mentions and sentiment.
4. **Transform:** dbt builds the ranking and the aggregates (Gold) and runs data tests.
5. **Export:** write small JSON files for the website.
6. **Publish:** commit the data to GitHub; Vercel rebuilds the static site.

**Persistence rule:** GitHub’s runners are wiped after every run, so history must live in the repository. Each run commits a compact Parquet history of the last 90 days. The DuckDB file itself is not committed; it is rebuilt from the Parquet history at the start of each run.

## 5. Unified data model

Every source is mapped to these fields:

- **From the source:** source, source_item_id, canonical_url, title, snippet, author, published_at (UTC), collected_at (UTC), source_score (points, upvotes, reactions or stars, if any), comments_count, source_tags, domain.
- **Derived by the pipeline:** topics (list), tools_mentioned (list), sentiment (−1 to 1), trust_weight, rank_score, mentioned_in_sources (list, when the same URL appears in several sources).

## 6. Trust and ranking rules (starting values, adjustable)

**Trust tiers**

- Tier 1, weight 1.0: official company engineering blogs and release notes, arXiv papers.
- Tier 2, weight 0.8: curated communities (Hacker News, Lobsters) and GitHub.
- Tier 3, weight 0.6: open platforms (dev.to, Bluesky, X, and Reddit if ever enabled).

**Rank score** = engagement percentile × trust weight × freshness × cross-source bonus.

- Engagement percentile: where the item stands among the same source’s items from the last 7 days, using points plus twice the comments. Sources with no engagement data (RSS, arXiv) get a fixed percentile of 0.7.
- Freshness: the value halves every 18 hours.
- Cross-source bonus: +15% for each additional source linking to the same URL, up to +45%.

**Relevance filter:** Lobsters, dev.to (restricted by tag), arXiv, RSS and GitHub are already tech-specific. Hacker News is general, so keep a Hacker News item only if its title or snippet matches at least one topic keyword.

**Quality filter:** drop items with an empty title, a missing URL, a title shorter than 10 characters, or a score below a per-source minimum (set in Phase 3 after looking at real data).

**Honesty rule:** the site never claims an item is “verified true”. It shows the source and its tier, and links to the original.

## 7. Repository layout

- **connectors/** — one file per source.
- **pipeline/** — normalize, enrich, export, and the run-everything entry point.
- **dbt_project/** — models and tests.
- **seeds/** — editable CSV files for topic keywords and the tools list.
- **data/raw/** — raw files (not committed). **data/history/** — compact Parquet history (committed).
- **site/** — the Next.js app, with the exported JSON in site/data.
- **airflow/** — local DAG and Docker files.
- **tests/** — unit tests with saved sample responses.
- **.github/workflows/** — the daily workflow.
- **docs/** — SOURCES, DATA_MODEL, METHODOLOGY. Plus README at the top level.

## 8. Phases and steps

### Phase 0 — Accounts and workspace

**Step 0.1 [Human] Install tools.** Python 3.11 or newer, Node.js (LTS), Git, VS Code, and Docker Desktop (needed only in Phase 10).
*Expected output:* the version command of each tool runs without errors.

**Step 0.2 [Human] Create the repository.** A new public GitHub repository with a README and a .gitignore for Python and Node. Clone it locally.
*Expected output:* a local folder linked to GitHub, and a test commit pushes successfully.

**Step 0.3 [Human] Create a Vercel account** (Hobby plan) using the GitHub login. Do not import the repository yet.
*Expected output:* a Vercel account connected to GitHub.

**Step 0.4 [AI] Project skeleton.** Create the folder layout from section 7, a Python virtual environment, a requirements file with pinned versions, a .gitignore (raw data, DuckDB file, environment file, node_modules), a central config file (enabled sources, tags, feeds, topic keywords, thresholds) and a README stub.
*Expected output:* the empty structure is committed; one command installs all dependencies; the config file loads without errors.

### Phase 1 — Source verification (no pipeline code yet)

**Step 1.1 [AI] Verify every core source** against its official documentation and write docs/SOURCES.md. For each source record: endpoints, authentication needed, rate limits, fields returned, terms of use, politeness rules.

- **Hacker News:** the official Firebase API (top, best and new lists, item details) and the Algolia search API (keyword and date search).
- **dev.to:** the public articles API by tag and by top-of-period. Starting tags: dataengineering, data, python, sql, ai, machinelearning, devops, opensource, cloud, database.
- **Lobsters:** the public JSON for hottest, newest and tag pages. Starting tags: databases, ai, programming, python, security, cloud (verify the exact tag names).
- **RSS:** propose about 15 official feeds (examples: Databricks, Snowflake, dbt Labs, Confluent, Google Cloud data analytics, AWS big data, Microsoft Fabric, Netflix tech blog, Uber engineering, Cloudflare, GitHub blog, Hugging Face blog, OpenAI, Data Engineering Weekly). Test every feed URL and keep only feeds that return recent items. Do not scrape HTML pages in version 1.
- **GitHub:** there is no official “trending” API. Approximate it with the search API (repositories created or pushed recently, sorted by stars, in relevant topics). Use the token that GitHub Actions provides.
- **arXiv:** the official API, categories cs.DB, cs.LG and cs.AI. Respect the documented request spacing (verify it; historically one request every 3 seconds).
- **Hugging Face Daily Papers:** check whether an official public endpoint exists. If not, skip it.

*Expected output:* the SOURCES document, plus one trimmed real sample response per source saved as a test fixture.

**Step 1.2 [Human] Approve the list.** Review SOURCES.md, remove anything you do not want, and confirm the RSS list and tags.
*Expected output:* the final approved source list in the config file.

### Phase 2 — Extraction (Bronze layer)

**Step 2.1 [AI] Connector contract and shared helpers.** Every connector takes its config and returns a list of raw records plus a status (ok, partial or failed), item count, duration and error message. A connector must never crash the whole run. Shared helpers: HTTP requests with a timeout, 3 retries with increasing waits, a clear User-Agent that identifies the project, a polite delay between calls, and logging.
*Expected output:* a shared helper module and a short description of the connector contract in docs.

**Steps 2.2 to 2.7 [AI] Build the connectors one by one:** Hacker News, dev.to, Lobsters, RSS, GitHub, arXiv (and Hugging Face papers if it exists). Look-back window: 48 hours. After each connector, run it alone and save its raw output.
*Expected output (per connector):* a raw JSON file in data/raw/DATE/SOURCE with realistic counts (tens to a few hundred items) and a one-line status.

**Step 2.8 [AI] Extraction runner.** One entry point runs all enabled connectors (a failure in one does not stop the others), saves the raw files and writes a run report (status, count, duration and error per source).
*Expected output:* one run creates raw files for all sources plus a run report, and at least 5 sources report ok.

### Phase 3 — Normalize and clean (Silver layer)

**Step 3.1 [AI] Map and clean.** Map each source to the unified schema (section 5). Strip HTML, trim whitespace, cut snippets to 300 characters, convert every time to UTC, keep English only (language detection) and drop invalid records.

**Step 3.2 [AI] Canonical URLs and deduplication.** Remove tracking parameters, normalize the host and trailing slashes. If the same canonical URL appears in several sources, keep one record: use the highest tier’s metadata, list all sources in mentioned_in_sources, keep the maximum score.

**Step 3.3 [AI] Store.** Append to the DuckDB table and write a Parquet snapshot. Keep 90 days.

**Step 3.4 [AI + Human] Threshold review.** The AI produces a profile report (rows per source, percentage dropped by each filter, score distribution). The human reviews it and approves the minimum-score thresholds.

*Expected output:* a Silver table where canonical_url is unique, no title or URL is null, and an approved profile report with final thresholds in the config.

### Phase 4 — Enrichment

**Step 4.1 [AI] Seed files.** Create editable CSV seeds: topics with keyword lists (one per topic in section 2) and a tools list of about 30 starting names (examples: dbt, Spark, Airflow, Snowflake, Databricks, Kafka, DuckDB, PostgreSQL, BigQuery, Power BI, Polars, Iceberg, ClickHouse, Kubernetes, PyTorch). Ambiguous names (such as Spark) must require a context word in the same text (for example Apache or data) to avoid false matches.

**Step 4.2 [AI] Topics and tools.** Apply the Hacker News relevance filter, tag each item with one or more topics, and detect tool mentions (whole word, case-insensitive).

**Step 4.3 [AI] Sentiment.** Run VADER on title plus snippet and store a score from −1 to 1. It is rough, rule-based and English-only; the site must describe it as the tone of discussion, not as quality.

**Step 4.4 [Human] Spot check.** Review 30 random items and edit the seed files until you are satisfied.
*Expected output:* the enriched Silver data has topics, tools_mentioned and sentiment filled, and about 80% or more of the sampled topic tags look right.

### Phase 5 — Gold layer with dbt

**Step 5.1 [AI] Initialize dbt** with the DuckDB adapter, reading the Silver Parquet data.

**Step 5.2 [AI] Models.** A staging model; ranked items (formula in section 6); today’s feed (top 100 items from the last 24 to 36 hours); daily topic counts (90 days); daily tool mentions with the change between the last 7 days and the 7 days before; weekly tool sentiment (show only tools with at least 10 mentions that week); source health (status, counts and last success per source).

**Step 5.3 [AI] Tests.** Not-null and unique on canonical_url; accepted values for source and tier; sentiment between −1 and 1; freshness (newest collected item within 36 hours); a row-count sanity check that warns when today’s count is under half of the 7-day median.

**Step 5.4 [AI] Documentation.** Generate dbt docs with a description for every model and column.

**Step 5.5 [Human] Review.** Look at today’s top 20 and decide whether it feels relevant. If not, ask the AI to adjust the weights in section 6.
*Expected output:* dbt build passes all tests on real data, the Gold tables can be queried, and the human approves the top-20 quality.

### Phase 6 — Export and history

**Step 6.1 [AI] Export step.** Write small JSON files into site/data: today (top 100), per-topic lists, trends (30 days of topic counts), tools (mentions and change), sentiment (weekly), sources (health, last success, tier) and meta (generation time, counts, version). Keep each file under about 1 MB.

**Step 6.2 [AI] History management.** Write compact Parquet history (last 90 days) into data/history, prune older data, and rebuild DuckDB from it at the start of each run.

**Step 6.3 [AI] One command to run everything:** extract, normalize, enrich, dbt build, export. If all sources fail, stop with an error and do not overwrite the site data.
*Expected output:* one command runs the full pipeline locally (target under 10 minutes), leaves updated JSON files and history, and running it twice in a row does not duplicate data.

### Phase 7 — Website

**Step 7.1 [AI] Create the site.** A Next.js app in site/ in static export mode that reads the JSON files at build time. No runtime calls to external APIs. Mobile first, with light and dark themes.

**Step 7.2 [AI] Pages.**

- **Today:** the ranked feed with filters by source and topic, text search in the browser, and sorting by rank or newest. Each card shows the title, a source badge with its tier, the time, topics, the snippet, a link to the original and an “also seen on” list when relevant.
- **Trends:** topic volume over 30 days, top tools and the biggest risers. Choose a chart library with a small bundle size.
- **Sentiment:** tool tone this week versus last week, with a note that it measures the tone of discussion and not product quality.
- **Sources:** a health table (last success, item count, status) and the trust tiers.
- **About and Methodology:** how ranking and trust work, limitations, attribution and a link to the repository.

**Step 7.3 [AI] Performance and quality.** Little client-side JavaScript on Today, lazy-loaded charts, optimized fonts, “last updated” on every page, and sensible empty and error states. Targets: mobile Lighthouse performance 90 or more, accessibility 90 or more.
*Expected output:* the site builds locally from the Phase 6 JSON, all five pages work on phone and desktop, and the Lighthouse targets are met.

### Phase 8 — Daily automation

**Step 8.1 [AI] Workflow file.** Schedule it once a day at a time that is morning in Cairo, at a minute that is not exactly on the hour (scheduled runs can be delayed under load). Also add a manual run button.

**Step 8.2 [AI] Workflow steps.** Check out the repository, set up Python with a dependency cache, run the full pipeline, and if the files in site/data or data/history changed, commit and push them to the main branch. Add a concurrency rule so two runs never overlap, and use minimal permissions (write access to repository contents only).

**Step 8.3 [Human] Secrets.** Add secrets in GitHub only if needed (none for the core sources; the GitHub API uses the built-in token). For local runs, put a GitHub personal access token (no special permissions) in the local environment file, because unauthenticated GitHub API limits are very low.

**Step 8.4 [AI] Failure behavior.** If some sources fail, commit anyway and let the Sources page show the failure. If all sources fail, or a dbt test fails with an error, do not commit and mark the run as failed so GitHub emails the owner.

**Step 8.5 Keep-alive check.** GitHub disables scheduled workflows in public repositories after 60 days without repository activity. Daily data commits should count as activity, but verify this after the first month. If the workflow gets disabled, re-enable it in the Actions tab.
*Expected output:* a manual run succeeds (green) and creates a data commit, the scheduled run happens by itself the next day, and a run takes under 15 minutes.

### Phase 9 — Deployment on Vercel

**Step 9.1 [Human] Import the repository** into Vercel. Set the Root Directory to site, the framework to Next.js and the production branch to main.

**Step 9.2 [AI + Human] End-to-end test.** Trigger the workflow manually, then confirm that the bot commit starts a new Vercel deployment and the site shows the new timestamp. If the deployment is blocked because of the commit author, first set the workflow’s commit author to the owner’s own GitHub identity. If it is still blocked, call a Vercel Deploy Hook at the end of the workflow (store the hook URL as a secret).

**Step 9.3 [Human] Optional custom domain.** Remember that Hobby is for personal, non-commercial use only.
*Expected output:* a live public URL, and the next morning the “last updated” time shows that the scheduled run updated the site without any manual action.

### Phase 10 — Airflow showcase (local only)

Airflow needs an always-on server, so production stays on GitHub Actions. This phase exists to demonstrate orchestration skills.

**Step 10.1 [AI] Local Airflow in Docker** with one DAG that mirrors the pipeline: extraction tasks per source in parallel, then normalize, enrich, dbt build and export. It must reuse the same Python modules (no duplicated logic), have retries, and be paused by default.

**Step 10.2 [Human] Run it.** Start Airflow locally, run the DAG once manually and take a screenshot of the graph.

**Step 10.3 [AI] README section** explaining how to run Airflow locally and why production uses GitHub Actions.
*Expected output:* the DAG appears in the Airflow UI, runs end to end successfully, and a screenshot is ready for the README.

### Phase 11 — Optional connectors (start after about one stable week)

Each connector is disabled by default through a switch in the config, runs after the core connectors, and its failure must never block the pipeline. All of them are Tier 3.

**Step 11.1 Bluesky.**

- **[Human]** Create a Bluesky account and an App Password (never the main password). Build a list of 30 to 50 handles of data and tech experts and organizations. The AI may suggest candidates, but the human verifies each one.
- **[AI]** Read recent posts from the listed accounts through the public API (no login). Add keyword search only if credentials are provided as secrets. Stay far below the documented rate limits. Verify the current endpoints and authentication rules first: keyword search required authentication at the time of research.

*Expected output:* Bluesky posts appear with the source “bluesky”, and the Sources page shows its status.

**Step 11.2 X (Twitter) by scraping — experimental.**

- **Known facts:** the older free tools (twint, snscrape, public Nitter instances) no longer work. Maintained tools such as Scweet reportedly work with a logged-in browser cookie, but they rely on undocumented endpoints that can break at any time. Scraping may violate X’s terms, and the account used can be restricted or banned. Do not use the python-twitter package: it is a wrapper for the official paid API, not a scraper, and it needs API keys.
- **[Human]** Create a brand-new dedicated X account (never your personal one). Log in through a browser, copy the auth_token cookie value and store it as a secret (local environment file and GitHub Secret). Build a list of about 30 expert accounts.
- **[AI]** First check which tool is currently maintained and working (read its documentation and recent releases). Read only the timelines of the listed accounts (no broad search), with a hard limit per run (about 200 posts) and polite delays. Test whether it works from GitHub-hosted runners; X may block data-center IPs (an expectation, not verified). If it is blocked, use these fallbacks in order: (1) run the X connector on the owner’s own computer on a schedule and push its output; (2) use a hosted scraping service with a free tier (check the cost first); (3) leave X disabled.
- **Failure handling:** if the cookie expires or access is blocked, mark the status “degraded” on the Sources page and let the pipeline continue.

*Expected output:* either X posts flowing with a clear status, or a documented “disabled” state with the reason. Both are acceptable outcomes.

**Step 11.3 Reddit — disabled stub.** Reddit stopped accepting new public API access requests after October 31, 2026, will end RSS on November 13, 2026, and plans to close the remaining public API access in March 2027. Create only a disabled connector stub. Enable it only if the human already has an approved registered app, and plan to remove it by March 2027.
*Expected output:* a disabled stub and a note in SOURCES.md.

### Phase 12 — Quality, tests and documentation

**Step 12.1 [AI] Unit tests** for each connector’s parser and for the cleaning, deduplication and ranking functions, using the saved sample responses (no live network calls in tests).

**Step 12.2 [AI] Staleness signal.** The Sources page shows each source’s last success, and a warning banner appears when the data is older than 36 hours.

**Step 12.3 [AI] README.** What the project is, the live link, an architecture diagram (image), the data model, how to run it locally, how the automation works, limitations, the list of sources with attribution, and the license. Add the dbt docs and Airflow screenshots.

**Step 12.4 [Human] Final review.** Read the README as a stranger would, and confirm that no secrets exist anywhere in the git history.
*Expected output:* all tests pass with one command, the README is complete, and the repository is ready to show.

### Phase 13 — Final acceptance checklist

- [ ] The pipeline ran by itself for 3 days in a row without human action.
- [ ] The website shows data from the last 24 hours and a correct “last updated” time.
- [ ] At least 5 sources report ok on the Sources page.
- [ ] Disabling one source does not break the run or the site.
- [ ] Mobile Lighthouse performance is 90 or more on Today.
- [ ] Every item shows its source and links to the original, and no full articles are stored.
- [ ] Tests and dbt tests pass.
- [ ] README, architecture diagram and Airflow screenshot are in the repository.
- [ ] No secrets in the repository or its history.
- [ ] Total cost is zero.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| A source changes its API or disappears | One connector per source with failure isolation, a Sources health page, fixture-based tests, a switch to disable it |
| X scraping is blocked or the account is banned | X is optional, uses a dedicated account, and has three fallbacks |
| Reddit closes its public API | Disabled stub, planned removal by March 2027 |
| The scheduled workflow is delayed or disabled | Off-peak minute, stale-data banner, the 60-day check, manual run button |
| The repository grows too large | 90-day Parquet history, DuckDB file not committed |
| Vercel does not deploy bot commits | Owner’s commit identity, or a Vercel Deploy Hook |
| The feed is noisy (especially Hacker News) | Relevance filter, editable keyword seeds, manual review in Phases 4 and 5 |
| Hobby plan terms | No ads or payments; change hosting before any monetization |
| Copyright | Snippets only, always attribute and link to the original |

## 10. Suggested timeline (part-time)

- **Week 1:** Phases 0 to 2.
- **Week 2:** Phases 3 to 6.
- **Week 3:** Phases 7 to 9 (launch).
- **Week 4:** Phases 10 and 12.
- **After the first stable week:** Phase 11 (optional connectors), then Phase 13 to close the project.
