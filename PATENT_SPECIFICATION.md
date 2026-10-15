# Patent Specification

## Title
**MelaDetect: An Intelligent Agentic System and Method for Multimodal Dermoscopic Risk Evaluation, Longitudinal Lesion Feature Progression Tracking, and Explainable Clinical Decision Support**

---

## Notice of Clinical Decision Support Framing
> **Regulatory and Operational Statement:** The system and methods described herein constitute an artificial intelligence-assisted clinical decision-support and risk-stratification platform. The system is designed strictly to assist qualified medical practitioners and dermatological researchers by providing quantitative image measurements, literature references, and risk indicators. The system does not provide an autonomous medical diagnosis, does not establish a definitive medical condition, and does not replace the professional clinical judgment of a licensed healthcare provider.

---

## Field of the Invention
This invention relates to computer-implemented clinical decision-support systems, and more specifically to an intelligent, agent-driven computational platform and method for automated dermoscopic image analysis, quantitative ABCDE morphological feature extraction, cross-temporal lesion feature progression tracking across sequential patient visits, multimodal risk fusion with dynamic weight reallocation, and retrieval-augmented clinical evidence synthesis for cutaneous melanoma risk assessment.

---

## Background of the Invention
Cutaneous malignant melanoma represents one of the most serious forms of skin neoplasm, where prognosis is substantially improved when suspicious lesions are identified and clinically evaluated at an early, localized stage. Clinical dermatologists evaluate pigmented skin lesions using the standardized ABCDE criteria: Asymmetry (A), Border irregularity (B), Color variegation (C), Diameter (D), and Evolution or morphological change over time (E). Among these, temporal evolution is widely recognized as a highly discriminative clinical indicator for early-stage melanomas that may initially present with subtle morphological characteristics.

Conventional computer-aided decision-support tools exhibit several practical limitations:
1. Conventional deep learning classifiers operate as single-image, black-box probability estimators. They output an isolated score without decomposing the lesion into interpretable morphological factors aligned with clinical dermatological standards.
2. Existing automated tools typically evaluate dermoscopic images as isolated, single-timepoint snapshots. They lack structured mechanisms to associate sequential encounters with a validated patient identifier and quantitatively evaluate progression in dimensional, border, and chromatic metrics across follow-up visits. Clinicians are therefore left to manually cross-reference historical photographs without quantitative delta metrics.
3. Deep learning vision models can be susceptible to visual attention shortcuts, focusing on extraneous background artifacts such as skin markings, hair, illumination gradients, or vignetting rather than the true lesion boundary. Existing workflows often lack self-evaluating loops that assess whether visual attention maps align with segmented lesion boundaries before accepting predictions.
4. Conventional machine learning classifiers do not ground their outputs in peer-reviewed clinical literature or medical practice guidelines, offering no contextual citations to assist practitioners in reviewing atypical presentations or differential considerations.
5. In clinical research environments, systems often fail to provide isolated calibration runtimes that allow model validation without contamination from patient historical priors.

Accordingly, there is an acute clinical need for a unified, agentic computational architecture that combines dual-branch transformer vision, quantitative morphological feature extraction, cross-temporal lesion feature comparison across patient visits, dynamic multimodal fusion with adaptive weight redistribution, and retrieval-augmented medical evidence synthesis within an authenticated, role-gated clinical provenance framework.

---

## Objects of the Invention
The primary object of this invention is to provide a unified, agentic clinical intelligence platform (MelaDetect) that supports comprehensive melanoma risk evaluation by combining deep learning vision, quantitative ABCDE morphological feature extraction, automated longitudinal feature progression tracking across patient visits, and grounded medical literature synthesis as an assistive clinical decision-support tool.

