# Tool: HDC Concept Hierarchy (`concept_hierarchy`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Concept Hierarchy. Use this tool to build and query **IS-A ontologies** — taxonomies where some concepts are sub-concepts of others (e.g., Poodle IS-A Dog, Dog IS-A Animal). This is ideal for knowledge base construction, domain ontology enforcement, type checking in planning tasks, and any scenario where you need to answer "Is X a kind of Y?"

## How It Works

Each class is represented as a bundle of its member concept vectors (plus the class vector itself). IS-A membership is tested by measuring cosine similarity between a concept vector and a class prototype. Transitive membership (via multi-hop IS-A chains) is checked through an explicit parent graph stored alongside the vectors.

## Schema & Actions

### 1. Action: `define_class`

Defines or extends a class with members and optional parent classes.

__Input Arguments:__
- `action` (string): `"define_class"`.
- `class_name` (string): The class name (e.g., `"Dog"`).
- `members` (array of strings): Concepts that are direct members of this class.
- `parent_classes` (array of strings, optional): Classes that this class IS-A member of.

__Example Payload:__

```json
{
    "action": "define_class",
    "class_name": "Dog",
    "members": ["Poodle", "Bulldog", "Labrador"],
    "parent_classes": ["Animal", "Pet"]
}
```

### 2. Action: `is_a`

Tests whether a concept is a member of a class (directly or transitively).

```json
{
    "action": "is_a",
    "concept": "Poodle",
    "class_name": "Animal"
}
```

### 3. Action: `get_ancestors`

Returns all ancestor classes of a concept by traversing the IS-A graph.

```json
{
    "action": "get_ancestors",
    "concept": "Poodle"
}
```

### 4. Action: `find_class`

Finds the most similar defined class for a given concept.

```json
{
    "action": "find_class",
    "concept": "Poodle"
}
```

## Strict Rules for the Agent

1. __Define Before Query:__ Call `define_class` before calling `is_a`, `get_ancestors`, or `find_class`.
2. __Explicit Hierarchy:__ Transitive IS-A membership is only detected if the parent chain was explicitly defined. The tool does not infer unseen relationships.
3. __Additive:__ Calling `define_class` multiple times for the same class adds new members; it does not replace the class.
