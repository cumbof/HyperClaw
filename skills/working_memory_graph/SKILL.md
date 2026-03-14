# Tool: HDC semantic Working Memory (`working_memory_graph`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Working Memory. This tool allows you to permanently store and retrieve factual relationships. You should use this tool whenever you are asked to "remember" facts, when you are reading long documents that exceed your standard context window, or when you need to build a persistent knowledge graph.

## How It Works

You do not pass raw text into this tool. You must first extract structured relational triples `(Subject, Predicate, Object)` from the text. The tool will mathematically bind these triples and store them in a persistent vector space. Later, you can query this space to retrieve exact facts.

## Schema & Actions

This tool accepts a JSON payload with a required `action` parameter. The action must be either `"store"` or `"query"`.

### 1. Action: `store`

Use this to save new facts into the memory graph.

__Input Arguments:__
- `action` (string): Must be `"store"`.
- `triples` (array of objects): A list of facts to store. Each object must have:
  - `subject` (string): The primary entity (e.g., "Aspirin").
  - `predicate` (string): The relationship verb (e.g., "treats").
  - `object` (string): The target entity (e.g., "Headache").

__Example Payload:__

```json
{
    "action": "store",
    "triples": [
        {"subject": "Aspirin", "predicate": "treats", "object": "Headache"},
        {"subject": "Aspirin", "predicate": "causes", "object": "Nausea"}
    ]
}
```

### 2. Action: `query`

Use this to retrieve a fact from the memory graph. You must provide exactly two known variables and one unknown variable (represented by `?`).

__Input Arguments:__
- `action` (string): Must be `"query"`.
- `subject` (string): The subject, or `?` if unknown.
- `predicate` (string): The predicate, or `?` if unknown.
- `object` (string): The object, or `?` if unknown.

__Example Payload (Asking "What does Aspirin treat?"):__

```json
{
    "action": "query",
    "subject": "Aspirin",
    "predicate": "treats",
    "object": "?"
}
```

## Strict Rules for the Agent

1. __Keep it Atomic:__ Do not pass entire paragraphs or complex sentences as subjects or objects. Break them down into single words or short phrases (e.g., "High Blood Pressure", not "the patient suffered from high blood pressure").
2. __Standardize Predicates:__ Try to use consistent predicates to make querying easier (e.g., prefer "is_a", "causes", "treats", "located_in", "part_of").
3. __One Unknown Only:__ When querying, exactly one of the three fields (subject, predicate, object) must be the `?` character. You cannot query with two unknowns.
4. __Trust the Return:__ The tool uses an iterative cleanup memory. If the tool returns a result, treat it as a mathematically verified fact in your response to the user. If the tool returns `null` or `low_confidence`, state that the fact is not in your working memory.