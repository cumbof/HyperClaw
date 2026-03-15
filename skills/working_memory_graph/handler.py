import json
import sys
import os
import pickle
import numpy as np

from hdlib import Space, Vector

# Configuration
STATE_FILE = "working_memory_state.pkl"
VECTOR_SIZE = 10000

class WorkingMemoryGraph:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        self.memory_graph = None # Will hold the bundled state vector
        self.load_state()

    def _get_or_create_vector(self, concept_name: str) -> Vector:
        """Retrieves a concept from the Codebook, or creates it if it doesn't exist."""
        if concept_name not in self.space.memory:
            # Create a new random bipolar vector for the concept
            vec = Vector(name=concept_name, size=VECTOR_SIZE)
            self.space.insert(vec)
        return self.space.get(concept_name)

    def load_state(self):
        """Loads the persistent HDC space and memory graph from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'rb') as f:
                state = pickle.load(f)
                self.space = state['space']
                self.memory_graph = state['memory_graph']

    def save_state(self):
        """Saves the persistent HDC space and memory graph to disk."""
        with open(STATE_FILE, 'wb') as f:
            pickle.dump({'space': self.space, 'memory_graph': self.memory_graph}, f)

    def store(self, triples: list) -> dict:
        """
        Binds (Subject * Predicate * Object) and bundles into the memory graph.
        """
        added_count = 0
        for triple in triples:
            sub = triple.get("subject")
            pred = triple.get("predicate")
            obj = triple.get("object")

            if not all([sub, pred, obj]):
                continue

            # Get or create orthogonal vectors for each concept
            v_sub = self._get_or_create_vector(sub)
            v_pred = self._get_or_create_vector(pred)
            v_obj = self._get_or_create_vector(obj)

            # BIND: V_fact = V_sub * V_pred * V_obj (Element-wise multiplication for bipolar)
            v_fact = Vector(
                name=f"fact_{added_count}", 
                size=VECTOR_SIZE, 
                vector=v_sub.vector * v_pred.vector * v_obj.vector
            )

            # BUNDLE: Add to the persistent memory graph
            if self.memory_graph is None:
                self.memory_graph = v_fact
            else:
                # Element-wise addition for bundling
                bundled_array = self.memory_graph.vector + v_fact.vector
                # Apply majority rule thresholding to keep it bipolar (-1, 1)
                # Note: For a true reversible memory, we would skip thresholding here, 
                # but for a standard queryable graph, thresholding controls noise.
                thresholded = np.where(bundled_array > 0, 1, -1)
                self.memory_graph = Vector(name="MemoryGraph", size=VECTOR_SIZE, vector=thresholded)
            
            added_count += 1

        self.save_state()
        return {"status": "success", "message": f"{added_count} triples successfully bundled into memory graph."}

    def query(self, subject: str, predicate: str, obj: str) -> dict:
        """
        Unbinds the known concepts from the memory graph and uses Cleanup Memory to find the unknown.
        """
        if self.memory_graph is None:
            return {"status": "failed", "message": "Memory graph is empty."}

        # Identify the unknown (marked as '?')
        knowns = []
        if subject != "?": knowns.append(subject)
        if predicate != "?": knowns.append(predicate)
        if obj != "?": knowns.append(obj)

        if len(knowns) != 2:
            return {"status": "failed", "message": "Query must contain exactly two knowns and one '?'"}

        # Get the vectors for the known concepts
        try:
            v_known1 = self.space.get(knowns[0])
            v_known2 = self.space.get(knowns[1])
        except Exception:
            return {"status": "failed", "message": "One or more queried concepts do not exist in the working memory."}

        # Bind the knowns to create the query pointer
        v_query_pointer = v_known1.vector * v_known2.vector

        # UNBIND: In bipolar HDC, unbinding is the same as binding (multiplication)
        noisy_result_array = self.memory_graph.vector * v_query_pointer
        noisy_vector = Vector(name="noisy_query", size=VECTOR_SIZE, vector=noisy_result_array)

        # CLEANUP MEMORY: Find the closest match in the Codebook using Cosine Similarity
        # hdlib's Space.find() handles distance calculations
        matches = self.space.find(noisy_vector)
        
        if not matches:
            return {"status": "failed", "message": "No strong matches found in cleanup memory."}

        # matches is typically a list of tuples: (Concept_Name, Distance)
        # Sort to get the closest match (lowest distance / highest similarity)
        best_match = matches[0] 
        best_name = best_match[0]
        # Calculate similarity score (1 - cosine distance)
        similarity = 1.0 - best_match[1] 

        # Filter out the concepts we used to query
        filtered_matches = [m for m in matches if m[0] not in knowns and m[0] != "noisy_query"]
        
        if not filtered_matches:
            return {"status": "failed", "message": "No logical answer found in memory."}

        best_result = filtered_matches[0]
        
        return {
            "status": "success", 
            "result": best_result[0], 
            "confidence": round((1.0 - best_result[1]) * 100, 2) # Convert distance to % confidence
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
    memory = WorkingMemoryGraph()

    if action == "store":
        triples = payload.get("triples", [])
        result = memory.store(triples)
        print(json.dumps(result))
        
    elif action == "query":
        subject = payload.get("subject", "?")
        predicate = payload.get("predicate", "?")
        obj = payload.get("object", "?")
        result = memory.query(subject, predicate, obj)
        print(json.dumps(result))
        
    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))

if __name__ == "__main__":
    main()