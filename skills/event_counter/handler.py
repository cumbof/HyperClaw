import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "event_counter_state.pkl"
VECTOR_SIZE = 10000


class EventCounter:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps counter_id -> np.ndarray  (raw integer accumulator)
        # Each item contributes its vector multiplied by its count.
        self.counters = {}
        # Maps counter_id -> total number of events observed
        self.totals = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and counter data from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.counters = state["counters"]
                self.totals = state["totals"]

    def save_state(self):
        """Saves the persistent HDC space and counter data to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump(
                {
                    "space": self.space,
                    "counters": self.counters,
                    "totals": self.totals,
                },
                f,
            )

    def observe(self, counter_id: str, events: list) -> dict:
        """
        Records one or more event observations (each event may appear multiple
        times in the list).  The handler increments the counter by adding the
        event's hypervector once per occurrence.

        Internally, the counter accumulator encodes:
          acc = Σ  count(item_i) * V_item_i
        
        The dot product (acc · V_item) / VECTOR_SIZE provides an approximate
        count for item_i.
        """
        if not counter_id or not events:
            return {"status": "failed", "message": "Missing 'counter_id' or 'events'."}

        if counter_id not in self.counters:
            self.counters[counter_id] = np.zeros(VECTOR_SIZE, dtype=int)
            self.totals[counter_id] = 0

        for event in events:
            name = str(event)
            self._get_or_create_vector(name)
            v = self.space.get(names=[name])[0]
            self.counters[counter_id] += v.vector
            self.totals[counter_id] += 1

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"{len(events)} event(s) observed in counter '{counter_id}'. "
                f"Total observations: {self.totals[counter_id]}."
            ),
        }

    def estimate_count(self, counter_id: str, item: str) -> dict:
        """
        Estimates the number of times an item was observed in a counter.
        Uses the dot-product projection:
          estimated_count ≈ (acc · V_item) / VECTOR_SIZE

        This is an approximation.  Cross-talk from other items adds noise.
        The absolute estimate is more accurate when the total count is low;
        relative comparisons between items are reliable regardless.
        """
        if counter_id not in self.counters:
            return {"status": "failed", "message": f"Counter '{counter_id}' not found."}

        name = str(item)
        self._get_or_create_vector(name)
        v = self.space.get(names=[name])[0]

        acc = self.counters[counter_id]
        dot = float(np.dot(acc.astype(float), v.vector.astype(float)))
        estimated = dot / VECTOR_SIZE

        return {
            "status": "success",
            "counter_id": counter_id,
            "item": name,
            "estimated_count": round(estimated, 2),
            "total_observations": self.totals[counter_id],
        }

    def top_items(self, counter_id: str, n: int = 5) -> dict:
        """
        Estimates the counts for all items in the codebook and returns the
        top n items by estimated frequency.
        """
        if counter_id not in self.counters:
            return {"status": "failed", "message": f"Counter '{counter_id}' not found."}

        acc = self.counters[counter_id]
        results = []

        for name in self.space.memory():
            if name.startswith("__"):
                continue
            v = self.space.get(names=[name])[0]
            dot = float(np.dot(acc.astype(float), v.vector.astype(float)))
            estimated = dot / VECTOR_SIZE
            if estimated > 0:
                results.append((name, round(estimated, 2)))

        results.sort(key=lambda x: x[1], reverse=True)
        top = results[:n]

        return {
            "status": "success",
            "counter_id": counter_id,
            "top_items": [{"item": name, "estimated_count": cnt} for name, cnt in top],
            "total_observations": self.totals[counter_id],
        }

    def reset_counter(self, counter_id: str) -> dict:
        """Resets a counter to zero."""
        if counter_id not in self.counters:
            return {"status": "failed", "message": f"Counter '{counter_id}' not found."}
        self.counters[counter_id] = np.zeros(VECTOR_SIZE, dtype=int)
        self.totals[counter_id] = 0
        self.save_state()
        return {"status": "success", "message": f"Counter '{counter_id}' reset."}


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
    counter = EventCounter()

    if action == "observe":
        counter_id = payload.get("counter_id")
        events = payload.get("events", [])
        if not counter_id or not events:
            print(json.dumps({"status": "error", "message": "Missing 'counter_id' or 'events'."}))
            sys.exit(1)
        result = counter.observe(counter_id, events)
        print(json.dumps(result))

    elif action == "estimate_count":
        counter_id = payload.get("counter_id")
        item = payload.get("item")
        if not counter_id or not item:
            print(json.dumps({"status": "error", "message": "Missing 'counter_id' or 'item'."}))
            sys.exit(1)
        result = counter.estimate_count(counter_id, item)
        print(json.dumps(result))

    elif action == "top_items":
        counter_id = payload.get("counter_id")
        n = int(payload.get("n", 5))
        if not counter_id:
            print(json.dumps({"status": "error", "message": "Missing 'counter_id'."}))
            sys.exit(1)
        result = counter.top_items(counter_id, n)
        print(json.dumps(result))

    elif action == "reset_counter":
        counter_id = payload.get("counter_id")
        if not counter_id:
            print(json.dumps({"status": "error", "message": "Missing 'counter_id'."}))
            sys.exit(1)
        result = counter.reset_counter(counter_id)
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
