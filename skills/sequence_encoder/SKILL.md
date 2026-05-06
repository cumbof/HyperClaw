# Tool: HDC Sequence Encoder (`sequence_encoder`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Sequence Encoder. Use this tool whenever you need to remember the **order** of steps, events, or symbols — such as a multi-step plan, a protocol, a workflow, a DNA strand, or any other ordered list. This tool mathematically encodes temporal or positional order so you can later verify that a step follows another or retrieve the next expected step.

## How It Works

You pass an ordered list of item labels. The tool binds each adjacent pair `(A → B)` using a permutation-based operation so that direction is preserved. Multiple sequences can be stored and queried independently using a `sequence_id`.

## Schema & Actions

This tool accepts a JSON payload with a required `action` parameter.

### 1. Action: `encode_sequence`

Use this to store a new ordered sequence.

__Input Arguments:__
- `action` (string): Must be `"encode_sequence"`.
- `sequence_id` (string): A unique name for the sequence (e.g., `"surgery_protocol"`).
- `items` (array of strings): The ordered list of items. Must contain at least 2 items.

__Example Payload:__

```json
{
    "action": "encode_sequence",
    "sequence_id": "surgery_protocol",
    "items": ["Anesthesia", "Incision", "Procedure", "Suture", "Recovery"]
}
```

### 2. Action: `query_next`

Use this to ask "What item comes immediately after X in sequence Y?"

__Input Arguments:__
- `action` (string): Must be `"query_next"`.
- `sequence_id` (string): The sequence to search.
- `item` (string): The item whose successor you want to find.

__Example Payload:__

```json
{
    "action": "query_next",
    "sequence_id": "surgery_protocol",
    "item": "Incision"
}
```

### 3. Action: `verify_order`

Use this to confirm whether item B directly follows item A in a stored sequence. Returns `"confirmed"` or `"denied"`.

__Input Arguments:__
- `action` (string): Must be `"verify_order"`.
- `sequence_id` (string): The sequence to check.
- `item_a` (string): The preceding item.
- `item_b` (string): The item you believe follows `item_a`.

__Example Payload:__

```json
{
    "action": "verify_order",
    "sequence_id": "surgery_protocol",
    "item_a": "Incision",
    "item_b": "Procedure"
}
```

## Strict Rules for the Agent

1. __Exact Strings:__ Item labels must match exactly what was used in `encode_sequence` (case-sensitive).
2. __Direct Successors Only:__ `query_next` returns the **immediate** next item, not an arbitrary later item.
3. __Multiple Sequences:__ Use different `sequence_id` values to track independent protocols or workflows.
4. __Additive Encoding:__ Encoding the same sequence multiple times reinforces those transitions in the memory, making them more robust.
