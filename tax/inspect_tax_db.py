import os
import sys
import pickle
import faiss

# Import the path to the FAISS index from your config
from config.settings import TAX_VECTOR_INDEX_PATH

# Derive metadata path
INDEX_PATH = TAX_VECTOR_INDEX_PATH
META_PATH = INDEX_PATH + ".meta.pkl"


def load_index_and_metadata():
    """
    Load the FAISS index and metadata list (e.g., country names).
    Exits if files are missing.
    """
    if not os.path.exists(INDEX_PATH):
        print(f"Error: FAISS index not found at {INDEX_PATH}")
        sys.exit(1)
    if not os.path.exists(META_PATH):
        print(f"Error: Metadata file not found at {META_PATH}")
        sys.exit(1)

    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)
    return index, metadata


def print_summary(index, metadata):
    """
    Print basic information about the loaded vector database.
    """
    print("=== Vector DB Summary ===")
    print(f"Index path: {INDEX_PATH}")
    print(f"Metadata path: {META_PATH}")
    print(f"Number of vectors: {index.ntotal}")
    # For flat indexes FAISS exposes dimension as 'd'
    dim = getattr(index, 'd', None)
    print(f"Vector dimension: {dim if dim is not None else 'unknown'}")
    print(f"Metadata entries: {len(metadata)}")
    print(f"Sample metadata: {metadata[:5]}")

    # If index supports reconstruction, show first vector slice
    if hasattr(index, 'reconstruct'):
        try:
            vec0 = index.reconstruct(0)
            print(f"First vector [0] (first 10 dims): {vec0[:10]}")
        except Exception:
            print("Index does not support reconstruct().")
    print("========================")


def main():
    index, metadata = load_index_and_metadata()
    print_summary(index, metadata)

    # Interactive lookup
    while True:
        selection = input("Enter vector ID to inspect (blank to exit): ").strip()
        if selection == "":
            break
        if not selection.isdigit():
            print("Please enter a valid integer ID or blank to exit.")
            continue
        idx = int(selection)
        if idx < 0 or idx >= len(metadata):
            print(f"Index {idx} out of range (0 to {len(metadata)-1}).")
            continue
        print(f"Metadata[{idx}]: {metadata[idx]}")
        if hasattr(index, 'reconstruct'):
            vec = index.reconstruct(idx)
            print(f"Vector[{idx}] (first 10 dims): {vec[:10]}")
        else:
            print("Cannot reconstruct vectors from this index.")

if __name__ == "__main__":
    main()

