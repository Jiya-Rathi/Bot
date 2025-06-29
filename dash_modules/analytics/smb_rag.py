# smb_rag.py

import json
from typing import Dict, Any

from langchain_ibm import WatsonxEmbeddings
from langchain_community.vectorstores import Chroma
from granite.client import GraniteAPI
from config.settings import GRANITE_API_KEY, GRANITE_ENDPOINT, GRANITE_PROJECT_ID
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes

SMB_VECTOR_INDEX_PATH = "dash_modules/analytics/smb_chroma_db"

class SMBBenchmarkRAG:
    def __init__(self, persist_dir: str = SMB_VECTOR_INDEX_PATH):
        self.persist_dir = persist_dir
        self.embedder = WatsonxEmbeddings(
            model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
            url=GRANITE_ENDPOINT,
            apikey=GRANITE_API_KEY,
            project_id=GRANITE_PROJECT_ID
        )
        try:
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embedder
            )
        except Exception as e:
            print(f"⚠️ Failed to load SMB benchmark vector store: {e}")
            self.vectorstore = None

    def _semantic_search(self, query: str, filters: dict = {}, top_k: int = 10):
        docs = self.vectorstore.similarity_search(query, k=top_k)
    
        def passes_filters(doc):
            for key, val in filters.items():
                if val is not None and str(doc.metadata.get(key)).lower() != str(val).lower():
                    return False
            return True
    
        return [doc for doc in docs if passes_filters(doc)]


    def query(self, query: str, filters: dict = {}, top_k: int = 10) -> list:
        try:
            context_docs = self._semantic_search(query, filters=filters, top_k=top_k)
            return [doc.metadata for doc in context_docs]
        except Exception as e:
            print(f"⚠️ Query error: {e}")
            return []

