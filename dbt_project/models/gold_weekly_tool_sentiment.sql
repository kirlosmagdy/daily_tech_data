-- Compute weekly average sentiment for tools with at least 10 mentions in that week.
WITH unnested AS (
    SELECT
        DATE_TRUNC('week', published_date) AS week_start,
        UNNEST(tools_mentioned) AS tool,
        sentiment,
        canonical_url
    FROM {{ ref('gold_ranked_items') }}
)
SELECT
    week_start,
    tool,
    COUNT(DISTINCT canonical_url) AS mentions_count,
    ROUND(AVG(sentiment), 4) AS avg_sentiment
FROM unnested
GROUP BY week_start, tool
HAVING COUNT(DISTINCT canonical_url) >= 10
ORDER BY week_start DESC, mentions_count DESC