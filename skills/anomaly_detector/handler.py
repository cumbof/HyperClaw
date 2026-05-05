import copy
import json
import os
import pickle
import sys

import numpy as np

from hdlib.space import Space
from hdlib.vector import Vector

# Configuration
STATE_FILE = "anomaly_detector_state.pkl"
VECTOR_SIZE = 10000
# Cosine distance below which an observation is considered "normal".
# Observations with distance >= ANOMALY_THRESHOLD are flagged as anomalies.
DEFAULT_ANOMALY_THRESHOLD = 0.6


class AnomalyDetector:
    def __init__(self):
        self.space = Space(size=VECTOR_SIZE)
        # Maps profile_id -> {
        #   "normal_acc": np.ndarray,  # integer accumulator of normal observations
        #   "sample_count": int,
        #   "threshold": float
        # }
        self.profiles = {}
        self.load_state()

    def _get_or_create_vector(self, name: str) -> Vector:
        """Retrieves a concept from the codebook, or creates it if missing."""
        if name not in self.space.memory():
            self.space.bulk_insert([name])
        return self.space.get(names=[name])[0]

    def load_state(self):
        """Loads the persistent HDC space and anomaly profiles from disk."""
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "rb") as f:
                state = pickle.load(f)
                self.space = state["space"]
                self.profiles = state["profiles"]

    def save_state(self):
        """Saves the persistent HDC space and anomaly profiles to disk."""
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"space": self.space, "profiles": self.profiles}, f)

    def _encode_observation(self, features: list) -> np.ndarray:
        """Encodes a list of feature strings into a sample accumulator vector."""
        sample_acc = np.zeros(VECTOR_SIZE, dtype=int)
        for feature in features:
            name = str(feature)
            self._get_or_create_vector(name)
            sample_acc += self.space.get(names=[name])[0].vector
        return sample_acc

    def train_normal(
        self, profile_id: str, observations: list, threshold: float = None
    ) -> dict:
        """
        Learns what is "normal" for a given profile by accumulating feature
        vectors from labeled normal observations.  Each observation is a list
        of feature strings.

        The normal prototype is the integer accumulation of all sample vectors.
        The decision boundary (threshold) can be provided explicitly or will
        default to DEFAULT_ANOMALY_THRESHOLD.
        """
        if not profile_id or not observations:
            return {"status": "failed", "message": "Missing 'profile_id' or 'observations'."}

        if profile_id not in self.profiles:
            self.profiles[profile_id] = {
                "normal_acc": np.zeros(VECTOR_SIZE, dtype=int),
                "sample_count": 0,
                "threshold": threshold if threshold is not None else DEFAULT_ANOMALY_THRESHOLD,
            }
        elif threshold is not None:
            self.profiles[profile_id]["threshold"] = threshold

        added = 0
        for obs in observations:
            if not obs:
                continue
            sample_acc = self._encode_observation(obs)
            self.profiles[profile_id]["normal_acc"] += sample_acc
            self.profiles[profile_id]["sample_count"] += 1
            added += 1

        self.save_state()
        return {
            "status": "success",
            "message": (
                f"{added} normal observation(s) added to profile '{profile_id}'. "
                f"Total samples: {self.profiles[profile_id]['sample_count']}."
            ),
        }

    def score_observation(self, profile_id: str, features: list) -> dict:
        """
        Scores a new observation against the normal prototype.  Returns a
        cosine distance score and an anomaly flag.

        A low distance (< threshold) means the observation looks normal.
        A high distance (>= threshold) means the observation is anomalous.
        """
        if profile_id not in self.profiles:
            return {"status": "failed", "message": f"Profile '{profile_id}' not found."}

        if not features:
            return {"status": "failed", "message": "No features provided."}

        profile = self.profiles[profile_id]

        if profile["sample_count"] == 0:
            return {"status": "failed", "message": "Profile has no normal training samples."}

        # Build the normal prototype vector
        normal_vec = Vector(
            name="__normal__",
            size=VECTOR_SIZE,
            vector=np.where(profile["normal_acc"] >= 0, 1, -1),
        )

        # Encode the observation
        obs_acc = self._encode_observation(features)
        obs_vec = Vector(
            name="__obs__",
            size=VECTOR_SIZE,
            vector=np.where(obs_acc >= 0, 1, -1),
        )

        dist = normal_vec.dist(obs_vec)
        threshold = profile["threshold"]
        is_anomaly = bool(dist >= threshold)

        return {
            "status": "success",
            "profile_id": profile_id,
            "anomaly_score": round(dist, 4),
            "threshold": threshold,
            "is_anomaly": is_anomaly,
            "label": "ANOMALY" if is_anomaly else "NORMAL",
        }

    def update_threshold(self, profile_id: str, threshold: float) -> dict:
        """Updates the anomaly detection threshold for a profile."""
        if profile_id not in self.profiles:
            return {"status": "failed", "message": f"Profile '{profile_id}' not found."}
        if threshold < 0.0 or threshold > 2.0:
            return {"status": "failed", "message": "Threshold must be between 0.0 and 2.0."}
        self.profiles[profile_id]["threshold"] = threshold
        self.save_state()
        return {
            "status": "success",
            "message": f"Threshold for profile '{profile_id}' updated to {threshold}.",
        }

    def list_profiles(self) -> dict:
        """Returns a summary of all anomaly detection profiles."""
        summary = {
            pid: {
                "sample_count": p["sample_count"],
                "threshold": p["threshold"],
            }
            for pid, p in self.profiles.items()
        }
        return {"status": "success", "profiles": summary}


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
    detector = AnomalyDetector()

    if action == "train_normal":
        profile_id = payload.get("profile_id")
        observations = payload.get("observations", [])
        threshold = payload.get("threshold")
        if not profile_id or not observations:
            print(json.dumps({"status": "error", "message": "Missing 'profile_id' or 'observations'."}))
            sys.exit(1)
        result = detector.train_normal(profile_id, observations, threshold)
        print(json.dumps(result))

    elif action == "score_observation":
        profile_id = payload.get("profile_id")
        features = payload.get("features", [])
        if not profile_id or not features:
            print(json.dumps({"status": "error", "message": "Missing 'profile_id' or 'features'."}))
            sys.exit(1)
        result = detector.score_observation(profile_id, features)
        print(json.dumps(result))

    elif action == "update_threshold":
        profile_id = payload.get("profile_id")
        threshold = payload.get("threshold")
        if not profile_id or threshold is None:
            print(json.dumps({"status": "error", "message": "Missing 'profile_id' or 'threshold'."}))
            sys.exit(1)
        result = detector.update_threshold(profile_id, float(threshold))
        print(json.dumps(result))

    elif action == "list_profiles":
        result = detector.list_profiles()
        print(json.dumps(result))

    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
