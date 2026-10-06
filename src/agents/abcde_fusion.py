"""
ABCDE Fusion Scorer
====================
Combines the Swin classifier melanoma probability with ABCDE clinical
feature scores into a single weighted composite melanoma score [0,1].

WEIGHT DESIGN (must sum to 1.0 after redistribution):
  classifier  0.60  - Swin model raw probability; primary signal
  E           0.15  - Evolution; strongest clinical discriminator
  A           0.08  - Asymmetry
  B           0.07  - Border irregularity
  C           0.06  - Color diversity
  D           0.04  - Diameter; lowest — often uncalibrated

NORMALISATION THRESHOLDS (each component maps to [0,1] melanoma risk):
  A  asymmetry_index:  0.0 (symmetric) -> 0.0,  >=0.35 (High) -> 1.0
                       Linear ramp from low_threshold=0.15 to high_threshold=0.35
  B  border:           0.0 (circle) -> 0.0,  >=0.35 (irregularity score) -> 1.0
                       Linear ramp, clips at 1.0
  C  color clusters:   1 cluster -> 0.0,  >=4 clusters -> 1.0
                       Stepped: 1=0.0, 2=0.33, 3=0.67, 4+=1.0
  D  diameter_mm:      <3mm -> 0.0,  >=10mm -> 1.0
                       Linear ramp; ABCDE flag threshold is 6mm -> 0.43
  E  evolution status:
       no_significant_evolution  -> 0.10 base
       possible_evolution        -> 0.55 base
       clear_evolution           -> 0.85 base
       unable_to_assess          -> excluded (weight redistributed)
     Each base is blended with confidence: score = base*conf + 0.5*(1-conf)
  text-reported E: keyword scan; "grew/larger/changed" -> 0.65, "stable/same" -> 0.20

MISSING COMPONENT HANDLING:
  When any component is unavailable (None score), its weight is redistributed
  proportionally to all present components so the total always sums to 1.0.
  Worst case (only classifier available): composite = 1.0 * melanoma_prob,
  which is identical to the standalone classifier result.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

BASE_WEIGHTS: Dict[str, float] = {
    "classifier": 0.60,
    "E": 0.15,
    "A": 0.08,
    "B": 0.07,
    "C": 0.06,
    "D": 0.04,
}

# Per-feature normalization bounds (used for A and B)
_A_LOW = 0.15   # asymmetry_index below this -> low risk
_A_HIGH = 0.35  # asymmetry_index at/above this -> high risk
_B_LOW = 0.15   # border irregularity below this -> low risk
_B_HIGH = 0.35  # border irregularity at/above this -> high risk


@dataclass
class FusionResult:
    """Full output of the ABCDE fusion scorer."""
    composite_score: float          # weighted melanoma probability [0,1]
    prediction: str                 # "Melanoma" | "Non-melanoma"
    threshold: float                # threshold used for the decision
    weights_used: Dict[str, float]  # effective weights after redistribution
    component_scores: Dict[str, float]   # normalised [0,1] score per component
    components_available: Dict[str, bool]  # which components contributed
    flags: list = field(default_factory=list)


def _linear_ramp(value: float, low: float, high: float) -> float:
    """Map value linearly from [low, high] -> [0, 1], clamped."""
    if high <= low:
        return 1.0 if value >= high else 0.0
    return float(min(1.0, max(0.0, (value - low) / (high - low))))


def _score_asymmetry(score_numeric: float) -> float:
    """
    Normalise asymmetry_index to [0,1] melanoma risk using clinical thresholds.
    0.0 (symmetric) -> 0.0 risk,  >=0.35 (High) -> 1.0 risk.
    """
    return _linear_ramp(score_numeric, _A_LOW, _A_HIGH)


def _score_border(score_numeric: float) -> float:
    """
    Normalise border irregularity (1-circularity) to [0,1] melanoma risk.
    0.0 (perfect circle) -> 0.0 risk,  >=0.35 -> 1.0 risk.
    """
    return _linear_ramp(score_numeric, _B_LOW, _B_HIGH)


def _score_color(score_numeric: float) -> float:
    """
    Normalise color score to [0,1] melanoma risk.
    The feature already maps: 0=uniform, 0.4=dual, 0.5+=multiple.
    Scale so that >=0.5 -> 1.0, giving more resolution.
    """
    return _linear_ramp(score_numeric, 0.0, 0.5)


def _normalise_evolution(ev_result: Any) -> Optional[float]:
    """
    Convert evolution data to [0,1] melanoma-risk score.
    Accepts a dict (image-assessed) or string (patient-reported text).
    Returns None when assessment is definitively unable_to_assess.
    """
    if ev_result is None:
        return None

    # --- Image-assessed evolution dict ---
    if isinstance(ev_result, dict):
        status = ev_result.get("status", "unable_to_assess")
        confidence = float(ev_result.get("confidence", 0.0))
        base = {
            "clear_evolution": 0.85,
            "possible_evolution": 0.55,
            "no_significant_evolution": 0.10,
            "unable_to_assess": None,
        }.get(status, None)
        if base is None:
            return None
        # Blend: low confidence pulls toward neutral 0.5
        return float(base * confidence + 0.5 * (1.0 - confidence))

    # --- Patient-reported text history ---
    if isinstance(ev_result, str):
        text = ev_result.strip().lower()
        if not text:
            return None
        # High-risk keywords: lesion has visibly changed
        high_risk_kw = ["grew", "grown", "larger", "bigger", "spread", "changed",
                        "darker", "bleed", "itch", "bled", "new", "appeared",
                        "different", "asymmetric", "irregular"]
        # Low-risk keywords: lesion is stable
        low_risk_kw = ["stable", "same", "unchanged", "no change", "not changed",
                       "consistent", "always", "born with", "no growth"]
        high_hit = any(kw in text for kw in high_risk_kw)
        low_hit = any(kw in text for kw in low_risk_kw)
        if high_hit and not low_hit:
            return 0.65
        if low_hit and not high_hit:
            return 0.20
        # Mixed or ambiguous reported history -> moderate
        return 0.45

    return None


def _normalise_diameter(abcde_d: Optional[Any]) -> Optional[float]:
    """
    Convert D ABCDEFeature into [0,1] risk score.
    Requires calibrated physical measurement in mm.
    Ramps linearly from 0 at 3mm to 1.0 at 10mm.
    The ABCDE D-criterion threshold of 6mm maps to 0.43.
    Returns None when uncalibrated (pixel-only).
    """
    if abcde_d is None:
        return None
    raw = getattr(abcde_d, "raw", {}) or {}
    phys = raw.get("physical_diameter", {})
    if isinstance(phys, dict) and phys.get("calibrated") and phys.get("value") is not None:
        d_mm = float(phys["value"])
        return _linear_ramp(d_mm, 3.0, 10.0)
    return None


def _redistribute_weights(w: Dict[str, float], available: Dict[str, bool]) -> Dict[str, float]:
    """
    Redistribute weights of unavailable components proportionally to present ones.
    Guarantees sum(w.values()) == 1.0 after redistribution.
    """
    missing = sum(w[k] for k in w if not available.get(k, False))
    present = [k for k in w if available.get(k, False)]
    if missing > 0.0 and present:
        total_present = sum(w[k] for k in present)
        if total_present > 0.0:
            for k in present:
                w[k] += missing * (w[k] / total_present)
        # If even present weights sum to 0 (shouldn't happen), give all to classifier
        elif "classifier" in w:
            w["classifier"] += missing
    return w


def compute_fusion(
    melanoma_prob: float,
    diagnosis_result: Any,
    abcde: Dict[str, Any],
    clinical_context: Dict[str, Any],
    classification_threshold: float = 0.5,
    weights: Optional[Dict[str, float]] = None,
) -> FusionResult:
    """
    Compute weighted composite melanoma score from classifier + ABCDE features.

    Each feature component is normalised to [0,1] where 0=benign-like and
    1=melanoma-like, then combined via weighted sum.  The composite score is
    compared against classification_threshold to decide the final prediction.

    If ANY component is unavailable its weight is redistributed proportionally
    to the remaining components.  When only the classifier is available the
    composite equals melanoma_prob (identical to standalone classifier).
    """
    w = dict(BASE_WEIGHTS if weights is None else weights)
    raw_scores: Dict[str, Optional[float]] = {"classifier": float(melanoma_prob)}
    available: Dict[str, bool] = {"classifier": True}

    # clinical_features from DiagnosisResult (FeatureScore objects)
    cf = {}
    if diagnosis_result is not None and hasattr(diagnosis_result, "clinical_features"):
        cf = diagnosis_result.clinical_features or {}

    # ---- A: Asymmetry -------------------------------------------------------
    a_fs = cf.get("asymmetry")
    if a_fs is not None and getattr(a_fs, "score_numeric", None) is not None:
        raw_scores["A"] = _score_asymmetry(float(a_fs.score_numeric))
    else:
        raw_scores["A"] = None

    # ---- B: Border irregularity --------------------------------------------
    b_fs = cf.get("border")
    if b_fs is not None and getattr(b_fs, "score_numeric", None) is not None:
        raw_scores["B"] = _score_border(float(b_fs.score_numeric))
    else:
        raw_scores["B"] = None

    # ---- C: Color diversity -------------------------------------------------
    c_fs = cf.get("color")
    if c_fs is not None and getattr(c_fs, "score_numeric", None) is not None:
        raw_scores["C"] = _score_color(float(c_fs.score_numeric))
    else:
        raw_scores["C"] = None

    # ---- D: Diameter (calibrated mm only) -----------------------------------
    raw_scores["D"] = _normalise_diameter(abcde.get("D"))

    # ---- E: Evolution (dict or patient-reported text) -----------------------
    ev = clinical_context.get("evolution")
    raw_scores["E"] = _normalise_evolution(ev)

    # ---- Availability map ---------------------------------------------------
    for k in w:
        available[k] = raw_scores.get(k) is not None

    # ---- Weight redistribution ---------------------------------------------
    w = _redistribute_weights(w, available)

    # ---- Weighted sum -------------------------------------------------------
    composite = sum(
        w[k] * raw_scores[k]
        for k in w
        if available.get(k) and raw_scores.get(k) is not None
    )
    composite = float(min(1.0, max(0.0, composite)))
    prediction = "Melanoma" if composite >= classification_threshold else "Non-melanoma"

    # ---- Audit flags --------------------------------------------------------
    flags: list = []
    if not available.get("E"):
        e_val = raw_scores.get("E")
        flags.append(
            "Evolution (E) unable to assess; weight redistributed to other components."
            if e_val is None else
            "Evolution (E) from text history; keyword-based risk applied."
        )
    if not available.get("D"):
        flags.append("Diameter (D) uncalibrated (no physical reference); D weight redistributed.")
    if not all(available.get(k) for k in ("A", "B", "C")):
        flags.append("One or more of A/B/C unavailable (segmentation error); weights redistributed.")
    if len([k for k in available if available[k]]) == 1:
        flags.append("WARNING: Only classifier available; fusion score equals raw classifier probability.")

    return FusionResult(
        composite_score=round(composite, 4),
        prediction=prediction,
        threshold=classification_threshold,
        weights_used={k: round(v, 4) for k, v in w.items()},
        component_scores={
            k: (round(float(v), 4) if v is not None else None)
            for k, v in raw_scores.items()
        },
        components_available=dict(available),
        flags=flags,
    )
