"""
State-guard skill handler.

Uses a raw integer accumulator for the rulebook bundle (no per-step thresholding)
so that retrieval is reliable even with many rules that share the same action vector.
"""
import json
import sys
import os
import pickle
import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "state_guard_memory.pkl"
VECTOR_SIZE = 10000
# Retrieval threshold: cosine distance > this value means the transition is not in the rulebook.
DISTANCE_THRESHOLD = 0.55

class DeterministicStateGuard:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Raw integer accumulator for the rulebook (same pattern as other skills)
        self.rulebook_acc = None
        self.known_states = set()  # Track which vectors are states (vs actions)
        self.load_state()

    def _get_or_create_vector(self, concept_name: str) -> Vector:
        """Retrieves or creates a bipolar vector in the codebook."""
        if concept_name not in self.space.memory():
            vec = Vector(name=concept_name, size=VECTOR_SIZE)
            self.space.insert(vec)
        return self.space.get(names=[concept_name])[0]

    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'rb') as f:
                state_data = pickle.load(f)
                self.space = state_data['space']
                self.rulebook_acc = state_data['rulebook']
                self.known_states = state_data['known_states']

    def save_state(self):
        with open(STATE_FILE, 'wb') as f:
            pickle.dump({
                'space': self.space,
                'rulebook': self.rulebook_acc,
                'known_states': self.known_states
            }, f)

    def define_rules(self, transitions: list) -> dict:
        """
        Compiles a list of transitions into the mathematical Rulebook vector.
        Uses a raw integer accumulator to preserve information across bundles.
        """
        added_count = 0
        for rule in transitions:
            curr = rule.get("current_state")
            act = rule.get("action")
            nxt = rule.get("next_state")

            if not all([curr, act, nxt]):
                continue

            # Track valid states to filter out actions during cleanup
            self.known_states.add(curr)
            self.known_states.add(nxt)

            v_curr = self._get_or_create_vector(curr)
            v_act = self._get_or_create_vector(act)
            v_nxt = self._get_or_create_vector(nxt)

            # BIND: Current * Action * Next
            v_rule = v_curr.vector * v_act.vector * v_nxt.vector

            # BUNDLE using raw integer accumulation (no per-step thresholding)
            if self.rulebook_acc is None:
                self.rulebook_acc = v_rule.copy()
            else:
                self.rulebook_acc = self.rulebook_acc + v_rule

            added_count += 1

        self.save_state()
        return {"status": "success", "message": f"Rulebook compiled with {added_count} valid transitions."}

    def verify_move(self, current_state: str, proposed_action: str) -> dict:
        """
        Mathematically verifies if an action is legal from the current state.
        """
        if self.rulebook_acc is None:
            return {"status": "error", "message": "No rules have been defined yet."}

        # If the LLM hallucinates a state or action that has NEVER been defined
        if current_state not in self.space.memory() or proposed_action not in self.space.memory():
            return {
                "status": "blocked",
                "reason": "HALLUCINATION",
                "message": f"'{current_state}' or '{proposed_action}' does not exist in the defined rulebook."
            }

        v_curr = self.space.get(names=[current_state])[0]
        v_act = self.space.get(names=[proposed_action])[0]

        # Create query pointer: Current * Action
        v_pointer = v_curr.vector * v_act.vector

        # Apply majority-rule threshold to rulebook accumulator at query time
        rulebook_thresholded = np.where(self.rulebook_acc >= 0, 1, -1)

        # UNBIND from Rulebook
        noisy_next_array = rulebook_thresholded * v_pointer
        v_noisy = Vector(name="noisy_query", size=VECTOR_SIZE, vector=noisy_next_array)

        # CLEANUP: Find the closest match
        distances, _ = self.space.find_all(v_noisy)

        # Filter matches to only include known states (ignore actions or the query itself)
        valid_state_matches = sorted(
            [(n, d) for n, d in distances.items() if n in self.known_states],
            key=lambda x: x[1],
        )

        if not valid_state_matches:
            return {"status": "blocked", "reason": "ILLEGAL_MOVE", "message": "Transition resulted in pure noise."}

        match_name, match_distance = valid_state_matches[0]

        # The Reality Check Boundary
        if match_distance > DISTANCE_THRESHOLD:
            return {
                "status": "blocked",
                "reason": "ILLEGAL_MOVE",
                "message": f"Action '{proposed_action}' is not legally permitted from state '{current_state}'."
            }

        return {
            "status": "allowed",
            "next_state": match_name,
            "confidence": round((1.0 - match_distance) * 100, 2)
        }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "No JSON payload provided."}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "message": "Invalid JSON payload."}))
        sys.exit(1)

    action = payload.get("action")
    guard = DeterministicStateGuard()

    if action == "define_rules":
        transitions = payload.get("transitions", [])
        result = guard.define_rules(transitions)
        print(json.dumps(result))
        
    elif action == "verify_move":
        curr = payload.get("current_state")
        proposed = payload.get("proposed_action")
        if not curr or not proposed:
            print(json.dumps({"status": "error", "message": "Missing current_state or proposed_action."}))
            sys.exit(1)
            
        result = guard.verify_move(curr, proposed)
        print(json.dumps(result))
        
    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))

if __name__ == "__main__":
    main()