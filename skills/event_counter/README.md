# Event Counter
__Category:__ Stream Processing

## Overview

The `event_counter` skill gives an AI agent a constant-space frequency counter for event streams. Instead of maintaining a raw frequency table, items are accumulated into a single integer vector. Frequencies are estimated via dot-product projection — a property unique to HDC that allows approximate counting from a single compressed representation.

### The LLM Problem

Agents processing event streams (log analysis, conversation analytics, error monitoring) cannot maintain incrementally growing dictionaries beyond the context window. Asking the LLM to count events from a stream requires re-injecting the entire history each time.

### The HDC Solution

HDC provides a mathematically grounded approximate counting mechanism. The accumulator stores `count(item_i) * V_item_i` implicitly in the sum. The dot product `(acc · V_item) / D` (where D is the dimension) gives an unbiased estimate of the item's count, scaled linearly with frequency.

## How the Math Works

1. __Observation:__ Each event increments the accumulator: `acc += V_event`.

2. __Count Estimation:__ `estimated_count(item) = (acc · V_item) / D`. This works because `E[V_item · V_item] = D` (self-dot) and `E[V_item · V_other] ≈ 0` (orthogonality). The noise term scales as O(√(total_events / D)).

3. __Top Items:__ Scan all codebook entries and return those with the highest estimated counts.

## Example Interaction

1. Observe Events (Action: `observe`)

```json
{
    "action": "observe",
    "counter_id": "http_errors",
    "events": ["404", "500", "404", "404", "403", "500"]
}
```

_Handler Response:_ `{"status": "success", "message": "6 event(s) observed in counter 'http_errors'. Total observations: 6."}`

2. Estimate Frequency (Action: `estimate_count`)

```json
{"action": "estimate_count", "counter_id": "http_errors", "item": "404"}
```

_Handler Response:_ `{"status": "success", "item": "404", "estimated_count": 2.99, "total_observations": 6}`

3. Top 3 Errors (Action: `top_items`)

```json
{"action": "top_items", "counter_id": "http_errors", "n": 3}
```

_Handler Response:_
```json
{
  "top_items": [
    {"item": "404", "estimated_count": 2.99},
    {"item": "500", "estimated_count": 1.97},
    {"item": "403", "estimated_count": 0.96}
  ]
}
```
