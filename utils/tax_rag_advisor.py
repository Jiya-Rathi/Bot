# ─── utils/tax_rag_advisor.py ─────────────────────────────────────────────────

import os
import pickle
import json
import faiss
import numpy as np
from typing import Dict, Any, List

from sentence_transformers import SentenceTransformer
from granite.client import GraniteAPI
from config.settings import TAX_VECTOR_INDEX_PATH


class TaxRAGAdvisor:
    """
    1. Attempts to load a pre‐built FAISS vector index of global SMB tax documents.
    2. If the index exists, runs a semantic search over “SMB tax code for {country}”.
    3. If not available, it falls back to prompting Granite to generate SMB tax details.
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
        Load FAISS index and metadata (index.pkl or .meta.pkl) from disk.
        """
        if not os.path.exists(self.index_path):
            print("⚠️ No tax index found. Will use LLM fallback.")
            return

        try:
            if os.path.isdir(self.index_path):
                faiss_file = os.path.join(self.index_path, "index.faiss")
                metadata_file = os.path.join(self.index_path, "index.pkl")
            else:
                faiss_file = self.index_path
                metadata_file = self.index_path + ".meta.pkl"

            if not os.path.exists(faiss_file):
                raise FileNotFoundError(f"FAISS index not found at {faiss_file}")

            self.index = faiss.read_index(faiss_file)

            if os.path.exists(metadata_file):
                with open(metadata_file, "rb") as f:
                    self.index_docs = pickle.load(f)
            else:
                print("⚠️ Metadata file not found; proceeding with empty document list.")
                self.index_docs = []

            # Normalize to strings
            if isinstance(self.index_docs, dict):
                self.index_docs = [v.page_content for v in self.index_docs.values()]
            else:
                self.index_docs = [
                    doc.page_content if hasattr(doc, "page_content") else str(doc)
                    for doc in self.index_docs
                ]

            print(f"✅ Tax vector index loaded ({len(self.index_docs)} entries).")

        except Exception as e:
            print(f"⚠️ Failed to load tax vector index: {e}")
            self.index = None
            self.index_docs = []

    def _semantic_search(self, country: str, top_k: int = 1) -> str:
        """
        Given a country string, run a semantic search in self.index to retrieve
        top_k passages. Returns a concatenated string of those passages.
        """
        if self.index is None or not self.index_docs:
            print("ℹ️ Semantic search skipped — index or docs missing.")
            return ""

        query = f"SMB tax code for {country}"
        try:
            query_vec = self.embedder.encode([query], normalize_embeddings=True)
            query_vec = np.array(query_vec, dtype=np.float32).reshape(1, -1)
            distances, indices = self.index.search(query_vec, top_k)

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
        Use RAG or fallback prompt to get SMB tax structure for `country`.
        Returns dict with keys: brackets, deductions, subsidies.
        """
        context_text = self._semantic_search(country)
        
        if context_text:
            print(f"🔍 Using semantic search context for {country}")
            prompt = f"""
    Below are excerpts from official SMB tax documents for {country}. 
    Extract and return a JSON object with:
    1) "brackets": list of objects with "min_income", "max_income", "rate" (decimal).
    2) "deductions": list of objects with "name" and "max_amount" or "percent".
    3) "subsidies": list of objects with "name" and "description".
    
    IMPORTANT: 
    - Use decimal rates (e.g., 0.05 for 5%)
    - Use null for unlimited maximum income
    - Use proper JSON syntax (not Python)
    
    Context Excerpts:
    \"\"\"{context_text}\"\"\"
    
    Respond ONLY with a valid JSON object.
    """
        else:
            print(f"📄 No RAG context available. Falling back to LLM-only prompt for {country}")
            rompt = f"""
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
            # First attempt - normal prompt
            granite_reply = self.granite.generate_text(prompt, max_tokens=512, temperature=0)
            
            # If empty response, try again with a higher temperature
            if not granite_reply or len(granite_reply.strip()) < 10:
                granite_reply = self.granite.generate_text(prompt, max_tokens=512, temperature=0.3)
            
            # Clean up common JSON errors before parsing
            granite_reply = (granite_reply
                .replace(",\n]", "\n]")
                .replace(",]", "]")
                .replace("None", "null")
                .replace("True", "true")
                .replace("False", "false"))
            
            # If response still doesn't contain valid JSON, generate a skeleton
            if "{" not in granite_reply:
                print("No JSON found in response. Using hardcoded structure for known countries.")
                if "india" in country.lower():
                    return {
                        "brackets": [
                            {"min_income": 0, "max_income": 250000, "rate": 0.0},
                            {"min_income": 250001, "max_income": 500000, "rate": 0.05},
                            {"min_income": 500001, "max_income": 1000000, "rate": 0.20},
                            {"min_income": 1000001, "max_income": None, "rate": 0.30}
                        ],
                        "deductions": [
                            {"name": "Standard Deduction", "max_amount": 50000, "percent": None},
                            {"name": "Professional Tax", "max_amount": 2500, "percent": None}
                        ],
                        "subsidies": [
                            {"name": "Startup India Initiative", "description": "Tax exemptions for eligible startups for 3 years"},
                            {"name": "MSME Credit Guarantee", "description": "Collateral-free loans up to Rs 2 crore"}
                        ]
                    }
                # Add other common countries as needed
                
            # Extract only the JSON part if there's extra text
            if '{' in granite_reply and '}' in granite_reply:
                start = granite_reply.find('{')
                end = granite_reply.rfind('}') + 1
                granite_reply = granite_reply[start:end]
                
            # Try to parse the JSON
            tax_data = json.loads(granite_reply)
            return tax_data
            
        except Exception as e:
            print(f"⚠️ Failed to parse Granite JSON for {country}: {e}")
            print(f"Raw response: {granite_reply}")
            
            # Deeper error recovery - extract directly from context
            if context_text and "brackets" in context_text.lower():
                print("Attempting direct extraction from context")
                try:
                    # Very simple direct extraction for emergency cases
                    brackets = []
                    if "Brackets:" in context_text:
                        bracket_section = context_text.split("Brackets:")[1].split("Deductions:")[0] if "Deductions:" in context_text else context_text.split("Brackets:")[1]
                        for line in bracket_section.strip().split('\n'):
                            if "%" in line and ("–" in line or "-" in line) and "at" in line:
                                parts = line.split("at")
                                range_part = parts[0].strip().replace('–', '-')
                                rate_part = float(parts[1].strip().replace('%', '')) / 100
                                
                                range_values = range_part.split('-')
                                min_val = int(range_values[0].replace(',', ''))
                                max_val = None if "None" in range_values[1] else int(range_values[1].replace(',', ''))
                                
                                brackets.append({
                                    "min_income": min_val,
                                    "max_income": max_val,
                                    "rate": rate_part
                                })
                    
                    # Return whatever we could extract
                    return {"brackets": brackets, "deductions": [], "subsidies": []}
                except:
                    pass
                    
            return {}
