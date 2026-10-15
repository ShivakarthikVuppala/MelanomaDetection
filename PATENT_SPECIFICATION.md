# Patent Specification

## Title
**MelaDetect: An Intelligent Agentic System and Method for Multimodal Dermoscopic Analysis, Temporal Lesion Evolution Tracking, and Explainable Clinical Evidence Synthesis**

---

## Field of the Invention
This invention relates to computer-implemented medical decision support systems, and more specifically to an intelligent, agent-driven computational platform and method for automated dermoscopic image analysis, clinical ABCDE feature extraction, cross-temporal lesion evolution modeling across sequential patient visits, multimodal risk fusion, and retrieval-augmented clinical evidence synthesis for cutaneous melanoma assessment.

---

## Background of the Invention
Cutaneous malignant melanoma represents one of the most lethal forms of skin cancer, yet its prognosis is overwhelmingly favorable when identified and excised at an early, localized stage. Clinical dermatologists evaluate skin lesions using the standardized ABCDE criteria: Asymmetry (A), Border irregularity (B), Color variegation (C), Diameter greater than 6 mm (D), and Evolution or morphological change over time (E). Among these, temporal evolution is universally recognized as the single most discriminative and sensitive clinical indicator for early melanomas that may initially mimic benign nevi.

Conventional computer-aided diagnosis (CAD) systems exhibit severe structural deficiencies. First, existing deep learning algorithms operate as static, isolated "black boxes" that process a single dermoscopic image and emit an uncalibrated classification probability without clinical grounding. They fail to decompose the lesion into interpretable morphological factors aligned with clinical dermoscopy standards. Second, conventional CAD systems treat patient evaluations as isolated snapshots, entirely lacking automated mechanisms to track, register, and compute relative morphological changes across sequential longitudinal visits. Dermatologists are thus forced to manually compare past and present photographs without quantitative progression metrics.

Furthermore, existing diagnostic vision models frequently suffer from visual attention bias, focusing on irrelevant artifacts such as surgical markings, hair, illumination gradients, or vignetting rather than the lesion margin, without possessing self-correcting cognitive loops. Traditional AI tools also fail to correlate diagnostic outputs with peer-reviewed medical literature, generating unverified outputs that cannot be safely adopted in clinical workflows. In addition, existing systems lack structured role-gated provenance capable of securely isolating patient-specific longitudinal histories under licensed medical practitioners while maintaining validation test environments.

Accordingly, there is an acute clinical need for a unified, agentic computational architecture that integrates dual-branch vision analysis, automated physical measurement calibration, cross-temporal lesion evolution comparator engines, dynamic ABCDE multimodal fusion with missing-component redistribution, and retrieval-augmented medical evidence synthesis within an authenticated, role-gated clinical provenance framework.

---

## Objects of the Invention
The primary object of this invention is to provide a unified, agentic clinical intelligence platform (MelaDetect) that supports comprehensive melanoma assessment by combining deep learning vision, quantitative ABCDE feature extraction, automated longitudinal evolution tracking across patient visits, and grounded medical literature synthesis.

Additional objects include:
- To provide a dual-branch vision processing architecture combining a hierarchical vision transformer (Swin Transformer) for deep feature classification and a semantic segmentation network (SegFormer) for precise lesion boundary delineation.
- To extract explainable morphological ABCDE clinical features including principal-axis asymmetry indices, perimeter compactness irregularity scores, color cluster entropy, and automated physical scale calibration.
- To provide an automated longitudinal evolution comparator that registers sequential image visits for a verified patient identifier, computes relative dimensional, chromatic, and structural delta vectors, and integrates progression into the composite diagnostic score.
- To incorporate a self-correcting cognitive deliberation loop wherein an orchestrator agent evaluates Grad-CAM visual attention alignment against segmented masks and triggers adaptive visual refinement when misalignments are detected.
- To provide a multimodal ABCDE fusion engine that dynamically blends raw classifier probability with clinical feature risk scores and proportionally reallocates weights when specific parameters are uncalibrated or unavailable.
- To provide a hybrid retrieval-augmented generation (RAG) assistant integrating dense vector representations, sparse lexical indexes, reciprocal rank fusion (RRF), cross-encoder reranking, and hypothetical document embeddings (HyDE) over curated medical literature.
- To establish a role-gated clinical provenance architecture wherein only authenticated medical practitioners and clinical researchers can upload patient scans using validated patient identifiers and names, with automated patient identification auto-fill and active progress tracking.
- To provide real-time patient record synchronization that renders actively running assessments in the patient's longitudinal timeline, commits successful assessments as stored records, and automatically suppresses failed evaluations from clinical records.
- To provide a distinct test credential runtime that processes patient cases through the identical agentic pipeline while isolating longitudinal priors, enabling objective calibration and model validation without historical parameter contamination.

