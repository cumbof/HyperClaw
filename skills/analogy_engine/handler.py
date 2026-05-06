import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "analogy_engine_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance below which a forward/reverse lookup is considered reliable.
RETRIEVAL_THRESHOLD = 0.75
# Cosine distance below which a conformance test passes.
CONFORMANCE_THRESHOLD = 0.75


class AnalogyEngine:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps relation_name -> {"transform": np.ndarray, "pairs": [(src, tgt), ...]}
        self.relations = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and relation data from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.relations = state["relations"]

    def save_state(self):
        """Saves the persistent HDC space and relation data to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "relations": self.relations}, f)

    def train_relation(self, relation_name: str, pairs: list) -> dict:
        """
        Learns a named relation from (source, target) example pairs.
        For each pair (A, B) the handler binds V_A * V_B and accumulates
        the results into a holistic relation transform vector.
        The same pairs are also indexed for exact forward/reverse lookup.
        """
        if not relation_name or not pairs:
            return {"status": "failed", "message": "Missing 'relation_name' or 'pairs'."}

        if relation_name not in self.relations:
            self.relations[relation_name] = {
                "transform": np.zeros(VECTOR_SIZE, dtype=int),
                "pairs": [],
            }

        added = 0
        for pair in pairs:
            src = pair.get("source")
            tgt = pair.get("target")
            if not src or not tgt:
                continue

            self._get_or_create_vector(str(src))
            self._get_or_create_vector(str(tgt))

            v_src = copy.deepcopy(self.space.get(names=[str(src)])[0])
            v_tgt = self.space.get(names=[str(tgt)])[0]

            # BIND: V_source * V_target (encodes the relationship direction)
            v_src.bind(v_tgt)

            # BUNDLE into the relation transform
            self.relations[relation_name]["transform"] += v_src.vector

            # Store pair for exact lookup
            self.relations[relation_name]["pairs"].append(
                (str(src), str(tgt))
            )
            added += 1

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"{added} pair(s) added to relation '{relation_name}'. "
                f"Total pairs: {len(self.relations[relation_name]['pairs'])}."
            ),
        }

    def forward_lookup(self, relation_name: str, source: str) -> dict:
        """
        Retrieves the target associated with the given source under a named
        relation.  Uses the inverse-bind property of bipolar HDC:
        transform * V_source ≈ V_target (works best for trained sources).
        """
        if relation_name not in self.relations:
            return {"status": "failed", "message": f"Relation '{relation_name}' not found."}

        src_str = str(source)
        self._get_or_create_vector(src_str)

        transform_acc = self.relations[relation_name]["transform"]
        transform_vec = Vector(
            name="__transform__",
            size=VECTOR_SIZE,
            vector=np.where(transform_acc >= 0, 1, -1),
        )
        # UNBIND: Transform * V_source ≈ V_target
        v_src = self.space.get(names=[src_str])[0]
        transform_vec.bind(v_src)

        distances, _ = self.space.find_all(transform_vec)
        candidates = sorted(
            [(n, d) for n, d in distances.items()
             if not n.startswith("__") and n != src_str],
            key=lambda x: x[1],
        )

        if not candidates:
            return {"status": "failed", "message": "No target found."}

        best_name, best_dist = candidates[0]
        if best_dist > RETRIEVAL_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": f"No confident target found for '{source}' under '{relation_name}'.",
            }

        return {
            "status": "success",
            "source": src_str,
            "relation": relation_name,
            "target": best_name,
            "confidence": round((1.0 - best_dist) * 100, 2),
        }

    def reverse_lookup(self, relation_name: str, target: str) -> dict:
        """
        Retrieves the source that maps to the given target under a named relation.
        Uses the same unbind operation since bind is its own inverse in bipolar HDC.
        """
        if relation_name not in self.relations:
            return {"status": "failed", "message": f"Relation '{relation_name}' not found."}

        tgt_str = str(target)
        self._get_or_create_vector(tgt_str)

        transform_acc = self.relations[relation_name]["transform"]
        transform_vec = Vector(
            name="__transform__",
            size=VECTOR_SIZE,
            vector=np.where(transform_acc >= 0, 1, -1),
        )
        # UNBIND: Transform * V_target ≈ V_source
        v_tgt = self.space.get(names=[tgt_str])[0]
        transform_vec.bind(v_tgt)

        distances, _ = self.space.find_all(transform_vec)
        candidates = sorted(
            [(n, d) for n, d in distances.items()
             if not n.startswith("__") and n != tgt_str],
            key=lambda x: x[1],
        )

        if not candidates:
            return {"status": "failed", "message": "No source found."}

        best_name, best_dist = candidates[0]
        if best_dist > RETRIEVAL_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": f"No confident source found for '{target}' under '{relation_name}'.",
            }

        return {
            "status": "success",
            "target": tgt_str,
            "relation": relation_name,
            "source": best_name,
            "confidence": round((1.0 - best_dist) * 100, 2),
        }

    def test_conformance(self, relation_name: str, source: str, target: str) -> dict:
        """
        Tests whether a (source, target) pair conforms to a named relation.
        A pair whose bind V_source * V_target is similar to the stored
        transform is likely to share the same relationship.  This works
        reliably for pairs that were part of the training set and provides
        a relative similarity score for novel pairs.
        """
        if relation_name not in self.relations:
            return {"status": "failed", "message": f"Relation '{relation_name}' not found."}

        src_str = str(source)
        tgt_str = str(target)
        self._get_or_create_vector(src_str)
        self._get_or_create_vector(tgt_str)

        # Bind the candidate pair
        v_src = copy.deepcopy(self.space.get(names=[src_str])[0])
        v_tgt = self.space.get(names=[tgt_str])[0]
        v_src.bind(v_tgt)

        # Compare to the relation transform
        transform_acc = self.relations[relation_name]["transform"]
        transform_vec = Vector(
            name="__transform__",
            size=VECTOR_SIZE,
            vector=np.where(transform_acc >= 0, 1, -1),
        )
        dist = transform_vec.dist(v_src)
        conforms = dist < CONFORMANCE_THRESHOLD

        return {
            "status": "success",
            "source": src_str,
            "target": tgt_str,
            "relation": relation_name,
            "conforms": bool(conforms),
            "similarity": round((1.0 - dist) * 100, 2),
        }

    def list_relations(self) -> dict:
        """Returns a summary of all trained relations."""
        summary = {
            name: {"pair_count": len(data["pairs"])}
            for name, data in self.relations.items()
        }
        return {"status": "success", "relations": summary}


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
    engine = AnalogyEngine()

    if action == "train_relation":
        relation_name = payload.get("relation_name")
        pairs = payload.get("pairs", [])
        result = engine.train_relation(relation_name, pairs)
        print(json.dumps(result))

    elif action == "forward_lookup":
        relation_name = payload.get("relation_name")
        source = payload.get("source")
        if not relation_name or not source:
            print(json.dumps({"status": "error", "message": "Missing parameters."}))
            sys.exit(1)
        result = engine.forward_lookup(relation_name, source)
        print(json.dumps(result))

    elif action == "reverse_lookup":
        relation_name = payload.get("relation_name")
        target = payload.get("target")
        if not relation_name or not target:
            print(json.dumps({"status": "error", "message": "Missing parameters."}))
            sys.exit(1)
        result = engine.reverse_lookup(relation_name, target)
        print(json.dumps(result))

    elif action == "test_conformance":
        relation_name = payload.get("relation_name")
        source = payload.get("source")
        target = payload.get("target")
        if not relation_name or not source or not target:
            print(json.dumps({"status": "error", "message": "Missing parameters."}))
            sys.exit(1)
        result = engine.test_conformance(relation_name, source, target)
        print(json.dumps(result))

    elif action == "list_relations":
        result = engine.list_relations()
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
