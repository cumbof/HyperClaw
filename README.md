# HyperClaw
Equip your AI agents with Hyperdimensional Computing superpowers.

While Large Language Models (LLMs) excel at flexible reasoning, they are held back by fundamental architectural flaws: limited context windows, catastrophic forgetting, rule hallucinations, and the inability to process high-speed data stream. HyperClaw functions as a mathematically rigorous cognitive co-processor, offloading these weaknesses to a deterministic vector-symbolic environment (powered by [hdlib](https://github.com/cumbof/hdlib)).

## The Skill Arsenal (Grounded in VSA Math)

The following skills are availabile to the agent. There is no "infinite capacity" magic, only highly optimized, deterministic vector operations.

| Skill ID | Name | Category | Mechanism and Reality Check |
|----------|------|----------|-----------------------------|
| `hdc_working_memory_graph` | Semantic Working Memory | Graph Reasoning | Binds `(Sub, Pred, Obj)` and bundles into a state vector. Capacity is not "infinite". To prevent crosstalk noise from drowning out facts, the Python handler uses Iterative Cleanup Memory to denoise query results. |
| `hdc_deterministic_state_guard` | Hallucination Guardrail | Logic and Compliance | Encodes operational rules/state machines. The agent queries this skill to perform a rapid cosine similarity check, acting as a hard mathematical boundary against LLM hallucinations. |
| `hdc_reversible_memory` | Reversible Persona Core | Privacy and Unlearning | A persistent user memory updated via vector addition and "unlearned" viasubtraction. Standard bipolar subtraction is lossy. This skill works flawlessly because the handler maintains an accumulator (pre-thresholding) to guarantee perfect data removal. |
| `hdc_stream_anomaly_watcher` | High-Speed Stream Watcher | Edge Processing | Builds a rolling "normalcy" prototype from live data streams (e.g., logs, telemetry). Proven edge-computing use case. Runs completely ourside the LLM. Only interrupts the LLM when an incoming vector statistically deviates beyond a strict cosine distance threshold. |
| `hdc_few_shot_classifier` | Fast Few-Shot Classifier | Edge Processing | Bundles a few labeled examples into class "prototype vectors" for instant classification. Fast and robust, buut handler must enforce pre-normalization of the prototypes so that classes with more examples don't mathematically skew the cosine similarity. |
| `hdc_sequence_motif_finder` | Sequence and Motif Aligner | Edge Processing | Uses vector permutation (shifting) to encode the strict order of events or strings. Permutations degrade if sequences are too long. Handler uses hierarchical chunking to safely find patterns in massive data streams without token usage. |
| `hdc_swarm_state_sync` | Multi-Agent State Sync | Swarm Dynamics | Compresses Agent A's semantic landscape into a single vector for Agent B to use. Agent B cannot "read" the vector like text. Furthermore, this only works if both agents initialize with a shared codebook seed. Once shared, Agent B can instantly evaluate if new data aligns with Agent A's context. |
| `hdc_swarm_consensus` | Swarm Consensus Evaluator | Swarm Dynamics | Bundles the semantic State Vectors of _N_ different agents into a single consensus vector. Bundling naturally creates a superposition favoring repeated concepts. Agents can calculate their cosine distance to this vector to measure mathematical agreement without LLM-to-LLM debates. |
| `hdc_zero_knowledge_classifier` | Zero-Knowledge Classifier | Privacy and Security | Local environments encode sensitive data into hypervectors before sending them to the LLM. Since the codebook stays local, the vecotrs are pseudo-random to the LLM. The LLM can still accurately cluster and classify the data using cosine similarity without ever accessing the plaintext. |
|`hdc_multimodal_alignment`| Cross-Modal Verifier | Multimodal Fusion | Encodes different modalities (e.g., text summaries vs. numeric logs) into the same dimensional space. Requires strict encoding rules (fractional encoding for continuous numbers, bag-of-words for text) and pre-bundle normalization to prevent numeric data from overpowering the text signature. |

## Installation & Architecture

> [!NOTE]  
> Requires the [hdlib](https://github.com/cumbof/hdlib) Python library for underlying VSA mathematical operations.

All skills are located in the `/skills` directory and include an LLM-facing `SKILL.md` (instructions) and an optional Python `handler.py` (execution logic).

### Usage Flow

1. __Agent Orchestration:__ The LLM decides to use a skill and outputs a JSON tool call.
2. __Background Math:__ The Python `handler.py` executes the MAP (Multiply-Add-Permute) operations.
3. __Deterministic Return:__ The handler returns a clean, mathematically verified string or boolean back to the LLM context.

### Repository Structure

```text
.
|-- README.md                      # Project overview and setup
|-- skills/                        # Root directory for skills
|   |-- catalog.json               # Master index of all available skills and categories
|   |-- hdc_working_memory_graph/  # Individual skill directory
|   |   |-- SKILL.md               # Prompt/schema defining the skill for the LLM agent
|   |   |-- handler.py             # Python execution logic (math via hdlib)
|   |   |-- examples/              # Example inputs/outputs for prompting
|   |   |-- tests/                 # Unit tests for the Python handler
|   |-- ...                        # Other skill directories
```

## Prerequisites

To use these skills locally or deploy them to an agent framework, you will need:
- Python 3.8+
- [hdlib](https://github.com/cumbof/hdlib)
- An agent framework (e.g., OpenClaw).

## Credits

If you use HyperClaw in your software or academic research, give it a credit:

> _Manuscript in preparation_

## License

This project is licensed under the [MIT License](LICENSE)