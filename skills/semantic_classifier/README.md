# Semantic Classifier
__Category:__ Classification

## Overview

The `semantic_classifier` skill gives an AI agent the ability to learn categorical labels from examples at runtime, without fine-tuning a model or calling an external API. It uses the HDC prototype (centroid) classification approach: each class is a single bundled hypervector that summarizes all its training examples.

### The LLM Problem

LLMs classify text probabilistically and are sensitive to prompt phrasing. They cannot easily be updated with new examples mid-conversation without risking context pollution or hallucinated rule changes. They also lack a deterministic decision boundary, making audit trails for classification impossible.

### The HDC Solution

HDC prototype classification is a well-studied, deterministic alternative to k-NN and shallow neural networks. Every training example is encoded into a feature hypervector (by bundling the vectors of its individual feature tokens). The class prototype is the running integer accumulation of all such sample vectors. Classification is a single cosine-distance lookup — constant time regardless of how many examples have been trained.

## How the Math Works

1. __Feature Encoding:__ Each feature word/token is assigned a random hypervector from the codebook. A sample is encoded by summing all its feature vectors (bundle without threshold), producing a raw integer accumulator.

2. __Prototype Update (Training):__ The sample accumulator is added element-wise to the class prototype accumulator. Over many examples the prototype vector converges to a direction that is more similar to class members than non-members.

3. __Classification:__ The query sample is thresholded to a bipolar vector. Each class prototype accumulator is independently thresholded. Cosine distances are computed and the class with the smallest distance wins.

## Example Interaction

1. Agent Trains Two Classes (Action: `train`)

```json
{"action": "train", "class_label": "spam",   "features": ["buy", "now", "free", "discount", "offer"]}
{"action": "train", "class_label": "ham",    "features": ["meeting", "agenda", "project", "deadline"]}
```

_Handler Response:_ `{"status": "success", "message": "Training example with 5 features added to class 'spam'."}`

2. Agent Classifies a New Message (Action: `classify`)

```json
{
    "action": "classify",
    "features": ["limited", "offer", "free", "click"]
}
```

_Handler Response:_
```json
{
    "status": "success",
    "predicted_class": "spam",
    "confidence": 25.4,
    "all_scores": [
        {"class": "spam", "confidence": 25.4},
        {"class": "ham",  "confidence": -0.6}
    ]
}
```
