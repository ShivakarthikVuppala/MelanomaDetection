"""
Create Vector Database — Agentic RAG v4.0
==========================================
Reads the existing knowledge base from rag_pipeline/ (PubMed-sourced
cleaned documents and pre-chunked JSONL) and builds:

1. Qdrant dense vector index  (child chunks)
2. BM25 sparse keyword index  (medical stemming)
3. Parent chunk store          (for context expansion)

Usage:
    python create_vector_db.py
    python main.py build-rag
"""

import os
import json
import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore

from .config import settings
from .chunking_strategy import (
    create_parent_child_chunks,
    save_parent_store,
)
from .bm25_utils import build_bm25_index


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # ============================================================
    # 1. Load existing knowledge base from rag_pipeline/
    # ============================================================

    RAG_PIPELINE_DIR = Path("rag_pipeline")
    CHUNKS_PATH = RAG_PIPELINE_DIR / "chunks.jsonl"
    CLEANED_DOCS_DIR = RAG_PIPELINE_DIR / "cleaned_documents"
    METADATA_PATH = RAG_PIPELINE_DIR / "documents_metadata.json"

    logger.info("=" * 60)
    logger.info("BUILDING HYBRID INDEX FROM EXISTING KNOWLEDGE BASE")
    logger.info("=" * 60)

    logger.info(f"1. Loading documents from {RAG_PIPELINE_DIR}...")

    documents = []

    # Strategy: Load from cleaned_documents/*.txt (full documents)
    # which gives better parent-child chunking than pre-chunked JSONL
    if CLEANED_DOCS_DIR.exists():
        # Load metadata for enrichment
        metadata_map = {}
        if METADATA_PATH.exists():
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                metadata_list = json.load(f)
            metadata_map = {m["document_id"]: m for m in metadata_list}
            logger.info(f"  Loaded metadata for {len(metadata_map)} documents")

        txt_files = sorted(CLEANED_DOCS_DIR.glob("*.txt"))
        for txt_file in txt_files:
            doc_id = txt_file.stem
            text = txt_file.read_text(encoding="utf-8").strip()

            if not text:
                continue

            meta = metadata_map.get(doc_id, {})

            documents.append(Document(
                page_content=text,
                metadata={
                    "document_id": doc_id,
                    "document_name": meta.get("title", doc_id),
                    "source": meta.get("source", "PubMed"),
                    "source_type": meta.get("document_type", "scientific_paper"),
                    "evidence_level": meta.get("document_type", "research"),
                    "topic": meta.get("topic", "ai_melanoma"),
                    "url": meta.get("url", ""),
                    "pmid": meta.get("pmid", ""),
                    "year": str(meta.get("year", "")),
                }
            ))

        logger.info(f"  Loaded {len(documents)} documents from cleaned_documents/")

    elif CHUNKS_PATH.exists():
        # Fallback: load from pre-chunked JSONL
        logger.info("  cleaned_documents/ not found, falling back to chunks.jsonl")

        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                chunk = json.loads(line.strip())
                documents.append(Document(
                    page_content=chunk["text"],
                    metadata={
                        "document_id": chunk.get("document_id", ""),
                        "chunk_id": chunk.get("chunk_id", ""),
                        "document_name": chunk.get("title", ""),
                        "source": chunk.get("source", "PubMed"),
                        "source_type": chunk.get("document_type", "scientific_paper"),
                        "evidence_level": chunk.get("document_type", "research"),
                        "topic": chunk.get("topic", "ai_melanoma"),
                        "url": chunk.get("url", ""),
                        "pmid": chunk.get("pmid", ""),
                        "year": str(chunk.get("year", "")),
                    }
                ))

        logger.info(f"  Loaded {len(documents)} chunks from chunks.jsonl")

    else:
        raise FileNotFoundError(
            f"No knowledge base found. Expected either "
            f"{CLEANED_DOCS_DIR} or {CHUNKS_PATH}"
        )


    # ============================================================
    # 2. Create parent-child chunk hierarchy
    # ============================================================

    logger.info("2. Creating parent-child chunk hierarchy...")

    child_chunks, parent_store = create_parent_child_chunks(
        documents,
        parent_chunk_size=settings.PARENT_CHUNK_SIZE,
        parent_chunk_overlap=settings.PARENT_CHUNK_OVERLAP,
        child_chunk_size=settings.CHILD_CHUNK_SIZE,
        child_chunk_overlap=settings.CHILD_CHUNK_OVERLAP,
    )

    logger.info(
        f"  Created {len(child_chunks)} child chunks and "
        f"{len(parent_store)} parent chunks."
    )


    # ============================================================
    # 3. Show example chunk
    # ============================================================

    if child_chunks:
        logger.info("3. Example child chunk:")
        logger.info(f"  Metadata: {child_chunks[0].metadata}")
        logger.info(f"  Text preview: {child_chunks[0].page_content[:100]}...")
        logger.info(f"  Parent ID: {child_chunks[0].metadata.get('parent_id', 'N/A')}")


    # ============================================================
    # 4. Load embedding model
    # ============================================================

    logger.info(f"4. Loading embedding model: {settings.EMBEDDING_MODEL}")

    embedding_model = FastEmbedEmbeddings(
        model_name=settings.EMBEDDING_MODEL
    )

    logger.info("  Embedding model loaded.")


    # ============================================================
    # 5. Create Qdrant database (dense vectors)
    # ============================================================

    if settings.QDRANT_MODE == "cloud":
        logger.info("5. Creating Qdrant Cloud collection...")

        if not settings.QDRANT_CLOUD_URL or not settings.QDRANT_CLOUD_API_KEY:
            raise ValueError(
                "QDRANT_MODE=cloud but QDRANT_CLOUD_URL and/or "
                "QDRANT_CLOUD_API_KEY are not set in .env"
            )

        vector_store = QdrantVectorStore.from_documents(
            documents=child_chunks,
            embedding=embedding_model,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            url=settings.QDRANT_CLOUD_URL,
            api_key=settings.QDRANT_CLOUD_API_KEY,
        )

        logger.info(
            f"  Stored {len(child_chunks)} child chunks in "
            f"Qdrant Cloud ({settings.QDRANT_CLOUD_URL})"
        )

    else:
        logger.info("5. Creating local Qdrant database...")

        vector_store = QdrantVectorStore.from_documents(
            documents=child_chunks,
            embedding=embedding_model,
            path=settings.QDRANT_LOCAL_PATH,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            force_recreate=True,
        )

        logger.info(
            f"  Stored {len(child_chunks)} child chunks in "
            f"local Qdrant ({settings.QDRANT_LOCAL_PATH})"
        )


    # ============================================================
    # 6. Save parent chunk store
    # ============================================================

    logger.info("6. Saving parent chunk store...")

    save_parent_store(parent_store, settings.PARENT_CHUNKS_PATH)


    # ============================================================
    # 7. Build BM25 index (sparse keywords with medical stemming)
    # ============================================================

    logger.info("7. Building BM25 index with medical stemming...")

    bm25 = build_bm25_index(child_chunks)

    logger.info("  BM25 index created successfully.")


    # ============================================================
    # Done
    # ============================================================

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUCCESS — HYBRID INDEX CREATED (v4.0)")
    logger.info("=" * 60)
    logger.info(f"  Source:           {RAG_PIPELINE_DIR}")
    logger.info(f"  Embedding model:  {settings.EMBEDDING_MODEL}")
    logger.info(f"  Qdrant mode:      {settings.QDRANT_MODE}")
    logger.info(f"  Child chunks:     {len(child_chunks)} (size={settings.CHILD_CHUNK_SIZE})")
    logger.info(f"  Parent chunks:    {len(parent_store)} (size={settings.PARENT_CHUNK_SIZE})")
    logger.info(f"  BM25 index:       {len(child_chunks)} documents (medical stemming)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()