Additional objects include:
- To provide a dual-branch vision processing architecture combining a hierarchical vision transformer (Swin Transformer V2) for deep feature classification and a semantic segmentation transformer (SegFormer) for lesion boundary delineation.
- To extract explainable morphological ABCDE clinical features including principal-axis asymmetry indices, perimeter compactness irregularity scores, color cluster entropy, and automated physical scale detection.
- To provide an automated longitudinal feature comparator that associates sequential image visits with a verified patient identifier, computes relative dimensional, chromatic, and morphological delta metrics, and integrates progression into a composite risk evaluation.
- To incorporate an attention verification loop wherein an orchestrator agent evaluates Grad-CAM visual attention alignment against segmented masks and triggers adaptive visual re-cropping and re-classification when misalignments are detected.
- To provide a multimodal ABCDE fusion engine that dynamically blends raw classifier probability with clinical feature risk scores and proportionally reallocates weights when specific parameters are uncalibrated or unavailable.
- To provide a hybrid retrieval-augmented generation (RAG) assistant integrating dense vector representations, sparse lexical indexes, reciprocal rank fusion (RRF), cross-encoder reranking, and hypothetical document embeddings (HyDE) over curated medical literature.
- To establish a role-gated clinical provenance architecture wherein only authenticated medical practitioners and clinical researchers can upload patient scans using validated patient identifiers and names, with automated patient identification lookup and active progress tracking.
- To provide real-time patient record synchronization that renders actively running assessments in the patient's longitudinal timeline, commits successful assessments as stored records, and automatically purges failed evaluations from clinical records.
- To provide a distinct test credential runtime that processes patient cases through the identical agentic pipeline while isolating longitudinal priors, enabling objective calibration and model validation without historical parameter contamination.

---

## Summary of the Invention
MelaDetect is an integrated, agent-driven computational platform and method that unifies dermoscopic lesion evaluation, longitudinal patient tracking, and explainable clinical evidence generation for assistive decision support. The system comprises:

1. **Role-gated clinical input ingestion and automated patient identity resolution**, validating practitioner credentials via token-based authentication and auto-populating patient identity records from prior encounters.
2. **A dual-branch vision pipeline** executing parallel transformer-based classification and semantic boundary segmentation, preceded by artifact and hair-removal morphological filtering.
3. **An automated clinical feature extraction module** that quantifies Asymmetry, Border irregularity, Color variegation, and Diameter with automated physical scale reference detection.
4. **A longitudinal feature comparator engine** that queries prior verified visits for the specified patient identifier and computes relative growth, chromatic drift, and morphological evolution metrics across encounters.
5. **A multimodal ABCDE fusion scorer** that merges deep classification probabilities with clinical feature scores via an adaptive weight redistribution mechanism.
6. **An orchestrator agent with a cognitive deliberation mind** that evaluates analytical and evidence sufficiency, directs targeted RAG literature retrieval over verified medical knowledge, and compiles comprehensive clinical decision-support reports.

The platform is realized as a modular microservices architecture coordinated by an Orchestrator Agent. The client layer provides interactive clinical dashboards, responsive patient directories, and timeline visualizations. The backend application server manages session authentication and asynchronous orchestration. Specialized subagents—the Vision Agent, Clinical Context Agent, Evidence Agent, and Report Agent—execute bounded, validated tasks under the supervision of the Orchestrator.

---

## Detailed Description of the Invention

### Overall System Architecture
The system comprises the following principal functional modules and agent subsystems:

#### 1. Clinical User Interface & Longitudinal Portal Module
A responsive, secure web interface tailored for medical practitioners and clinical researchers. The portal restricts image submission to authorized practitioners, enforcing mandatory Patient ID and Patient Name attributes. When a practitioner enters a Patient ID, the client interface queries the database to auto-fill the patient's full name. The portal provides a two-column longitudinal record directory comprising a searchable patient list with risk badges and an interactive visit timeline displaying historical lesion thumbnails, confidence scores, and report generation options.

