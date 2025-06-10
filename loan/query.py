# loan/query.py

import json
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
from loan.config import INDEX_PATH, MODEL_NAME


class LoanQueryEngine:
    def __init__(self, index_path: str = INDEX_PATH, model_name: str = MODEL_NAME):
        self.index_path = index_path
        self.model = SentenceTransformer(model_name)

        # Load FAISS index
        self.index = faiss.read_index(index_path)

        # Load metadata for retrieved results
        with open(index_path + ".meta.json", "r") as f:
            self.index_docs = json.load(f)

    def query(self, user_query: str, top_k: int = 3):
        """Run semantic search using FAISS index."""
        q_embedding = self.model.encode([user_query])
        q_embedding = np.array(q_embedding).astype('float32')
        _, I = self.index.search(q_embedding, top_k)
        return [self.index_docs[i] for i in I[0]]

    def format_for_whatsapp(self, loans, max_len=3):
        """Format top-k results in WhatsApp-friendly format."""
        messages = []
        for i, loan in enumerate(loans[:max_len], 1):
            msg = (
                f"🔹 Loan Option {i}:\n"
                f"🏦 Bank: {loan['bank_name']}\n"
                f"📌 Name: {loan['loan_name']}\n"
                f"💰 Amount: {loan['min_amount']} – {loan['max_amount']}\n"
                f"📈 Interest: {loan['interest_rate']}\n"
                f"🧾 Eligibility: {loan['eligibility_criteria']}\n"
            )
            if 'collateral_required' in loan:
                msg += f"🧭 Collateral: {loan['collateral_required']}\n"
            if 'documentation_required' in loan:
                docs = ', '.join(loan['documentation_required'])
                msg += f"📄 Docs: {docs}\n"
            msg += "—" * 20
            messages.append(msg)
        return "\n\n".join(messages)
