# Tool: HDC Attribute Filter (`attribute_filter`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Attribute Filter. Use this tool to store records with named attributes and retrieve all records matching a set of attribute-value constraints. This is ideal for finding employees by department and city, filtering products by category and price tier, locating patients by diagnosis and medication, or any "SELECT WHERE" type query over structured records.

## How It Works

Each entity is stored as a hypervector that encodes both the entity's identity and all its attribute-value pairs. A filter query is encoded in the same way, and entities close to the filter vector (by cosine distance) are returned as matches.

## Schema & Actions

### 1. Action: `store_entity`

Stores an entity with its attributes.

__Input Arguments:__
- `action` (string): `"store_entity"`.
- `store_id` (string): The named collection (e.g., `"employees"`).
- `entity_name` (string): The unique entity identifier.
- `attributes` (object): A flat `{attribute_name: value}` mapping. Both keys and values must be strings.

__Example Payload:__

```json
{
    "action": "store_entity",
    "store_id": "employees",
    "entity_name": "Alice",
    "attributes": {"dept": "Eng", "city": "NYC", "level": "Senior"}
}
```

### 2. Action: `filter_entities`

Finds all entities matching the given attribute-value filters.

__Input Arguments:__
- `action` (string): `"filter_entities"`.
- `store_id` (string): The collection to search.
- `filters` (object): Attribute-value pairs to match (e.g., `{"city": "NYC"}`).

__Example Payload:__

```json
{
    "action": "filter_entities",
    "store_id": "employees",
    "filters": {"city": "NYC", "dept": "Eng"}
}
```

### 3. Action: `list_entities`

Returns all entity names in a store.

```json
{"action": "list_entities", "store_id": "employees"}
```

### 4. Action: `get_entity`

Checks whether a specific entity exists in the store.

```json
{"action": "get_entity", "store_id": "employees", "entity_name": "Alice"}
```

## Strict Rules for the Agent

1. __String Values Only:__ All attribute names and values must be strings. Use `"30"` rather than `30`.
2. __Exact Attribute Vocabulary:__ Use consistent attribute name and value strings. `"dept"` and `"department"` are different attributes.
3. __Approximate Matching:__ The filter uses cosine distance — it is not an exact SQL-style WHERE. An entity that matches 2 out of 3 filters may still appear in results with a lower score.
4. __Re-store to Update:__ To update an entity's attributes, call `store_entity` again with the same `entity_name`. This overwrites the previous encoding for that entity.
