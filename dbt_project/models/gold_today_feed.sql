-- Select up to 300 newest relevant items published within the last 7 days of the latest run.
WITH max_ts AS (
    SELECT MAX(collected_at) AS ref_time FROM {{ ref('gold_ranked_items') }}
)
SELECT
    r.*
FROM {{ ref('gold_ranked_items') }} r
CROSS JOIN max_ts m
WHERE r.published_at >= m.ref_time - INTERVAL 7 DAY
ORDER BY r.published_at DESC, r.rank_score DESC
LIMIT 300