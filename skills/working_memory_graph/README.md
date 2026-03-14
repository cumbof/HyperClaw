# Semantic Working Memory
__Category:__ Graph Reasoning

## Overview

The `working_memory_graph` skill provides an AI agent with a persistent, constant-size, and queryable memory space. It allows an LLM to extract semantic facts from long texts and encode them into a single Hyperdimensional Computing (HDC) state vector.

### The LLM Problem

Standard Retrieval-Augmented Generation (RAG) pipelines rely on Vector Databases that chop documents into arbitrary 500-word chunks. This destroys complex, multi-hop semantic relationships (e.g., if _Fact A_ is in chunk 1 and _Fact C_ is in chunk 10, the LLM loses the connecting _Fact B_). Furthermmore, LLMs have finite context windows and "forget" earlier parts of a conversation.

### The HDC Solution

Instead of chunking text, the agent extracts structured triples: `(Subject, Predicate, Object)`. Using _hdlib_, this skill mathematically binds these three concepts into a single "Fact Vector", and then bundles multiple Fact Vectors into a single "Memory Vector". The agent can then deterministically query this Memory Vector later without needing the original text in its context window.

## How the Math Works

1. __Encoding a Fact (Binding):__ To store the fact "Aspirin treats Headache", the handler retrieves or generates random hypervectors for each concept and binds them using element-wise multiplication.

2. __Building the Graph (Bundling):__ To store multiple facts, the handler adds them together element-wise (with thresholding).

3. __Querying (Unbinding):__ When the agent asks "What does Aspirin treat?", the handler creates a query pointer and unbinds it from the memory graph.

## The Reality Check: Iterative Cleanup

__HDC capacity is not infinite.__ If you bundle 10,000 facts into a 10,000-dimensional vector, the signal is destroyed by crosstalk noise.

When the handler unbinds from the vector memory graph, the resulting vector is an approximation of the answer, not the exact vector. Therefore, the handler relies on an iterative cleanup memory. It takes the noisy result, compares it against the entire local codebook using cosine similarity, and returns the exact string label of the closest match back to the LLM.

## Example Interaction

1. Agent Stores Facts (Action: `store`)

```json
{
    "action": "store",
    "triples": [
        {"subject": "Aspirine", "predicate": "treats", "object": "Headache"},
        {"subject": "Aspirine", "predicate": "causes", "object": "Nausea"}
    ]
}
```

_Handler Response:_ `{"status": "success", "message": "2 triples successfully bundled into memory graph"}`

2. Agent Queries the Graph (Action: `query`)

```json
{
    "action": "query",
    "subject": "Aspirin",
    "predicate": "causes",
    "object": "?"
}
```

_Handler Response:_ `{"status": "success", "result": "Nausea", "confidence": 0.82}`