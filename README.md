# HyperClaw
Equip your AI agents with Hyperdimensional Computing superpowers.

While Large Language Models (LLMs) excel at flexible reasoning, they are held back by fundamental architectural flaws: limited context windows, catastrophic forgetting, rule hallucinations, and the inability to process high-speed data stream. HyperClaw functions as a mathematically rigorous cognitive co-processor, offloading these weaknesses to a deterministic vector-symbolic environment (powered by [hdlib](https://github.com/cumbof/hdlib)).

> [!CAUTION]  
> __LLM-Generated Content Disclaimer:__ The conceptual design, prompt schemas (`SKILL.md`), and mathematical mappings outlined in this repository were generated with the assistance of a Large Language Model (LLM) that can produce subtle logic errors, unoptimized vector operations, or flawed assumptions. Please use these tools wit caution. It is highly recommended to rigorously test the Python execution handlers (`handler.py`) and verify their deterministic outputs befre deploying these skills in any production or sensitive autonomous agent workflows.

## The Skill Arsenal (Grounded in VSA Math)

The following skills are availabile to the agent. There is no "infinite capacity" magic, only highly optimized, deterministic vector operations.

| Skill ID | Name | Category |
|----------|------|----------|
| [working_memory_graph](skills/working_memory_graph) | Semantic Working Memory | Graph Reasoning |
| [deterministic_state_guard](skills/deterministic_state_guard) | Hallucination Guardrail | Logic and Compliance |
| [reversible_memory](skills/reversible_memory) | Reversible Persona Core | Privacy and Unlearning |
| [stream_anomaly_watcher](skills/stream_anomaly_watcher) | High-Speed Stream Watcher | Edge Processing |
| [few_shot_classifier](few_shot_classifier) | Fast Few-Shot Classifier | Edge Processing |
| [sequence_motif_finder](skills/sequence_motif_finder) | Sequence and Motif Aligner | Edge Processing |
| [swarm_state_sync](skills/swarm_state_sync) | Multi-Agent State Sync | Swarm Dynamics |
| [swarm_consensus](skills/swarm_consensus) | Swarm Consensus Evaluator | Swarm Dynamics |
| [zero_knowledge_classifier](skills/zero_knowledge_classifier) | Zero-Knowledge Classifier | Privacy and Security |
| [multimodal_alignment](skills/multimodal_alignment) | Cross-Modal Verifier | Multimodal Fusion |

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
|-- README.md                  # Project overview and setup
|-- skills/                    # Root directory for skills
|   |-- catalog.json           # Master index of all available skills and categories
|   |-- working_memory_graph/  # Individual skill directory
|   |   |-- SKILL.md           # Prompt/schema defining the skill for the LLM agent
|   |   |-- handler.py         # Python execution logic (math via hdlib)
|   |   |-- examples/          # Example inputs/outputs for prompting
|   |   |-- tests/             # Unit tests for the Python handler
|   |-- ...                    # Other skill directories
```

## Prerequisites

To use these skills locally or deploy them to an agent framework, you will need:
- Python 3.8+
- [hdlib](https://github.com/cumbof/hdlib)
- An agent framework (e.g., OpenClaw).

## Credits

If you use HyperClaw in your software or academic research, give it a credit:

```bibtex
@software{hyperclaw2026,
    author = {Cumbo, Fabio},
    title  = {{HyperClaw}: Equip your AI agents with Hyperdimensional Computing superpowers},
    year   = {2026},
    url    = {https://github.com/cumbof/HyperClaw},
    note   = {GitHub repository}
}
```

## License

This project is licensed under the [MIT License](LICENSE)