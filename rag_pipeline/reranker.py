"""
Cross-Encoder Re-Ranker — v4.0 (Medical-Grade Reranker)

Upgraded from v3.0:
- Model: bge-reranker-v2-m3 (multilingual, domain-aware)
  replaces ms-marco-MiniLM-L-6-v2 (web-QA only)
- Score threshold filtering: discards passages below a
  minimum relevance score (eliminates noise)
- Device auto-detection: uses CUDA if available, else CPU
- Configurable via config.py settings

After initial hybrid retrieval (dense + BM25), this module
re-scores each (query, passage) pair using a cross-encoder
model, which is significantly more accurate than bi-encoder
similarity alone.
"""

import logging
import threading
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Global model cache
_cross_encoder = None
_cross_encoder_lock = threading.Lock()
_cross_encoder_retry_after = 0.0


def get_cross_encoder(model_name: str = None):
    # Startup warm-up and the first upload can arrive together.
    with _cross_encoder_lock:
        return _load_cross_encoder(model_name)


def _load_cross_encoder(model_name: str = None):
    """
    Lazy-load the cross-encoder model.
    Cached globally to avoid reloading on every call.
    Uses CUDA if available, otherwise CPU.
    """
    global _cross_encoder, _cross_encoder_retry_after

    if _cross_encoder is None:
        if time.monotonic() < _cross_encoder_retry_after:
            return None
        # Get model name from config
        if model_name is None:
            try:
                from .config import settings
                model_name = settings.RERANKER_MODEL
            except ImportError:
                model_name = "BAAI/bge-reranker-v2-m3"

        logger.info(f"Loading cross-encoder reranker: {model_name}")

        try:
            import torch
            from sentence_transformers import CrossEncoder

            # Auto-detect device
            if torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"

            logger.info(f"Reranker device: {device}")

            try:
                # Cached weights must not wait on Hugging Face metadata calls
                # every time the backend restarts.
                _cross_encoder = CrossEncoder(model_name, device=device, local_files_only=True)
            except OSError:
                _cross_encoder = CrossEncoder(model_name, device=device)

            logger.info(f"Cross-encoder loaded successfully: {model_name}")

        except ImportError:
            _cross_encoder_retry_after = time.monotonic() + 60.0
            logger.warning(
                "sentence-transformers or torch not installed. "
                "Re-ranking will be skipped."
            )
            return None

        except Exception as e:
            # Do not repeat a failed download for every query in the same case.
            _cross_encoder_retry_after = time.monotonic() + 60.0
            logger.warning(
                f"Failed to load cross-encoder '{model_name}': {e}. "
                f"Re-ranking will be skipped."
            )
            return None

    return _cross_encoder


def rerank(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = 5,
    text_key: str = "text",
    min_score: float = None
) -> List[Dict[str, Any]]:
    """
    Re-rank documents using the cross-encoder with
    threshold-based filtering.

    Parameters
    ----------
    query : str
        The search query
    documents : list
        List of document dicts, each containing a text field
    top_k : int
        Number of top results to return after re-ranking
    text_key : str
        Key in the document dict that contains the text
    min_score : float
        Minimum reranker score threshold. Passages scoring
        below this are discarded as irrelevant noise.
        If None, uses the value from config.settings.

    Returns
    -------
    Re-ranked list of documents with added 'rerank_score' field.
    Only includes passages above the minimum score threshold.
    """

    if not documents:
        return []

    # Get threshold from config if not specified
    if min_score is None:
        try:
            from .config import settings
            min_score = settings.RERANKER_MIN_SCORE
        except ImportError:
            min_score = -2.0

    model = get_cross_encoder()

    if model is None:
        logger.warning("Cross-encoder unavailable, returning original order.")
        return documents[:top_k]

    # Create (query, passage) pairs for scoring
    pairs = [
        (query, doc[text_key])
        for doc in documents
    ]

    # Score all pairs
    scores = model.predict(pairs)

    # Attach scores to documents
    for doc, score in zip(documents, scores):
        doc["rerank_score"] = float(score)

    # Filter by minimum score threshold
    filtered = [
        doc for doc in documents
        if doc["rerank_score"] >= min_score
    ]

    if len(filtered) < len(documents):
        logger.info(
            f"Score threshold filtering: {len(documents)} → {len(filtered)} "
            f"(removed {len(documents) - len(filtered)} below {min_score:.2f})"
        )

    # Sort by re-rank score (descending)
    reranked = sorted(
        filtered,
        key=lambda x: x.get("rerank_score", 0),
        reverse=True
    )

    if reranked:
        logger.info(
            f"Re-ranked {len(filtered)} documents. "
            f"Top score: {reranked[0]['rerank_score']:.4f}, "
            f"Bottom score: {reranked[-1]['rerank_score']:.4f}"
        )
    else:
        logger.warning("No documents passed the score threshold filter.")

    return reranked[:top_k]
