# Tool: HDC Deduplication Cache (`deduplication_cache`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Deduplication Cache. Use this tool to efficiently detect whether an item has been processed before, without keeping a raw list of everything you have seen. This is ideal for avoiding duplicate tool calls, deduplicating search results, tracking already-processed URLs or document IDs, or preventing repeated notifications.

## How It Works

Seen items are accumulated into a single hypervector (the cache vector). To check if a new item has been seen, its vector is compared to the cache via cosine distance. Items in the cache produce low distance (~0.5), while unseen items produce high distance (~1.0). A configurable threshold separates the two.

## Schema & Actions

### 1. Action: `check_and_add`

The primary operation: checks if an item is a duplicate and, if not, adds it to the cache.

__Input Arguments:__
- `action` (string): `"check_and_add"`.
- `cache_id` (string): Name of the cache (e.g., `"visited_urls"`).
- `item` (string): The item to check. Can be a single word, a URL slug, or a space-separated list of features.
- `threshold` (float, optional): Cosine distance cutoff. Default is `0.75`.

__Example Payload:__

```json
{
    "action": "check_and_add",
    "cache_id": "visited_pages",
    "item": "page_42"
}
```

### 2. Action: `check_only`

Checks for a duplicate without modifying the cache.

```json
{
    "action": "check_only",
    "cache_id": "visited_pages",
    "item": "page_42"
}
```

### 3. Action: `clear_cache`

Resets the cache to empty (preserves the threshold setting).

```json
{"action": "clear_cache", "cache_id": "visited_pages"}
```

### 4. Action: `cache_stats`

Returns the current item count and threshold for a cache.

```json
{"action": "cache_stats", "cache_id": "visited_pages"}
```

## Strict Rules for the Agent

1. __`check_and_add` is Idempotent for Duplicates:__ If an item is detected as a duplicate, it is NOT added again. Safe to call repeatedly.
2. __Approximate Detection:__ This is a probabilistic structure. False positives (flagging a new item as seen) increase as the cache grows. Reliable for caches up to a few hundred items at dimension 10,000.
3. __No Individual Removal:__ Once added, individual items cannot be removed. Use `clear_cache` to reset entirely.
4. __Item Encoding:__ Items are tokenized by whitespace. `"doc 42"` is treated as a bundle of two features `"doc"` and `"42"`. Use consistent tokenization.