#### 2. Application Server & Workflow Orchestration Module
A server that coordinates user authentication, session lifecycle, and request routing. It implements the top-level Orchestrator Agent executing a bounded decision loop governed by Hybrid Guided Reasoning. The Orchestrator enforces strict Safety Prerequisite Ordering (Image Quality Validation → Dual-Branch Vision → Attention Alignment Check → Longitudinal Evolution → Multimodal ABCDE Fusion → Cognitive Deliberation → Report Generation) and maintains an immutable execution trace recording both operational actions and clinical reasoning thoughts.

#### 3. Dual-Branch Vision Agent Module
A vision subsystem executing dual transformer networks in parallel:
- The classification branch utilizes a Swin Transformer V2 backbone (`swinv2_base_window12to16_192to256`) fine-tuned for dermoscopic lesion categorization, extracting hierarchical feature representations.
- The segmentation branch employs a SegFormer encoder-decoder architecture (`mit_b2`) generating high-resolution binary masks separating lesion tissue from surrounding healthy skin.
- A morphological black-hat preprocessing pipeline removes hair occlusions prior to transformer inference.

#### 4. Morphological Feature Extraction & Scale Calibration Module
Extracts quantitative clinical markers conforming to the ABCDE criteria from the segmented lesion mask and raw image:
- **Asymmetry (A):** Computed by calculating the lesion's major and minor principal axes of inertia and evaluating geometric non-overlap upon 180-degree reflection.
- **Border Irregularity (B):** Quantified through perimeter compactness ratios and radial margin variance, capturing scalloped or notched contours.
- **Color Variegation (C):** Applies K-means clustering across CIE Lab color space to quantify entropy across dermatological pigment bands (light brown, dark brown, black, red, white, blue-gray).
- **Diameter (D):** Employs an automated scale reference detector identifying metric markers; if calibrated, it outputs physical millimeter measurements, and if uncalibrated, it explicitly tracks uncertainty without fabricating physical scale.

#### 5. Clinical Context Agent & Longitudinal Feature Comparator Module
A dedicated Clinical Context Agent that manages patient-reported history and evaluates the 'E' (Evolution) factor across sequential patient encounters. Upon receiving a scan associated with a patient identifier, the agent queries the database for previous valid visits associated with that patient. It extracts quantitative morphological metrics (surface area, maximum diameter, border scalloping, and color distribution) for each visit, computes relative percentage changes across time intervals, and maps progression into discrete clinical categories (`no_significant_evolution`, `possible_evolution`, `clear_evolution`). The comparator operates on extracted quantitative feature vectors and comparative clinical review rather than automated spatial image warping. When no prior history is available, it marks Evolution unavailable and raises a targeted clinical question rather than inferring history from a single image.

#### 6. Grad-CAM Visual Attention Refinement Subsystem
A visual verification loop. The system computes Gradient-weighted Class Activation Mapping (Grad-CAM) heatmaps from the classifier. The Orchestrator evaluates the spatial overlap between the high-attention activation regions and the segmented lesion mask via an Attention Inside Lesion (AIL) metric. If visual attention deviates materially toward image borders or background artifacts, the Orchestrator triggers an adaptive refinement action (`refine_and_reclassify`) that re-crops, re-normalizes, and re-infers the lesion.

#### 7. Multimodal ABCDE Fusion Engine
A mathematically grounded fusion engine that synthesizes the deep classification probability and individual ABCDE feature metrics into a composite risk score [0, 1]. The base weighting allocates: Classifier = 0.60, Evolution (E) = 0.15, Asymmetry (A) = 0.08, Border Irregularity (B) = 0.07, Color Variegation (C) = 0.06, and Diameter (D) = 0.04. Each raw feature is normalized via clinical thresholds. When any feature is uncalibrated or unavailable (e.g., baseline visit lacking prior evolution data, or absence of physical scale), the engine executes proportional weight redistribution across all active parameters, ensuring the weights always sum to exactly 1.0 while preserving standalone classifier fidelity in the worst-case boundary.

