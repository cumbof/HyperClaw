# Associative Recall
__Category:__ Associative Memory

## Overview

The `associative_recall` skill implements a **heteroassociative memory** using Hyperdimensional Computing. It stores `(key → value)` bindings as holographic vectors and retrieves the associated value from a cue key alone. The memory is fully reversible — specific associations can be surgically removed via exact vector subtraction.

### The LLM Problem

LLMs retrieve associations from their training weights (e.g., "Paris is the capital of France") but cannot learn new arbitrary mappings at inference time without either fine-tuning or context-window stuffing. A dynamically loaded key-value map (product codes, drug-brand pairs, user preferences, API endpoint mappings) quickly consumes context tokens and disappears when the window is cleared.

### The HDC Solution

In Vector-Symbolic Architectures, a heteroassociative memory stores `(K, V)` pairs as `V_K ⊗ V_V` (element-wise multiplication / binding). Multiple pairs are superimposed (bundled) into a single holistic store vector. Recall is performed by multiplying the store by the query key vector, which "unbinds" the matching value, leaving a noisy estimate that the cleanup memory resolves to the exact stored string.

## How the Math Works

1. __Binding (Store):__ For each pair `(key, value)`, the handler computes `V_key ⊗ V_value` and adds it to the raw integer accumulator.

2. __Unbinding (Recall):__ To recall the value for key K, the handler thresholds the accumulator to a bipolar vector and computes `Store ⊗ V_K ≈ V_value`. The codebook cleanup finds the closest concept.

3. __Forgetting (Remove):__ The exact same bound pair is subtracted from the accumulator. Because the integer accumulator is never thresholded until query time, this subtraction is perfectly reversible.

## The Reality Check

Heteroassociative HDC memories are **not perfectly accurate**. Cross-talk from multiple stored pairs adds noise to the unbound result. Accuracy degrades as the number of pairs grows relative to the vector dimension. At dimension 10,000, the memory reliably handles up to a few hundred pairs. Overlapping keys or values increase interference.

## Example Interaction

1. Agent Stores Translations (Action: `store_association`)

```json
{
    "action": "store_association",
    "store_id": "en_fr",
    "pairs": [
        {"key": "cat",  "value": "chat"},
        {"key": "dog",  "value": "chien"},
        {"key": "bird", "value": "oiseau"}
    ]
}
```

_Handler Response:_ `{"status": "success", "message": "3 association(s) stored in 'en_fr'."}`

2. Agent Recalls a Translation (Action: `recall`)

```json
{"action": "recall", "store_id": "en_fr", "key": "dog"}
```

_Handler Response:_ `{"status": "success", "key": "dog", "value": "chien", "confidence": 49.7}`

3. Agent Removes an Association (Action: `forget_association`)

```json
{"action": "forget_association", "store_id": "en_fr", "pairs": [{"key": "cat", "value": "chat"}]}
```

_Handler Response:_ `{"status": "success", "message": "1 association(s) removed from 'en_fr'."}`
