-- Fail if the newest collected item in Silver is older than 36 hours.
SELECT
    MAX(collected_at) AS newest_collected_at
FROM {{ ref('stg_silver_items') }}
HAVING MAX(collected_at) < NOW() - INTERVAL 36 HOUR