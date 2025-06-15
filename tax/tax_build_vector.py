import os
import sys
import json
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

# Vector index output path (must be a directory name)
from config.settings import TAX_VECTOR_INDEX_PATH  # e.g. "tax/tax_vector_index"

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")


def flatten_country_text(country: str, payload: dict) -> str:
    parts = [f"Country: {country}"]
    if payload.get("currency"):
        parts.append(f"Currency: {payload['currency']}")
    parts.append("Brackets:")
    for b in payload.get("brackets", []):
        min_inc = b.get("min_income")
        max_inc = b.get("max_income", "∞") if b.get("max_income") is None else b.get("max_income")
        rate = b.get("rate", 0.0) * 100
        parts.append(f"{min_inc}–{max_inc} at {rate:.1f}%")

    parts.append("Deductions:")
    for d in payload.get("deductions", []):
        if "max_amount" in d:
            parts.append(f"{d['name']} up to {d['max_amount']}")
        elif "percent" in d or "rate" in d:
            rate = d.get("percent", d.get("rate", 0.0)) * 100
            parts.append(f"{d['name']} at {rate:.1f}%")
        else:
            parts.append(d.get("name", ""))

    parts.append("Subsidies:")
    for s in payload.get("subsidies", []):
        parts.append(f"{s['name']}: {s['description']}")

    return "\n".join(parts)


def build_vector_index(input_json_path: str):
    if not os.path.exists(input_json_path):
        print(f"❌ Error: JSON not found at {input_json_path}")
        sys.exit(1)

    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for country, payload in data.items():
        text = flatten_country_text(country, payload)
        doc = Document(page_content=text, metadata={"country": country})
        documents.append(doc)

    # Initialize embedding model
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

    # Build vector index
    vectorstore = FAISS.from_documents(documents, embeddings)

    # Save as directory-based index (for FAISS.load_local)
    vectorstore.save_local(TAX_VECTOR_INDEX_PATH)
    print(f"✅ Vector DB saved to folder: {TAX_VECTOR_INDEX_PATH}")


if __name__ == "__main__":
    default_json = "tax/tax_subsidy_bracket.json"

    import argparse
    parser = argparse.ArgumentParser(description="Build LangChain-compatible FAISS index from tax JSON")
    parser.add_argument("input_json", nargs="?", default=default_json, help="Path to tax JSON file")
    args = parser.parse_args()

    build_vector_index(args.input_json)