---

## Summary of the Invention
MelaDetect is an integrated, agent-driven computational platform and method that unifies dermoscopic lesion evaluation, longitudinal patient tracking, and explainable clinical evidence generation. The system combines:

1. **Role-gated clinical input ingestion and automated patient identity resolution**, validating practitioner credentials and auto-populating patient identity records from prior encounters.
2. **A dual-branch vision pipeline** executing parallel transformer-based classification and semantic boundary segmentation, preceded by artifact and hair-removal morphological filtering.
3. **An automated clinical feature extraction module** that quantifies Asymmetry, Border irregularity, Color variegation, and Diameter with automated physical scale detection.
4. **A longitudinal evolution comparator engine** that queries all prior verified visits for the specified patient ID, performs cross-temporal registration, and computes relative growth, chromatic drift, and structural evolution vectors.
5. **A multimodal ABCDE fusion scorer** that merges deep classification probabilities with clinical feature scores via an adaptive weight redistribution mechanism.
6. **An orchestrator agent with a cognitive deliberation mind** that evaluates diagnostic sufficiency, directs targeted RAG literature retrieval over verified medical knowledge, and compiles comprehensive clinical diagnostic reports.

The platform is realized as a modular microservices architecture coordinated by an Orchestrator Agent. The client layer provides interactive clinical dashboards, responsive patient directories, and timeline visualizations. The backend application server manages session authentication, cryptographic token validation, and asynchronous orchestration. Specialized subagents—the Vision Agent, Clinical Context Agent, Evidence Agent, and Report Agent—execute bounded, validated tasks under the supervision of the Orchestrator.

The invention significantly advances the state of the art by transforming melanoma CAD from an uncalibrated, single-image prediction into a continuous, longitudinal, and explainable clinical evaluation system. It replaces isolated guesswork with quantifiable morphological tracking, protects diagnostic integrity through self-correcting attention feedback, and ensures clinical transparency through grounded citations from peer-reviewed dermatology literature. The system is designed as an assistive diagnostic support platform for medical professionals and clinical researchers.

---

## Detailed Description of the Invention

### Overall System Architecture
The system comprises the following principal functional modules and agent subsystems:

#### 1. Clinical User Interface & Longitudinal Portal Module
A responsive, secure web interface tailored for medical practitioners and clinical researchers. The portal restricts image submission to authorized practitioners, enforcing mandatory Patient ID and Patient Name attributes. When a practitioner enters a Patient ID, the client interface automatically executes client-side caching and background database lookups to auto-fill the patient's full name. The portal provides a two-column longitudinal record directory comprising a searchable patient list with risk badges and an interactive visit timeline displaying historical lesion thumbnails, confidence scores, and full diagnostic report generation.

#### 2. Application Server & Workflow Orchestration Module
A high-performance server that coordinates user authentication, session lifecycle with time-to-live indexes, and request routing. It implements the top-level Orchestrator Agent executing a bounded decision loop governed by Hybrid Guided Reasoning. The Orchestrator enforces strict Safety Prerequisite Ordering (Image Quality Validation → Dual-Branch Vision → Attention Alignment Check → Longitudinal Evolution → Multimodal ABCDE Fusion → Cognitive Deliberation → Report Generation) and maintains an immutable execution trace recording both operational actions and clinical reasoning thoughts.

