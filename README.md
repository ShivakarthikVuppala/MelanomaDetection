# Melanoma Detection

This project is an AI-assisted research/decision-support system. It does not
provide a definitive diagnosis and does not replace a qualified clinician.

## Architecture

![Architecture](assets/architecture.jpg)

The system is driven by a state-based Supervisor with exactly **three**
top-level agents:

1. `SupervisorAgent` observes `CaseState`, chooses an action, executes it,
   records a concise execution event, and reassesses.
2. `VisionAgent` coordinates image validation, preprocessing, SwinV2,
   SegFormer, OpenCV/scikit-image measurements, calibration, Grad-CAM, and
   the authoritative image-derived ABCD observations. Swin classification
   and SegFormer segmentation run as **parallel** branches.
3. `EvidenceAgent` is the only retrieval path. Its backend is the existing
   advanced BGE + Qdrant + BM25 + RRF + cross-encoder + parent-expansion +
   HyDE-capable retrieval stack, with bounded evidence-gap follow-up cycles.
4. `ReportAgent` creates the validated JSON report and uses the PDF renderer
   when available.

Clinical context (evolution history and patient-reported information) is
handled as an internal utility of the Supervisor workflow. It records
supplied history, asks for missing evolution/context, and never infers
patient history from a single image.

`CaseState` (`src/agents/state.py`) is the central contract. It deliberately
separates model output, raw pixel measurements, calibrated physical
measurements, supplied clinical context, untrusted evidence, uncertainty, and
the public execution trace. A pixel measurement is always `{unit: "pixels",
calibrated: false}`; no millimetre threshold is applied without valid scale
calibration.

## Flow

```text
image / supplied context -> Supervisor -> CaseState -> decide next tool
                                      -> Vision | Evidence
                                      -> Supervisor -> Report -> JSON / PDF
```

The supervisor is not a fixed phase sequence. For example, low classification
confidence requests a differential-evidence goal, unavailable evolution
creates a clinical question, and an evidence gap starts a targeted retrieval
cycle up to the configured maximum.

## Usage

```bash
python main.py orchestrate path/to/image.jpg
python main.py serve
python -m pytest -q
```

`POST /api/analyze` is the single canonical API analysis workflow. The
optional `clinical_context_json` multipart field accepts a JSON object such as
`{"evolution": {"reported_change": true, "timeframe_months": 3}}`.
Responses include `execution_trace` and `clinical_questions`; these contain
operational events only, not private chain-of-thought.

## Setup

Install dependencies with `pip install -r requirements.txt`, provide the
configured SwinV2/SegFormer checkpoints, and build the advanced RAG index via
`python main.py build-rag`. The evidence backend loads lazily, so image-only
validation does not require Qdrant or an LLM connection.
