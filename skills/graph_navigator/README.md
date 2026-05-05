# Graph Navigator
__Category:__ Graph Reasoning

## Overview

The `graph_navigator` skill lets an AI agent store arbitrary graphs and query neighborhood relationships in constant time using Hyperdimensional Computing. Each node's neighbor set is compressed into a single adjacency hypervector; neighbor queries are cosine-distance comparisons against the full codebook.

### The LLM Problem

Agents that reason about graphs (org charts, dependency graphs, knowledge graphs) typically inject the full edge list into the context window. For non-trivial graphs (>100 nodes), this consumes most of the context budget and is discarded when the window fills. There is no native mechanism to ask "who are the 2-hop neighbors of node X?" without exhausting the context.

### The HDC Solution

HDC naturally represents set membership via superposition. Each node's adjacency bundle is the sum of its neighbor vectors. Querying neighbors is equivalent to finding the vectors closest to the adjacency bundle — no edge list traversal needed. Multiple named graphs are maintained independently.

## How the Math Works

1. __Edge Addition:__ For each edge `(u → v)`, add `V_v` to `u`'s integer adjacency accumulator: `adj[u] += V_v`.

2. __Neighbor Query:__ Threshold `adj[u]` to a bipolar vector. Run `find_all` against the codebook. Concepts with cosine distance below the threshold are reported as neighbors.

3. __Undirected Graphs:__ Symmetrically add `V_u` to `adj[v]` as well.

## Example Interaction

1. Build a Graph (Action: `add_edges`)

```json
{
    "action": "add_edges",
    "graph_id": "roadmap",
    "edges": [
        {"from": "A", "to": "B"},
        {"from": "A", "to": "C"},
        {"from": "B", "to": "D"},
        {"from": "C", "to": "D"}
    ]
}
```

_Handler Response:_ `{"status": "success", "message": "4 edge(s) added to graph 'roadmap' (undirected)."}`

2. Get Neighbors (Action: `get_neighbors`)

```json
{"action": "get_neighbors", "graph_id": "roadmap", "node": "A"}
```

_Handler Response:_ `{"status": "success", "node": "A", "neighbors": [{"node": "B", "distance": 0.499}, {"node": "C", "distance": 0.505}]}`

3. Connectivity Check (Action: `are_neighbors`)

```json
{"action": "are_neighbors", "graph_id": "roadmap", "node_a": "A", "node_b": "D"}
```

_Handler Response:_ `{"status": "success", "node_a": "A", "node_b": "D", "are_neighbors": false}`
