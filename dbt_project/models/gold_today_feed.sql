-- Select the top 100 ranked items published or collected within the last 36 hours of the latest run.
WITH max_ts AS (
    SELECT MAX(collected_at) AS ref_time FROM {{ ref('gold_ranked_items') }}
)
SELECT
    r.*
FROM {{ ref('gold_ranked_items') }} r
CROSS JOIN max_ts m
WHERE r.published_at >= m.ref_time - INTERVAL 36 HOUR
   OR r.collected_at >= m.ref_time - INTERVAL 36 HOUR
ORDER BY r.rank_score DESC
LIMIT 100