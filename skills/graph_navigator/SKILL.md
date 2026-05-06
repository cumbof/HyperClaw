# Tool: HDC Graph Navigator (`graph_navigator`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Graph Navigator. Use this tool to store and query **graph structures** — sets of nodes connected by edges. This is ideal for knowledge graphs, dependency graphs, social network snippets, workflow DAGs, road networks, or any domain where you need to ask "What is connected to X?" without linear scans.

## How It Works

Each node's neighborhood is stored as a bundled hypervector (the superposition of all neighbor vectors). Querying neighbors is a constant-time cosine-distance comparison between the node's adjacency bundle and all known concept vectors. Both directed and undirected graphs are supported.

## Schema & Actions

### 1. Action: `add_edges`

Adds edges to a named graph.

__Input Arguments:__
- `action` (string): `"add_edges"`.
- `graph_id` (string): The name of the graph.
- `edges` (array of objects): Each object must have `"from"` and `"to"` string fields.
- `directed` (boolean, optional): If `true`, edges are one-way. Default is `false` (undirected).

__Example Payload:__

```json
{
    "action": "add_edges",
    "graph_id": "org_chart",
    "directed": true,
    "edges": [
        {"from": "CEO",   "to": "CTO"},
        {"from": "CEO",   "to": "CFO"},
        {"from": "CTO",   "to": "DevLead"},
        {"from": "CTO",   "to": "InfraLead"}
    ]
}
```

### 2. Action: `get_neighbors`

Returns the direct neighbors of a node.

```json
{
    "action": "get_neighbors",
    "graph_id": "org_chart",
    "node": "CTO"
}
```

### 3. Action: `are_neighbors`

Checks whether two nodes are directly connected.

```json
{
    "action": "are_neighbors",
    "graph_id": "org_chart",
    "node_a": "CEO",
    "node_b": "DevLead"
}
```

### 4. Action: `list_nodes`

Returns all nodes that have at least one outgoing edge.

```json
{"action": "list_nodes", "graph_id": "org_chart"}
```

## Strict Rules for the Agent

1. __Graph ID Scoping:__ Use distinct `graph_id` values for independent graphs. Nodes in different graphs are independent even if they share the same name.
2. __Approximate Neighbors:__ Neighbor detection is based on cosine distance. When a node has many neighbors (>50), some may fall below the detection threshold due to bundle saturation.
3. __Directed vs. Undirected:__ The `directed` flag is set when the graph is first created. Adding edges with a different `directed` value later will not change the original setting for consistency.
4. __Additive:__ Calling `add_edges` multiple times is additive. You cannot remove individual edges (use `set_membership_oracle` if you need reversible set operations).
