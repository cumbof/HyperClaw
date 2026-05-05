# Tool: HDC Multicontext Switcher (`multicontext_switcher`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Multicontext Switcher. Use this tool to maintain multiple named **working contexts** — independent memory slots that hold different bundles of facts. This is ideal for multi-task agents that switch between different projects, users, or conversation threads without mixing their knowledge.

## How It Works

Each context is a separate integer accumulator that stores bundled fact vectors. You can switch the active context, add facts to it, query whether a topic is encoded in a context, and search all contexts to find the most relevant one for a given set of query terms.

## Schema & Actions

### 1. Action: `create_context`

Creates a new named context.

```json
{"action": "create_context", "context_id": "project_alpha", "tags": ["backend", "authentication"]}
```

### 2. Action: `switch_to`

Sets the active context. Subsequent `add_facts` calls will go to this context.

```json
{"action": "switch_to", "context_id": "project_alpha"}
```

### 3. Action: `add_facts`

Adds facts to a context (defaults to the active context).

__Input Arguments:__
- `action` (string): `"add_facts"`.
- `facts` (array of strings): Fact strings to add. Each fact is tokenized by whitespace.
- `context_id` (string, optional): Target context. If omitted, uses the active context.

__Example Payload:__

```json
{
    "action": "add_facts",
    "facts": [
        "database PostgreSQL version 14",
        "API rate limit 1000 per minute",
        "auth JWT RS256"
    ]
}
```

### 4. Action: `query_context`

Checks how relevant query terms are to a context's content.

```json
{
    "action": "query_context",
    "context_id": "project_alpha",
    "query_terms": ["JWT", "authentication"]
}
```

### 5. Action: `find_relevant_context`

Finds the context most relevant to given query terms across all contexts.

```json
{
    "action": "find_relevant_context",
    "query_terms": ["PostgreSQL", "database"]
}
```

### 6. Action: `list_contexts`

Returns all contexts with fact counts, active status, and tags.

```json
{"action": "list_contexts"}
```

## Strict Rules for the Agent

1. __Switch Before Adding:__ Always call `switch_to` at the start of a task, or provide `context_id` explicitly in `add_facts`.
2. __Contexts Are Additive:__ Facts are added to a context cumulatively. Contexts cannot be partially cleared.
3. __Query vs. Find:__ Use `query_context` to measure relevance within a known context; use `find_relevant_context` to discover which context matches a topic when the context is unknown.
