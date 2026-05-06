# Deduplication Cache
__Category:__ Data Structures

## Overview

The `deduplication_cache` skill gives an AI agent a constant-size memory that answers "Have I seen this before?" in constant time. It is an HDC implementation of a Bloom-filter-like structure: seen items are superimposed into a single accumulator vector; membership is tested by cosine distance. Unlike a Bloom filter, the accumulator supports graceful degradation rather than hard hash collisions.

### The LLM Problem

Agents running multi-step agentic loops (web crawling, search result processing, tool-call deduplication) need to track what they have already processed. Maintaining a raw list consumes O(n) context tokens and must be re-injected every session. The LLM may also hallucinate incorrect membership in the list.

### The HDC Solution

Every seen item is summed into an integer accumulator. The cosine distance between the (thresholded) accumulator and a new item vector indicates membership: members sit near 0.5; non-members near 1.0. The threshold is user-tunable.

## How the Math Works

1. __Adding an Item:__ `cache += V_item`.
2. __Membership Test:__ `dist(thresh(cache), V_item) < threshold → DUPLICATE`.
3. __Graceful Degradation:__ As more items are added, the bundled vector approaches a random vector and the false positive rate increases. At 10,000 dimensions, up to ~200 items maintain reliable discrimination.

## Example Interaction

```json
{"action": "check_and_add", "cache_id": "urls", "item": "page_1"}
```
_Response:_ `{"is_duplicate": false, "was_added": true, "cache_size": 1}`

```json
{"action": "check_and_add", "cache_id": "urls", "item": "page_2"}
```
_Response:_ `{"is_duplicate": false, "was_added": true, "cache_size": 2}`

```json
{"action": "check_and_add", "cache_id": "urls", "item": "page_1"}
```
_Response:_ `{"is_duplicate": true, "was_added": false, "cache_size": 2}`

```json
{"action": "check_only", "cache_id": "urls", "item": "page_99"}
```
_Response:_ `{"is_duplicate": false, "distance": 1.004}`
