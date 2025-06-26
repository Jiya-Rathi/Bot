import json
import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np
from loan.config import JSON_PATH, INDEX_PATH, MODEL_NAME


class LoanVectorDB:
    def __init__(self, json_path: str = JSON_PATH, index_path: str = INDEX_PATH, model_name: str = MODEL_NAME):
        self.json_path = json_path
        self.index_path = index_path  # Without extension
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.embeddings = None
        self.index_docs = []

    def load_and_embed(self):
        with open(self.json_path, "r") as f:
            data = json.load(f)

        all_texts = []
        for country, loans in data.items():
            for loan in loans:
                text = f"{loan['loan_name']} by {loan['bank_name']} in {country}: {loan['eligibility_criteria']}, Amount: {loan['min_amount']}–{loan['max_amount']}"
                loan["country"] = country  # 🔒 Ensure country is part of metadata
                self.index_docs.append(loan)
                all_texts.append(text)

        embeddings = self.model.encode(all_texts, show_progress_bar=True)
        self.embeddings = np.array(embeddings).astype('float32')

    def build_index(self):
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(self.embeddings)

    def save_index(self):
        faiss.write_index(self.index, self.index_path + ".faiss")  # ✅ Standardized to .faiss
        with open(self.index_path + ".pkl", "wb") as f:            # ✅ Metadata as .pkl
            pickle.dump(self.index_docs, f)

    def build_and_save(self):
        self.load_and_embed()
        self.build_index()
        self.save_index()
