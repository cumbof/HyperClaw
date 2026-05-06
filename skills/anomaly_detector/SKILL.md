# Tool: HDC Anomaly Detector (`anomaly_detector`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Anomaly Detector. Use this tool to detect unusual observations in a data stream by learning what "normal" looks like from labeled examples. This is ideal for fraud detection, system health monitoring, intrusion detection, medical alert systems, or any scenario where you need to flag observations that deviate significantly from a learned baseline.

## How It Works

Normal observations are provided as feature sets. The tool builds a single "normal prototype" hypervector by bundling all normal feature vectors. New observations are encoded the same way and compared to the prototype using cosine distance. Observations that are far from the normal prototype are flagged as anomalies.

## Schema & Actions

### 1. Action: `train_normal`

Teaches the detector what "normal" looks like.

__Input Arguments:__
- `action` (string): `"train_normal"`.
- `profile_id` (string): A unique profile name (e.g., `"network_traffic"`, `"user_behavior"`).
- `observations` (array of arrays): Each inner array is a list of feature strings for one normal observation.
- `threshold` (float, optional): Cosine distance cutoff (0.0–2.0). Observations at or above this are anomalous. Default is `0.6`.

__Example Payload:__

```json
{
    "action": "train_normal",
    "profile_id": "login_behavior",
    "observations": [
        ["morning", "office_IP", "standard_browser", "email_access"],
        ["afternoon", "office_IP", "standard_browser", "file_access"],
        ["morning", "VPN", "standard_browser", "email_access"]
    ]
}
```

### 2. Action: `score_observation`

Scores a new observation for anomalousness.

__Input Arguments:__
- `action` (string): `"score_observation"`.
- `profile_id` (string): The profile to compare against.
- `features` (array of strings): Feature strings describing the new observation.

__Example Payload:__

```json
{
    "action": "score_observation",
    "profile_id": "login_behavior",
    "features": ["midnight", "foreign_IP", "tor_browser", "admin_access"]
}
```

### 3. Action: `update_threshold`

Adjusts the anomaly detection threshold for a profile.

```json
{"action": "update_threshold", "profile_id": "login_behavior", "threshold": 0.55}
```

### 4. Action: `list_profiles`

Returns all anomaly detection profiles and their settings.

```json
{"action": "list_profiles"}
```

## Strict Rules for the Agent

1. __Train Before Scoring:__ Call `train_normal` with at least 3–5 representative observations before calling `score_observation`.
2. __Feature Consistency:__ Use the same vocabulary across training and scoring. Unseen features at score time will generate new random vectors, increasing the anomaly score.
3. __Threshold Tuning:__ The default threshold of `0.6` is a starting point. For tight security applications, lower it (e.g., `0.45`). For loose monitoring, raise it (e.g., `0.75`).
4. __Multiple Profiles:__ Use separate `profile_id` values for independent monitoring contexts.
