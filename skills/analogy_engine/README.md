# Analogy Engine
__Category:__ Relational Reasoning

## Overview

The `analogy_engine` skill teaches an AI agent to learn and apply named semantic relationships from labeled examples. It uses Vector-Symbolic Architecture binding to encode (source, target) pairs as holographic relation transforms, enabling bidirectional lookups and conformance testing without storing raw lookup tables.

### The LLM Problem

LLMs apply analogical reasoning probabilistically from training data. At runtime, they cannot learn new domain-specific relationships (e.g., a proprietary drug-indication mapping) without context-window injection. Large lookup tables rapidly saturate context capacity and vanish when the window is truncated.

### The HDC Solution

In HDC, a semantic relation is represented as the holographic superposition of all its (source, target) bind vectors. The unbind operation reverses the binding, allowing either direction of lookup from a single stored transform vector. Multiple relations are stored independently and never interfere with each other.

## How the Math Works

1. __Binding a Pair:__ For each `(source, target)` pair, compute `V_source ⊗ V_target` (element-wise multiplication).

2. __Building the Relation Transform:__ Bundle all bind vectors: `T = Σ (V_source_i ⊗ V_target_i)`.

3. __Forward Lookup:__ Unbind the source from the transform: `T ⊗ V_source ≈ V_target` (since `V_source ⊗ V_source = 1`). Cleanup memory finds the closest concept.

4. __Reverse Lookup:__ Unbind the target from the transform: `T ⊗ V_target ≈ V_source`. This direction is often more accurate because each target appears in only one pair.

5. __Conformance Test:__ Compute `V_source ⊗ V_target` for a candidate pair and measure its cosine distance to the transform `T`. Trained pairs yield low distance.

## Example Interaction

1. Train the Relation (Action: `train_relation`)

```json
{
    "action": "train_relation",
    "relation_name": "capital_of",
    "pairs": [
        {"source": "France",  "target": "Paris"},
        {"source": "Germany", "target": "Berlin"},
        {"source": "Italy",   "target": "Rome"}
    ]
}
```

_Handler Response:_ `{"status": "success", "message": "3 pair(s) added to relation 'capital_of'. Total pairs: 3."}`

2. Reverse Lookup (Action: `reverse_lookup`)

```json
{"action": "reverse_lookup", "relation_name": "capital_of", "target": "Berlin"}
```

_Handler Response:_ `{"status": "success", "target": "Berlin", "relation": "capital_of", "source": "Germany", "confidence": 50.34}`

3. Conformance Test (Action: `test_conformance`)

```json
{"action": "test_conformance", "relation_name": "capital_of", "source": "France", "target": "Paris"}
```

_Handler Response:_ `{"status": "success", "conforms": true, "similarity": 36.4}`
