-- Compare tool mentions in the last 7 days versus the prior 7-day window.
WITH ref AS (
    SELECT MAX(published_at) AS max_pub FROM {{ ref('gold_ranked_items') }}
),
unnested AS (
    SELECT
        UNNEST(r.tools_mentioned) AS tool,
        r.published_at,
        r.sentiment,
        ref.max_pub
    FROM {{ ref('gold_ranked_items') }} r
    CROSS JOIN ref
)
SELECT
    tool,
    COUNT(*) FILTER (WHERE published_at >= max_pub - INTERVAL 7 DAY) AS mentions_last_7d,
    COUNT(*) FILTER (
        WHERE published_at < max_pub - INTERVAL 7 DAY
          AND published_at >= max_pub - INTERVAL 14 DAY
    ) AS mentions_prev_7d,
    COUNT(*) FILTER (WHERE published_at >= max_pub - INTERVAL 7 DAY)
      - COUNT(*) FILTER (
          WHERE published_at < max_pub - INTERVAL 7 DAY
            AND published_at >= max_pub - INTERVAL 14 DAY
      ) AS mentions_delta,
    ROUND(AVG(sentiment) FILTER (WHERE published_at >= max_pub - INTERVAL 7 DAY), 4) AS avg_sentiment_7d
FROM unnested
GROUP BY tool
HAVING COUNT(*) FILTER (WHERE published_at >= max_pub - INTERVAL 14 DAY) > 0
ORDER BY mentions_last_7d DESC, mentions_delta DESC