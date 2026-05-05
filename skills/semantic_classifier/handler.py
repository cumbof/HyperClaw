import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "semantic_classifier_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance threshold for confident classification.
# A query closer than this to a class prototype is considered a match.
CONFIDENCE_THRESHOLD = 0.75


class SemanticClassifier:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps class_label -> raw integer accumulator (prototype bundle)
        self.prototypes = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and class prototypes from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.prototypes = state["prototypes"]

    def save_state(self):
        """Saves the persistent HDC space and class prototypes to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "prototypes": self.prototypes}, f)

    def train(self, class_label: str, features: list) -> dict:
        """
        Adds a training example to the prototype for the given class.
        Each feature is encoded as a random hypervector; all feature vectors
        for the example are bundled into a sample vector that is then added
        to the class prototype accumulator.
        """
        if not class_label or not features:
            return {"status": "failed", "message": "Missing 'class_label' or 'features'."}

        if class_label not in self.prototypes:
            self.prototypes[class_label] = np.zeros(VECTOR_SIZE, dtype=int)

        for feature in features:
            self._get_or_create_vector(str(feature))

        # Build a sample vector by bundling all feature vectors
        sample_acc = np.zeros(VECTOR_SIZE, dtype=int)
        for feature in features:
            v = self.space.get(names=[str(feature)])[0]
            sample_acc += v.vector

        # Add the sample to the class prototype accumulator
        self.prototypes[class_label] += sample_acc

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"Training example with {len(features)} features "
                f"added to class '{class_label}'."
            ),
        }

    def classify(self, features: list) -> dict:
        """
        Encodes the query features into a sample vector and computes the cosine
        distance to every class prototype.  Returns the closest class label.
        """
        if not self.prototypes:
            return {"status": "failed", "message": "No classes have been trained yet."}

        if not features:
            return {"status": "failed", "message": "No features provided for classification."}

        # Build query sample vector
        query_acc = np.zeros(VECTOR_SIZE, dtype=int)
        for feature in features:
            name = str(feature)
            if name not in self.space.memory():
                # Unknown feature — create a new random vector for it
                self.space.bulk_insert([name])
            v = self.space.get(names=[name])[0]
            query_acc += v.vector

        query_vec = Vector(
            name="__query__",
            size=VECTOR_SIZE,
            vector=np.where(query_acc > 0, 1, -1),
        )

        # Compare query to every class prototype
        results = []
        for class_label, proto_acc in self.prototypes.items():
            proto_vec = Vector(
                name=f"__proto_{class_label}__",
                size=VECTOR_SIZE,
                vector=np.where(proto_acc > 0, 1, -1),
            )
            dist = query_vec.dist(proto_vec)
            results.append((class_label, dist))

        results.sort(key=lambda x: x[1])
        best_label, best_dist = results[0]

        if best_dist > CONFIDENCE_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": "Query does not match any trained class with sufficient confidence.",
                "best_guess": best_label,
                "confidence": round((1.0 - best_dist) * 100, 2),
            }

        all_scores = [
            {"class": label, "confidence": round((1.0 - dist) * 100, 2)}
            for label, dist in results
        ]

        return {
            "status": "success",
            "predicted_class": best_label,
            "confidence": round((1.0 - best_dist) * 100, 2),
            "all_scores": all_scores,
        }

    def list_classes(self) -> dict:
        """Returns the list of trained class labels."""
        return {
            "status": "success",
            "classes": list(self.prototypes.keys()),
            "count": len(self.prototypes),
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
    classifier = SemanticClassifier()

    if action == "train":
        class_label = payload.get("class_label")
        features = payload.get("features", [])
        result = classifier.train(class_label, features)
        print(json.dumps(result))

    elif action == "classify":
        features = payload.get("features", [])
        if not features:
            print(json.dumps({"status": "error", "message": "Missing 'features'."}))
            sys.exit(1)
        result = classifier.classify(features)
        print(json.dumps(result))

    elif action == "list_classes":
        result = classifier.list_classes()
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
