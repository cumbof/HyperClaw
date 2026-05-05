# Tool: HDC Event Counter (`event_counter`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Event Counter. Use this tool to track the frequency of events in a stream without storing a raw frequency table. This is ideal for counting word frequencies, API call frequencies, user action tallies, error code occurrences, or any scenario where you need to answer "How many times did X occur?" or "What are the most frequent events?" without a persistent database.

## How It Works

Events are recorded by adding their hypervectors to a single integer accumulator. Item frequencies are estimated using the dot-product projection property of HDC: the inner product between the accumulator and an item's vector scales linearly with how many times the item was observed.

## Schema & Actions

### 1. Action: `observe`

Records one or more events (repeat an item in the list to count it multiple times).

__Input Arguments:__
- `action` (string): `"observe"`.
- `counter_id` (string): Name of the counter (e.g., `"api_calls"`, `"word_freq"`).
- `events` (array of strings): List of event labels to observe. Repeat a label to increment its count.

__Example Payload:__

```json
{
    "action": "observe",
    "counter_id": "error_codes",
    "events": ["404", "500", "404", "404", "403", "500"]
}
```

### 2. Action: `estimate_count`

Estimates how many times an item was observed.

__Input Arguments:__
- `action` (string): `"estimate_count"`.
- `counter_id` (string): The counter to query.
- `item` (string): The event label to estimate.

__Example Payload:__

```json
{
    "action": "estimate_count",
    "counter_id": "error_codes",
    "item": "404"
}
```

### 3. Action: `top_items`

Returns the top N most frequently observed items.

__Input Arguments:__
- `action` (string): `"top_items"`.
- `counter_id` (string): The counter to query.
- `n` (integer, optional): Number of top items to return. Default is `5`.

```json
{"action": "top_items", "counter_id": "error_codes", "n": 3}
```

### 4. Action: `reset_counter`

Resets a counter to zero.

```json
{"action": "reset_counter", "counter_id": "error_codes"}
```

## Strict Rules for the Agent

1. __Approximate Counts:__ Estimated counts are approximate due to cross-talk between item vectors. Use them for relative comparison ("X was more frequent than Y") rather than exact arithmetic.
2. __Repeat Items to Increment:__ To observe item X 5 times, include it 5 times in the `events` list: `["X","X","X","X","X"]`.
3. __Relative Comparison Is Reliable:__ Even when absolute counts are slightly off, the ranking of items by frequency is robust.
