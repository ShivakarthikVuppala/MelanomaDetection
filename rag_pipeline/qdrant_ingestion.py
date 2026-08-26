import os
import json
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

COLLECTION_NAME = "medical_evidence"

def main():
    out_dir = Path(".")
    chunks_path = out_dir / "chunks.jsonl"
    qdrant_path = Path("../data/qdrant_db")
    
    logging.info("Loading BGE embedding model...")
    encoder = SentenceTransformer("BAAI/bge-small-en-v1.5")
    # Handle API change in sentence-transformers
    if hasattr(encoder, "get_sentence_embedding_dimension"):
        embedding_dim = encoder.get_sentence_embedding_dimension()
    else:
        embedding_dim = encoder.get_embedding_dimension()
    
    logging.info(f"Initializing Qdrant at {qdrant_path}...")
    client = QdrantClient(path=str(qdrant_path))
    
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=embedding_dim,
            distance=Distance.COSINE,
        ),
    )
    
    points = []
    texts_to_embed = []
    payloads = []
    
    logging.info("Reading chunks...")
    if not chunks_path.exists():
        logging.error(f"Chunks file not found: {chunks_path}")
        return
        
    with open(chunks_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            payload = json.loads(line)
            # Add text for embedding
            text_for_embedding = f"{payload['title']}. {payload['text']}"
            texts_to_embed.append(text_for_embedding)
            payloads.append(payload)
            
    logging.info(f"Generating embeddings for {len(texts_to_embed)} chunks...")
    embeddings = encoder.encode(texts_to_embed, show_progress_bar=True)
    
    logging.info("Upserting into Qdrant...")
    for i, (embedding, payload) in enumerate(zip(embeddings, payloads)):
        points.append(PointStruct(
            id=i,
            vector=embedding.tolist(),
            payload=payload,
        ))
        
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )
    
    logging.info(f"Successfully ingested {len(points)} vectors into Qdrant database.")

if __name__ == "__main__":
    main()
