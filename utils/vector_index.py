import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from config.settings import SBA_VECTOR_INDEX_PATH, SBA_DOCS_PATH
from utils.business_profile import load_profile
from utils.granite import summarize_with_granite


class RAGLoanAdvisor:
    """
    Uses FAISS-based RAG to recommend loans based on user question and profile.
    """

    def __init__(self, index_path: str = None, docs_path: str = None):
        self.index_path = index_path or SBA_VECTOR_INDEX_PATH      # e.g., "loan/index.faiss"
        self.doc_path = docs_path or SBA_DOCS_PATH                 # e.g., "loan/index.pkl"
        self.index = None
        self.index_docs = []
        self.model = SentenceTransformer("all-MiniLM-L6-v2")       # Use same model as during indexing
        self._load_index()

    def _load_index(self):
        """
        Load FAISS index and loan metadata from disk.
        """
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            print(f"❌ FAISS index not found at {self.index_path}")
            self.index = None

        if os.path.exists(self.doc_path):
            with open(self.doc_path, "rb") as f:
                self.index_docs = pickle.load(f)
        else:
            print(f"❌ Metadata (.pkl) not found at {self.doc_path}")
            self.index_docs = []

    def query(self, question: str, top_k: int = 5) -> list:
        """
        Embed the question, run semantic search, filter by country from profile.
        """
        if not self.index or not self.index_docs:
            return []

        profile = load_profile()
        user_country = profile.get("country", "").lower()

        # Step 1: Embed the user query
        embedding = self.model.encode([question])
        embedding = np.array(embedding).astype('float32')

        # Step 2: Perform FAISS search
        distances, indices = self.index.search(embedding, top_k + 10)  # over-fetch for country filtering

        results = []
        for idx, score in zip(indices[0], distances[0]):
            if idx >= len(self.index_docs):
                continue

            doc = self.index_docs[idx]
            doc_country = doc.get("country", "").lower()

            if doc_country == user_country:
                results.append({
                    "text": (
                        f"Loan Name: {doc['loan_name']}\n"
                        f"Bank: {doc['bank_name']}\n"
                        f"Eligibility: {doc['eligibility_criteria']}\n"
                        f"Amount Range: {doc['min_amount']} – {doc['max_amount']}\n"
                        f"Interest Rate: {doc.get('interest_rate', 'N/A')}\n"
                        f"Tenure: {doc.get('tenure', 'N/A')}\n"
                        f"Collateral Required: {doc.get('collateral_required', 'N/A')}\n"
                        f"Repayment Terms: {doc.get('repayment_terms', 'N/A')}\n"
                    ),
                    "score": float(score),
                    "source": doc
                })

            if len(results) >= top_k:
                break

        return results

    def answer_loan_question(self, granite_client, question: str) -> str:
        """
        Retrieve top-k relevant loan options and generate an LLM-based answer.
        """
        contexts = self.query(question)
        if not contexts:
            return "❌ No loan matches found for your country or business profile."

        context_text = "\n\n".join([doc['text'] for doc in contexts])

        prompt = f"""
You are a small‐business loan advisor. Based on the following loan listings and eligibility criteria, answer the user's question.

Context:
\"\"\"{context_text}\"\"\"

Question: "{question}"

Provide a short, actionable recommendation. Focus only on loans relevant to the user's region and small business size.
"""

        try:
            print("loan prompt ::: ", prompt)
            return summarize_with_granite(prompt, temperature=0.2, max_new_tokens=700)
        except Exception:
            return "Sorry, I couldn’t retrieve loan information at the moment."
