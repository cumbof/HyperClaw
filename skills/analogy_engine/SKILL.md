# Tool: HDC Analogy Engine (`analogy_engine`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Analogy Engine. Use this tool to learn named semantic relationships from examples and then perform forward and reverse lookups, or verify whether a new pair of concepts conforms to a known relationship. This is ideal for building domain-specific ontologies, translation tables, drug-target mappings, causal role encodings, or any domain where you need to answer "What is the X of Y?" type questions.

## How It Works

A relation (e.g., `"capital_of"`, `"synonym_of"`, `"treats"`) is learned from `(source, target)` example pairs. Each pair is mathematically bound into a single vector, and all pair vectors are superimposed into a holistic relation transform. Forward lookups (`source → target`) and reverse lookups (`target → source`) are performed by unbinding the known entity from the transform.

## Schema & Actions

### 1. Action: `train_relation`

Use this to teach the engine a named relationship from examples.

__Input Arguments:__
- `action` (string): Must be `"train_relation"`.
- `relation_name` (string): The name of the relation (e.g., `"capital_of"`).
- `pairs` (array of objects): Each object must have:
  - `source` (string): The input concept.
  - `target` (string): The related output concept.

__Example Payload:__

```json
{
    "action": "train_relation",
    "relation_name": "capital_of",
    "pairs": [
        {"source": "France",  "target": "Paris"},
        {"source": "Germany", "target": "Berlin"},
        {"source": "Italy",   "target": "Rome"}
    ]
}
```

### 2. Action: `forward_lookup`

Use this to retrieve the target for a given source under a named relation.

```json
{
    "action": "forward_lookup",
    "relation_name": "capital_of",
    "source": "France"
}
```

### 3. Action: `reverse_lookup`

Use this to retrieve the source for a given target under a named relation.

```json
{
    "action": "reverse_lookup",
    "relation_name": "capital_of",
    "target": "Berlin"
}
```

### 4. Action: `test_conformance`

Use this to check whether a `(source, target)` pair conforms to a learned relation.

```json
{
    "action": "test_conformance",
    "relation_name": "capital_of",
    "source": "Spain",
    "target": "Madrid"
}
```

### 5. Action: `list_relations`

Returns all trained relation names and their example counts.

```json
{"action": "list_relations"}
```

## Strict Rules for the Agent

1. __Train Before Query:__ You must call `train_relation` before `forward_lookup`, `reverse_lookup`, or `test_conformance`.
2. __Training Examples Work Best:__ `forward_lookup` and `reverse_lookup` are most reliable for concepts that were explicitly included in the training pairs. For novel concepts, results may be unreliable.
3. __Reverse Lookup Is More Robust:__ Due to the bundling math, `reverse_lookup` (target → source) tends to be more accurate than `forward_lookup` (source → target) when the relation has many training pairs.
4. __Conformance for Training Pairs:__ `test_conformance` reliably identifies pairs that ARE in the training set. Use the `similarity` score comparatively rather than as an absolute truth measure.
