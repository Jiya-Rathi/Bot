#!/usr/bin/env python3
import os
import sys
import json
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from config.settings import TAX_VECTOR_INDEX_PATH

# Default embedding model (must match builder)
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")

# Paths
INDEX_PATH = TAX_VECTOR_INDEX_PATH
META_PATH = INDEX_PATH + ".meta.pkl"
# JSON data file assumed in project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_JSON = os.getenv("TAX_JSON_PATH", os.path.join(PROJECT_ROOT, "tax_subsidy_bracket.json"))


def load_index_and_metadata():
    if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
        print(f"Error: Index or metadata missing.\nExpected index: {INDEX_PATH}\nMetadata: {META_PATH}")
        sys.exit(1)
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, 'rb') as f:
        metadata = pickle.load(f)
    return index, metadata


def embed_query(text: str):
    model = SentenceTransformer(EMBED_MODEL_NAME)
    return model.encode([text], normalize_embeddings=True)


def semantic_search(query: str, k: int=3):
    index, metadata = load_index_and_metadata()
    q_emb = embed_query(query)
    D, I = index.search(q_emb, k)
    hits = [(metadata[idx], float(score)) for score, idx in zip(D[0], I[0])]
    return hits


def load_json_data(path: str):
    if not os.path.exists(path):
        print(f"Error: JSON data file not found at {path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_country_info(country: str, data: dict):
    info = data.get(country)
    if info is None:
        print(f"Country '{country}' not found in JSON data.")
        return
    print(f"\n=== Tax & Subsidy Info for {country} ===")
    print(json.dumps(info, indent=2, ensure_ascii=False))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Semantic lookup and display of country tax/subsidy info.")
    parser.add_argument('query', help='Natural language query to find a country')
    parser.add_argument('-k', type=int, default=3, help='Number of top candidates')
    args = parser.parse_args()

    # Semantic search
    hits = semantic_search(args.query, args.k)
    print("Top matches:")
    for idx, (country, score) in enumerate(hits, 1):
        print(f"{idx}. {country} (score: {score:.4f})")

    # Load JSON data
    data = load_json_data(DATA_JSON)

    # Print info for top 1 by default
    best = hits[0][0]
    print_country_info(best, data)

if __name__ == '__main__':
    main()
