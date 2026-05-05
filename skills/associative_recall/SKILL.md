# Tool: HDC Associative Recall (`associative_recall`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Associative Recall engine. Use this tool to build and query **key-value pair memories** — where you want to store `(cue → answer)` associations and later retrieve the answer given only the cue. Use it for translation pairs, vocabulary lookup, configuration mappings, abbreviation expansion, or any scenario where you need to answer "what is X associated with?"

## How It Works

Each `(key, value)` pair is mathematically bound into a single hypervector and all pairs are bundled into the store. To retrieve a value, the tool unbinds the key from the store and finds the closest matching concept.

## Schema & Actions

This tool accepts a JSON payload with a required `action` parameter.

### 1. Action: `store_association`

Use this to store one or more key-value associations.

__Input Arguments:__
- `action` (string): Must be `"store_association"`.
- `store_id` (string): A unique name for this association store (e.g., `"translations_en_fr"`).
- `pairs` (array of objects): Each object must have:
  - `key` (string): The cue or input concept.
  - `value` (string): The associated answer or output concept.

__Example Payload:__

```json
{
    "action": "store_association",
    "store_id": "translations_en_fr",
    "pairs": [
        {"key": "cat",  "value": "chat"},
        {"key": "dog",  "value": "chien"},
        {"key": "bird", "value": "oiseau"}
    ]
}
```

### 2. Action: `recall`

Use this to retrieve the value associated with a given key.

__Input Arguments:__
- `action` (string): Must be `"recall"`.
- `store_id` (string): The store to search.
- `key` (string): The cue or input concept to look up.

__Example Payload:__

```json
{
    "action": "recall",
    "store_id": "translations_en_fr",
    "key": "cat"
}
```

### 3. Action: `forget_association`

Use this to remove specific key-value pairs from the store. The key and value strings must match exactly what was used in `store_association`.

__Input Arguments:__
- `action` (string): Must be `"forget_association"`.
- `store_id` (string): The store to update.
- `pairs` (array of objects): The exact pairs to remove.

__Example Payload:__

```json
{
    "action": "forget_association",
    "store_id": "translations_en_fr",
    "pairs": [
        {"key": "cat", "value": "chat"}
    ]
}
```

## Strict Rules for the Agent

1. __One Value Per Key:__ The tool performs best when each key maps to exactly one value. Storing two different values for the same key causes them to interfere in the vector space.
2. __Exact Match for Deletion:__ To successfully forget a pair, both the `key` and `value` strings must be 100% identical to the stored pair.
3. __Atomic Strings:__ Keys and values should be single words or short phrases for best retrieval accuracy.
4. __Multiple Stores:__ Use different `store_id` values for independent mappings (e.g., separate stores for English→French and English→German translations).