#### 3. Dual-Branch Vision Agent Module
An advanced vision subsystem executing dual transformer networks in parallel. The classification branch utilizes a Swin Transformer backbone fine-tuned for dermoscopic malignancy detection, extracting hierarchical feature representations robust to scale and angle variations. The segmentation branch employs a SegFormer encoder-decoder architecture generating high-resolution binary masks separating lesion tissue from surrounding healthy skin. The Vision Agent incorporates a morphological black-hat preprocessing pipeline to remove hair occlusions and air bubbles prior to transformer inference.

#### 4. Morphological Feature Extraction & Scale Calibration Module
Extracts quantitative clinical markers conforming to the ABCDE criteria from the segmented lesion mask and raw image. Asymmetry (A) is computed by calculating the lesion's major and minor principal axes of inertia and evaluating geometric non-overlap upon 180-degree reflection. Border Irregularity (B) is quantified through perimeter compactness ratios and radial margin variance, capturing scalloped or notched contours. Color Variegation (C) applies K-means clustering across CIE Lab color space to quantify entropy across six dermatological pigment bands (light brown, dark brown, black, red, white, blue-gray). Diameter (D) employs an automated scale reference detector identifying metric rulers or standard coins within the field of view; if calibrated, it outputs physical millimeter measurements, and if uncalibrated, it explicitly tracks uncertainty without fabricating scale.

#### 5. Clinical Context Agent & Longitudinal Evolution Comparator Module
A dedicated first-class Clinical Context Agent that owns patient-reported history and evaluates the 'E' (Evolution) factor across sequential patient encounters through a temporal comparator. Upon receiving a scan under a patient identifier, the agent queries the database for all previous valid visits associated with that patient. It executes image registration, aligns lesion contours across time intervals, and calculates relative percentage changes in surface area, maximum diameter delta, border irregularity drift, and color shift vectors. The agent computes an evolution confidence score and categorizes progression into distinct clinical states (`no_significant_evolution`, `possible_evolution`, `clear_evolution`), providing the strongest discriminative weight in early melanoma detection. When no prior history is available, it marks Evolution unavailable and raises a targeted clinical question rather than inferring history from a single image.

#### 6. Grad-CAM Visual Attention Refinement Subsystem
A self-correcting visual verification loop. The system computes Gradient-weighted Class Activation Mapping (Grad-CAM) heatmaps from the final convolutional/transformer layer of the classifier. The Orchestrator evaluates the spatial overlap between the high-attention activation regions and the segmented lesion mask. If the visual focus deviates materially toward image borders, ruler artifacts, or skin creases (Grad-CAM misalignment), the Orchestrator triggers an adaptive refinement action (`refine_and_reclassify`) that re-crops, re-normalizes, and re-infers the lesion, suppressing artifact-induced false positives.

#### 7. Multimodal ABCDE Fusion Engine
A mathematically grounded fusion engine that synthesizes the deep classification probability and individual ABCDE feature metrics into a composite risk score [0, 1]. The base weighting allocates: Classifier = 0.60, Evolution (E) = 0.15, Asymmetry (A) = 0.08, Border Irregularity (B) = 0.07, Color Variegation (C) = 0.06, and Diameter (D) = 0.04. Each raw feature is normalized via clinical thresholds using linear ramps and step functions. Crucially, when any feature is uncalibrated or unavailable (e.g. baseline visit lacking prior evolution data, or absence of physical scale), the engine executes proportional weight redistribution across all active parameters, ensuring the weights always sum to exactly 1.0 while preserving standalone classifier fidelity in the worst-case boundary.

#### 8. Evidence Agent & Hybrid RAG Microservice
A clinical evidence retrieval engine operating over a curated repository of peer-reviewed dermatology literature, clinical practice guidelines, and histopathological studies. The subsystem executes a multi-stage hybrid search:
1. Dense semantic embedding search using BAAI/bge-large-en-v1.5 and a Qdrant vector database;
2. Sparse lexical keyword retrieval using BM25;
3. Reciprocal Rank Fusion (RRF) to merge dense and sparse candidate rankings;
4. Cross-encoder reranking to isolate the top clinical passages; and
5. Hypothetical Document Embeddings (HyDE) expansion for ambiguous clinical presentations.
The cognitive orchestrator queries this service to validate diagnostic ambiguities and embed factual literature citations directly into the clinical explanation.

