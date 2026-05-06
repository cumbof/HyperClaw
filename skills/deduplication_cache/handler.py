import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "deduplication_cache_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance below which an item is considered a duplicate (already seen).
# Items in the cache produce distance ~0.5; unseen items produce distance ~1.0.
DEFAULT_DUPLICATE_THRESHOLD = 0.75


class DeduplicationCache:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps cache_id -> {
        #   "seen_acc": np.ndarray,   # integer accumulator of seen item vectors
        #   "item_count": int,
        #   "threshold": float
        # }
        self.caches = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and cache data from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.caches = state["caches"]

    def save_state(self):
        """Saves the persistent HDC space and cache data to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "caches": self.caches}, f)

    def _encode_item(self, item: str) -> np.ndarray:
        """
        Encodes a single string item as a vector.  For multi-feature items
        pass a whitespace-joined feature string; this method splits and bundles.
        Items with multiple features are encoded as a bundle of their parts.
        """
        parts = str(item).split()
        acc = np.zeros(VECTOR_SIZE, dtype=int)
        for part in parts:
            self._get_or_create_vector(part)
            acc += self.space.get(names=[part])[0].vector
        return acc

    def check_and_add(self, cache_id: str, item: str, threshold: float = None) -> dict:
        """
        The core deduplication operation.  Checks whether the item has been
        seen before; if not, adds it to the cache.

        The check is based on the cosine distance between the item vector and
        the (thresholded) cache accumulator.  Items in the cache produce a
        lower distance (~0.5) than unseen items (~1.0).

        Returns both the duplicate verdict and whether the item was added.
        """
        if not cache_id or not item:
            return {"status": "failed", "message": "Missing 'cache_id' or 'item'."}

        if cache_id not in self.caches:
            t = threshold if threshold is not None else DEFAULT_DUPLICATE_THRESHOLD
            self.caches[cache_id] = {
                "seen_acc": np.zeros(VECTOR_SIZE, dtype=int),
                "item_count": 0,
                "threshold": t,
            }
        elif threshold is not None:
            self.caches[cache_id]["threshold"] = threshold

        cache = self.caches[cache_id]
        item_acc = self._encode_item(item)
        item_vec = Vector(
            name="__item__",
            size=VECTOR_SIZE,
            vector=np.where(item_acc >= 0, 1, -1),
        )

        is_duplicate = False
        distance = float("inf")

        if cache["item_count"] > 0:
            seen_vec = Vector(
                name="__seen__",
                size=VECTOR_SIZE,
                vector=np.where(cache["seen_acc"] >= 0, 1, -1),
            )
            distance = float(seen_vec.dist(item_vec))
            is_duplicate = distance < cache["threshold"]

        if not is_duplicate:
            cache["seen_acc"] += item_acc
            cache["item_count"] += 1

        self.save_state()
        return {
            "status": "success",
            "cache_id": cache_id,
            "item": item,
            "is_duplicate": is_duplicate,
            "was_added": not is_duplicate,
            "distance": round(distance, 4) if distance != float("inf") else None,
            "threshold": cache["threshold"],
            "cache_size": cache["item_count"],
        }

    def check_only(self, cache_id: str, item: str) -> dict:
        """
        Checks whether the item is likely a duplicate without modifying
        the cache.
        """
        if cache_id not in self.caches:
            return {
                "status": "success",
                "cache_id": cache_id,
                "item": item,
                "is_duplicate": False,
                "message": "Cache does not exist yet.",
            }

        cache = self.caches[cache_id]
        if cache["item_count"] == 0:
            return {
                "status": "success",
                "cache_id": cache_id,
                "item": item,
                "is_duplicate": False,
                "message": "Cache is empty.",
            }

        item_acc = self._encode_item(item)
        item_vec = Vector(
            name="__item__",
            size=VECTOR_SIZE,
            vector=np.where(item_acc >= 0, 1, -1),
        )
        seen_vec = Vector(
            name="__seen__",
            size=VECTOR_SIZE,
            vector=np.where(cache["seen_acc"] >= 0, 1, -1),
        )
        distance = float(seen_vec.dist(item_vec))
        is_duplicate = distance < cache["threshold"]

        return {
            "status": "success",
            "cache_id": cache_id,
            "item": item,
            "is_duplicate": is_duplicate,
            "distance": round(distance, 4),
            "threshold": cache["threshold"],
        }

    def clear_cache(self, cache_id: str) -> dict:
        """Resets a cache to empty."""
        if cache_id not in self.caches:
            return {"status": "failed", "message": f"Cache '{cache_id}' not found."}
        threshold = self.caches[cache_id]["threshold"]
        self.caches[cache_id] = {
            "seen_acc": np.zeros(VECTOR_SIZE, dtype=int),
            "item_count": 0,
            "threshold": threshold,
        }
        self.save_state()
        return {"status": "success", "message": f"Cache '{cache_id}' cleared."}

    def cache_stats(self, cache_id: str) -> dict:
        """Returns statistics for a cache."""
        if cache_id not in self.caches:
            return {"status": "failed", "message": f"Cache '{cache_id}' not found."}
        cache = self.caches[cache_id]
        return {
            "status": "success",
            "cache_id": cache_id,
            "item_count": cache["item_count"],
            "threshold": cache["threshold"],
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
    cache = DeduplicationCache()

    if action == "check_and_add":
        cache_id = payload.get("cache_id")
        item = payload.get("item")
        threshold = payload.get("threshold")
        if not cache_id or not item:
            print(json.dumps({"status": "error", "message": "Missing 'cache_id' or 'item'."}))
            sys.exit(1)
        result = cache.check_and_add(cache_id, item, threshold)
        print(json.dumps(result))

    elif action == "check_only":
        cache_id = payload.get("cache_id")
        item = payload.get("item")
        if not cache_id or not item:
            print(json.dumps({"status": "error", "message": "Missing 'cache_id' or 'item'."}))
            sys.exit(1)
        result = cache.check_only(cache_id, item)
        print(json.dumps(result))

    elif action == "clear_cache":
        cache_id = payload.get("cache_id")
        if not cache_id:
            print(json.dumps({"status": "error", "message": "Missing 'cache_id'."}))
            sys.exit(1)
        result = cache.clear_cache(cache_id)
        print(json.dumps(result))

    elif action == "cache_stats":
        cache_id = payload.get("cache_id")
        if not cache_id:
            print(json.dumps({"status": "error", "message": "Missing 'cache_id'."}))
            sys.exit(1)
        result = cache.cache_stats(cache_id)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
