import os
import csv
import json
import time
import logging
from pathlib import Path
from Bio import Entrez
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

Entrez.email = "research@melanoma-rag.local"

# Target categories and search queries
CATEGORIES = {
    "melanoma_fundamentals": {"query": "melanoma[Title/Abstract] AND (fundamentals OR biology OR overview) AND review[Publication Type]", "target": 20},
    "dermoscopy": {"query": "dermoscopy AND melanoma[Title/Abstract]", "target": 30},
    "differential_diagnosis": {"query": "(melanoma AND (differential diagnosis OR benign nevi OR seborrheic keratosis))", "target": 20},
    "melanoma_subtypes": {"query": "melanoma AND (acral OR nodular OR lentigo maligna OR superficial spreading)", "target": 15},
    "histopathology_prognosis": {"query": "melanoma AND (Breslow thickness OR histopathology OR prognosis OR staging)", "target": 15},
    "clinical_guidelines": {"query": "melanoma AND (guidelines OR management) AND (NCCN OR AAD OR EADO OR WHO)", "target": 15},
    "ai_melanoma": {"query": "artificial intelligence AND melanoma[Title/Abstract] AND (deep learning OR CNN)", "target": 25},
    "lesion_segmentation_medsam": {"query": "skin lesion segmentation AND (MedSAM OR foundation model OR deep learning)", "target": 10},
    "abcd_image_measurements": {"query": "melanoma AND (ABCDE OR asymmetry OR border OR color OR diameter OR image measurement)", "target": 10},
    "explainable_clinical_ai": {"query": "explainable artificial intelligence AND dermatology AND (Grad-CAM OR saliency)", "target": 10},
    "datasets_benchmarks": {"query": "(ISIC OR HAM10000 OR Derm7pt) AND melanoma dataset", "target": 10},
}

# The user explicitly asked for these seeds:
SEED_PMIDS = [
    ("36001057", "ai_melanoma"),
    ("39088883", "ai_melanoma"),
    ("39806282", "ai_melanoma"),
    ("37835388", "ai_melanoma"),
    ("38722750", "ai_melanoma"),
    ("38611119", "ai_melanoma"),
    ("41879756", "ai_melanoma"), # Might fail if invalid, we'll try
    ("19302072", "ai_melanoma"),
]

def fetch_details(pmid):
    """Fetch metadata and abstract for a PMID"""
    try:
        handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
        records = Entrez.read(handle)
        if not records or "PubmedArticle" not in records:
            return None
        if not records["PubmedArticle"]: return None
        article = records["PubmedArticle"][0]["MedlineCitation"]["Article"]
        title = article.get("ArticleTitle", "")
        abstract = ""
        if "Abstract" in article and "AbstractText" in article["Abstract"]:
            abstract_texts = article["Abstract"]["AbstractText"]
            abstract = " ".join([str(t) for t in abstract_texts])
            
        authors = []
        if "AuthorList" in article:
            for author in article["AuthorList"]:
                last = author.get("LastName", "")
                fore = author.get("ForeName", "")
                if last or fore:
                    authors.append(f"{last} {fore}".strip())
                    
        year = None
        if "Journal" in article and "JournalIssue" in article["Journal"] and "PubDate" in article["Journal"]["JournalIssue"]:
            year = article["Journal"]["JournalIssue"]["PubDate"].get("Year")
            
        doi = None
        if "ELocationID" in article:
            for eloc in article["ELocationID"]:
                if eloc.attributes.get("EIdType") == "doi":
                    doi = str(eloc)
                    
        return {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "year": int(year) if year else None,
            "doi": doi
        }
    except Exception as e:
        logging.error(f"Error fetching PMID {pmid}: {e}")
        return None

def search_pubmed(query, max_results):
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        return record.get("IdList", [])
    except Exception as e:
        logging.error(f"Search failed for {query}: {e}")
        return []

def main():
    out_dir = Path("rag_pipeline")
    cleaned_dir = out_dir / "cleaned_documents"
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_path = out_dir / "documents_manifest.csv"
    metadata_path = out_dir / "documents_metadata.json"
    
    metadata_db = []
    manifest_rows = []
    seen_pmids = set()
    total_docs = 0
    
    logging.info("Processing explicit seeds...")
    for pmid, cat in SEED_PMIDS:
        if pmid in seen_pmids: continue
        details = fetch_details(pmid)
        if not details: continue
        
        doc_id = f"seed_{pmid}"
        full_text = details['title'] + "\n\n" + details['abstract']
        if len(full_text) < 50: continue # Skip if no meaningful abstract
        
        with open(cleaned_dir / f"{doc_id}.txt", "w", encoding="utf-8") as f:
            f.write(full_text)
            
        meta = {
            "document_id": doc_id,
            "title": details['title'],
            "authors": details['authors'],
            "year": details['year'],
            "source": "PubMed",
            "pmid": pmid,
            "doi": details['doi'],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "document_type": "scientific_paper",
            "topic": cat,
            "subtopic": "general",
            "evidence_level": "high",
            "full_text_available": False,
            "license": "open_access_abstract",
            "keywords": []
        }
        
        metadata_db.append(meta)
        manifest_rows.append(meta)
        seen_pmids.add(pmid)
        total_docs += 1
        time.sleep(0.35) # respect rate limit
    
    logging.info("Searching across categories to hit ~180 documents...")
    for cat, info in CATEGORIES.items():
        logging.info(f"Targeting {info['target']} for category {cat}...")
        pmids = search_pubmed(info["query"], info["target"] + 10) # fetch a bit more for buffer
        
        count = 0
        for pmid in pmids:
            if count >= info["target"]: break
            if pmid in seen_pmids: continue
            
            details = fetch_details(pmid)
            if not details or not details['abstract']: continue
            
            doc_id = f"doc_{pmid}"
            full_text = details['title'] + "\n\n" + details['abstract']
            if len(full_text) < 150: continue # ensure good length
            
            with open(cleaned_dir / f"{doc_id}.txt", "w", encoding="utf-8") as f:
                f.write(full_text)
                
            meta = {
                "document_id": doc_id,
                "title": details['title'],
                "authors": details['authors'],
                "year": details['year'],
                "source": "PubMed",
                "pmid": pmid,
                "doi": details['doi'],
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "document_type": "scientific_paper",
                "topic": cat,
                "subtopic": "general",
                "evidence_level": "high",
                "full_text_available": False,
                "license": "open_access_abstract",
                "keywords": []
            }
            metadata_db.append(meta)
            manifest_rows.append(meta)
            seen_pmids.add(pmid)
            count += 1
            total_docs += 1
            time.sleep(0.35)
            
    logging.info(f"Writing manifests for {total_docs} documents...")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_db, f, indent=2)
        
    if manifest_rows:
        keys = ["document_id", "title", "authors", "year", "source", "pmid", "doi", "url", "document_type", "topic", "subtopic", "full_text_available"]
        with open(manifest_path, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(manifest_rows)
            
    logging.info(f"Data Collection Phase Complete! Fetched {total_docs} valid documents.")

if __name__ == "__main__":
    main()
