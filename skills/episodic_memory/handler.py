import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "episodic_memory_state.pkl"
VECTOR_SIZE = 10000
RETRIEVAL_THRESHOLD = 0.75


class EpisodicMemory:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps episode_id -> {
        #   "context_vec": np.ndarray,   # bundled context (tags/labels for the episode)
        #   "sequence_acc": np.ndarray,  # temporally-ordered event chain (permutation bigrams)
        #   "events": [str, ...]         # ordered event list (for metadata)
        # }
        self.episodes = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and episode data from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.episodes = state["episodes"]

    def save_state(self):
        """Saves the persistent HDC space and episode data to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "episodes": self.episodes}, f)

    def record_episode(
        self, episode_id: str, events: list, context_tags: list
    ) -> dict:
        """
        Records a new episode as an ordered sequence of events with associated
        context tags (e.g., location, mood, date label).

        The episode is encoded in two complementary ways:
        1.  Context vector: all context_tags bundled together.
        2.  Sequence vector: permutation-based bigram chain over events,
            identical to the sequence_encoder approach.
        """
        if not episode_id or not events:
            return {"status": "failed", "message": "Missing 'episode_id' or 'events'."}

        if len(events) < 2:
            return {"status": "failed", "message": "An episode must have at least 2 events."}

        # Initialize accumulators
        ctx_acc = np.zeros(VECTOR_SIZE, dtype=int)
        seq_acc = np.zeros(VECTOR_SIZE, dtype=int)

        # Encode all events and context tags
        for item in events + (context_tags or []):
            self._get_or_create_vector(item)

        # 1. Context bundle
        for tag in (context_tags or []):
            ctx_acc += self.space.get(names=[tag])[0].vector

        # 2. Sequence chain: permute(A) * B for each adjacent pair
        for i in range(len(events) - 1):
            v_a = copy.deepcopy(self.space.get(names=[events[i]])[0])
            v_b = self.space.get(names=[events[i + 1]])[0]
            v_a.permute(1)
            v_a.bind(v_b)
            seq_acc += v_a.vector

        self.episodes[episode_id] = {
            "context_vec": ctx_acc,
            "sequence_acc": seq_acc,
            "events": list(events),
        }

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"Episode '{episode_id}' recorded: {len(events)} events, "
                f"{len(context_tags or [])} context tag(s)."
            ),
        }

    def recall_by_context(self, context_tags: list) -> dict:
        """
        Finds the stored episode whose context vector is most similar to the
        provided context tags.  Use this to answer "What episode happened
        when I was at the hospital last Tuesday?"
        """
        if not self.episodes:
            return {"status": "failed", "message": "No episodes stored yet."}

        if not context_tags:
            return {"status": "failed", "message": "No context_tags provided."}

        # Build query context vector
        query_acc = np.zeros(VECTOR_SIZE, dtype=int)
        for tag in context_tags:
            self._get_or_create_vector(tag)
            query_acc += self.space.get(names=[tag])[0].vector

        query_vec = Vector(
            name="__ctx_query__",
            size=VECTOR_SIZE,
            vector=np.where(query_acc >= 0, 1, -1),
        )

        results = []
        for ep_id, ep in self.episodes.items():
            ep_ctx_vec = Vector(
                name=f"__ctx_{ep_id}__",
                size=VECTOR_SIZE,
                vector=np.where(ep["context_vec"] >= 0, 1, -1),
            )
            dist = query_vec.dist(ep_ctx_vec)
            results.append((ep_id, dist))

        results.sort(key=lambda x: x[1])
        best_id, best_dist = results[0]

        if best_dist > RETRIEVAL_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": "No episode closely matches the provided context.",
                "best_guess": best_id,
                "similarity": round((1.0 - best_dist) * 100, 2),
            }

        all_scores = [
            {"episode_id": eid, "similarity": round((1.0 - d) * 100, 2)}
            for eid, d in results
        ]

        return {
            "status": "success",
            "best_match": best_id,
            "events": self.episodes[best_id]["events"],
            "similarity": round((1.0 - best_dist) * 100, 2),
            "all_scores": all_scores,
        }

    def query_next_event(self, episode_id: str, event: str) -> dict:
        """
        Retrieves the event that directly followed the given event in a stored
        episode.  Uses the same permutation-based unbinding as sequence_encoder.
        """
        if episode_id not in self.episodes:
            return {"status": "failed", "message": f"Episode '{episode_id}' not found."}

        if event not in self.space.memory():
            return {"status": "failed", "message": f"Event '{event}' not in codebook."}

        seq_acc = self.episodes[episode_id]["sequence_acc"]
        seq_vec = Vector(
            name="__seq__",
            size=VECTOR_SIZE,
            vector=np.where(seq_acc >= 0, 1, -1),
        )

        v_query = copy.deepcopy(self.space.get(names=[event])[0])
        v_query.permute(1)
        seq_vec.bind(v_query)

        distances, _ = self.space.find_all(seq_vec)
        candidates = sorted(
            [(n, d) for n, d in distances.items()
             if not n.startswith("__") and n != event],
            key=lambda x: x[1],
        )

        if not candidates:
            return {"status": "failed", "message": "No successor found."}

        best_name, best_dist = candidates[0]
        if best_dist > RETRIEVAL_THRESHOLD:
            return {
                "status": "low_confidence",
                "message": f"No confident successor found after '{event}' in episode '{episode_id}'.",
            }

        return {
            "status": "success",
            "episode_id": episode_id,
            "event": event,
            "next_event": best_name,
            "confidence": round((1.0 - best_dist) * 100, 2),
        }

    def list_episodes(self) -> dict:
        """Returns a summary of all stored episodes."""
        summary = {
            ep_id: {
                "event_count": len(ep["events"]),
                "first_event": ep["events"][0] if ep["events"] else None,
                "last_event": ep["events"][-1] if ep["events"] else None,
            }
            for ep_id, ep in self.episodes.items()
        }
        return {"status": "success", "episodes": summary, "count": len(self.episodes)}


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
    memory = EpisodicMemory()

    if action == "record_episode":
        episode_id = payload.get("episode_id")
        events = payload.get("events", [])
        context_tags = payload.get("context_tags", [])
        if not episode_id or not events:
            print(json.dumps({"status": "error", "message": "Missing 'episode_id' or 'events'."}))
            sys.exit(1)
        result = memory.record_episode(episode_id, events, context_tags)
        print(json.dumps(result))

    elif action == "recall_by_context":
        context_tags = payload.get("context_tags", [])
        if not context_tags:
            print(json.dumps({"status": "error", "message": "Missing 'context_tags'."}))
            sys.exit(1)
        result = memory.recall_by_context(context_tags)
        print(json.dumps(result))

    elif action == "query_next_event":
        episode_id = payload.get("episode_id")
        event = payload.get("event")
        if not episode_id or not event:
            print(json.dumps({"status": "error", "message": "Missing 'episode_id' or 'event'."}))
            sys.exit(1)
        result = memory.query_next_event(episode_id, event)
        print(json.dumps(result))

    elif action == "list_episodes":
        result = memory.list_episodes()
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
