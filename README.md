# Melanoma Detection

An agentic, retrieval-augmented framework for explainable melanoma analysis from dermoscopic images and supplied clinical context.

> **Disclaimer:** This is an AI-assisted research and decision-support system. It does **not** provide a definitive diagnosis and does not replace a qualified clinician. Do not use it for clinical decisions.

---

## Architecture

![Architecture](assets/architecture.png)

A state-based **Orchestrator** drives three specialist agents through a shared `CaseState`.

| Component | Role |
|---|---|
| `OrchestratorAgent` | Observes `CaseState`, chooses the next action, executes it, records a concise execution event, and reassesses until complete |
| `VisionAgent` | Image validation, preprocessing, SwinV2 classification, SegFormer segmentation, OpenCV/scikit-image measurements, calibration, Grad-CAM, and the authoritative image-derived ABCD observations. Classification and segmentation run as **parallel** branches |
| `EvidenceAgent` | The only retrieval path. BGE embeddings + Qdrant + BM25 + RRF fusion + cross-encoder reranking + parent expansion + HyDE-capable queries, with bounded evidence-gap follow-up cycles |
| `ReportAgent` | Synthesizes results, explanation, and uncertainty into a validated JSON report, and renders a PDF when available |

**Clinical context** (evolution history and patient-reported information) is an internal utility of the Orchestrator workflow, not a separate agent. It records supplied history, asks for missing evolution/context, and never infers patient history from a single image.

### Flow

```text
image / supplied context -> Orchestrator -> CaseState -> decide next tool
                                         -> Vision | Evidence
                                         -> Orchestrator -> Report -> JSON / PDF
```

The Orchestrator is not a fixed phase sequence. Examples:

- Low classification confidence → requests a differential-evidence goal
- Evolution unavailable → raises a clinical question
- Evidence gap → targeted retrieval cycle, up to the configured maximum

### CaseState

`CaseState` (`src/agents/state.py`) is the central contract. It deliberately separates:

- model outputs
- raw pixel measurements
- calibrated physical measurements
- supplied clinical context
- untrusted retrieved evidence
- uncertainty
- the public execution trace

Pixel measurements are always `{unit: "pixels", calibrated: false}`. No millimetre threshold (e.g. the ABCD "D > 6 mm" criterion) is applied without valid scale calibration.

---

## Features

- Parallel SwinV2 classification and SegFormer segmentation
- Grad-CAM visual explanations
- Automated ABCD feature extraction (Asymmetry, Border, Color, Diameter), with Evolution supplied as clinical context
- Hybrid RAG over medical literature with reranking and gap-driven re-retrieval
- Uncertainty-aware reporting and explicit missing-information questions
- Validated JSON output and optional PDF report
- Operational execution trace (events only, no private chain-of-thought)
- Lazy evidence backend: image-only validation needs no Qdrant or LLM connection

---

## Project Structure

```text
.
├── main.py                 # CLI entry point
├── requirements.txt
├── assets/
│   └── architecture.png
├── src/
│   ├── agents/
│   │   ├── state.py        # CaseState contract
│   │   ├── orchestrator.py # OrchestratorAgent
│   │   ├── vision.py       # VisionAgent
│   │   ├── evidence.py     # EvidenceAgent
│   │   └── report.py       # ReportAgent
│   └── ...                 # TODO: adjust to your actual layout
└── tests/
```

> TODO: replace the tree above with the output of `tree -L 3` from your repo.

---

## Setup

```bash
git clone https://github.com/ShivakarthikVuppala/MelanomaDetection.git
cd MelanomaDetection
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Required before running:**

1. **Model checkpoints:** place the SwinV2 classifier and SegFormer segmentation checkpoints at the paths set in your config. TODO: add paths or download links.
2. **RAG index:** build it once with:
```bash
   python main.py build-rag
```
3. **Environment:** TODO: list required variables (e.g. Qdrant URL, LLM provider/API key). Image-only validation works without them.

---

## Usage

### CLI

```bash
python main.py orchestrate path/to/image.jpg   # run the full agent workflow
python main.py serve                           # start the API server
python -m pytest -q                            # run tests
```

### API

`POST /api/analyze` is the single canonical analysis endpoint (multipart form).

| Field | Required | Description |
|---|---|---|
| `image` | yes | Dermoscopic image (TODO: confirm field name) |
| `clinical_context_json` | no | JSON object with supplied clinical context |

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "image=@path/to/image.jpg" \
  -F 'clinical_context_json={"evolution": {"reported_change": true, "timeframe_months": 3}}'
```

> TODO: confirm host/port and field names against your FastAPI app.

**Response includes:**

- the validated report (classification, segmentation, measurements, ABCD observations, evidence references, explanation, uncertainty)
- `execution_trace`: operational events only
- `clinical_questions`: missing information the user should supply

---

## Data and Models

| Component | Detail |
|---|---|
| Classifier | SwinV2 (TODO: variant, input size) |
| Segmentation | SegFormer (TODO: variant) |
| Training data | TODO: e.g. ISIC 2018 / ISIC 2020, with split details |
| Retrieval | BGE embeddings, Qdrant, BM25, RRF, cross-encoder reranker |

### Results

> TODO: add held-out test metrics (AUC, sensitivity, specificity) with dataset and split. Report specificity alongside accuracy; melanoma data is heavily imbalanced.

---

## Limitations

- Not validated for clinical use; research only
- Performance depends on image quality and on whether the image resembles the training distribution
- Pixel measurements are uncalibrated unless a valid scale is provided
- Retrieved evidence is treated as untrusted and may be incomplete
- Evolution and history come only from user-supplied context, never from the image

---

## Contributing

Issues and pull requests are welcome. Please run `python -m pytest -q` before submitting.

## License

TODO: add a license (e.g. MIT) and a `LICENSE` file.

## Acknowledgements

ISIC Archive, Hugging Face Transformers, Qdrant, and the authors of SwinV2 and SegFormer. TODO: add your mentor/institution if desired.