import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "multicontext_switcher_state.pkl"
VECTOR_SIZE = 10000
RETRIEVAL_THRESHOLD = 0.75


class MulticontextSwitcher:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps context_id -> {
        #   "acc": np.ndarray,    # integer accumulator of bundled facts
        #   "active": bool,       # whether this is the currently active context
        #   "fact_count": int,
        #   "tags": [str, ...]    # metadata tags for context search
        # }
        self.contexts = {}
        self.active_context_id = None
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and context data from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.contexts = state["contexts"]
                self.active_context_id = state["active_context_id"]

    def save_state(self):
        """Saves the persistent HDC space and context data to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump(
                {
                    "space": self.space,
                    "contexts": self.contexts,
                    "active_context_id": self.active_context_id,
                },
                f,
            )

    def create_context(self, context_id: str, tags: list = None) -> dict:
        """
        Creates a new named context (like opening a new scratch-pad).
        Does not make it the active context automatically.
        """
        if not context_id:
            return {"status": "failed", "message": "Missing 'context_id'."}

        if context_id in self.contexts:
            return {
                "status": "success",
                "message": f"Context '{context_id}' already exists.",
                "context_id": context_id,
            }

        self.contexts[context_id] = {
            "acc": np.zeros(VECTOR_SIZE, dtype=int),
            "active": False,
            "fact_count": 0,
            "tags": list(tags or []),
        }

        self.save_state()
        return {
            "status": "success",
            "message": f"Context '{context_id}' created.",
            "context_id": context_id,
        }

    def switch_to(self, context_id: str) -> dict:
        """
        Switches the active context.  Any subsequent `add_facts` calls will
        go into this context.
        """
        if context_id not in self.contexts:
            # Auto-create if not yet existing
            self.create_context(context_id)

        # Mark old context inactive
        if self.active_context_id and self.active_context_id in self.contexts:
            self.contexts[self.active_context_id]["active"] = False

        self.contexts[context_id]["active"] = True
        self.active_context_id = context_id

        self.save_state()
        return {
            "status": "success",
            "message": f"Switched to context '{context_id}'.",
            "active_context": context_id,
        }

    def add_facts(
        self, facts: list, context_id: str = None
    ) -> dict:
        """
        Adds a list of fact strings to a context (defaults to the active context).
        Each fact string is tokenized by whitespace and bundled into the
        context accumulator.
        """
        target_id = context_id or self.active_context_id
        if not target_id:
            return {
                "status": "failed",
                "message": "No active context. Call 'switch_to' first or provide 'context_id'.",
            }

        if target_id not in self.contexts:
            self.create_context(target_id)

        added = 0
        for fact in (facts or []):
            parts = str(fact).split()
            for part in parts:
                self._get_or_create_vector(part)
            # Bundle the fact vector (tokenized)
            fact_acc = np.zeros(VECTOR_SIZE, dtype=int)
            for part in parts:
                fact_acc += self.space.get(names=[part])[0].vector
            self.contexts[target_id]["acc"] += fact_acc
            self.contexts[target_id]["fact_count"] += 1
            added += 1

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"{added} fact(s) added to context '{target_id}'. "
                f"Total facts: {self.contexts[target_id]['fact_count']}."
            ),
            "context_id": target_id,
        }

    def query_context(self, query_terms: list, context_id: str = None) -> dict:
        """
        Checks how relevant a set of query terms are to a context's content.
        Returns a similarity score between the query vector and the context vector.
        Use this to determine whether a topic is encoded in the current context.
        """
        target_id = context_id or self.active_context_id
        if not target_id or target_id not in self.contexts:
            return {"status": "failed", "message": "Context not found."}

        if self.contexts[target_id]["fact_count"] == 0:
            return {"status": "failed", "message": f"Context '{target_id}' is empty."}

        if not query_terms:
            return {"status": "failed", "message": "No query_terms provided."}

        # Build query vector
        q_acc = np.zeros(VECTOR_SIZE, dtype=int)
        for term in query_terms:
            self._get_or_create_vector(str(term))
            q_acc += self.space.get(names=[str(term)])[0].vector

        q_vec = Vector(
            name="__query__",
            size=VECTOR_SIZE,
            vector=np.where(q_acc >= 0, 1, -1),
        )

        ctx_vec = Vector(
            name="__ctx__",
            size=VECTOR_SIZE,
            vector=np.where(self.contexts[target_id]["acc"] >= 0, 1, -1),
        )

        dist = ctx_vec.dist(q_vec)
        return {
            "status": "success",
            "context_id": target_id,
            "query_terms": query_terms,
            "relevance": round((1.0 - dist) * 100, 2),
            "distance": round(dist, 4),
        }

    def find_relevant_context(self, query_terms: list) -> dict:
        """
        Searches all contexts and returns the one most relevant to the
        provided query terms.
        """
        if not self.contexts:
            return {"status": "failed", "message": "No contexts exist yet."}

        if not query_terms:
            return {"status": "failed", "message": "No query_terms provided."}

        q_acc = np.zeros(VECTOR_SIZE, dtype=int)
        for term in query_terms:
            self._get_or_create_vector(str(term))
            q_acc += self.space.get(names=[str(term)])[0].vector

        q_vec = Vector(
            name="__frc_query__",
            size=VECTOR_SIZE,
            vector=np.where(q_acc >= 0, 1, -1),
        )

        results = []
        for ctx_id, ctx in self.contexts.items():
            if ctx["fact_count"] == 0:
                continue
            ctx_vec = Vector(
                name=f"__ctx_{ctx_id}__",
                size=VECTOR_SIZE,
                vector=np.where(ctx["acc"] >= 0, 1, -1),
            )
            dist = ctx_vec.dist(q_vec)
            results.append((ctx_id, dist))

        if not results:
            return {"status": "failed", "message": "All contexts are empty."}

        results.sort(key=lambda x: x[1])
        best_id, best_dist = results[0]

        all_scores = [
            {"context_id": cid, "relevance": round((1.0 - d) * 100, 2)}
            for cid, d in results
        ]

        return {
            "status": "success",
            "best_context": best_id,
            "relevance": round((1.0 - best_dist) * 100, 2),
            "all_scores": all_scores,
        }

    def list_contexts(self) -> dict:
        """Returns a summary of all contexts."""
        summary = {
            cid: {
                "fact_count": ctx["fact_count"],
                "active": ctx["active"],
                "tags": ctx["tags"],
            }
            for cid, ctx in self.contexts.items()
        }
        return {
            "status": "success",
            "contexts": summary,
            "active_context": self.active_context_id,
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
    switcher = MulticontextSwitcher()

    if action == "create_context":
        context_id = payload.get("context_id")
        tags = payload.get("tags", [])
        result = switcher.create_context(context_id, tags)
        print(json.dumps(result))

    elif action == "switch_to":
        context_id = payload.get("context_id")
        if not context_id:
            print(json.dumps({"status": "error", "message": "Missing 'context_id'."}))
            sys.exit(1)
        result = switcher.switch_to(context_id)
        print(json.dumps(result))

    elif action == "add_facts":
        facts = payload.get("facts", [])
        context_id = payload.get("context_id")
        if not facts:
            print(json.dumps({"status": "error", "message": "Missing 'facts'."}))
            sys.exit(1)
        result = switcher.add_facts(facts, context_id)
        print(json.dumps(result))

    elif action == "query_context":
        query_terms = payload.get("query_terms", [])
        context_id = payload.get("context_id")
        if not query_terms:
            print(json.dumps({"status": "error", "message": "Missing 'query_terms'."}))
            sys.exit(1)
        result = switcher.query_context(query_terms, context_id)
        print(json.dumps(result))

    elif action == "find_relevant_context":
        query_terms = payload.get("query_terms", [])
        if not query_terms:
            print(json.dumps({"status": "error", "message": "Missing 'query_terms'."}))
            sys.exit(1)
        result = switcher.find_relevant_context(query_terms)
        print(json.dumps(result))

    elif action == "list_contexts":
        result = switcher.list_contexts()
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