#### 9. Explainable Clinical Report Generation Module
Synthesizes the complete diagnostic trajectory into validated JSON and structured, downloadable clinical PDF reports. The report incorporates original and preprocessed lesion imagery, segmentation contour overlays, Grad-CAM attention heatmaps, decomposed ABCDE numerical feature cards, longitudinal evolution progression graphs, literature citations, and tailored clinical follow-up questions for practitioner review.

### Integration and Orchestration
The Orchestrator Agent coordinates all subagent invocations through an asynchronous threadpool. When an upload request arrives at the API endpoint, the Orchestrator validates practitioner JWT claims, verifies image integrity, and records an in-progress record in the database. As the case progresses, the Orchestrator updates the CaseState data structure, recording intermediate measurement objects, Grad-CAM attention metrics, and cognitive thoughts. Subagent responses are strictly validated against Pydantic schemas before state ingestion, preventing data corruption or pipeline divergence.

### Data Handling, Provenance, and Privacy Controls
All patient lesion imagery and clinical context records are strictly partitioned by authenticated practitioner user IDs and patient identifiers. Image files are stored with cryptographically generated unique identifiers, and access is restricted via authorization middleware. The system enforces zero data leakage: patient identifiers are scrubbed from literature queries sent to the RAG service, and all external vector searches operate purely on clinical feature tokens.

### Real-Time Record State Synchronization and Failure Suppression
The system incorporates an active status synchronization mechanism. When an analysis is initiated, the platform immediately publishes a "running" status state accessible via the Patient Records interface. In the patient's record timeline, an active assessment card renders real-time progress indicators, thumbnail previews, and pipeline state. Upon successful conclusion, the record automatically transitions into a permanent "stored record". If the analysis fails due to insufficient image quality or pipeline exception, the system automatically purges the temporary record and filters it out from patient history queries, ensuring that patient medical records remain pristine and devoid of corrupted entries.

### Isolated Test Runtime Calibration Mode
To enable rigorous clinical validation, model benchmarking, and audit without historical bias, the invention includes a dedicated test account runtime. When an authenticated account flagged with the test credential attribute submits a case, the application server dynamically suppresses all longitudinal baseline injections (forcing historical image paths to empty). The system otherwise executes the identical dual-branch vision, feature extraction, fusion, and report generation workflows, permitting medical auditors to assess baseline classification performance in complete isolation.

---

## Drawings

```
[INSERT FIGURE 1: OVERALL SYSTEM ARCHITECTURE DIAGRAM HERE]
```
**Figure 1: Overall System Architecture Diagram**
Depicts the clinical client portal communicating with the Application Server and Orchestrator Agent, which coordinates the Vision Agent (Swin Transformer and SegFormer), Clinical Context Agent (Longitudinal Evolution Comparator), Evidence Agent (Hybrid RAG), Report Agent, and MongoDB persistent storage partitioned by practitioner and patient identifiers.

```
[INSERT FIGURE 2: MULTI-AGENT WORKFLOW AND COGNITIVE DELIBERATION PIPELINE HERE]
```
**Figure 2: Multi-Agent Workflow and Cognitive Deliberation Pipeline**
Illustrates the sequential state progression from image ingestion, quality gating, parallel vision inference, attention validation, longitudinal history injection, multimodal fusion, and cognitive deliberation loop to final report synthesis.

```
[INSERT FIGURE 3: DUAL-BRANCH VISION AND GRAD-CAM ATTENTION REFINEMENT LOOP HERE]
```
**Figure 3: Dual-Branch Vision and Grad-CAM Attention Refinement Loop**
Shows the parallel execution of the Swin Transformer classification branch and SegFormer segmentation branch, followed by morphological ABCDE calculation and the Grad-CAM alignment evaluation triggering adaptive visual re-classification.

