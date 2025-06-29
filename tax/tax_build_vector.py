# tax/vector_db.py
import os
import json
from pathlib import Path
from langchain_core.documents import Document
from langchain_ibm import WatsonxEmbeddings
from langchain.vectorstores import Chroma
from config.settings import GRANITE_API_KEY,GRANITE_ENDPOINT,GRANITE_PROJECT_ID
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes

TAX_VECTOR_INDEX_PATH = "tax/tax_vector_store"

class TaxVectorDB:
    def __init__(self, input_json_path: str, persist_dir: str = TAX_VECTOR_INDEX_PATH):
        self.input_json_path = input_json_path
        self.persist_dir = persist_dir
        self.docs = []
        self.vectorstore = None

        self.embedder = WatsonxEmbeddings(
            model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
            url=GRANITE_ENDPOINT,
            apikey=GRANITE_API_KEY,
            project_id=GRANITE_PROJECT_ID
        )

    def flatten_country_text(self, country: str, payload: dict) -> str:
        parts = [f"Country: {country}"]
        if payload.get("currency"):
            parts.append(f"Currency: {payload['currency']}")
        parts.append("Brackets:")
        for b in payload.get("brackets", []):
            min_inc = b.get("min_income")
            max_inc = b.get("max_income", "∞") if b.get("max_income") is None else b.get("max_income")
            rate = b.get("rate", 0.0) * 100
            parts.append(f"{min_inc}–{max_inc} at {rate:.1f}%")

        parts.append("Deductions:")
        for d in payload.get("deductions", []):
            if "max_amount" in d:
                parts.append(f"{d['name']} up to {d['max_amount']}")
            elif "percent" in d or "rate" in d:
                rate = d.get("percent", d.get("rate", 0.0)) * 100
                parts.append(f"{d['name']} at {rate:.1f}%")
            else:
                parts.append(d.get("name", ""))

        parts.append("Subsidies:")
        for s in payload.get("subsidies", []):
            parts.append(f"{s['name']}: {s['description']}")

        return "\n".join(parts)

    def build_and_persist(self):
        if not os.path.exists(self.input_json_path):
            raise FileNotFoundError(f"❌ JSON not found at {self.input_json_path}")

        with open(self.input_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        documents = []
        for country, payload in data.items():
            text = self.flatten_country_text(country, payload)
            doc = Document(page_content=text, metadata={"country": country})
            documents.append(doc)

        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embedder,
            persist_directory=self.persist_dir
        )
        print(f"✅ Tax vector DB saved to: {self.persist_dir}")

if __name__ == "__main__":
    taxvectorDB = TaxVectorDB("tax/tax_subsidy_bracket.json")
    taxvectorDB.build_and_persist()