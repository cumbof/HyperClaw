# Episodic Memory
__Category:__ Temporal Reasoning

## Overview

The `episodic_memory` skill gives an AI agent a persistent memory for **multi-event episodes** — ordered sequences of events tagged with contextual metadata. It combines two complementary HDC encodings: a context bundle for tag-based retrieval, and a permutation-based sequence chain for event-order querying. Together they enable "where was I?" (context recall) and "what happened next?" (event-chain navigation).

### The LLM Problem

LLMs have no persistent episodic memory. Each session starts blank. Complex multi-step interactions (an emergency room visit, a debugging session, a legal case timeline) cannot be recalled across context window resets. Even within a single session, LLMs struggle to maintain precise temporal ordering of many events without error.

### The HDC Solution

Each episode is stored as a constant-size pair of vectors. The context vector compresses all tags into a single superposition. The sequence vector uses permutation-based bigram binding (identical to `sequence_encoder`) to encode temporal order. Both vectors are stored per episode and persist to disk.

## How the Math Works

1. __Context Bundle:__ All context tags for an episode are bundled: `C_ep = Σ V_tag_i`. At query time, the query tags are bundled and compared to each episode's context vector via cosine distance.

2. __Sequence Chain:__ For each adjacent event pair `(A, B)`, the handler computes `permute(V_A) ⊗ V_B` and accumulates into the sequence vector. To find the successor of event E, it unbinds `permute(V_E)` from the sequence vector and runs cleanup memory.

## Example Interaction

1. Record an Episode (Action: `record_episode`)

```json
{
    "action": "record_episode",
    "episode_id": "visit_2025_01_10",
    "events": ["Arrival", "Triage", "X-Ray", "Diagnosis", "Discharge"],
    "context_tags": ["hospital", "morning", "emergency"]
}
```

_Handler Response:_ `{"status": "success", "message": "Episode 'visit_2025_01_10' recorded: 5 events, 3 context tag(s)."}`

2. Recall by Context (Action: `recall_by_context`)

```json
{"action": "recall_by_context", "context_tags": ["hospital", "emergency"]}
```

_Handler Response:_ `{"status": "success", "best_match": "visit_2025_01_10", "events": ["Arrival", "Triage", "X-Ray", "Diagnosis", "Discharge"], "similarity": 50.2}`

3. Query Next Event (Action: `query_next_event`)

```json
{"action": "query_next_event", "episode_id": "visit_2025_01_10", "event": "Triage"}
```

_Handler Response:_ `{"status": "success", "event": "Triage", "next_event": "X-Ray", "confidence": 51.0}`
