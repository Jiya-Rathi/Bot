import os
import json
import faiss
import pickle
import numpy as np
from typing import Dict, Any, List

from sentence_transformers import SentenceTransformer
from granite.client import GraniteAPI
from config.settings import TAX_VECTOR_INDEX_PATH

class TaxRAGAdvisor:
    """
    Semantic retriever + generation wrapper for SMB tax information.
    Loads a FAISS index and its metadata if available.
    """

    def __init__(self, granite_client: GraniteAPI, index_path: str = None):
        self.granite = granite_client
        self.index_path = index_path or TAX_VECTOR_INDEX_PATH
        self.index = None
        self.index_docs: List[str] = []
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self._load_index()

    def _load_index(self):
        """
        Load FAISS index and accompanying metadata (.meta.pkl).
        """
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.index_path + ".meta.pkl", "rb") as f:
                    self.index_docs = pickle.load(f)
                print(f"✅ Tax vector index loaded ({len(self.index_docs)} entries).")
            except Exception as e:
                print(f"⚠️ Failed to load tax vector index: {e}")
        else:
            print("⚠️ No tax index found. Will use LLM fallback.")

    def _semantic_search(self, country: str, top_k: int = 3) -> str:
        """
        Embed the query and retrieve top-k closest entries from FAISS index.
        Returns a string with top contexts joined by double newlines.
        """
        if not self.index or not self.index_docs:
            return ""

        query = f"SMB tax code for {country}"
        try:
            query_vec = self.embedder.encode([query], normalize_embeddings=True)
            distances, indices = self.index.search(np.array(query_vec), top_k)

            hits = [
                self.index_docs[i]
                for i in indices[0]
                if 0 <= i < len(self.index_docs)
            ]
            return "\n\n".join(hits)
        except Exception as e:
            print(f"⚠️ Semantic search failed: {e}")
            return ""

    def fetch_tax_brackets(self, country: str) -> Dict[str, Any]:
        """
        Get structured SMB tax info for a given country, either via RAG or fallback prompt.
        Returns a dictionary with "brackets", "deductions", and "subsidies".
        """
        context = self._semantic_search(country)
        if context:
            prompt = f"""
Below are excerpts from official SMB tax documents for {country}. 
Extract and return a JSON object with:
1) "brackets": list of objects with "min_income", "max_income", "rate" (decimal).
2) "deductions": list of objects with "name" and "max_amount" or "percent".
3) "subsidies": list of objects with "name" and "description".

Context Excerpts:
\"\"\"{context}\"\"\"

Respond ONLY with a valid JSON object.
"""
        else:
            prompt = f"""
You are a knowledgeable global tax advisor. Provide, in JSON format, the key SMB 
tax details for {country}, including:
1) "brackets": each with "min_income", "max_income", "rate"
2) "deductions": each with "name", and "max_amount" or "percent"
3) "subsidies": each with "name" and "description"

Example:
{{
  "brackets": [
    {{"min_income": 0, "max_income": 50000, "rate": 0.10}},
    {{"min_income": 50001, "max_income": 100000, "rate": 0.20}}
  ],
  "deductions": [
    {{"name": "Startup Deduction", "max_amount": 5000}}
  ],
  "subsidies": [
    {{"name": "SMB Tech Grant", "description": "Tax credit for adopting digital tools."}}
  ]
}}
"""

        try:
            response = self.granite.generate_text(prompt, max_tokens=512, temperature=0.0)
            return json.loads(response)
        except Exception as e:
            print(f"⚠️ Failed to parse Granite JSON for {country}: {e}")
            return {}
