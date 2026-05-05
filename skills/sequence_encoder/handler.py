import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "sequence_encoder_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance threshold: below this, the match is considered confident.
# Members of the sequence sit at ~0.5; random vectors sit at ~1.0.
DISTANCE_THRESHOLD = 0.75


class SequenceEncoder:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps sequence_id -> raw integer accumulator (bigram bundle)
        self.sequences = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and sequence accumulators from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.sequences = state["sequences"]

    def save_state(self):
        """Saves the persistent HDC space and sequence accumulators to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "sequences": self.sequences}, f)

    def encode_sequence(self, sequence_id: str, items: list) -> dict:
        """
        Encodes an ordered sequence using permutation-based bigram binding.
        For every adjacent pair (A, B) in the sequence the handler binds
        permute(V_A) * V_B and accumulates the result into a holistic
        sequence vector.  The permute operator acts as a positional shift so
        the direction of the pair is preserved.
        """
        if len(items) < 2:
            return {"status": "failed", "message": "Sequence must have at least 2 items."}

        if sequence_id not in self.sequences:
            self.sequences[sequence_id] = np.zeros(VECTOR_SIZE, dtype=int)

        for item in items:
            self._get_or_create_vector(item)

        bigrams_added = 0
        for i in range(len(items) - 1):
            v_a = copy.deepcopy(self.space.get(names=[items[i]])[0])
            v_b = self.space.get(names=[items[i + 1]])[0]

            # BIND: permute(A) * B  (encodes "A is immediately followed by B")
            v_a.permute(1)
            v_a.bind(v_b)

            # BUNDLE: raw integer accumulation preserves reversibility
            self.sequences[sequence_id] += v_a.vector
            bigrams_added += 1

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"Sequence '{sequence_id}' encoded with {bigrams_added} bigrams "
                f"({len(items)} items)."
            ),
        }

    def query_next(self, sequence_id: str, item: str) -> dict:
        """
        Retrieves what item directly follows the given item in the stored
        sequence.  The query pointer is permute(V_item), which is unbound from
        the sequence memory via element-wise multiplication.  The cleanup memory
        then finds the closest concept in the codebook.
        """
        if sequence_id not in self.sequences:
            return {"status": "failed", "message": f"Sequence '{sequence_id}' not found."}

        if item not in self.space.memory():
            return {"status": "failed", "message": f"Item '{item}' not in codebook."}

        raw_acc = self.sequences[sequence_id]
        # Apply majority-rule threshold to recover a bipolar representation.
        # Ties (zero) are broken to +1 arbitrarily; they contribute negligible signal.
        thresholded = np.where(raw_acc >= 0, 1, -1)
        v_mem = Vector(name="__seq_mem__", size=VECTOR_SIZE, vector=thresholded)

        # UNBIND: Memory * permute(item)  ≈  V_next
        v_query = copy.deepcopy(self.space.get(names=[item])[0])
        v_query.permute(1)
        v_mem.bind(v_query)

        distances, _ = self.space.find_all(v_mem)

        # Filter out internal helpers and the query item itself
        candidates = sorted(
            [(name, dist) for name, dist in distances.items()
             if not name.startswith("__") and name != item],
            key=lambda x: x[1],
        )

        if not candidates:
            return {"status": "failed", "message": "No successor found."}

        best_name, best_dist = candidates[0]

        if best_dist > DISTANCE_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": f"No confident successor found after '{item}'.",
            }

        return {
            "status": "success",
            "result": best_name,
            "confidence": round((1.0 - best_dist) * 100, 2),
        }

    def verify_order(self, sequence_id: str, item_a: str, item_b: str) -> dict:
        """
        Checks whether item_b directly follows item_a in the named sequence.
        """
        if sequence_id not in self.sequences:
            return {"status": "failed", "message": f"Sequence '{sequence_id}' not found."}

        result = self.query_next(sequence_id, item_a)
        if result["status"] != "success":
            return {"status": "unverified", "message": result["message"]}

        if result["result"] == item_b:
            return {
                "status": "confirmed",
                "message": (
                    f"'{item_b}' directly follows '{item_a}' "
                    f"in sequence '{sequence_id}'."
                ),
                "confidence": result["confidence"],
            }

        return {
            "status": "denied",
            "message": (
                f"'{item_b}' does not directly follow '{item_a}'. "
                f"Expected successor: '{result['result']}'."
            ),
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
    encoder = SequenceEncoder()

    if action == "encode_sequence":
        seq_id = payload.get("sequence_id")
        items = payload.get("items", [])
        if not seq_id or not items:
            print(json.dumps({"status": "error", "message": "Missing 'sequence_id' or 'items'."}))
            sys.exit(1)
        result = encoder.encode_sequence(seq_id, items)
        print(json.dumps(result))

    elif action == "query_next":
        seq_id = payload.get("sequence_id")
        item = payload.get("item")
        if not seq_id or not item:
            print(json.dumps({"status": "error", "message": "Missing 'sequence_id' or 'item'."}))
            sys.exit(1)
        result = encoder.query_next(seq_id, item)
        print(json.dumps(result))

    elif action == "verify_order":
        seq_id = payload.get("sequence_id")
        item_a = payload.get("item_a")
        item_b = payload.get("item_b")
        if not seq_id or not item_a or not item_b:
            print(json.dumps({"status": "error", "message": "Missing required parameters."}))
            sys.exit(1)
        result = encoder.verify_order(seq_id, item_a, item_b)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
