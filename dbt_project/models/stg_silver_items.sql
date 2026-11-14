{{ config(materialized='view') }}

-- Read enriched Silver items from Parquet and standardize types and tier names.
SELECT
    source,
    source_item_id,
    canonical_url,
    title,
    snippet,
    author,
    CAST(published_at AS TIMESTAMPTZ) AS published_at,
    CAST(collected_at AS TIMESTAMPTZ) AS collected_at,
    CAST(published_at AS DATE) AS published_date,
    CAST(collected_at AS DATE) AS collected_date,
    CAST(source_score AS INTEGER) AS source_score,
    CAST(comments_count AS INTEGER) AS comments_count,
    source_tags,
    domain,
    topics,
    tools_mentioned,
    CAST(sentiment AS DOUBLE) AS sentiment,
    CAST(trust_weight AS DOUBLE) AS trust_weight,
    CASE
        WHEN trust_weight >= 0.95 THEN 'tier_1'
        WHEN trust_weight >= 0.75 THEN 'tier_2'
        ELSE 'tier_3'
    END AS tier,
    mentioned_in_sources
FROM read_parquet('data/history/silver_items.parquet')