#### 8. Evidence Agent & Hybrid RAG Microservice
A clinical evidence retrieval engine operating over a curated repository of peer-reviewed dermatology literature, clinical practice guidelines, and studies. The subsystem executes a multi-stage hybrid search:
1. Dense semantic embedding search using `BAAI/bge-large-en-v1.5` and a Qdrant vector database;
2. Sparse lexical keyword retrieval using BM25;
3. Reciprocal Rank Fusion (RRF) to merge dense and sparse candidate rankings;
4. Cross-encoder reranking to isolate top clinical passages; and
5. Hypothetical Document Embeddings (HyDE) expansion for ambiguous clinical presentations.
The cognitive orchestrator queries this service to retrieve relevant literature passages and embed citations directly into the clinical explanation.

#### 9. Explainable Clinical Report Generation Module
Synthesizes the complete analytical trajectory into validated JSON and structured, downloadable clinical PDF reports. The report incorporates original and preprocessed lesion imagery, segmentation contour overlays, Grad-CAM attention heatmaps, decomposed ABCDE numerical feature cards, longitudinal progression metrics, literature citations, and tailored clinical follow-up questions for practitioner review.

### Integration and Orchestration
The Orchestrator Agent coordinates all subagent invocations through an asynchronous threadpool. When an upload request arrives at the API endpoint, the Orchestrator validates practitioner credentials, verifies image integrity, and records an in-progress record in the database. As the case progresses, the Orchestrator updates the CaseState data structure, recording intermediate measurement objects, Grad-CAM attention metrics, and cognitive thoughts. Subagent responses are strictly validated against schemas before state ingestion, preventing pipeline divergence.

### Data Handling and Role-Based Access Controls
All patient lesion imagery and clinical context records are partitioned by practitioner user accounts and patient identifiers. Access is restricted via role-based authorization middleware, limiting image submission to verified practitioner and researcher roles.

### Real-Time Record State Synchronization and Failure Suppression
The system incorporates an active status synchronization mechanism. When an analysis is initiated, the platform publishes a "running" status state accessible via the Patient Records interface. In the patient's record timeline, an active assessment card renders real-time progress indicators, thumbnail previews, and pipeline state. Upon successful conclusion, the record automatically transitions into a permanent stored record. If the analysis encounters an unrecoverable failure due to insufficient image quality or pipeline exception, the system automatically purges the temporary record and filters it out from patient history queries, preserving medical record integrity.

### Isolated Test Runtime Calibration Mode
To enable clinical validation, model benchmarking, and audit without historical bias, the platform includes a dedicated test account runtime. When an authenticated account flagged with the test credential attribute submits a case, the application server dynamically suppresses longitudinal baseline injections (forcing historical image paths to empty). The system otherwise executes the identical dual-branch vision, feature extraction, fusion, and report generation workflows, permitting evaluators to assess baseline classification performance in complete isolation.

---

## Drawings

```
[INSERT FIGURE 1: OVERALL SYSTEM ARCHITECTURE DIAGRAM HERE]
```
**Figure 1: Overall System Architecture Diagram**
Depicts the clinical client portal communicating with the Application Server and Orchestrator Agent, which coordinates the Vision Agent (Swin Transformer and SegFormer), Clinical Context Agent (Longitudinal Feature Comparator), Evidence Agent (Hybrid RAG), Report Agent, and database storage partitioned by practitioner and patient identifiers.

```
[INSERT FIGURE 2: MULTI-AGENT WORKFLOW AND COGNITIVE DELIBERATION PIPELINE HERE]
```
**Figure 2: Multi-Agent Workflow and Cognitive Deliberation Pipeline**
Illustrates the sequential state progression from image ingestion, quality gating, parallel vision inference, attention validation, longitudinal history injection, multimodal fusion, and cognitive deliberation loop to final report synthesis.

```
[INSERT FIGURE 3: DUAL-BRANCH VISION AND GRAD-CAM ATTENTION REFINEMENT LOOP HERE]
```
**Figure 3: Dual-Branch Vision and Grad-CAM Attention Refinement Loop**
Shows the parallel execution of the Swin Transformer classification branch and SegFormer segmentation branch, followed by morphological ABCDE calculation and the Grad-CAM alignment evaluation triggering adaptive visual re-cropping and re-classification.

