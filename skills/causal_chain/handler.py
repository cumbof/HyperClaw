import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "causal_chain_state.pkl"
VECTOR_SIZE = 10000
RETRIEVAL_THRESHOLD = 0.75
# Maximum BFS depth for multi-hop causal tracing
MAX_HOP_DEPTH = 10


class CausalChain:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps store_id -> {
        #   "forward_acc": np.ndarray,   # bundle of bind(cause, effect)
        #   "backward_acc": np.ndarray,  # bundle of bind(effect, cause)
        # }
        self.stores = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and causal stores from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.stores = state["stores"]

    def save_state(self):
        """Saves the persistent HDC space and causal stores to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "stores": self.stores}, f)

    def add_links(self, store_id: str, links: list) -> dict:
        """
        Adds causal links to the store.  Each link is a (cause, effect) pair.
        The handler builds two bidirectional association memories:
          - forward_acc  = Σ bind(V_cause, V_effect)   → given cause, find effect
          - backward_acc = Σ bind(V_effect, V_cause)   → given effect, find cause
        """
        if not store_id or not links:
            return {"status": "failed", "message": "Missing 'store_id' or 'links'."}

        if store_id not in self.stores:
            self.stores[store_id] = {
                "forward_acc": np.zeros(VECTOR_SIZE, dtype=int),
                "backward_acc": np.zeros(VECTOR_SIZE, dtype=int),
            }

        added = 0
        for link in links:
            cause = str(link.get("cause", ""))
            effect = str(link.get("effect", ""))
            if not cause or not effect:
                continue

            self._get_or_create_vector(cause)
            self._get_or_create_vector(effect)

            # Forward: bind(cause, effect)
            v_cause_fwd = copy.deepcopy(self.space.get(names=[cause])[0])
            v_effect = self.space.get(names=[effect])[0]
            v_cause_fwd.bind(v_effect)
            self.stores[store_id]["forward_acc"] += v_cause_fwd.vector

            # Backward: bind(effect, cause)
            v_effect_bwd = copy.deepcopy(self.space.get(names=[effect])[0])
            v_cause = self.space.get(names=[cause])[0]
            v_effect_bwd.bind(v_cause)
            self.stores[store_id]["backward_acc"] += v_effect_bwd.vector

            added += 1

        self.save_state()
        return {
            "status": "success",
            "message": f"{added} causal link(s) added to store '{store_id}'.",
        }

    def _unbind_from(self, accumulator: np.ndarray, query_name: str) -> tuple:
        """
        Unbinds a query vector from an accumulator and finds the closest concept.
        Returns (best_name, distance).
        """
        store_vec = Vector(
            name="__store__",
            size=VECTOR_SIZE,
            vector=np.where(accumulator >= 0, 1, -1),
        )
        v_query = self.space.get(names=[query_name])[0]
        store_vec.bind(v_query)

        distances, _ = self.space.find_all(store_vec)
        candidates = sorted(
            [(n, d) for n, d in distances.items()
             if not n.startswith("__") and n != query_name],
            key=lambda x: x[1],
        )
        if not candidates:
            return None, float("inf")
        return candidates[0]

    def get_effect(self, store_id: str, cause: str) -> dict:
        """Returns the most likely direct effect of the given cause."""
        if store_id not in self.stores:
            return {"status": "failed", "message": f"Store '{store_id}' not found."}

        cause_str = str(cause)
        self._get_or_create_vector(cause_str)

        best_name, best_dist = self._unbind_from(
            self.stores[store_id]["forward_acc"], cause_str
        )

        if best_name is None or best_dist > RETRIEVAL_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": f"No confident effect found for cause '{cause}'.",
            }

        return {
            "status": "success",
            "cause": cause_str,
            "effect": best_name,
            "confidence": round((1.0 - best_dist) * 100, 2),
        }

    def get_cause(self, store_id: str, effect: str) -> dict:
        """Returns the most likely direct cause of the given effect."""
        if store_id not in self.stores:
            return {"status": "failed", "message": f"Store '{store_id}' not found."}

        effect_str = str(effect)
        self._get_or_create_vector(effect_str)

        best_name, best_dist = self._unbind_from(
            self.stores[store_id]["backward_acc"], effect_str
        )

        if best_name is None or best_dist > RETRIEVAL_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": f"No confident cause found for effect '{effect}'.",
            }

        return {
            "status": "success",
            "effect": effect_str,
            "cause": best_name,
            "confidence": round((1.0 - best_dist) * 100, 2),
        }

    def trace_forward(self, store_id: str, start: str, max_hops: int = MAX_HOP_DEPTH) -> dict:
        """
        Traces a causal chain forward from the starting concept, following
        the most likely effect at each step until no confident effect is found
        or the maximum hop depth is reached.
        """
        if store_id not in self.stores:
            return {"status": "failed", "message": f"Store '{store_id}' not found."}

        chain = [str(start)]
        current = str(start)
        self._get_or_create_vector(current)
        hops = 0

        while hops < max_hops:
            best_name, best_dist = self._unbind_from(
                self.stores[store_id]["forward_acc"], current
            )
            if best_name is None or best_dist > RETRIEVAL_THRESHOLD or best_name in chain:
                break
            chain.append(best_name)
            current = best_name
            hops += 1

        return {
            "status": "success",
            "start": str(start),
            "causal_chain": chain,
            "hops": len(chain) - 1,
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
    causal = CausalChain()

    if action == "add_links":
        store_id = payload.get("store_id")
        links = payload.get("links", [])
        if not store_id or not links:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'links'."}))
            sys.exit(1)
        result = causal.add_links(store_id, links)
        print(json.dumps(result))

    elif action == "get_effect":
        store_id = payload.get("store_id")
        cause = payload.get("cause")
        if not store_id or not cause:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'cause'."}))
            sys.exit(1)
        result = causal.get_effect(store_id, cause)
        print(json.dumps(result))

    elif action == "get_cause":
        store_id = payload.get("store_id")
        effect = payload.get("effect")
        if not store_id or not effect:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'effect'."}))
            sys.exit(1)
        result = causal.get_cause(store_id, effect)
        print(json.dumps(result))

    elif action == "trace_forward":
        store_id = payload.get("store_id")
        start = payload.get("start")
        max_hops = int(payload.get("max_hops", MAX_HOP_DEPTH))
        if not store_id or not start:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'start'."}))
            sys.exit(1)
        result = causal.trace_forward(store_id, start, max_hops)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
