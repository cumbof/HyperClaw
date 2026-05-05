# Tool: HDC Role-Filler Memory (`role_filler_memory`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Role-Filler Memory. Use this tool to store and retrieve **structured event records** or **schemas** where information is organized into named roles (e.g., `who`, `action`, `what`, `when`, `where`). This is ideal for tracking events, transactions, medical records, meeting summaries, or any other structured data that must survive beyond your context window.

## How It Works

Each record (called a "frame") is a flat dictionary of `role → filler` pairs. The tool mathematically binds every role to its filler and bundles all pairs into a single holistic frame vector. You can later retrieve the value of any role from a frame, or find which stored frame best matches a partial description.

## Schema & Actions

This tool accepts a JSON payload with a required `action` parameter.

### 1. Action: `store_frame`

Use this to store a new structured record.

__Input Arguments:__
- `action` (string): Must be `"store_frame"`.
- `frame_id` (string): A unique name for the record (e.g., `"event_001"`).
- `bindings` (object): A flat key-value mapping of role names to filler values. Both keys and values must be strings.

__Example Payload:__

```json
{
    "action": "store_frame",
    "frame_id": "event_001",
    "bindings": {
        "who": "Alice",
        "action": "purchased",
        "what": "Laptop",
        "when": "Monday",
        "where": "Online"
    }
}
```

### 2. Action: `query_role`

Use this to retrieve the value of a specific role from a stored frame.

__Input Arguments:__
- `action` (string): Must be `"query_role"`.
- `frame_id` (string): The frame to search.
- `role` (string): The role whose filler you want to retrieve.

__Example Payload:__

```json
{
    "action": "query_role",
    "frame_id": "event_001",
    "role": "who"
}
```

### 3. Action: `find_similar_frame`

Use this to find which stored frame best matches a partial description. Provide the role-filler pairs you know, and the tool returns the closest matching frame.

__Input Arguments:__
- `action` (string): Must be `"find_similar_frame"`.
- `bindings` (object): A partial set of role-filler pairs describing the frame you are searching for.

__Example Payload:__

```json
{
    "action": "find_similar_frame",
    "bindings": {
        "who": "Alice",
        "what": "Laptop"
    }
}
```

## Strict Rules for the Agent

1. __Flat Bindings Only:__ The `bindings` object must be a flat `{string: string}` mapping. Do not nest objects.
2. __Exact Strings for Retrieval:__ The same string casing used in `store_frame` must be used in `query_role` for the role name.
3. __Unique Frame IDs:__ Using the same `frame_id` twice will add to the existing frame, not replace it. Use distinct IDs for distinct records.
4. __Trust Confidence Scores:__ A `confidence` below 25 means the retrieval is unreliable. Treat `"low_confidence"` responses as "fact not in memory."
