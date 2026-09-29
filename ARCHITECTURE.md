# CaseState Agent Architecture

`SupervisorAgent` runs a bounded decision loop. It records public operational
metadata (`agent`, `action`, `result`, `reason_category`, timestamp and small
state details), never private reasoning.

```text
observe CaseState -> choose action -> invoke one tool/agent -> update CaseState
                     ^                                           |
                     +-------------------------------------------+
```

## Top-Level Agents

The system has exactly **three** top-level agents orchestrated by the Supervisor:

| Concern | Owner | Contract |
|---|---|---|
| Image quality, Swin, SegFormer, CV, Grad-CAM, calibration | **Vision Agent** | validated observations and raw measurements |
| Medical sources and coverage gaps | **Evidence Agent** | untrusted evidence records and bounded sufficiency assessment |
| Output | **Report Agent** | validated JSON plus optional PDF rendering |
| Routing | **Supervisor Agent** | selected action and concise execution trace |

```text
Supervisor Agent
    |
    ├── Vision Agent
    │     ├── Swin Transformer — Classification  ─┐
    │     ├── SegFormer — Segmentation           ─┘  parallel
    │     └── Measurement / ABCD extraction
    │
    ├── Evidence Agent
    │     └── Hybrid RAG
    │           ├── BGE
    │           ├── Qdrant
    │           ├── BM25
    │           └── HyDE
    │
    └── Report Agent
```

## Clinical Context Handling

Clinical context (evolution history, patient-reported symptoms) is managed
as an **internal utility** of the Supervisor workflow, not a separate
top-level agent. The `clinical_context` module normalises supplied history,
populates the ABCDE "E" feature, and emits missing-information questions.
It never fabricates patient history from image data.

## Evidence Agent

The Evidence Agent is the sole retrieval entry point. Its backend is
`rag_pipeline.agent.AdvancedRetrievalBackend`; it retains hybrid dense/BM25
retrieval, RRF, parent expansion, cross-encoder reranking, and HyDE query
support. The old simple BGE/Qdrant retriever was removed.

## Measurement Safety

`CaseState.pixel_measurements` and `CaseState.physical_measurements` use
different `Measurement` objects. A physical value requires `calibrated=True`;
otherwise its value is `None` and the D feature says that physical diameter
is unavailable. Evolution is also `unavailable` until a caller supplies
clinical information.
