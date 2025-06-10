import os
import sys
import json
import pickle
import faiss
from sentence_transformers import SentenceTransformer

# import vector index path from config
from config.settings import TAX_VECTOR_INDEX_PATH

# Optionally override embedding model via env var
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")


def flatten_country_text(country: str, payload: dict) -> str:
    """
    Convert a country payload into a single text string for embedding.
    Treat max_income=None as '∞'.
    """
    parts = [f"Country: {country}"]
    if payload.get("currency"):
        parts.append(f"Currency: {payload['currency']}")
    parts.append("Brackets:")
    for b in payload.get("brackets", []):
        min_inc = b.get("min_income")
        max_inc = b.get("max_income")
        max_inc_str = "∞" if max_inc is None else str(max_inc)
        parts.append(f"{min_inc}–{max_inc_str} at {b['rate']*100:.1f}%")
    parts.append("Deductions:")
    for d in payload.get("deductions", []):
        if "max_amount" in d:
            parts.append(f"{d['name']} up to {d['max_amount']}")
        elif "percent" in d or "rate" in d:
            # some entries use 'percent', others use 'rate'
            pct = d.get("percent", d.get("rate"))
            parts.append(f"{d['name']} at {pct*100:.1f}%")
        else:
            # fallback to just the name
            parts.append(d.get("name", ""))
    parts.append("Subsidies:")
    for s in payload.get("subsidies", []):
        parts.append(f"{s['name']}: {s['description']}")
    return "".join(parts)


def build_vector_index(input_json_path: str):
    """
    Read the input JSON file, build a FAISS vector index,
    and save to TAX_VECTOR_INDEX_PATH (plus .meta.pkl for metadata).
    """
    # Load JSON
    try:
        with open(input_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {input_json_path}")
        sys.exit(1)

    # Flatten each country for embedding
    texts, countries = [], []
    for country, payload in data.items():
        texts.append(flatten_country_text(country, payload))
        countries.append(country)

    # Compute embeddings
    model = SentenceTransformer(EMBED_MODEL_NAME)
    embeddings = model.encode(texts, normalize_embeddings=True)

    # Build FAISS index (cosine similarity via inner product on normalized vectors)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Persist index and metadata
    faiss.write_index(index, TAX_VECTOR_INDEX_PATH)
    meta_path = TAX_VECTOR_INDEX_PATH + ".meta.pkl"
    with open(meta_path, "wb") as f:
        pickle.dump(countries, f)

    print(f"Vector index saved to {TAX_VECTOR_INDEX_PATH}")
    print(f"Metadata saved to {meta_path}")


if __name__ == "__main__":
    # Determine project root (one level above utils/)
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    default_json = os.path.join(ROOT, "tax_subsidy_bracket.json")

    import argparse
    parser = argparse.ArgumentParser(
        description="Build FAISS vector DB for tax+subsidy data from JSON."
    )
    parser.add_argument(
        "input_json",
        nargs='?',
        default=default_json,
        help=f"Path to tax/subsidy JSON file (default: {default_json})"
    )
    args = parser.parse_args()
    build_vector_index(args.input_json)