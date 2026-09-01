"""
Medical Retrieval Agent — Phase 2
===================================

Retrieves relevant medical evidence for a given diagnosis using
BGE embeddings and Qdrant vector database (in-memory mode).

The agent:
1. Loads a curated medical knowledge base from JSON on first use.
2. Embeds all entries using BAAI/bge-small-en-v1.5.
3. Stores embeddings in a Qdrant in-memory collection.
4. At query time, constructs a semantic query from the DiagnosisResult
   and retrieves the top-k most relevant evidence entries.

Usage:
    agent = MedicalRetrievalAgent(config)
    evidence = agent.retrieve(diagnosis_result)
"""

import json
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvidenceItem:
    """A single piece of retrieved medical evidence."""
    id: str
    title: str
    source: str
    category: str
    content: str
    relevance_score: float = 0.0


class MedicalRetrievalAgent:
    """
    Phase 2 agent: retrieves medical evidence using BGE embeddings + Qdrant.

    Args:
        config: Dict with keys:
            - knowledge_base: path to knowledge_base.json
            - embedding_model: HuggingFace model name (default: BAAI/bge-small-en-v1.5)
            - qdrant_mode: 'memory' | 'docker' | 'cloud'
            - top_k: number of results to retrieve (default: 5)
    """

    COLLECTION_NAME = "medical_evidence"
    _initialization_lock = threading.Lock()

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.top_k = config.get("top_k", 5)
        self._kb_path = Path(config.get("knowledge_base", "data/knowledge_base.json"))
        self._model_name = config.get("embedding_model", "BAAI/bge-small-en-v1.5")
        self._model_path = Path(config["embedding_model_path"]) if config.get("embedding_model_path") else None
        self._embedding_cache_dir = Path(config["embedding_cache_dir"]) if config.get("embedding_cache_dir") else None
        self._qdrant_mode = config.get("qdrant_mode", "disk")

        self._encoder = None
        self._qdrant_client = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Lazy initialization (heavy imports deferred until first use)
    # ------------------------------------------------------------------

    def _ensure_initialized(self):
        """Initialize embedding model and Qdrant on first use."""
        if self._initialized:
            return

        # Several API requests can reach retrieval simultaneously on the
        # first request.  Only one thread may load the encoder/open the local
        # Qdrant store; the other requests reuse the initialized objects.
        with self._initialization_lock:
            if self._initialized:
                return

            from sentence_transformers import SentenceTransformer
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            import transformers
        
            # Suppress the "Loading weights" progress bar
            transformers.utils.logging.disable_progress_bar()

            if self._model_path and self._model_path.exists():
                logger.info("Loading cached BGE embedding model from local storage")
                self._encoder = SentenceTransformer(str(self._model_path))
            else:
                logger.info("Downloading BGE embedding model once: %s", self._model_name)
                if self._embedding_cache_dir:
                    self._embedding_cache_dir.mkdir(parents=True, exist_ok=True)
                self._encoder = SentenceTransformer(
                    self._model_name,
                    cache_folder=str(self._embedding_cache_dir) if self._embedding_cache_dir else None,
                )
                if self._model_path:
                    self._model_path.parent.mkdir(parents=True, exist_ok=True)
                    self._encoder.save(str(self._model_path))
                    logger.info("Saved BGE embedding model to local storage")
            embedding_dim = self._encoder.get_embedding_dimension()

            # Initialize Qdrant client
            if self._qdrant_mode == "memory":
                self._qdrant_client = QdrantClient(":memory:")
                self._qdrant_client.recreate_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
                )
                self._index_knowledge_base(PointStruct)
            elif self._qdrant_mode == "disk":
                db_path = self.config.get("qdrant_path", "data/qdrant_db")
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                self._qdrant_client = QdrantClient(path=str(db_path))
                if not self._qdrant_client.collection_exists(self.COLLECTION_NAME):
                    self._qdrant_client.create_collection(
                        collection_name=self.COLLECTION_NAME,
                        vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
                    )
                    self._index_knowledge_base(PointStruct)
            elif self._qdrant_mode == "docker":
                host = self.config.get("qdrant_host", "localhost")
                port = self.config.get("qdrant_port", 6333)
                self._qdrant_client = QdrantClient(host=host, port=port)
                self._qdrant_client.recreate_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE),
                )
                self._index_knowledge_base(PointStruct)
            else:
                raise ValueError(f"Unsupported qdrant_mode: {self._qdrant_mode}")

            self._initialized = True
            logger.info(f"Medical retrieval agent initialized ({self._qdrant_mode} mode)")

    def _index_knowledge_base(self, PointStruct):
        """Load knowledge base JSON and index into Qdrant."""
        if not self._kb_path.exists():
            logger.warning(f"Knowledge base not found: {self._kb_path}")
            return

        with open(self._kb_path, "r", encoding="utf-8") as f:
            entries = json.load(f)

        logger.info(f"Indexing {len(entries)} knowledge base entries")

        # Encode all entries
        texts = [
            f"{e['title']}. {e['content']}" for e in entries
        ]
        embeddings = self._encoder.encode(texts, show_progress_bar=False)

        # Upsert into Qdrant
        points = []
        for i, (entry, embedding) in enumerate(zip(entries, embeddings)):
            points.append(PointStruct(
                id=i,
                vector=embedding.tolist(),
                payload={
                    "entry_id": entry["id"],
                    "title": entry["title"],
                    "source": entry["source"],
                    "category": entry["category"],
                    "content": entry["content"],
                },
            ))

        self._qdrant_client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
        )
        logger.info(f"Indexed {len(points)} entries into Qdrant")

    # ------------------------------------------------------------------
    # Query construction
    # ------------------------------------------------------------------

    def _build_query(self, diagnosis_result) -> str:
        """
        Build a semantic search query from the DiagnosisResult.

        Combines the prediction, clinical feature labels, and any
        relevant measurements into a natural-language query.
        """
        parts = []

        # Primary diagnosis
        prediction = diagnosis_result.diagnosis.prediction
        confidence = diagnosis_result.diagnosis.confidence
        parts.append(f"{prediction} diagnosis with {confidence:.0f}% confidence")

        # Clinical features (ABCD)
        for name, feat in diagnosis_result.clinical_features.items():
            parts.append(f"{name}: {feat.score_label}")

        # Color info from measurements
        color_meas = diagnosis_result.measurements.get("color", {})
        derm_colors = color_meas.get("detected_derm_colors", [])
        if derm_colors:
            parts.append(f"detected colors: {', '.join(derm_colors)}")

        # Grad-CAM reliability context
        ail = getattr(diagnosis_result.explainability, "attention_inside_lesion", None)
        if ail is not None and ail < 0.30:
            parts.append("Grad-CAM attention outside lesion")

        return ". ".join(parts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        diagnosis_result,
        extra_query: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[EvidenceItem]:
        """
        Retrieve relevant medical evidence for a DiagnosisResult.

        Args:
            diagnosis_result: DiagnosisResult from Phase 1.
            extra_query: Optional additional search terms.
            top_k: Override default top_k.

        Returns:
            List of EvidenceItem sorted by relevance (highest first).
        """
        self._ensure_initialized()

        query_text = self._build_query(diagnosis_result)
        if extra_query:
            query_text = f"{query_text}. {extra_query}"

        logger.info(f"Retrieval query: {query_text}")

        # Encode query
        query_vector = self._encoder.encode(query_text).tolist()

        # Search Qdrant with a larger limit to allow deduplication
        k = top_k or self.top_k
        search_limit = max(k * 3, 15)
        results = self._qdrant_client.query_points(
            collection_name=self.COLLECTION_NAME,
            query=query_vector,
            limit=search_limit,
        ).points

        # Convert to EvidenceItems and deduplicate sources
        evidence = []
        seen_docs = set()
        for hit in results:
            payload = hit.payload
            doc_id = payload.get("document_id") or payload.get("entry_id")
            if doc_id in seen_docs:
                continue
                
            evidence.append(EvidenceItem(
                id=doc_id,
                title=payload.get("title", ""),
                source=f"{payload.get('source', '')} {payload.get('year', '')}".strip() or "Knowledge Base",
                category=payload.get("topic") or payload.get("category", ""),
                content=payload.get("text") or payload.get("content", ""),
                relevance_score=round(float(hit.score), 4),
            ))
            seen_docs.add(doc_id)
            if len(evidence) >= k:
                break

        logger.info(f"Retrieved {len(evidence)} evidence items")
        return evidence