```
[INSERT FIGURE 4: LONGITUDINAL FEATURE PROGRESSION COMPARATOR FLOW HERE]
```
**Figure 4: Longitudinal Feature Progression Comparator Flow**
Illustrates chronological comparison between prior visits (Visit T-0, Visit T-1) and the current follow-up (Visit T-N), detailing the extraction of surface area deltas, diameter progression rates, color shifts, and evolution status categorization.

```
[INSERT FIGURE 5: MULTIMODAL ABCDE FUSION ARCHITECTURE WITH DYNAMIC WEIGHT REDISTRIBUTION HERE]
```
**Figure 5: Multimodal ABCDE Fusion Architecture with Dynamic Weight Redistribution**
Details the combination of classifier probability (0.60) and clinical ABCDE feature scores (0.40 total), illustrating proportional weight reallocation when individual features (such as physical scale or temporal priors) are absent.

```
[INSERT FIGURE 6: HYBRID RAG EVIDENCE RETRIEVAL AND REAL-TIME RECORD STATE SYNCHRONIZATION HERE]
```
**Figure 6: Hybrid RAG Evidence Retrieval and Real-Time Record State Synchronization**
Depicts dense vector search combined with sparse BM25 retrieval, RRF ranking, cross-encoder reranking, and the patient record lifecycle transitioning from 'running' to 'stored record' while purging failed evaluations.

---

## Abstract
An integrated agentic computational system and method for multimodal dermoscopic lesion risk evaluation, longitudinal feature progression tracking, and explainable clinical decision support. The system incorporates a dual-branch vision pipeline comprising parallel transformer-based classification and semantic boundary segmentation networks, automated extraction of quantitative ABCDE morphological features, and a longitudinal feature comparator that evaluates morphological parameter changes across sequential patient encounters. An orchestrator agent coordinates evaluation execution through a cognitive deliberation loop, verifying Grad-CAM visual attention alignment and querying a hybrid retrieval-augmented generation (RAG) knowledge engine over peer-reviewed medical literature. A multimodal fusion scorer blends classification probabilities with clinical feature scores, adaptively reallocating weights when components are uncalibrated. The system provides role-gated access for medical practitioners, real-time active assessment tracking in patient timelines, automatic suppression of failed evaluations, and isolated test runtimes for unbiased baseline calibration. The platform provides transparent, grounded, and longitudinal decision support for clinical dermatology.

---

## Claims
We claim:

1. **A computer-implemented clinical decision-support system for multimodal dermoscopic lesion evaluation and longitudinal progression tracking, comprising:**
   - a client computing interface configured to authenticate users and accept dermoscopic lesion images associated with a patient identifier and patient name;
   - a database storing patient records, historical lesion imagery, and analytical traces partitioned by practitioner and patient identifiers;
   - an application server executing an orchestrator agent configured to coordinate decision-support workflows across specialized subagents;
   - a dual-branch vision subsystem executing in parallel a hierarchical vision transformer for lesion classification and a semantic segmentation transformer for lesion boundary delineation;
   - a morphological feature extraction module configured to quantify clinical Asymmetry, Border irregularity, Color variegation, and Diameter metrics from said segmentation mask and lesion image;
   - a longitudinal feature comparator configured to retrieve prior lesion records matching said patient identifier, compute cross-temporal dimensional deltas and color shift metrics across sequential encounters, and map progression into discrete evolution categories;
   - a multimodal fusion engine configured to compute a composite lesion risk score by combining classification probabilities with clinical feature scores using an adaptive weight redistribution mechanism; and
   - a report generation module configured to compile an explainable clinical decision-support report incorporating segmented overlays, feature metrics, longitudinal progression data, and medical literature citations.

2. **The system of claim 1**, wherein said orchestrator agent executes a cognitive deliberation loop governed by safety prerequisite ordering, verifying image quality prior to vision inference and evaluating spatial alignment between classifier Grad-CAM attention heatmaps and the segmented lesion mask to trigger adaptive visual re-cropping upon detecting artifact misalignment.

