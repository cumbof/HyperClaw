# Tool: HDC Episodic Memory (`episodic_memory`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Episodic Memory. Use this tool to store and retrieve **multi-event episodes** — ordered sequences of events annotated with contextual tags (e.g., date, location, mood, session ID). This is ideal for maintaining a diary of past interactions, tracking multi-step processes, replaying event chains, or contextual conversation history.

## How It Works

Each episode is encoded in two layers: (1) a **context vector** that captures associated tags, and (2) a **sequence vector** that encodes the order of events via permutation-based bigram chaining. You can retrieve an episode by its context, or query what event follows a given event in a stored episode.

## Schema & Actions

### 1. Action: `record_episode`

Stores a new episode.

__Input Arguments:__
- `action` (string): `"record_episode"`.
- `episode_id` (string): Unique identifier for the episode.
- `events` (array of strings): Ordered list of events (minimum 2).
- `context_tags` (array of strings): Optional labels describing the context (e.g., `["hospital", "Tuesday", "emergency"]`).

__Example Payload:__

```json
{
    "action": "record_episode",
    "episode_id": "visit_2025_01_10",
    "events": ["Arrival", "Triage", "X-Ray", "Diagnosis", "Discharge"],
    "context_tags": ["hospital", "morning", "emergency"]
}
```

### 2. Action: `recall_by_context`

Finds the episode whose context best matches the provided tags.

```json
{
    "action": "recall_by_context",
    "context_tags": ["hospital", "emergency"]
}
```

### 3. Action: `query_next_event`

Retrieves what event follows a given event in a stored episode.

```json
{
    "action": "query_next_event",
    "episode_id": "visit_2025_01_10",
    "event": "Triage"
}
```

### 4. Action: `list_episodes`

Returns a summary of all stored episodes.

```json
{"action": "list_episodes"}
```

## Strict Rules for the Agent

1. __Unique Episode IDs:__ Using the same `episode_id` twice overwrites the previous episode.
2. __Exact String Matching:__ Event and tag strings are case-sensitive.
3. __Minimum 2 Events:__ Episodes need at least 2 events to encode a sequence.
4. __Context Tags Are Optional:__ If no context tags are provided, `recall_by_context` cannot differentiate this episode from others. Always provide meaningful tags.