```
[INSERT FIGURE 4: LONGITUDINAL EVOLUTION (E) COMPARATOR AND TEMPORAL ALIGNMENT FLOW HERE]
```
**Figure 4: Longitudinal Evolution (E) Comparator and Temporal Alignment Flow**
Illustrates cross-temporal registration between baseline visits (Visit T-0, Visit T-1) and the current follow-up (Visit T-N), detailing the extraction of area growth deltas, diameter progression rates, chromatic shift vectors, and evolution status mapping.

```
[INSERT FIGURE 5: MULTIMODAL ABCDE FUSION ARCHITECTURE WITH DYNAMIC WEIGHT REDISTRIBUTION HERE]
```
**Figure 5: Multimodal ABCDE Fusion Architecture with Dynamic Weight Redistribution**
Details the mathematical combination of classifier probability (0.60) and clinical ABCDE feature scores (0.40 total), illustrating proportional weight reallocation when individual features (such as physical scale or temporal priors) are absent.

```
[INSERT FIGURE 6: HYBRID RAG EVIDENCE RETRIEVAL AND REAL-TIME RECORD STATE SYNCHRONIZATION HERE]
```
**Figure 6: Hybrid RAG Evidence Retrieval and Real-Time Record State Synchronization**
Depicts dense vector search combined with sparse BM25 retrieval, RRF ranking, cross-encoder reranking, and the patient record lifecycle transitioning from 'running' to 'stored record' while purging failed evaluations.

---

## Abstract
This patent presents MelaDetect, an integrated agentic computational system and method for multimodal dermoscopic analysis, longitudinal lesion evolution assessment, and explainable clinical evidence synthesis for cutaneous melanoma. The system incorporates a dual-branch vision pipeline comprising parallel transformer-based classification and semantic boundary segmentation networks, automated extraction of standardized ABCDE clinical features, and an automated longitudinal evolution comparator that registers and evaluates morphological changes across sequential patient encounters. An orchestrator agent coordinates diagnostic execution through a cognitive deliberation loop, verifying Grad-CAM visual attention alignment and querying a hybrid retrieval-augmented generation (RAG) knowledge engine over peer-reviewed medical literature. A multimodal fusion scorer dynamically blends deep classification probabilities with clinical feature scores, adaptively reallocating weights when components are uncalibrated. The system provides role-gated clinical provenance for practitioners, real-time active assessment tracking in patient timelines, automatic suppression of failed evaluations, and isolated test runtimes for unbiased calibration. The platform provides transparent, grounded, and longitudinal decision support for clinical dermatology.

---

## Claims
We claim:

1. **An intelligent computational system for multimodal dermoscopic lesion analysis and longitudinal tracking, comprising:**
   - a client computing interface configured to authenticate medical practitioners and accept dermoscopic lesion images associated with a patient identifier and patient name;
   - a database storing structured patient records, historical lesion imagery, and diagnostic trajectories partitioned by practitioner and patient identifiers;
   - an application server executing an orchestrator agent configured to coordinate diagnostic workflows across specialized subagents;
   - a dual-branch vision subsystem executing in parallel a hierarchical vision transformer for malignancy classification and a semantic segmentation transformer for lesion boundary delineation;
   - a morphological feature extraction module configured to quantify clinical Asymmetry, Border irregularity, Color variegation, and Diameter metrics from said segmentation mask and lesion image;
   - a longitudinal evolution comparator configured to retrieve prior lesion records matching said patient identifier, register sequential lesion images across time intervals, and compute cross-temporal growth, chromatic drift, and morphological evolution vectors;
   - a multimodal fusion engine configured to compute a composite malignancy score by combining classification probabilities with clinical feature scores using an adaptive weight redistribution mechanism; and
   - a report generation module configured to compile an explainable clinical report incorporating segmented overlays, feature metrics, longitudinal progression data, and factual medical literature citations.

2. **The system of claim 1**, wherein said orchestrator agent executes a cognitive deliberation loop governed by safety prerequisite ordering, verifying image quality prior to vision inference and evaluating spatial alignment between classifier Grad-CAM attention heatmaps and the segmented lesion mask to trigger adaptive visual re-classification upon detecting artifact misalignment.

