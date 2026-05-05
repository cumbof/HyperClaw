import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "set_membership_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance threshold for set membership.
# Members of a bundled set typically land at ~0.5 while non-members land at ~1.0.
MEMBERSHIP_THRESHOLD = 0.75


class SetMembershipOracle:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps set_id -> raw integer accumulator
        self.sets = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and set accumulators from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.sets = state["sets"]

    def save_state(self):
        """Saves the persistent HDC space and set accumulators to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "sets": self.sets}, f)

    def add_elements(self, set_id: str, elements: list) -> dict:
        """
        Adds elements to a named set by bundling their hypervectors into the
        set accumulator.  The raw integer accumulator is maintained so elements
        can be removed later via exact subtraction.
        """
        if not set_id or not elements:
            return {"status": "failed", "message": "Missing 'set_id' or 'elements'."}

        if set_id not in self.sets:
            self.sets[set_id] = np.zeros(VECTOR_SIZE, dtype=int)

        added = 0
        for element in elements:
            name = str(element)
            self._get_or_create_vector(name)
            v = self.space.get(names=[name])[0]
            self.sets[set_id] += v.vector
            added += 1

        self.save_state()
        return {
            "status": "success",
            "message": f"{added} element(s) added to set '{set_id}'.",
        }

    def remove_elements(self, set_id: str, elements: list) -> dict:
        """
        Removes elements from a named set via exact vector subtraction.
        The element strings must match exactly what was used in add_elements.
        """
        if set_id not in self.sets:
            return {"status": "failed", "message": f"Set '{set_id}' does not exist."}

        removed = 0
        for element in elements:
            name = str(element)
            if name not in self.space.memory():
                continue
            v = self.space.get(names=[name])[0]
            self.sets[set_id] -= v.vector
            removed += 1

        self.save_state()
        return {
            "status": "success",
            "message": f"{removed} element(s) removed from set '{set_id}'.",
        }

    def test_membership(self, set_id: str, element: str) -> dict:
        """
        Checks whether an element is likely a member of a set by computing the
        cosine distance between the element's hypervector and the (thresholded)
        set vector.
        """
        if set_id not in self.sets:
            return {"status": "failed", "message": f"Set '{set_id}' does not exist."}

        name = str(element)
        self._get_or_create_vector(name)
        v_element = self.space.get(names=[name])[0]

        raw_acc = self.sets[set_id]
        set_vec = Vector(
            name="__set__",
            size=VECTOR_SIZE,
            vector=np.where(raw_acc >= 0, 1, -1),
        )

        dist = set_vec.dist(v_element)
        is_member = dist < MEMBERSHIP_THRESHOLD

        return {
            "status": "success",
            "element": name,
            "set_id": set_id,
            "is_member": bool(is_member),
            "confidence": round((1.0 - dist) * 100, 2),
        }

    def set_similarity(self, set_id_a: str, set_id_b: str) -> dict:
        """
        Computes the cosine similarity between two set vectors.  A high
        similarity means the two sets share many common elements; a low
        similarity means they are mostly disjoint.
        """
        if set_id_a not in self.sets:
            return {"status": "failed", "message": f"Set '{set_id_a}' does not exist."}
        if set_id_b not in self.sets:
            return {"status": "failed", "message": f"Set '{set_id_b}' does not exist."}

        vec_a = Vector(
            name="__set_a__",
            size=VECTOR_SIZE,
            vector=np.where(self.sets[set_id_a] >= 0, 1, -1),
        )
        vec_b = Vector(
            name="__set_b__",
            size=VECTOR_SIZE,
            vector=np.where(self.sets[set_id_b] >= 0, 1, -1),
        )

        dist = vec_a.dist(vec_b)
        return {
            "status": "success",
            "set_a": set_id_a,
            "set_b": set_id_b,
            "similarity": round((1.0 - dist) * 100, 2),
            "distance": round(dist, 4),
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
    oracle = SetMembershipOracle()

    if action == "add_elements":
        set_id = payload.get("set_id")
        elements = payload.get("elements", [])
        result = oracle.add_elements(set_id, elements)
        print(json.dumps(result))

    elif action == "remove_elements":
        set_id = payload.get("set_id")
        elements = payload.get("elements", [])
        result = oracle.remove_elements(set_id, elements)
        print(json.dumps(result))

    elif action == "test_membership":
        set_id = payload.get("set_id")
        element = payload.get("element")
        if not set_id or not element:
            print(json.dumps({"status": "error", "message": "Missing 'set_id' or 'element'."}))
            sys.exit(1)
        result = oracle.test_membership(set_id, element)
        print(json.dumps(result))

    elif action == "set_similarity":
        set_id_a = payload.get("set_id_a")
        set_id_b = payload.get("set_id_b")
        if not set_id_a or not set_id_b:
            print(json.dumps({"status": "error", "message": "Missing 'set_id_a' or 'set_id_b'."}))
            sys.exit(1)
        result = oracle.set_similarity(set_id_a, set_id_b)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
