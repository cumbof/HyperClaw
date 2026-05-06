# Anomaly Detector
__Category:__ Monitoring and Safety

## Overview

The `anomaly_detector` skill enables an AI agent to learn what is "normal" from labeled examples and then flag deviations in new observations. It uses the HDC prototype model: a single "normal state" hypervector is formed by bundling all training observations, and anomaly scores are computed as cosine distances from that prototype.

### The LLM Problem

LLMs cannot maintain a running statistical model of observed data. They cannot score "is this transaction normal?" in a mathematically principled, threshold-based way without injecting large volumes of historical data into the context window. They also drift over long interactions, failing to hold a consistent detection boundary.

### The HDC Solution

HDC prototype learning is one of the most well-established applications of hyperdimensional computing. By encoding observations as feature bundles and accumulating them into an integer prototype vector, the skill captures the "center of mass" of normal behavior. A new observation is compared via cosine distance: close to the prototype = normal; far away = anomalous. The threshold is tunable per profile.

## How the Math Works

1. __Observation Encoding:__ Each feature in an observation is retrieved or created as a random bipolar hypervector. The feature vectors are summed into a sample accumulator.

2. __Normal Prototype:__ All training sample accumulators are summed into the profile's integer accumulator. At query time, the majority-rule threshold yields a bipolar prototype vector.

3. __Anomaly Scoring:__ The new observation is encoded the same way and thresholded. Cosine distance between the observation vector and the normal prototype is the anomaly score. Distance ≥ threshold → ANOMALY.

## Example Interaction

1. Train Normal Behavior (Action: `train_normal`)

```json
{
    "action": "train_normal",
    "profile_id": "login",
    "observations": [
        ["morning", "office_IP", "email_access"],
        ["afternoon", "office_IP", "file_access"]
    ],
    "threshold": 0.6
}
```

_Handler Response:_ `{"status": "success", "message": "2 normal observation(s) added to profile 'login'. Total samples: 2."}`

2. Score an Anomalous Login (Action: `score_observation`)

```json
{"action": "score_observation", "profile_id": "login", "features": ["midnight", "foreign_IP", "admin_access"]}
```

_Handler Response:_ `{"status": "success", "anomaly_score": 0.88, "threshold": 0.6, "is_anomaly": true, "label": "ANOMALY"}`

3. Score a Normal Login (Action: `score_observation`)

```json
{"action": "score_observation", "profile_id": "login", "features": ["morning", "office_IP", "email_access"]}
```

_Handler Response:_ `{"status": "success", "anomaly_score": 0.49, "threshold": 0.6, "is_anomaly": false, "label": "NORMAL"}`
