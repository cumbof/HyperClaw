# Reversible Persona Core
__Category:__ Privacy and Unlearning

## Overview

The `reversible_memory` skill provides autonomous agents with a persistent, lifelong memory core that can flawlessly "unlearn" specific facts on command. It is designed for managing user personas, continuous learning sessions, and ensuring strict data privacy compliance (like GDPR's "Right to be Forgotten").

### The LLM Problem

Large Language Models suffer from two massive memory issues:

1. __Catastrophic Forgetting:__ As the context window fills up over long interactions, the LLM naturally drops older facts.

2. __The "Unlearning" Impossibility:__ If a user tells an agent, _"Forget everything I told you about my medical history"_, an LLM cannot cleanly do this. The data is either baked into its weights or scattered randomly throughout a RAG Vector Database, requiring complex metadata filtering to remove.

### The HDC Solution

In Vector-Symbolic Architectures, learning is just vector addition, and unlearning is simply vector subtraction. By mapping user facts into hypervectors, the agent can maintain a single "Persona Vector." When instructed to forget a fact, the skill calculates the exact vector for that fact and subtracts it from the Persona Vector, mathematically guaranteeing its complete removal from the agent's memory.

## How the Math Works

1. __Learning (Addition):__ When the user states "I am allergic to Peanuts", the handler binds those concepts and adds them to the memory accumulator.

2. __Unlearning (Subtraction):__ When the user later says "Forget my peanut allergy", the handler recreates the exact same fact vector and subtracts it.

## The Reality Check: Iterative Cleanup

In standard binary or bipolar HDC, vectors consist of 1s and -1s. When you bundle multiple facts, you apply a majority-rule threshold to keep the resulting vector bipolar.

__The Trap:__ If you apply this threshold before saving the state, you permanently lose the exact addition history. Subtraction becomes lossy, and the memory will degrade into noise (violating the promise of perfect unlearning).

__The Grounded Fix:__ This skill's Python handler explicitly separates the state. It maintains a raw Integer Accumulator vector (e.g., `[3, -1, 5, 0, -2...]`) where the math actually happens. It only applies the bipolar threshold (`> 0 ? 1 : -1`) dynamically when the LLM needs to query the Persona Vector. This guarantees 100% mathematically flawless reversibility.

## Example Interaction

1. Agent Memorizes a Fact (Action: `memorize`)

```json
{
    "action": "memorize",
    "persona_id": "user_123",
    "facts": [
        {"subject": "User", "predicate": "lives_in", "object": "Cleveland"},
        {"subject": "User", "action": "likes", "next_state": "Sci-Fi"}
    ]
}
```

_Handler Response:_ `{"status": "success", "message": "2 facts securely added to persona accumulator"}`

2. Agent Unlearns a Fact (Action: `forget`)

```json
{
    "action": "forget",
    "persona_id": "user_123",
    "facts": [
        {"subject": "User", "predicate": "lives_in", "object": "Cleveland"}
    ]
}
```

_Handler Response:_ `{"status": "success", "message": "Fact mathematically subtracted and forgotten"}`