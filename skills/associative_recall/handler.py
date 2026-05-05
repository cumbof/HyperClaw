import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "associative_recall_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance threshold below which a recall is considered reliable.
DISTANCE_THRESHOLD = 0.75


class AssociativeRecall:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps store_id -> raw integer accumulator of (key * value) bindings
        self.stores = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and association stores from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.stores = state["stores"]

    def save_state(self):
        """Saves the persistent HDC space and association stores to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "stores": self.stores}, f)

    def store_association(self, store_id: str, pairs: list) -> dict:
        """
        Stores (key, value) associations by binding each key vector to its
        value vector and bundling the result into the association store.
        To recall value V given key K:  Store * V_K  ≈  V_V.
        """
        if not store_id or not pairs:
            return {"status": "failed", "message": "Missing 'store_id' or 'pairs'."}

        if store_id not in self.stores:
            self.stores[store_id] = np.zeros(VECTOR_SIZE, dtype=int)

        added = 0
        for pair in pairs:
            key = pair.get("key")
            value = pair.get("value")
            if not key or not value:
                continue

            self._get_or_create_vector(str(key))
            self._get_or_create_vector(str(value))

            v_key = copy.deepcopy(self.space.get(names=[str(key)])[0])
            v_value = self.space.get(names=[str(value)])[0]

            # BIND: V_key * V_value
            v_key.bind(v_value)

            # BUNDLE: accumulate into store
            self.stores[store_id] += v_key.vector
            added += 1

        self.save_state()
        return {
            "status": "success",
            "message": f"{added} association(s) stored in '{store_id}'.",
        }

    def recall(self, store_id: str, key: str) -> dict:
        """
        Recalls the value associated with the given key from the store.
        Unbinds the key from the association store and finds the closest
        concept in the codebook.
        """
        if store_id not in self.stores:
            return {"status": "failed", "message": f"Store '{store_id}' not found."}

        key_str = str(key)
        self._get_or_create_vector(key_str)

        raw_acc = self.stores[store_id]
        store_vec = Vector(
            name="__store__",
            size=VECTOR_SIZE,
            vector=np.where(raw_acc > 0, 1, -1),
        )

        # UNBIND: Store * V_key  ≈  V_value
        v_key = self.space.get(names=[key_str])[0]
        store_vec.bind(v_key)

        distances, _ = self.space.find_all(store_vec)

        # Exclude internal helpers and the key itself
        candidates = sorted(
            [(name, dist) for name, dist in distances.items()
             if not name.startswith("__") and name != key_str],
            key=lambda x: x[1],
        )

        if not candidates:
            return {"status": "failed", "message": f"No associations found for key '{key}'."}

        best_name, best_dist = candidates[0]

        if best_dist > DISTANCE_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": f"No confident association found for key '{key}'.",
            }

        return {
            "status": "success",
            "key": key_str,
            "value": best_name,
            "confidence": round((1.0 - best_dist) * 100, 2),
        }

    def forget_association(self, store_id: str, pairs: list) -> dict:
        """
        Removes (key, value) associations from the store via exact vector
        subtraction.  The key and value strings must match exactly what was
        used in store_association.
        """
        if store_id not in self.stores:
            return {"status": "failed", "message": f"Store '{store_id}' not found."}

        removed = 0
        for pair in pairs:
            key = pair.get("key")
            value = pair.get("value")
            if not key or not value:
                continue

            key_str = str(key)
            value_str = str(value)

            if key_str not in self.space.memory() or value_str not in self.space.memory():
                continue

            v_key = copy.deepcopy(self.space.get(names=[key_str])[0])
            v_value = self.space.get(names=[value_str])[0]
            v_key.bind(v_value)

            self.stores[store_id] -= v_key.vector
            removed += 1

        self.save_state()
        return {
            "status": "success",
            "message": f"{removed} association(s) removed from '{store_id}'.",
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
    memory = AssociativeRecall()

    if action == "store_association":
        store_id = payload.get("store_id")
        pairs = payload.get("pairs", [])
        if not store_id or not pairs:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'pairs'."}))
            sys.exit(1)
        result = memory.store_association(store_id, pairs)
        print(json.dumps(result))

    elif action == "recall":
        store_id = payload.get("store_id")
        key = payload.get("key")
        if not store_id or not key:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'key'."}))
            sys.exit(1)
        result = memory.recall(store_id, key)
        print(json.dumps(result))

    elif action == "forget_association":
        store_id = payload.get("store_id")
        pairs = payload.get("pairs", [])
        if not store_id or not pairs:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'pairs'."}))
            sys.exit(1)
        result = memory.forget_association(store_id, pairs)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
