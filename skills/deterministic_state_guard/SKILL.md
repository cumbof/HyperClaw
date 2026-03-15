# Tool: Hallucination Guardrail (`deterministic_state_guard`)

## Tool Description

You are equipped with a Deterministic State Guard tool. You must use this tool when navigating stric workflows, standard operating procedures, or complex rule sets. Because you are a probabilistic model, you must rely on this tool to mathematically verify if your planned actions are "legal" within the current environment state before executing them.

## Schema & Actions

This tool accepts a JSON payload with a required `action` parameter. The action must be either `"define_rules"` or `"verify_move"`.

### 1. Action: `define_rules`

Use this to action at the beginning of a task to load a workflow, finite state machine, or set of rules into the guardrail.

__Input Arguments:__
- `action` (string): Must be `"define_rules"`.
- `transitions` (array of objects): A list of legal state transitions. Each object must have:
  - `current_state` (string): The starting state (e.g., "Draft").
  - `action` (string): The action taken (e.g., "Submit").
  - `next_state` (string): The resulting state (e.g., "Under_Review").

__Example Payload:__

```json
{
    "action": "define_rules",
    "triples": [
        {"current_state": "Draft", "action": "Submit", "next_state": "Under_Review"},
        {"current_state": "Under_Review", "action": "Approve", "next_state": "Published"}
    ]
}
```

### 2. Action: `verify_move`

Use this action before you execute any critical step in a workflow to ensure it is mathematically allowed.

__Input Arguments:__
- `action` (string): Must be `"verify_move"`.
- `current_state` (string): Your current known state in the workflow.
- `proposed_action` (string): The action you intend to take next.

__Example Payload:__

```json
{
    "action": "verify_move",
    "current_state": "Draft",
    "proposed_action": "Approve"
}
```

## Strict Rules for the Agent

1. __Mandatory Verification:__ You must never assume an action is legal based on your own internal reasoning or context window. Always use `verify_move` is a fulebook has been defined.
2. __Handle Rejections Gracefully:__ If a tool responds with `{"status": "blocked"}`, you must not proceed with the action. You must output a thought process explaining why the move was blocked and formulate a new, legal plan.
3. __Exact Strings:__ State and action names must match exactly what was defined in `define_rules`. Do not use synonyms (e.g., if the state is "Under_Review", do not query "Reviewing").