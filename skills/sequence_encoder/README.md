# Sequence Encoder
__Category:__ Sequence Learning

## Overview

The `sequence_encoder` skill gives an AI agent deterministic memory for **ordered sequences**. It uses permutation-based bigram binding from Hyperdimensional Computing to encode the direction of every adjacent pair of items in a sequence. An agent can later ask "what comes next?" or verify whether a specific ordering is correct.

### The LLM Problem

LLMs predict the most *statistically likely* next token — they do not track absolute order. When executing a multi-step procedure (surgical protocol, CI/CD pipeline, legal compliance checklist), the LLM may skip, re-order, or repeat steps. Prompt engineering with numbered lists helps superficially but is fragile under long-context pressure.

### The HDC Solution

In Vector-Symbolic Architectures, sequence order is encoded via the **permutation** operator (circular shift). For a sequence `[A, B, C, D]`, the handler builds:

```
Memory = permute(V_A) ⊗ V_B  +  permute(V_B) ⊗ V_C  +  permute(V_C) ⊗ V_D
```

Because `permute(V_X)` is orthogonal to `V_X`, every bigram is directionally encoded: `permute(V_B) ⊗ V_C ≠ permute(V_C) ⊗ V_B`. The memory holographically bundles all bigrams into a single constant-size vector.

## How the Math Works

1. __Permutation Encoding:__ Each item vector is circularly shifted by one position before binding, making the pair `(A → B)` distinguishable from `(B → A)`.

2. __Bigram Binding:__ `permute(V_A) ⊗ V_B` creates a unique vector for the ordered pair. This is stored in a raw integer accumulator to allow future reversibility.

3. __Query (Unbinding):__ To find what follows item X, the handler computes the query pointer `permute(V_X)`, applies a majority-rule threshold to recover a bipolar memory vector, and then unbinds: `result = Memory ⊗ permute(V_X)`. The cleanup memory finds the closest concept.

4. __Verification:__ `verify_order` calls `query_next` internally and compares the result to the candidate item.

## Example Interaction

1. Agent Encodes a Protocol (Action: `encode_sequence`)

```json
{
    "action": "encode_sequence",
    "sequence_id": "surgery_protocol",
    "items": ["Anesthesia", "Incision", "Procedure", "Suture", "Recovery"]
}
```

_Handler Response:_ `{"status": "success", "message": "Sequence 'surgery_protocol' encoded with 4 bigrams (5 items)."}`

2. Agent Queries the Next Step (Action: `query_next`)

```json
{
    "action": "query_next",
    "sequence_id": "surgery_protocol",
    "item": "Incision"
}
```

_Handler Response:_ `{"status": "success", "result": "Procedure", "confidence": 50.46}`

3. Agent Verifies an Ordering (Action: `verify_order`)

```json
{
    "action": "verify_order",
    "sequence_id": "surgery_protocol",
    "item_a": "Incision",
    "item_b": "Recovery"
}
```

_Handler Response:_ `{"status": "denied", "message": "'Recovery' does not directly follow 'Incision'. Expected successor: 'Procedure'."}`
