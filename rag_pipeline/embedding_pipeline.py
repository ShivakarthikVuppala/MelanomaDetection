import os
import json
import tiktoken
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_chunks(text, max_tokens=250):
    enc = tiktoken.get_encoding("cl100k_base")
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for p in paragraphs:
        p = p.strip()
        if not p: continue
        tokens = len(enc.encode(p))
        if current_tokens + tokens > max_tokens and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = p
            current_tokens = tokens
        else:
            current_chunk += "\n\n" + p if current_chunk else p
            current_tokens += tokens
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def main():
    out_dir = Path(".")
    cleaned_dir = out_dir / "cleaned_documents"
    metadata_path = out_dir / "documents_metadata.json"
    chunks_out_path = out_dir / "chunks.jsonl"
    
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata_db = json.load(f)
        
    metadata_map = {m["document_id"]: m for m in metadata_db}
    
    total_chunks = 0
    with open(chunks_out_path, "w", encoding="utf-8") as f_out:
        for doc_file in cleaned_dir.glob("*.txt"):
            doc_id = doc_file.stem
            meta = metadata_map.get(doc_id)
            if not meta:
                logging.warning(f"No metadata found for {doc_id}")
                continue
                
            with open(doc_file, "r", encoding="utf-8") as f_in:
                text = f_in.read()
                
            chunks = get_chunks(text, max_tokens=250)
            
            for i, chunk_text in enumerate(chunks):
                chunk_payload = {
                    "document_id": doc_id,
                    "chunk_id": f"{doc_id}_chunk_{i}",
                    "text": chunk_text,
                    "title": meta["title"],
                    "authors": meta["authors"],
                    "year": meta["year"],
                    "source": meta["source"],
                    "pmid": meta["pmid"],
                    "doi": meta["doi"],
                    "url": meta["url"],
                    "document_type": meta["document_type"],
                    "topic": meta["topic"],
                    "subtopic": meta["subtopic"],
                    "keywords": meta["keywords"]
                }
                f_out.write(json.dumps(chunk_payload) + "\n")
                total_chunks += 1
                
    logging.info(f"Chunking complete. Created {total_chunks} chunks from {len(metadata_db)} documents.")

if __name__ == "__main__":
    main()
