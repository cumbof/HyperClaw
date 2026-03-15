# Tool: Reversible Persona Core (`reversible_memory`)

## Tool Description

You are equipped with a Reversible Persona Core. This tool provides you with a persistent, long-term memory for tracking user facts, preferences, and session context over time.

Because you are a stateless Large Language Model, you must use this tool to remember important user details. Crucially, this tool also allows you to perfectly unlearn information. If a user asks you to forget a specific fact, or requests data deletion for privacy compliance, you must use this tool to mathematically erase that knowledge from your working memory.

## Schema & Actions

This tool accepts a JSON payload with a required action parameter. The action must be either `"memorize"` or `"forget"`.

### 1. Action: `memorize`

Use this action to securely store new facts about a user.

__Input Arguments:__
- `action` (string): Must be `"memorize"`.
- `persona_id` (string): A unique identifier for the user or session (e.g., `"user_123"`).
- `facts` (array of objects): A list of facts to store. Each object must have:
  - `subject` (string): Usually the user or a related entity.
  - `predicate` (string): The relationship.
  - `object` (string): The target value.

__Example Payload:__

```json
{
    "action": "memorize",
    "persona_id": "user_123",
    "facts": [
        {"subject": "User", "predicate": "lives_in", "object": "Cleveland"},
        {"subject": "User", "predicate": "allergic_to", "object": "Peanuts"}
    ]
}
```

### 2. Action: `forget`

Use this action when the user explicitly asks you to forget something, or when a previous fact is no longer true (e.g., the user moved to a new city).

__Input Arguments:__
- `action` (string): Must be `"forget"`.
- `persona_id` (string): The unique identifier for the user.
- `facts` (array of objects): The exact facts to remove from memory.

__Example Payload:__

```json
{
    "action": "forget",
    "persona_id": "user_123",
    "facts": [
        {"subject": "User", "predicate": "allergic_to", "object": "Peanuts"}
    ]
}
```

## Strict Rules for the Agent

1. __Exact String Matching (CRITICAL):__ The unlearning math relies on exact vector subtraction. To successfully forget a fact, the `subject`, `predicate`, and `object` must be 100% identical to the strings you used to `memorize` it. (e.g., If you memorized "Cleveland", trying to forget "Cleveland, Ohio" will fail).

2. __Atomicity:__ Keep facts as atomic as possible (single words or short phrases). This makes it much easier to recall the exact string later when you need to delete it.

3. __Mandatory Deletion:__ If a user invokes their right to privacy (e.g., "Delete everything you know about my location"), you must immediately construct a `forget` payload for all location-based facts you have stored for that `persona_id`.