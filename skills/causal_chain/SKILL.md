# Tool: HDC Causal Chain (`causal_chain`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Causal Chain engine. Use this tool to store cause-and-effect relationships and trace causal chains forward or backward. This is ideal for root-cause analysis, failure mode reasoning, disease progression modeling, dependency impact analysis, or any domain where you need to answer "What does X lead to?" or "What caused Y?"

## How It Works

Each `(cause, effect)` link is stored as a bidirectional associative memory — one transform for forward lookup (cause → effect) and one for backward lookup (effect → cause). Multi-hop causal chains are traced by repeatedly following the most confident effect until no more links are found.

## Schema & Actions

### 1. Action: `add_links`

Stores causal links.

__Input Arguments:__
- `action` (string): `"add_links"`.
- `store_id` (string): Name of the causal store (e.g., `"disease_model"`).
- `links` (array of objects): Each object must have:
  - `cause` (string): The triggering concept.
  - `effect` (string): The resulting concept.

__Example Payload:__

```json
{
    "action": "add_links",
    "store_id": "disease_model",
    "links": [
        {"cause": "Infection",    "effect": "Inflammation"},
        {"cause": "Inflammation", "effect": "Fever"},
        {"cause": "Fever",        "effect": "Dehydration"}
    ]
}
```

### 2. Action: `get_effect`

Retrieves the most likely direct effect of a cause.

```json
{"action": "get_effect", "store_id": "disease_model", "cause": "Infection"}
```

### 3. Action: `get_cause`

Retrieves the most likely direct cause of an effect.

```json
{"action": "get_cause", "store_id": "disease_model", "effect": "Fever"}
```

### 4. Action: `trace_forward`

Traces the complete causal chain forward from a starting concept.

__Input Arguments:__
- `action` (string): `"trace_forward"`.
- `store_id` (string): The causal store to search.
- `start` (string): The starting concept.
- `max_hops` (integer, optional): Maximum chain length. Default is `10`.

```json
{"action": "trace_forward", "store_id": "disease_model", "start": "Infection", "max_hops": 5}
```

## Strict Rules for the Agent

1. __Atomic Concepts:__ Use single words or short phrases as cause/effect strings.
2. __One-to-One Links:__ The tool stores ONE primary effect per cause. If a cause has multiple effects, only the one that dominated the bundle will be reliably retrieved.
3. __Chain Termination:__ `trace_forward` stops when no confident next step is found OR when a cycle is detected.
4. __Multiple Stores:__ Use separate `store_id` values for independent causal domains.