3. **The system of claim 1**, wherein said morphological feature extraction module comprises an automated scale calibration detector that identifies physical reference objects within the field of view to compute physical millimeter diameter, and wherein uncertainty tracking suppresses physical diameter calculation when scale references are absent.

4. **The system of claim 1**, wherein said longitudinal feature comparator calculates surface area delta percentage, maximum diameter change rate, and border scalloping variance over calculated visit intervals, mapping said metrics into discrete evolution categories comprising no significant evolution, possible evolution, and clear evolution.

5. **The system of claim 1**, wherein said multimodal fusion engine allocates base weights of approximately 0.60 to the vision classifier, 0.15 to evolution, 0.08 to asymmetry, 0.07 to border irregularity, 0.06 to color variegation, and 0.04 to diameter, and wherein the weight of any uncalibrated or unavailable parameter is proportionally redistributed to all active parameters such that total weight strictly equals 1.0.

6. **The system of claim 1**, further comprising a hybrid retrieval-augmented generation (RAG) evidence module integrating dense vector embeddings, sparse lexical indexes, reciprocal rank fusion, and cross-encoder reranking over curated peer-reviewed dermatology sources to validate clinical uncertainties and supply grounded literature citations.

7. **The system of claim 1**, wherein said client interface automatically queries said database upon practitioner entry of a patient identifier to auto-fill the associated patient name, and displays a searchable patient directory linked to a chronological visit timeline.

8. **The system of claim 1**, wherein said application server records an in-progress status upon image submission, causing said client interface to render an active running assessment card within the patient's record timeline displaying live pipeline state, and wherein said active assessment card transitions into a permanent stored record upon successful completion.

9. **The system of claim 8**, wherein if an evaluation fails due to image quality insufficiency or execution error, the application server automatically purges the temporary record and suppresses failed entries from patient history queries, preserving medical record integrity.

10. **The system of claim 1**, further comprising an isolated test runtime configured to execute the identical dual-branch vision, feature extraction, fusion, and reporting pipelines for test accounts while suppressing longitudinal baseline image injection, enabling unbiased model calibration and auditing.

11. **A computer-implemented method for multimodal dermoscopic lesion assessment and longitudinal feature tracking, comprising:**
    - authenticating a practitioner account and receiving a dermoscopic lesion image associated with a patient identifier;
    - querying a database using said patient identifier to retrieve prior chronological lesion records associated with the patient;
    - processing the received image in parallel through a vision transformer classifier to compute a lesion probability and a semantic segmentation transformer to delineate a lesion boundary mask;
    - extracting quantitative Asymmetry, Border irregularity, Color variegation, and Diameter (ABCD) morphological measurements from said mask and image;
    - comparing extracted morphological metrics from prior chronological records against the received image to calculate cross-temporal dimensional deltas representing longitudinal Evolution (E);
    - synthesizing the classification probability and ABCDE feature metrics into a composite risk score via an adaptive fusion model that proportionally redistributes weights when parameters are uncalibrated; and
    - generating an explainable clinical decision-support report with visual overlays, longitudinal progression metrics, and literature citations.

12. **The method of claim 11**, further comprising evaluating Grad-CAM visual attention activation against the segmented boundary mask and automatically triggering an adaptive re-cropping and re-classification action when activation focus falls outside the lesion contour.

13. **The method of claim 11**, further comprising rendering a real-time running indicator in the patient's record timeline while the workflow executes, committing the record upon successful completion, and automatically deleting the temporary record if the evaluation encounters an error.

14. **The method of claim 11**, further comprising identifying test account credentials and selectively bypassing temporal history injection to evaluate baseline inference without historical parameter contamination.

15. **A non-transitory computer-readable storage medium** comprising instructions that, when executed by one or more processors, cause the processors to execute the multimodal dermoscopic analysis and longitudinal tracking method of claim 11.
