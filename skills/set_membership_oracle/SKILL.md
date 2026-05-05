# Tool: HDC Set Membership Oracle (`set_membership_oracle`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Set Membership Oracle. Use this tool whenever you need to maintain **dynamic sets** of items and answer membership queries without a linear-time scan. This tool is ideal for managing allow-lists, deny-lists, visited-node sets in graph traversal, active ingredient databases, or any collection that needs fast approximate membership testing.

## How It Works

Each set is stored as a single bundled hypervector (the superposition of all member vectors). Membership is tested by comparing the query element's hypervector against the set vector via cosine distance. Sets support both adding and reversibly removing elements.

## Schema & Actions

This tool accepts a JSON payload with a required `action` parameter.

### 1. Action: `add_elements`

Use this to add one or more items to a named set.

__Input Arguments:__
- `action` (string): Must be `"add_elements"`.
- `set_id` (string): The unique name of the set.
- `elements` (array of strings): Items to add.

__Example Payload:__

```json
{
    "action": "add_elements",
    "set_id": "approved_drugs",
    "elements": ["Aspirin", "Ibuprofen", "Paracetamol"]
}
```

### 2. Action: `remove_elements`

Use this to remove one or more items from a set. The element strings must match exactly what was used during `add_elements`.

__Input Arguments:__
- `action` (string): Must be `"remove_elements"`.
- `set_id` (string): The unique name of the set.
- `elements` (array of strings): Items to remove.

__Example Payload:__

```json
{
    "action": "remove_elements",
    "set_id": "approved_drugs",
    "elements": ["Aspirin"]
}
```

### 3. Action: `test_membership`

Use this to check whether a specific item is likely in a set.

__Input Arguments:__
- `action` (string): Must be `"test_membership"`.
- `set_id` (string): The unique name of the set.
- `element` (string): The item to test.

__Example Payload:__

```json
{
    "action": "test_membership",
    "set_id": "approved_drugs",
    "element": "Ibuprofen"
}
```

### 4. Action: `set_similarity`

Use this to measure how similar (overlapping) two sets are. Returns a similarity score from `−100` (maximally different) to `+100` (identical).

__Input Arguments:__
- `action` (string): Must be `"set_similarity"`.
- `set_id_a` (string): Name of the first set.
- `set_id_b` (string): Name of the second set.

__Example Payload:__

```json
{
    "action": "set_similarity",
    "set_id_a": "approved_drugs",
    "set_id_b": "banned_substances"
}
```

## Strict Rules for the Agent

1. __Exact Strings:__ Element strings are case-sensitive. `"Aspirin"` and `"aspirin"` are different elements.
2. __Approximate Membership:__ Because sets are compressed into a single vector, the `is_member` result is probabilistic. False positives increase as a set grows. Use sets of up to a few hundred elements for reliable results at dimension 10,000.
3. __Reversible Removal:__ You can only remove elements that were previously added with the exact same string. Removing an element that was never added will silently corrupt the set.
4. __Multiple Sets:__ Use different `set_id` values for independent collections.
