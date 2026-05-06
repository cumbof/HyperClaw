# Causal Chain
__Category:__ Causal Reasoning

## Overview

The `causal_chain` skill lets an AI agent store and navigate cause-and-effect relationships using Hyperdimensional Computing. It builds two bidirectional association memories (forward: cause→effect, backward: effect→cause) and supports single-hop lookup and multi-hop chain tracing.

### The LLM Problem

LLMs reason about causality from training data but cannot maintain a dynamic, runtime-mutable causal model. Domain-specific causal graphs (e.g., "In our manufacturing process, Vibration causes Bearing_Wear which causes Overheating which causes Shutdown") cannot be reliably tracked across context resets or updated without full context re-injection.

### The HDC Solution

Causal relationships are stored as bidirectional heteroassociative HDC memories. Each `(cause, effect)` pair is bound and bundled in both directions. Forward chains are traced by iteratively unbinding the current node until no confident next step is found.

## How the Math Works

1. __Forward Store:__ `F += V_cause ⊗ V_effect`.
2. __Backward Store:__ `B += V_effect ⊗ V_cause`.
3. __Effect Lookup:__ `F ⊗ V_cause ≈ V_effect` → cleanup memory finds the concept.
4. __Cause Lookup:__ `B ⊗ V_effect ≈ V_cause`.
5. __Chain Tracing:__ Repeatedly apply effect lookup, appending each step to the chain. Stops at low confidence or cycle detection.

## Example Interaction

1. Store Causal Links (Action: `add_links`)

```json
{
    "action": "add_links",
    "store_id": "disease",
    "links": [
        {"cause": "Infection",    "effect": "Inflammation"},
        {"cause": "Inflammation", "effect": "Fever"},
        {"cause": "Fever",        "effect": "Dehydration"}
    ]
}
```

2. Single-Hop Forward Lookup (Action: `get_effect`)

```json
{"action": "get_effect", "store_id": "disease", "cause": "Infection"}
```

_Handler Response:_ `{"status": "success", "cause": "Infection", "effect": "Inflammation", "confidence": 49.8}`

3. Backward Lookup (Action: `get_cause`)

```json
{"action": "get_cause", "store_id": "disease", "effect": "Fever"}
```

_Handler Response:_ `{"status": "success", "effect": "Fever", "cause": "Inflammation", "confidence": 50.1}`

4. Multi-Hop Chain Trace (Action: `trace_forward`)

```json
{"action": "trace_forward", "store_id": "disease", "start": "Infection"}
```

_Handler Response:_ `{"status": "success", "causal_chain": ["Infection", "Inflammation", "Fever", "Dehydration"], "hops": 3}`
