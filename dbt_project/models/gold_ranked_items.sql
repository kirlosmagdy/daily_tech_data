-- Compute rank_score using engagement percentile, trust weight, 18h freshness decay, and cross-source bonus.
WITH base AS (
    SELECT
        *,
        MAX(collected_at) OVER () AS latest_run_at,
        (source_score + 2 * comments_count) AS raw_engagement
    FROM {{ ref('stg_silver_items') }}
),
scored AS (
    SELECT
        *,
        CASE
            WHEN source IN ('rss', 'arxiv') THEN 0.7
            WHEN published_at >= latest_run_at - INTERVAL 7 DAY THEN
                CUME_DIST() OVER (
                    PARTITION BY source, (published_at >= latest_run_at - INTERVAL 7 DAY)
                    ORDER BY raw_engagement ASC
                )
            ELSE 0.5
        END AS engagement_percentile,
        POWER(
            0.5,
            GREATEST(date_diff('minute', published_at, latest_run_at) / 60.0, 0.0) / 18.0
        ) AS freshness_score,
        1.0 + LEAST(GREATEST(len(mentioned_in_sources) - 1, 0) * 0.15, 0.45) AS cross_source_bonus
    FROM base
)
SELECT
    source,
    tier,
    source_item_id,
    canonical_url,
    title,
    snippet,
    author,
    published_at,
    collected_at,
    published_date,
    collected_date,
    source_score,
    comments_count,
    source_tags,
    domain,
    topics,
    tools_mentioned,
    sentiment,
    trust_weight,
    mentioned_in_sources,
    ROUND(engagement_percentile, 4) AS engagement_percentile,
    ROUND(freshness_score, 4) AS freshness_score,
    ROUND(cross_source_bonus, 2) AS cross_source_bonus,
    ROUND(engagement_percentile * trust_weight * freshness_score * cross_source_bonus, 4) AS rank_score
FROM scored
ORDER BY rank_score DESC