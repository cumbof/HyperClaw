import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "role_filler_memory_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance below which a filler retrieval is considered confident.
RETRIEVAL_THRESHOLD = 0.75
# Cosine distance below which a frame is considered a good match during search.
SIMILARITY_THRESHOLD = 0.75


class RoleFillerMemory:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps frame_id -> raw integer accumulator of role-filler bindings
        self.frames = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and frame accumulators from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.frames = state["frames"]

    def save_state(self):
        """Saves the persistent HDC space and frame accumulators to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "frames": self.frames}, f)

    def store_frame(self, frame_id: str, bindings: dict) -> dict:
        """
        Stores a structured frame by binding each role to its filler and then
        bundling all role-filler pairs into a single frame accumulator.
        A frame is a flat dict mapping role names (strings) to filler values
        (strings), e.g. {"who": "Alice", "action": "bought", "what": "Book"}.
        """
        if not frame_id or not bindings:
            return {"status": "failed", "message": "Missing 'frame_id' or 'bindings'."}

        if frame_id not in self.frames:
            self.frames[frame_id] = np.zeros(VECTOR_SIZE, dtype=int)

        bound_count = 0
        for role, filler in bindings.items():
            role_str = str(role)
            filler_str = str(filler)
            self._get_or_create_vector(role_str)
            self._get_or_create_vector(filler_str)

            v_role = copy.deepcopy(self.space.get(names=[role_str])[0])
            v_filler = self.space.get(names=[filler_str])[0]

            # BIND: V_role * V_filler
            v_role.bind(v_filler)

            # BUNDLE: accumulate into frame
            self.frames[frame_id] += v_role.vector
            bound_count += 1

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"Frame '{frame_id}' stored with {bound_count} role-filler binding(s)."
            ),
        }

    def query_role(self, frame_id: str, role: str) -> dict:
        """
        Retrieves the filler for a given role from a stored frame.
        Unbinding: result = Frame * V_role  ≈  V_filler
        """
        if frame_id not in self.frames:
            return {"status": "failed", "message": f"Frame '{frame_id}' not found."}

        role_str = str(role)
        if role_str not in self.space.memory():
            return {"status": "failed", "message": f"Role '{role_str}' not in codebook."}

        raw_acc = self.frames[frame_id]
        frame_vec = Vector(
            name="__frame__",
            size=VECTOR_SIZE,
            vector=np.where(raw_acc >= 0, 1, -1),
        )

        # UNBIND: Frame * V_role  ≈  V_filler
        v_role = self.space.get(names=[role_str])[0]
        frame_vec.bind(v_role)

        distances, _ = self.space.find_all(frame_vec)

        # Exclude internal helpers and the role itself
        candidates = sorted(
            [(name, dist) for name, dist in distances.items()
             if not name.startswith("__") and name != role_str],
            key=lambda x: x[1],
        )

        if not candidates:
            return {"status": "failed", "message": "No filler found for this role."}

        best_name, best_dist = candidates[0]

        if best_dist > RETRIEVAL_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": f"No confident filler found for role '{role}' in frame '{frame_id}'.",
            }

        return {
            "status": "success",
            "frame_id": frame_id,
            "role": role_str,
            "filler": best_name,
            "confidence": round((1.0 - best_dist) * 100, 2),
        }

    def find_similar_frame(self, bindings: dict) -> dict:
        """
        Given a partial set of role-filler bindings, finds the stored frame
        whose vector is most similar.  Useful for pattern-matching events or
        identifying which stored record best matches a partial description.
        """
        if not self.frames:
            return {"status": "failed", "message": "No frames stored yet."}

        if not bindings:
            return {"status": "failed", "message": "No bindings provided for search."}

        # Encode the query as a partial frame vector
        query_acc = np.zeros(VECTOR_SIZE, dtype=int)
        for role, filler in bindings.items():
            role_str = str(role)
            filler_str = str(filler)
            self._get_or_create_vector(role_str)
            self._get_or_create_vector(filler_str)

            v_role = copy.deepcopy(self.space.get(names=[role_str])[0])
            v_filler = self.space.get(names=[filler_str])[0]
            v_role.bind(v_filler)
            query_acc += v_role.vector

        query_vec = Vector(
            name="__query_frame__",
            size=VECTOR_SIZE,
            vector=np.where(query_acc >= 0, 1, -1),
        )

        results = []
        for frame_id, raw_acc in self.frames.items():
            frame_vec = Vector(
                name=f"__f_{frame_id}__",
                size=VECTOR_SIZE,
                vector=np.where(raw_acc >= 0, 1, -1),
            )
            dist = query_vec.dist(frame_vec)
            results.append((frame_id, dist))

        results.sort(key=lambda x: x[1])
        best_id, best_dist = results[0]

        if best_dist > SIMILARITY_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": "No stored frame closely matches the provided bindings.",
                "best_guess": best_id,
                "similarity": round((1.0 - best_dist) * 100, 2),
            }

        all_scores = [
            {"frame_id": fid, "similarity": round((1.0 - d) * 100, 2)}
            for fid, d in results
        ]

        return {
            "status": "success",
            "best_match": best_id,
            "similarity": round((1.0 - best_dist) * 100, 2),
            "all_scores": all_scores,
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
    memory = RoleFillerMemory()

    if action == "store_frame":
        frame_id = payload.get("frame_id")
        bindings = payload.get("bindings", {})
        if not frame_id or not bindings:
            print(json.dumps({"status": "error", "message": "Missing 'frame_id' or 'bindings'."}))
            sys.exit(1)
        result = memory.store_frame(frame_id, bindings)
        print(json.dumps(result))

    elif action == "query_role":
        frame_id = payload.get("frame_id")
        role = payload.get("role")
        if not frame_id or not role:
            print(json.dumps({"status": "error", "message": "Missing 'frame_id' or 'role'."}))
            sys.exit(1)
        result = memory.query_role(frame_id, role)
        print(json.dumps(result))

    elif action == "find_similar_frame":
        bindings = payload.get("bindings", {})
        if not bindings:
            print(json.dumps({"status": "error", "message": "Missing 'bindings'."}))
            sys.exit(1)
        result = memory.find_similar_frame(bindings)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
