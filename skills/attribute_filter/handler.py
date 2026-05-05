import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "attribute_filter_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance below which an entity is considered to match a filter.
MATCH_THRESHOLD = 0.75


class AttributeFilter:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps store_id -> {
        #   entity_name: np.ndarray  # entity vector = bundle(V_entity + Σ bind(V_attr, V_val))
        # }
        self.stores = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and entity stores from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.stores = state["stores"]

    def save_state(self):
        """Saves the persistent HDC space and entity stores to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "stores": self.stores}, f)

    def _encode_entity(self, entity_name: str, attributes: dict) -> np.ndarray:
        """
        Encodes an entity as the bundle of its own vector and all
        attribute-value bind vectors:
          V_entity + Σ (V_attribute * V_value)
        """
        acc = np.zeros(VECTOR_SIZE, dtype=int)
        acc += self.space.get(names=[entity_name])[0].vector
        for attr, val in attributes.items():
            v_attr = copy.deepcopy(self.space.get(names=[str(attr)])[0])
            v_val = self.space.get(names=[str(val)])[0]
            v_attr.bind(v_val)
            acc += v_attr.vector
        return acc

    def store_entity(self, store_id: str, entity_name: str, attributes: dict) -> dict:
        """
        Stores an entity with its attribute-value pairs.  The entity is
        encoded as a single hypervector and saved in the named store.
        """
        if not store_id or not entity_name:
            return {"status": "failed", "message": "Missing 'store_id' or 'entity_name'."}

        if store_id not in self.stores:
            self.stores[store_id] = {}

        # Register all concepts in the codebook
        self._get_or_create_vector(entity_name)
        for attr, val in attributes.items():
            self._get_or_create_vector(str(attr))
            self._get_or_create_vector(str(val))

        self.stores[store_id][entity_name] = self._encode_entity(entity_name, attributes)

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"Entity '{entity_name}' stored in '{store_id}' "
                f"with {len(attributes)} attribute(s)."
            ),
        }

    def filter_entities(self, store_id: str, filters: dict) -> dict:
        """
        Finds all entities in the store that match the given attribute-value
        filters.  A filter is a dict like {"city": "NYC", "dept": "Eng"}.

        The query vector is the bundle of all filter bind vectors:
          Q = Σ (V_attribute * V_value)

        Each entity's vector is compared to Q via cosine distance.
        Entities with distance < MATCH_THRESHOLD are returned.
        """
        if store_id not in self.stores:
            return {"status": "failed", "message": f"Store '{store_id}' not found."}

        if not filters:
            return {"status": "failed", "message": "No filters provided."}

        # Build query vector
        query_acc = np.zeros(VECTOR_SIZE, dtype=int)
        for attr, val in filters.items():
            self._get_or_create_vector(str(attr))
            self._get_or_create_vector(str(val))
            v_attr = copy.deepcopy(self.space.get(names=[str(attr)])[0])
            v_val = self.space.get(names=[str(val)])[0]
            v_attr.bind(v_val)
            query_acc += v_attr.vector

        query_vec = Vector(
            name="__query__",
            size=VECTOR_SIZE,
            vector=np.where(query_acc >= 0, 1, -1),
        )

        matches = []
        for entity_name, entity_acc in self.stores[store_id].items():
            entity_vec = Vector(
                name=f"__e_{entity_name}__",
                size=VECTOR_SIZE,
                vector=np.where(entity_acc >= 0, 1, -1),
            )
            dist = entity_vec.dist(query_vec)
            if dist < MATCH_THRESHOLD:
                matches.append({"entity": entity_name, "score": round((1.0 - dist) * 100, 2)})

        matches.sort(key=lambda x: x["score"], reverse=True)

        return {
            "status": "success",
            "store_id": store_id,
            "filters": filters,
            "matches": matches,
            "count": len(matches),
        }

    def get_entity(self, store_id: str, entity_name: str) -> dict:
        """Returns confirmation that an entity exists in the store."""
        if store_id not in self.stores:
            return {"status": "failed", "message": f"Store '{store_id}' not found."}
        exists = entity_name in self.stores[store_id]
        return {
            "status": "success",
            "store_id": store_id,
            "entity": entity_name,
            "exists": exists,
        }

    def list_entities(self, store_id: str) -> dict:
        """Returns all entity names in a store."""
        if store_id not in self.stores:
            return {"status": "failed", "message": f"Store '{store_id}' not found."}
        entities = list(self.stores[store_id].keys())
        return {
            "status": "success",
            "store_id": store_id,
            "entities": entities,
            "count": len(entities),
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
    af = AttributeFilter()

    if action == "store_entity":
        store_id = payload.get("store_id")
        entity_name = payload.get("entity_name")
        attributes = payload.get("attributes", {})
        if not store_id or not entity_name:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'entity_name'."}))
            sys.exit(1)
        result = af.store_entity(store_id, entity_name, attributes)
        print(json.dumps(result))

    elif action == "filter_entities":
        store_id = payload.get("store_id")
        filters = payload.get("filters", {})
        if not store_id or not filters:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'filters'."}))
            sys.exit(1)
        result = af.filter_entities(store_id, filters)
        print(json.dumps(result))

    elif action == "get_entity":
        store_id = payload.get("store_id")
        entity_name = payload.get("entity_name")
        if not store_id or not entity_name:
            print(json.dumps({"status": "error", "message": "Missing 'store_id' or 'entity_name'."}))
            sys.exit(1)
        result = af.get_entity(store_id, entity_name)
        print(json.dumps(result))

    elif action == "list_entities":
        store_id = payload.get("store_id")
        if not store_id:
            print(json.dumps({"status": "error", "message": "Missing 'store_id'."}))
            sys.exit(1)
        result = af.list_entities(store_id)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
