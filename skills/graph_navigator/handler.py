import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "graph_navigator_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance below which a node is considered a neighbor.
NEIGHBOR_THRESHOLD = 0.75


class GraphNavigator:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps graph_id -> {
        #   "adjacency": {node_name: np.ndarray},  # each node's neighbor bundle
        #   "directed": bool
        # }
        self.graphs = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and graph data from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.graphs = state["graphs"]

    def save_state(self):
        """Saves the persistent HDC space and graph data to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "graphs": self.graphs}, f)

    def add_edges(self, graph_id: str, edges: list, directed: bool = False) -> dict:
        """
        Adds edges to a named graph.  For each edge (u → v) the handler adds
        V_v to the adjacency bundle of u.  For undirected graphs it also adds
        V_u to the adjacency bundle of v.

        Each node's adjacency bundle is an integer accumulator of its neighbors'
        vectors, enabling cosine-distance-based neighbor lookup.
        """
        if not graph_id or not edges:
            return {"status": "failed", "message": "Missing 'graph_id' or 'edges'."}

        if graph_id not in self.graphs:
            self.graphs[graph_id] = {
                "adjacency": {},
                "directed": directed,
            }

        graph = self.graphs[graph_id]
        added = 0

        for edge in edges:
            u = str(edge.get("from", ""))
            v = str(edge.get("to", ""))
            if not u or not v:
                continue

            self._get_or_create_vector(u)
            self._get_or_create_vector(v)

            # Add v to u's adjacency bundle
            if u not in graph["adjacency"]:
                graph["adjacency"][u] = np.zeros(VECTOR_SIZE, dtype=int)
            graph["adjacency"][u] += self.space.get(names=[v])[0].vector

            # For undirected graphs, also add u to v's bundle
            if not directed:
                if v not in graph["adjacency"]:
                    graph["adjacency"][v] = np.zeros(VECTOR_SIZE, dtype=int)
                graph["adjacency"][v] += self.space.get(names=[u])[0].vector

            added += 1

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"{added} edge(s) added to graph '{graph_id}' "
                f"({'directed' if directed else 'undirected'})."
            ),
        }

    def get_neighbors(self, graph_id: str, node: str) -> dict:
        """
        Returns the neighbors of a node by comparing the node's adjacency
        bundle against all known concept vectors in the codebook.  The k
        closest concepts below the neighbor threshold are returned.
        """
        if graph_id not in self.graphs:
            return {"status": "failed", "message": f"Graph '{graph_id}' not found."}

        node_str = str(node)
        graph = self.graphs[graph_id]

        if node_str not in graph["adjacency"]:
            return {
                "status": "success",
                "node": node_str,
                "neighbors": [],
                "message": f"Node '{node_str}' has no outgoing edges in graph '{graph_id}'.",
            }

        adj_vec = Vector(
            name="__adj__",
            size=VECTOR_SIZE,
            vector=np.where(graph["adjacency"][node_str] >= 0, 1, -1),
        )

        distances, _ = self.space.find_all(adj_vec)
        neighbors = sorted(
            [(n, d) for n, d in distances.items()
             if not n.startswith("__") and n != node_str and d < NEIGHBOR_THRESHOLD],
            key=lambda x: x[1],
        )

        return {
            "status": "success",
            "graph_id": graph_id,
            "node": node_str,
            "neighbors": [
                {"node": n, "distance": round(d, 4)}
                for n, d in neighbors
            ],
        }

    def are_neighbors(self, graph_id: str, node_a: str, node_b: str) -> dict:
        """
        Checks whether node_b is a direct neighbor of node_a in the graph.
        """
        result = self.get_neighbors(graph_id, node_a)
        if result["status"] != "success":
            return result

        neighbor_names = [n["node"] for n in result["neighbors"]]
        return {
            "status": "success",
            "node_a": node_a,
            "node_b": node_b,
            "are_neighbors": node_b in neighbor_names,
        }

    def list_nodes(self, graph_id: str) -> dict:
        """Returns all nodes that have at least one outgoing edge in the graph."""
        if graph_id not in self.graphs:
            return {"status": "failed", "message": f"Graph '{graph_id}' not found."}

        nodes = list(self.graphs[graph_id]["adjacency"].keys())
        return {
            "status": "success",
            "graph_id": graph_id,
            "nodes": nodes,
            "count": len(nodes),
            "directed": self.graphs[graph_id]["directed"],
        }


def main():
    """
    Entry point for the LLM Agent Framework.
    Expects a JSON string passed as a command-line argument.
    """
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "No JSON payload provided."}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "message": "Invalid JSON payload."}))
        sys.exit(1)

    action = payload.get("action")
    navigator = GraphNavigator()

    if action == "add_edges":
        graph_id = payload.get("graph_id")
        edges = payload.get("edges", [])
        directed = payload.get("directed", False)
        if not graph_id or not edges:
            print(json.dumps({"status": "error", "message": "Missing 'graph_id' or 'edges'."}))
            sys.exit(1)
        result = navigator.add_edges(graph_id, edges, directed)
        print(json.dumps(result))

    elif action == "get_neighbors":
        graph_id = payload.get("graph_id")
        node = payload.get("node")
        if not graph_id or not node:
            print(json.dumps({"status": "error", "message": "Missing 'graph_id' or 'node'."}))
            sys.exit(1)
        result = navigator.get_neighbors(graph_id, node)
        print(json.dumps(result))

    elif action == "are_neighbors":
        graph_id = payload.get("graph_id")
        node_a = payload.get("node_a")
        node_b = payload.get("node_b")
        if not graph_id or not node_a or not node_b:
            print(json.dumps({"status": "error", "message": "Missing required parameters."}))
            sys.exit(1)
        result = navigator.are_neighbors(graph_id, node_a, node_b)
        print(json.dumps(result))

    elif action == "list_nodes":
        graph_id = payload.get("graph_id")
        if not graph_id:
            print(json.dumps({"status": "error", "message": "Missing 'graph_id'."}))
            sys.exit(1)
        result = navigator.list_nodes(graph_id)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
