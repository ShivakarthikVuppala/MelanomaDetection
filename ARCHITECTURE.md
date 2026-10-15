# CaseState Agent Architecture

`OrchestratorAgent` runs a bounded decision loop powered by **Hybrid Guided Reasoning**:
- **Safety Prerequisite Ordering**: Enforces foundational medical prerequisites (Image Quality → Vision & ABCD extraction → Temporal Evolution → Multimodal Fusion).
- **Cognitive Mind (LLM Deliberation)**: Uses Google Gemini to dynamically analyze clinical findings, identify diagnostic uncertainties, formulate targeted RAG literature queries, and evaluate evidence sufficiency and stop criteria.
- **Execution Trace**: Records both operational actions and clinical agent thoughts in the execution trace for full transparency.

```text
observe CaseState -> LLM Cognitive Deliberation -> invoke subagent -> update CaseState
                     ^                                                   |
                     +---------------------------------------------------+
```

## Top-Level Agents

The system has exactly **four** top-level agents orchestrated by the Orchestrator:

| Concern | Owner | Contract |
|---|---|---|
| Image quality, Swin, SegFormer, CV, Grad-CAM, calibration | **Vision Agent** | validated observations and raw measurements |
| Patient history and ABCDE Evolution (E) | **Clinical Context Agent** | normalized history, evolution assessment, and missing-information questions |
| Medical sources and coverage gaps | **Evidence Agent** | untrusted evidence records and bounded sufficiency assessment |
| Output | **Report Agent** | validated JSON plus optional PDF rendering |
| Routing | **Orchestrator Agent** | selected action and concise execution trace |

```text
Orchestrator Agent
    |
    ├── Vision Agent
    │     ├── Swin Transformer — Classification  ─┐
    │     ├── SegFormer — Segmentation           ─┘  parallel
    │     └── Measurement / ABCD extraction
    │
    ├── Clinical Context Agent
    │     ├── Patient history / context intake (E criterion)
    │     └── Longitudinal evolution comparison across visits
    │
    ├── Evidence Agent
    │     └── Hybrid RAG (BGE + Qdrant + BM25 + HyDE)
    │
    └── Report Agent
```

## Clinical Context Agent

The **Clinical Context Agent** is a first-class top-level agent that owns patient
history and the ABCDE Evolution (E) criterion. It:
1. **Normalizes patient history**: records supplied clinical context (reported
   evolution, duration, symptoms) and never fabricates history from a single image.
2. **Assesses temporal evolution**: compares historical image visits to evaluate the
   E criterion and categorizes progression (`no_significant_evolution`,
   `possible_evolution`, `clear_evolution`, `unable_to_assess`).
3. **Emits missing-information questions**: when evolution/history is unavailable it
   marks E `unavailable` and raises a targeted clinical question instead of guessing.

## Evidence Agent

The Evidence Agent is the sole medical-literature entry point:
`rag_pipeline.agent.AdvancedRetrievalBackend` provides hybrid dense/BM25 retrieval,
RRF, parent expansion, cross-encoder reranking, and HyDE query support, with bounded
evidence-gap follow-up cycles.

## Measurement Safety

`CaseState.pixel_measurements` and `CaseState.physical_measurements` use
different `Measurement` objects. A physical value requires `calibrated=True`;
otherwise its value is `None` and the D feature says that physical diameter
is unavailable. Evolution is also `unavailable` until a caller supplies
clinical information.
