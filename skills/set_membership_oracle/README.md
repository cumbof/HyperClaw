# Set Membership Oracle
__Category:__ Data Structures

## Overview

The `set_membership_oracle` skill provides an AI agent with a constant-size, dynamically updatable set data structure backed by Hyperdimensional Computing. It compresses an arbitrarily large collection of items into a single hypervector and supports approximate membership testing, element removal, and inter-set similarity measurement — all in constant time.

### The LLM Problem

Agents that need to maintain large dynamic collections (e.g., "has this URL been visited?", "is this drug on the banned list?") typically resort to keeping raw lists in their context window. This wastes context tokens, grows linearly, and vanishes when the context is truncated.

### The HDC Solution

In Vector-Symbolic Architectures, set membership is a natural operation. Every element is mapped to a random orthogonal hypervector. A set is formed by bundling (element-wise adding) all member vectors together. Because random hypervectors are nearly orthogonal in high dimensions, the bundled set vector retains a detectable "trace" of each member. Cosine distance between the set vector and any element vector reveals membership probability.

## How the Math Works

1. __Element Encoding:__ Each item string is assigned a unique random bipolar hypervector in the codebook.

2. __Set Bundling (Addition):__ Adding an element bundles its vector into the set's raw integer accumulator: `Set += V_element`.

3. __Set Unbundling (Subtraction):__ Removing an element subtracts its exact vector: `Set -= V_element`. This is fully reversible because the integer accumulator is never thresholded until query time.

4. __Membership Test:__ At query time, the accumulator is thresholded to a bipolar vector. The cosine distance to the query element's vector is computed. Members score near 0.5 (moderate similarity), non-members score near 1.0 (orthogonal).

5. __Set Similarity:__ Two set vectors are compared directly. Disjoint sets are nearly orthogonal (similarity ≈ 0); sets with large overlaps are more similar.

## The Reality Check

Bundled sets are **approximate** by nature (analogous to Bloom filters). False positives increase as the number of elements grows relative to the vector dimension. At dimension 10,000, reliable operation requires keeping sets well below ~1,000 elements.

## Example Interaction

1. Agent Builds an Allow-List (Action: `add_elements`)

```json
{
    "action": "add_elements",
    "set_id": "approved_drugs",
    "elements": ["Aspirin", "Ibuprofen", "Paracetamol"]
}
```

_Handler Response:_ `{"status": "success", "message": "3 element(s) added to set 'approved_drugs'."}`

2. Agent Tests Membership (Action: `test_membership`)

```json
{"action": "test_membership", "set_id": "approved_drugs", "element": "Ibuprofen"}
```

_Handler Response:_ `{"status": "success", "element": "Ibuprofen", "set_id": "approved_drugs", "is_member": true, "confidence": 50.6}`

```json
{"action": "test_membership", "set_id": "approved_drugs", "element": "Heroin"}
```

_Handler Response:_ `{"status": "success", "element": "Heroin", "set_id": "approved_drugs", "is_member": false, "confidence": -0.6}`
