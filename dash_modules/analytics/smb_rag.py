# smb_rag.py
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

class SMBBenchmarkRAG:
    def __init__(self, index_path="dash_modules/analytics/smb_faiss_index.faiss", metadata_path="dash_modules/analytics/smb_faiss_metadata.pkl"):
        self.index = faiss.read_index(index_path)
        with open(metadata_path, "rb") as f:
            self.docs = pickle.load(f)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def query(self, query: str, filters: dict = {}, top_k: int = 10):
        embedding = self.model.encode([query]).astype("float32")
        distances, indices = self.index.search(embedding, top_k)
        results = [self.docs[i] for i in indices[0]]

        def passes_filters(doc):
            for key, val in filters.items():
                if val is not None and str(doc.get(key)).lower() != str(val).lower():
                    return False
            return True

        return [r for r in results if passes_filters(r)]
