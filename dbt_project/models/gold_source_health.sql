-- Summarize health status, item counts, trust tier, and latest collection timestamp per source.
WITH expected_sources AS (
    SELECT * FROM (
        VALUES
            ('medium', 'tier_3', 0.6),
            ('daily_dev', 'tier_3', 0.6),
            ('devbytes', 'tier_3', 0.6)
    ) AS t(source, tier, trust_weight)
),
stats AS (
    SELECT
        source,
        COUNT(*) AS total_items,
        MAX(collected_at) AS last_success_at
    FROM {{ ref('stg_silver_items') }}
    GROUP BY source
)
SELECT
    e.source,
    e.tier,
    e.trust_weight,
    COALESCE(s.total_items, 0) AS item_count,
    s.last_success_at,
    CASE
        WHEN COALESCE(s.total_items, 0) > 0 THEN 'ok'
        ELSE 'failed'
    END AS status
FROM expected_sources e
LEFT JOIN stats s ON e.source = s.source
ORDER BY e.trust_weight DESC, e.source ASC