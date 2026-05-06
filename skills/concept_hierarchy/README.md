# Concept Hierarchy
__Category:__ Knowledge Representation

## Overview

The `concept_hierarchy` skill lets an AI agent build and navigate **IS-A taxonomies** using Hyperdimensional Computing. Each class is a compressed hypervector that encodes all its members; IS-A tests are constant-time cosine-distance queries. A lightweight parent graph enables transitive multi-hop IS-A reasoning.

### The LLM Problem

LLMs do not have a native, modifiable ontology. Asking an LLM "Is a Maltese a Pet?" relies entirely on its training data. For domain-specific taxonomies (medical device types, supply chain categories, internal product hierarchies), the LLM may hallucinate incorrect classifications or fail entirely on novel concepts not in its training data.

### The HDC Solution

Every concept IS-A relationship is represented by bundling member vectors into a class prototype. Membership probability is measured by cosine distance between the query vector and the class prototype. A separate parent graph provides deterministic transitive closure that is independent of the probabilistic vector test.

## How the Math Works

1. __Class Prototype:__ `C_class = V_class + Σ V_member_i`. Each member's presence shifts the prototype toward that member in vector space.

2. __Direct Membership Test:__ `dist(C_class, V_concept) < threshold`. Members land near 0.5; non-members near 1.0.

3. __Transitive IS-A:__ The parent graph records direct parent assignments. A BFS traversal checks transitive reachability. This is fully deterministic and does not rely on vector similarity.

## Example Interaction

1. Define the Hierarchy (Action: `define_class`)

```json
{"action": "define_class", "class_name": "Dog",    "members": ["Poodle","Bulldog","Labrador"], "parent_classes": ["Animal","Pet"]}
{"action": "define_class", "class_name": "Animal",  "members": ["Dog","Cat","Fish"]}
```

2. Direct and Transitive IS-A (Action: `is_a`)

```json
{"action": "is_a", "concept": "Poodle", "class_name": "Animal"}
```

_Handler Response:_ `{"status": "success", "concept": "Poodle", "class": "Animal", "is_direct_member": false, "is_transitive_member": true, "similarity": -0.1}`

3. Get All Ancestors (Action: `get_ancestors`)

```json
{"action": "get_ancestors", "concept": "Poodle"}
```

_Handler Response:_ `{"status": "success", "concept": "Poodle", "ancestors": ["Dog", "Animal", "Pet"]}`
