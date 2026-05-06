import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "concept_hierarchy_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance below which a concept is considered a member of a class.
MEMBERSHIP_THRESHOLD = 0.75


class ConceptHierarchy:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps class_name -> raw integer accumulator (bundle of self + all members)
        self.classes = {}
        # Maps concept_name -> list of direct parent class names
        self.parents = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and class data from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.classes = state["classes"]
                self.parents = state["parents"]

    def save_state(self):
        """Saves the persistent HDC space and class data to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump(
                {
                    "space": self.space,
                    "classes": self.classes,
                    "parents": self.parents,
                },
                f,
            )

    def define_class(self, class_name: str, members: list, parent_classes: list = None) -> dict:
        """
        Defines or extends a class by adding member concepts and optional
        parent class names.  The class prototype is the bundle of the class
        vector itself and all member vectors.  Parent-child relationships are
        tracked for transitive IS-A queries.
        """
        if not class_name:
            return {"status": "failed", "message": "Missing 'class_name'."}

        self._get_or_create_vector(class_name)

        if class_name not in self.classes:
            self.classes[class_name] = np.zeros(VECTOR_SIZE, dtype=int)
            # Include the class vector itself so it's a member of itself
            self.classes[class_name] += self.space.get(names=[class_name])[0].vector

        added_members = 0
        for member in (members or []):
            member_str = str(member)
            self._get_or_create_vector(member_str)
            self.classes[class_name] += self.space.get(names=[member_str])[0].vector
            # Record parent for this member
            if member_str not in self.parents:
                self.parents[member_str] = []
            if class_name not in self.parents[member_str]:
                self.parents[member_str].append(class_name)
            added_members += 1

        # Record parent classes for the class itself
        for parent in (parent_classes or []):
            parent_str = str(parent)
            self._get_or_create_vector(parent_str)
            if class_name not in self.parents:
                self.parents[class_name] = []
            if parent_str not in self.parents[class_name]:
                self.parents[class_name].append(parent_str)

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"Class '{class_name}' updated: {added_members} member(s) added, "
                f"{len(parent_classes or [])} parent class(es) linked."
            ),
        }

    def is_a(self, concept: str, class_name: str) -> dict:
        """
        Tests whether `concept` is a member of `class_name`, either directly
        or transitively through the IS-A hierarchy.

        The direct test uses cosine similarity between the concept vector and the
        class prototype.  Transitive reachability is checked by walking the
        parents dictionary.
        """
        concept_str = str(concept)
        class_str = str(class_name)

        if class_str not in self.classes:
            return {"status": "failed", "message": f"Class '{class_str}' not defined."}

        self._get_or_create_vector(concept_str)

        # Direct HDC membership test
        class_vec = Vector(
            name="__class__",
            size=VECTOR_SIZE,
            vector=np.where(self.classes[class_str] >= 0, 1, -1),
        )
        v_concept = self.space.get(names=[concept_str])[0]
        direct_dist = class_vec.dist(v_concept)
        direct_member = direct_dist < MEMBERSHIP_THRESHOLD

        # Transitive reachability via the parents dictionary (BFS)
        transitive = self._is_transitive_member(concept_str, class_str)

        return {
            "status": "success",
            "concept": concept_str,
            "class": class_str,
            "is_direct_member": bool(direct_member),
            "is_transitive_member": transitive,
            "similarity": round((1.0 - direct_dist) * 100, 2),
        }

    def _is_transitive_member(self, concept: str, target_class: str) -> bool:
        """BFS through the parents graph to check transitive IS-A membership."""
        visited = set()
        queue = [concept]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for parent in self.parents.get(current, []):
                if parent == target_class:
                    return True
                queue.append(parent)
        return False

    def get_ancestors(self, concept: str) -> dict:
        """
        Returns all ancestor classes of a concept (BFS through the IS-A graph).
        """
        concept_str = str(concept)
        if concept_str not in self.space.memory():
            return {"status": "failed", "message": f"Concept '{concept_str}' not in codebook."}

        visited = set()
        ancestors = []
        queue = list(self.parents.get(concept_str, []))
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            ancestors.append(current)
            queue.extend(self.parents.get(current, []))

        return {
            "status": "success",
            "concept": concept_str,
            "ancestors": ancestors,
        }

    def find_class(self, concept: str) -> dict:
        """
        Finds the most similar class for a given concept using cosine distance
        across all class prototypes.
        """
        if not self.classes:
            return {"status": "failed", "message": "No classes defined yet."}

        concept_str = str(concept)
        self._get_or_create_vector(concept_str)
        v_concept = self.space.get(names=[concept_str])[0]

        results = []
        for class_name, class_acc in self.classes.items():
            class_vec = Vector(
                name=f"__cls_{class_name}__",
                size=VECTOR_SIZE,
                vector=np.where(class_acc >= 0, 1, -1),
            )
            dist = class_vec.dist(v_concept)
            results.append((class_name, dist))

        results.sort(key=lambda x: x[1])
        best_name, best_dist = results[0]

        all_scores = [
            {"class": cn, "similarity": round((1.0 - d) * 100, 2)}
            for cn, d in results
        ]

        return {
            "status": "success",
            "concept": concept_str,
            "best_class": best_name,
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
    hierarchy = ConceptHierarchy()

    if action == "define_class":
        class_name = payload.get("class_name")
        members = payload.get("members", [])
        parent_classes = payload.get("parent_classes", [])
        result = hierarchy.define_class(class_name, members, parent_classes)
        print(json.dumps(result))

    elif action == "is_a":
        concept = payload.get("concept")
        class_name = payload.get("class_name")
        if not concept or not class_name:
            print(json.dumps({"status": "error", "message": "Missing 'concept' or 'class_name'."}))
            sys.exit(1)
        result = hierarchy.is_a(concept, class_name)
        print(json.dumps(result))

    elif action == "get_ancestors":
        concept = payload.get("concept")
        if not concept:
            print(json.dumps({"status": "error", "message": "Missing 'concept'."}))
            sys.exit(1)
        result = hierarchy.get_ancestors(concept)
        print(json.dumps(result))

    elif action == "find_class":
        concept = payload.get("concept")
        if not concept:
            print(json.dumps({"status": "error", "message": "Missing 'concept'."}))
            sys.exit(1)
        result = hierarchy.find_class(concept)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
