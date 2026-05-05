# Multicontext Switcher
__Category:__ Cognitive Architecture

## Overview

The `multicontext_switcher` skill enables an AI agent to manage multiple independent **cognitive contexts** — named memory slots that can be populated, switched between, and queried for relevance. It solves the context pollution problem in multi-task agents, where facts from one task bleed into unrelated tasks.

### The LLM Problem

LLMs maintain a single undifferentiated context window. A multi-task agent handling simultaneous projects (Project Alpha + Project Beta + User Session C) accumulates all their facts together. This leads to cross-task contamination, incorrect answers, and eventual context overflow.

### The HDC Solution

Each named context is an independent integer accumulator. Facts are bundled into their context's vector space. Switching contexts means selecting a different accumulator — zero computational overhead. Relevance queries use cosine distance between a query vector and a context vector.

## How the Math Works

1. __Context Accumulator:__ Each context is an integer accumulator. Adding a fact tokenizes it and sums feature vectors: `ctx_acc += Σ V_token_i`.

2. __Relevance Query:__ The query terms are bundled into `V_query = Σ V_term_i`. Cosine distance between `thresh(ctx_acc)` and `V_query` measures topical alignment.

3. __Context Search:__ All context vectors are compared to the query vector. The one with lowest cosine distance is the most topically relevant.

## Example Interaction

1. Create and Populate Two Contexts

```json
{"action": "create_context", "context_id": "project_alpha", "tags": ["backend"]}
{"action": "switch_to", "context_id": "project_alpha"}
{"action": "add_facts", "facts": ["PostgreSQL database migration", "JWT authentication RS256"]}

{"action": "create_context", "context_id": "project_beta"}
{"action": "switch_to", "context_id": "project_beta"}
{"action": "add_facts", "facts": ["React frontend deployment", "CDN caching strategy"]}
```

2. Find the Right Context (Action: `find_relevant_context`)

```json
{"action": "find_relevant_context", "query_terms": ["database", "PostgreSQL"]}
```

_Handler Response:_ `{"status": "success", "best_context": "project_alpha", "relevance": 28.4, "all_scores": [...]}`

3. Query a Specific Context (Action: `query_context`)

```json
{"action": "query_context", "context_id": "project_beta", "query_terms": ["CDN", "caching"]}
```

_Handler Response:_ `{"status": "success", "relevance": 25.6, "distance": 0.744}`
