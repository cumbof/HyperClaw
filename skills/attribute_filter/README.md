# Attribute Filter
__Category:__ Structured Query

## Overview

The `attribute_filter` skill provides an AI agent with a constant-space structured query capability. Entities and their attributes are compressed into hypervectors using role-filler binding; multi-attribute filter queries are encoded the same way and evaluated by cosine distance. This is the HDC equivalent of a lightweight `SELECT * WHERE attr=val AND attr2=val2` without a relational database.

### The LLM Problem

Agents that manage structured records (employee directories, product catalogs, patient lists) cannot efficiently answer multi-attribute queries from memory. Injecting the full table into the context window is expensive and forces the LLM to scan it textually, leading to missed matches and hallucinated results.

### The HDC Solution

Each entity is represented as a hypervector that encodes its attributes via role-filler binding (same as `role_filler_memory`). A filter query is represented as a bundle of the filter attribute-value bind vectors. Entities that match all or most filter criteria have low cosine distance to the filter query vector.

## How the Math Works

1. __Entity Encoding:__ `V_entity = V_name + Σ (V_attribute ⊗ V_value)`.

2. __Filter Encoding:__ `Q_filter = Σ (V_filter_attr ⊗ V_filter_val)`.

3. __Matching:__ `dist(V_entity, Q_filter) < threshold` → the entity matches the filter. Entities are ranked by distance (lower distance = better match).

## Example Interaction

1. Store Entities (Action: `store_entity`)

```json
{"action": "store_entity", "store_id": "employees", "entity_name": "Alice", "attributes": {"dept":"Eng","city":"NYC","level":"Senior"}}
{"action": "store_entity", "store_id": "employees", "entity_name": "Bob",   "attributes": {"dept":"Sales","city":"LA","level":"Junior"}}
{"action": "store_entity", "store_id": "employees", "entity_name": "Carol", "attributes": {"dept":"Eng","city":"NYC","level":"Lead"}}
```

2. Filter by Attributes (Action: `filter_entities`)

```json
{"action": "filter_entities", "store_id": "employees", "filters": {"dept": "Eng", "city": "NYC"}}
```

_Handler Response:_
```json
{
  "status": "success",
  "matches": [
    {"entity": "Alice", "score": 37.2},
    {"entity": "Carol", "score": 36.8}
  ],
  "count": 2
}
```
