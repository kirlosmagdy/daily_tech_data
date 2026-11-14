{{ config(severity='warn') }}

-- Warn if the latest day's item count is less than half of the 7-day median daily count.
WITH daily_counts AS (
    SELECT
        collected_date,
        COUNT(*) AS cnt
    FROM {{ ref('stg_silver_items') }}
    WHERE collected_date >= CURRENT_DATE - INTERVAL 7 DAY
    GROUP BY collected_date
),
summary AS (
    SELECT
        (SELECT cnt FROM daily_counts ORDER BY collected_date DESC LIMIT 1) AS latest_count,
        MEDIAN(cnt) AS median_7d_count
    FROM daily_counts
)
SELECT *
FROM summary
WHERE latest_count < 0.5 * median_7d_count