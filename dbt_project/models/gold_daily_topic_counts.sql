-- Aggregate daily item counts per topic across the 90-day history window.
WITH unnested AS (
    SELECT
        published_date AS metric_date,
        UNNEST(topics) AS topic,
        canonical_url
    FROM {{ ref('gold_ranked_items') }}
    WHERE published_date >= CURRENT_DATE - INTERVAL 90 DAY
)
SELECT
    metric_date,
    topic,
    COUNT(DISTINCT canonical_url) AS item_count
FROM unnested
GROUP BY metric_date, topic
ORDER BY metric_date DESC, item_count DESC