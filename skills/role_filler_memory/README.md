# Role-Filler Memory
__Category:__ Structural Reasoning

## Overview

The `role_filler_memory` skill allows an AI agent to store and retrieve **structured frames** — records where information is organized into typed roles. It uses HDC role-filler binding, a technique from cognitive science (Smolensky's tensor product representations), adapted to bipolar hypervectors. Every record is stored as a single constant-size vector; retrieval is a simple cosine-distance lookup.

### The LLM Problem

LLMs have no native mechanism to store structured records beyond the context window. Saving an event like `{who: Alice, action: bought, what: Laptop, when: Monday}` either consumes context tokens in JSON form or requires an external database. When the context is flushed, the data is lost. RAG approaches retrieve whole chunks but cannot surgically extract a single field from a stored record.

### The HDC Solution

HDC role-filler binding maps each `(role, filler)` pair to a bound vector: `V_role ⊗ V_filler`. All bound pairs for a frame are bundled into a single holistic frame vector. To retrieve the filler for role R, the handler unbinds: `Frame ⊗ V_role ≈ V_filler`. The cleanup memory finds the closest concept in the codebook.

## How the Math Works

1. __Role and Filler Encoding:__ Every role name and filler value is assigned a random orthogonal hypervector in the shared codebook.

2. __Binding (Store):__ For each `(role, filler)` pair, the handler computes `V_role ⊗ V_filler` (element-wise multiplication) and adds it to the frame's raw integer accumulator.

3. __Unbinding (Query Role):__ The accumulated frame is thresholded to bipolar. The handler then multiplies by `V_role` (binding is its own inverse in bipolar HDC: `V_role ⊗ V_role = 1`), giving a noisy estimate of `V_filler`. The codebook cleanup finds the best match.

4. __Frame Similarity (Find Similar Frame):__ To locate the closest stored frame, the query is encoded as a partial frame vector using the same binding procedure. Cosine distance between the query frame vector and all stored frame vectors reveals the closest match.

## Example Interaction

1. Agent Stores an Event Record (Action: `store_frame`)

```json
{
    "action": "store_frame",
    "frame_id": "event_001",
    "bindings": {"who": "Alice", "action": "purchased", "what": "Laptop", "when": "Monday"}
}
```

_Handler Response:_ `{"status": "success", "message": "Frame 'event_001' stored with 4 role-filler binding(s)."}`

2. Agent Retrieves a Role (Action: `query_role`)

```json
{"action": "query_role", "frame_id": "event_001", "role": "who"}
```

_Handler Response:_ `{"status": "success", "frame_id": "event_001", "role": "who", "filler": "Alice", "confidence": 36.2}`

3. Agent Finds a Matching Record (Action: `find_similar_frame`)

```json
{"action": "find_similar_frame", "bindings": {"who": "Alice", "what": "Laptop"}}
```

_Handler Response:_ `{"status": "success", "best_match": "event_001", "similarity": 49.7, "all_scores": [...]}`
