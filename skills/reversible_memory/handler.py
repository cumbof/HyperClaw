import json
import sys
import os
import pickle
import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "reversible_persona_state.pkl"
VECTOR_SIZE = 10000

class ReversiblePersonaCore:
    def __init__(self):
        # The Codebook (maps concepts to base hypervectors)
        self.space = Space(size=VECTOR_SIZE)
        # Dictionary mapping persona_id -> Integer Accumulator (NumPy array)
        self.accumulators = {}
        self.load_state()

    def _get_or_create_vector(self, concept_name: str) -> Vector:
        """Retrieves a concept from the Codebook, or creates it if it doesn't exist."""
        if concept_name not in self.space.memory():
            # Create a new random bipolar vector (-1, 1) for the concept
            vec = Vector(name=concept_name, size=VECTOR_SIZE)
            self.space.insert(vec)
        return self.space.get(names=[concept_name])[0]

    def load_state(self):
        """Loads the persistent HDC space and persona accumulators from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'rb') as f:
                state = pickle.load(f)
                self.space = state['space']
                self.accumulators = state['accumulators']

    def save_state(self):
        """Saves the persistent HDC space and persona accumulators to disk."""
        with open(STATE_FILE, 'wb') as f:
            pickle.dump({'space': self.space, 'accumulators': self.accumulators}, f)

    def _bind_fact(self, subject: str, predicate: str, obj: str) -> np.ndarray:
        """Helper function to mathematically bind a S-P-O fact into a single vector."""
        v_sub = self._get_or_create_vector(subject)
        v_pred = self._get_or_create_vector(predicate)
        v_obj = self._get_or_create_vector(obj)

        # BIND: Element-wise multiplication for bipolar vectors
        return v_sub.vector * v_pred.vector * v_obj.vector

    def memorize(self, persona_id: str, facts: list) -> dict:
        """
        Binds facts and ADDS them to the raw integer accumulator for perfect memory retention.
        """
        if persona_id not in self.accumulators:
            # Initialize an empty integer array (zeros) for the new persona
            self.accumulators[persona_id] = np.zeros(VECTOR_SIZE, dtype=int)

        added_count = 0
        for fact in facts:
            sub = fact.get("subject")
            pred = fact.get("predicate")
            obj = fact.get("object")

            if not all([sub, pred, obj]):
                continue

            # Get the exact bound fact vector
            bound_array = self._bind_fact(sub, pred, obj)

            # MEMORIZE (Addition without thresholding)
            self.accumulators[persona_id] += bound_array
            added_count += 1

        self.save_state()
        return {"status": "success", "message": f"{added_count} facts mathematically added to persona '{persona_id}'."}

    def forget(self, persona_id: str, facts: list) -> dict:
        """
        Binds the EXACT same facts and SUBTRACTS them from the integer accumulator for perfect unlearning.
        """
        if persona_id not in self.accumulators:
            return {"status": "failed", "message": f"Persona '{persona_id}' does not exist in memory."}

        removed_count = 0
        for fact in facts:
            sub = fact.get("subject")
            pred = fact.get("predicate")
            obj = fact.get("object")

            if not all([sub, pred, obj]):
                continue

            # To successfully unlearn, the vectors retrieved must be EXACTLY the same
            try:
                bound_array = self._bind_fact(sub, pred, obj)
            except Exception as e:
                # If a concept doesn't exist, we never learned it in the first place
                continue

            # UNLEARN (Exact subtraction)
            self.accumulators[persona_id] -= bound_array
            removed_count += 1

        self.save_state()
        return {"status": "success", "message": f"{removed_count} facts mathematically subtracted and forgotten."}
        
    def get_thresholded_persona(self, persona_id: str) -> Vector:
        """
        Helper method (for future querying tools): 
        Dynamically applies the threshold ONLY when the LLM needs to interact with the state.
        """
        if persona_id not in self.accumulators:
            return None
            
        raw_accumulator = self.accumulators[persona_id]
        # Apply majority-rule threshold to convert back to standard bipolar (-1, 1)
        thresholded_array = np.where(raw_accumulator >= 0, 1, -1)
        return Vector(name=f"persona_{persona_id}", size=VECTOR_SIZE, vector=thresholded_array)

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
    persona_id = payload.get("persona_id")
    facts = payload.get("facts", [])
    
    if not persona_id:
        print(json.dumps({"status": "error", "message": "Missing 'persona_id'."}))
        sys.exit(1)

    core = ReversiblePersonaCore()

    if action == "memorize":
        result = core.memorize(persona_id, facts)
        print(json.dumps(result))
        
    elif action == "forget":
        result = core.forget(persona_id, facts)
        print(json.dumps(result))
        
    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))

if __name__ == "__main__":
    main()