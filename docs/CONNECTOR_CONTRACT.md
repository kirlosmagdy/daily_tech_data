# Connector Contract

Every source module in `connectors/` must expose a single entry-point function with the following signature:

```python
def extract(cfg: dict) -> dict:
```

## Return Dictionary Schema

Each connector must return a dictionary created via `connectors.common.make_result` containing these exact keys:

| Key | Type | Description |
|---|---|---|
| `source` | `str` | Canonical source identifier (e.g., `"hackernews"`, `"arxiv"`, `"github"`). |
| `status` | `str` | Execution outcome: `"ok"`, `"partial"`, or `"failed"`. |
| `count` | `int` | Number of raw items returned in `items` (`len(items)`). |
| `duration_s` | `float` | Wall-clock execution time in seconds, rounded to 2 decimals. |
| `error` | `str \| None` | Error summary when `status` is `"partial"` or `"failed"`, otherwise `None`. |
| `collected_at` | `str` | ISO-8601 UTC timestamp when extraction completed. |
| `items` | `list[dict]` | List of source-specific raw item dictionaries. |

## Status Values

* **`ok`**: All requests for the source succeeded without errors.
* **`partial`**: Some sub-requests (e.g., individual RSS feeds or categories) failed, but at least one item was collected.
* **`failed`**: Extraction failed completely or returned zero items due to an unhandled network/API error.