# loan/query_engine.py
import os
from langchain_ibm import WatsonxEmbeddings
from langchain.vectorstores import Chroma
from utils.business_profile import load_profile
from utils.granite import summarize_with_granite
from config.settings import GRANITE_API_KEY,GRANITE_ENDPOINT,GRANITE_PROJECT_ID
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes

class RAGLoanAdvisor:
    """
    Uses Chroma + WatsonxEmbeddings for RAG-based loan recommendation.
    """

    def __init__(self, persist_dir="loan"):
        self.persist_dir = persist_dir
        self.embedder = WatsonxEmbeddings(
            model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
            url=GRANITE_ENDPOINT,
            apikey=GRANITE_API_KEY,
            project_id=GRANITE_PROJECT_ID
        )
        self.vectorstore = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self.embedder
        )

    def query(self, question: str, top_k: int = 5) -> list:
        """
        Embed the question, run semantic search, filter by country from profile.
        """
        profile = load_profile()
        user_country = profile.get("country", "").lower()

        docs = self.vectorstore.similarity_search(question, k=top_k + 10)
        filtered = [
            {
                "text": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in docs if doc.metadata.get("country", "").lower() == user_country
        ]

        return filtered[:top_k]

    def answer_loan_question(self, question: str) -> str:
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