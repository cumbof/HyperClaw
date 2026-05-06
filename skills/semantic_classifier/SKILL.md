# Tool: HDC Semantic Classifier (`semantic_classifier`)

## Tool Description

You are equipped with a Hyperdimensional Computing (HDC) Semantic Classifier. Use this tool to learn and apply categorical labels from examples, without retraining a neural network. You should use it whenever you need to classify new items into known categories based on labeled training examples (e.g., categorizing emails, medical symptoms, intents, or text topics).

## How It Works

Each class is represented by a **prototype hypervector** built by bundling the feature vectors of all its training examples. To classify a new item, its features are encoded the same way and the closest prototype is returned.

## Schema & Actions

This tool accepts a JSON payload with a required `action` parameter.

### 1. Action: `train`

Use this to add a labeled training example to a class prototype.

__Input Arguments:__
- `action` (string): Must be `"train"`.
- `class_label` (string): The category name (e.g., `"spam"`, `"benign"`).
- `features` (array of strings): Descriptive feature words or tags for this example.

__Example Payload:__

```json
{
    "action": "train",
    "class_label": "spam",
    "features": ["buy", "now", "discount", "offer", "free"]
}
```

### 2. Action: `classify`

Use this to assign the most likely class to a new set of features.

__Input Arguments:__
- `action` (string): Must be `"classify"`.
- `features` (array of strings): Descriptive feature words or tags of the item to classify.

__Example Payload:__

```json
{
    "action": "classify",
    "features": ["discount", "limited", "offer"]
}
```

### 3. Action: `list_classes`

Use this to inspect which classes have been trained.

__Input Arguments:__
- `action` (string): Must be `"list_classes"`.

__Example Payload:__

```json
{
    "action": "list_classes"
}
```

## Strict Rules for the Agent

1. __Feature Atomicity:__ Features should be individual words or short tags. Do not pass full sentences as a single feature.
2. __Minimum Training:__ Provide at least 3–5 training examples per class for meaningful accuracy. The more examples, the more robust the prototype.
3. __Consistent Features:__ Use the same vocabulary across training and classification calls. A typo in a feature name will generate a new, unrelated hypervector.
4. __Low-Confidence Responses:__ If the tool returns `"low_confidence"`, it means the query is equidistant from all classes. Add more training examples or refine the features.
