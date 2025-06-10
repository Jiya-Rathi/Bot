# ─── utils/vector_index.py ────────────────────────────────────────────────────

import os
import pickle
from config.settings import SBA_VECTOR_INDEX_PATH

class RAGLoanAdvisor:
    """
    Uses a pre-built vector index (e.g., on SBA.gov docs) to answer loan‐related questions.
    You can implement this with FAISS, Pinecone, or any vector DB―here is a placeholder.
    """
    def __init__(self, index_path: str = None):
        self.index_path = index_path or SBA_VECTOR_INDEX_PATH
        self.index = None
        self._load_index()

    def _load_index(self):
        """
        Load your SBA.gov vector index from disk. 
        E.g., if you used FAISS + pickle, or a JSON embedding store, etc.
        """
        if os.path.exists(self.index_path):
            with open(self.index_path, 'rb') as f:
                self.index = pickle.load(f)
        else:
            self.index = None

    def query(self, question: str, top_k: int = 3) -> list:
        """
        Return top_k context passages/documents + embeddings to feed into an LLM (Granite).
        Example return: [{'text': "...", 'score': 0.87}, ...]
        """
        if not self.index:
            return []
        # TODO: replace with your actual FAISS/Pinecone lookup logic
        # For now, return an empty list or dummy
        return []

    def answer_loan_question(self, granite_client, question: str) -> str:
        """
        Given a free‐text question about SBA loans, retrieve top‐k contexts,
        then send a RAG‐style prompt to Granite.
        """
        contexts = self.query(question)
        context_text = "\n\n".join([doc['text'] for doc in contexts])

        prompt = f"""
You are a small‐business loan advisor. Use the following SBA.gov excerpts to answer the question.
Context:
{context_text}

Question: "{question}"

Provide a concise, actionable answer, citing SBA.gov where appropriate.
"""
        try:
            return granite_client.generate_text(prompt, max_tokens=256, temperature=0.3)
        except Exception:
            return "Sorry, I couldn’t retrieve loan information at the moment."
