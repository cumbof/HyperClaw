# Deterministic State Guard
__Category:__ Logic and Compliance

## Overview

The `deterministic_state_guard` skill acts as a mathematical "straighjacket" for autonomous agents. It prevents them from hallucinating impossible actions, skipping mandatory steps in a workflow, or breaking strict operational rules.

### The LLM Problem

Large Language Models are probabilistic sequence predictors. If you give an LLM a strict 15-step Standard Operating Procedure (SOP), a legal compliance checklist, or the rules of a complex board game, it will eventually hallucinate an "illegal" move. Prompt engineering cannot fix this reliably because LLMs fo not possess native, deterministic state-tracking architecture.

### The HDC Solution

Hyperdimensional Computing natively supports Finite State Automata (FSA). By representing states and actions as hypervectors, we can mathematically define a "Rulebook". Before the LLM agent is allowed to execute a critical action, it must query this HDC skill. If the math does not resolve to a valid state, the action is blocked, forcing the LLM to rethink its plan.

## How the Math Works

1. __Defining the State Machine:__ Every state (e.g., `Idle`, `Processing`, `Review`) and every action (e.g., `Start_Job`, `Approve`) is assigned a random orthogonal hypervector.

2. __Encoding Valid Transitions (Binding):__ A valid rule is encoded by binding the current state, the action, and the resulting next state using element-wise multiplication.

3. __Bundling the Rulebook (Bundling):__ All valid rules are bundled together (element-wise addition with majority thresholding) into a single, holistic vector that represents the entire legal universe of the workflow.

4. __Verifying an Agent's Move (Unbinding):__ When the agent attempts to perform `Action_Start` while in `State_Idle`, the handler queries the Rulebook by unbinding the current state and proposed action.

## The Reality Check: Iterative Cleanup

Unlike an LLM's fuzzy logic, this skill relies on strict mathematical distance. When the vector representation of the query is calculated, the Python handler compares it against all known state vectors in the Codebook using Cosine Similarity.

- If the similarity to a known state is high, the move is legal.
- If the similarity to all known states is low (just noise), the transition does not exist in the Rulebook. The move is illegal, and the skill returns a hard `false` or `blocked` status.

## Example Interaction

1. Agent Defines the Rules (Action: `define_rules`)

```json
{
    "action": "define_rules",
    "transitions": [
        {"current_state": "Draft", "action": "Submit", "next_state": "Under_Review"},
        {"current_state": "Under_Review", "action": "Approve", "next_state": "Published"}
    ]
}
```

_Handler Response:_ `{"status": "success", "message": "Rulebook compiled with 2 valid transitions"}`

2. Agent Attempts an Action (Action: `verify_move`)

```json
{
    "action": "verify_move",
    "current_state": "Draft",
    "proposed_action": "Approve"
}
```

_Handler Response:_ `{"status": "blocked", "reason": "ILLEGAL_MOVE", "message": "You cannot 'Approve' from the 'Draft' state"}`