3. **The system of claim 1**, wherein said morphological feature extraction module comprises an automated scale calibration detector that identifies physical reference objects within the field of view to compute physical millimeter diameter, and wherein uncertainty tracking suppresses physical diameter calculation when scale references are absent.

4. **The system of claim 1**, wherein said longitudinal evolution comparator calculates surface area delta percentage, maximum diameter change rate, and border scalloping degradation over calculated visit intervals, mapping said vectors into discrete evolution status categories comprising no significant evolution, possible evolution, and clear evolution.

5. **The system of claim 1**, wherein said multimodal fusion engine allocates base weights of approximately 0.60 to the vision classifier, 0.15 to evolution, 0.08 to asymmetry, 0.07 to border irregularity, 0.06 to color variegation, and 0.04 to diameter, and wherein the weight of any uncalibrated or unavailable parameter is proportionally redistributed to all active parameters such that total weight strictly equals 1.0.

6. **The system of claim 1**, further comprising a hybrid retrieval-augmented generation (RAG) evidence module integrating dense vector embeddings, sparse lexical indexes, reciprocal rank fusion, and cross-encoder reranking over curated peer-reviewed dermatology sources to validate diagnostic uncertainties and supply grounded literature citations.

7. **The system of claim 1**, wherein said client interface automatically queries said database upon practitioner entry of a patient identifier to auto-fill the associated patient name, and displays a searchable patient directory linked to a chronological visit timeline.

8. **The system of claim 1**, wherein said application server records an in-progress status upon image submission, causing said client interface to render an active running assessment card within the patient's record timeline displaying live pipeline state, and wherein said active assessment card seamlessly transitions into a permanent stored record upon successful completion.

9. **The system of claim 8**, wherein if an analysis fails due to image quality insufficiency or execution error, the application server automatically purges the temporary record and suppresses failed entries from patient history queries, preserving medical record integrity.

10. **The system of claim 1**, further comprising an isolated test runtime configured to execute the identical dual-branch vision, feature extraction, fusion, and reporting pipelines for test accounts while strictly suppressing longitudinal baseline image injection, enabling unbiased model calibration and clinical auditing.

11. **A computer-implemented method for multimodal dermoscopic lesion assessment and longitudinal tracking, comprising:**
    - authenticating a medical practitioner and receiving a dermoscopic lesion image associated with a patient identifier;
    - querying a database using said patient identifier to retrieve all prior chronological lesion scans associated with the patient;
    - processing the received image in parallel through a vision transformer classifier to compute a malignancy probability and a semantic segmentation transformer to delineate a lesion boundary mask;
    - extracting quantitative Asymmetry, Border irregularity, Color variegation, and Diameter (ABCD) morphological measurements from said mask and image;
    - registering said prior chronological lesion scans against the received image to calculate cross-temporal dimensional deltas and color shift vectors representing longitudinal Evolution (E);
    - synthesizing the classification probability and ABCDE feature metrics into a composite risk score via an adaptive fusion model that proportionally redistributes weights when parameters are uncalibrated; and
    - generating an explainable clinical diagnostic report with visual overlays, longitudinal progression metrics, and literature citations.

12. **The method of claim 11**, further comprising evaluating Grad-CAM visual attention activation against the segmented boundary mask and automatically triggering an adaptive re-cropping and re-classification action when activation focus falls outside the lesion contour.

13. **The method of claim 11**, further comprising rendering a real-time running indicator in the patient's record timeline while the diagnostic workflow executes, committing the record upon successful completion, and automatically deleting the temporary record if the evaluation encounters an error.

14. **The method of claim 11**, further comprising identifying test account credentials and selectively bypassing temporal registration to evaluate pure baseline diagnostic inference without historical parameter contamination.

15. **A non-transitory computer-readable storage medium** comprising instructions that, when executed by one or more processors, cause the processors to execute the multimodal dermoscopic analysis and longitudinal tracking method of claim 11.
