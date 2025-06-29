# smb/vector_db.py

import os
import pandas as pd
from langchain_core.documents import Document
from langchain_ibm import WatsonxEmbeddings
from langchain.vectorstores import Chroma
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes
from config.settings import GRANITE_API_KEY, GRANITE_ENDPOINT, GRANITE_PROJECT_ID

SMB_VECTOR_INDEX_PATH = "dash_modules/analytics/smb_chroma_db"

class SMBBenchmarkVectorDB:
    def __init__(self, input_csv_path: str, persist_dir: str = SMB_VECTOR_INDEX_PATH):
        self.input_csv_path = input_csv_path
        self.persist_dir = persist_dir
        self.docs = []
        self.vectorstore = None

        self.embedder = WatsonxEmbeddings(
            model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
            url=GRANITE_ENDPOINT,
            apikey=GRANITE_API_KEY,
            project_id=GRANITE_PROJECT_ID
        )

    def format_for_embedding(self, row) -> str:
        return (
            f"{row['industry']} SMB in {row['country']} ({row['region']}) with "
            f"{row['employees']} employees, ${row['revenue']:,.0f} revenue, "
            f"{row['years_in_business']} years, model: {row['business_model']}, "
            f"cash runway: {row['cash_runway_months']} months, profit margin: {row['net_profit_margin']}, "
            f"churn: {row['customer_churn_rate']}, recurring revenue: {row['recurring_revenue_pct']}, "
            f"revenue predictability: {row['revenue_predictability']}, "
            f"concentration: {row['revenue_concentration_pct']}, "
            f"cash flow: {row['cash_flow_rating']}"
        )

    def build_and_persist(self):
        if not os.path.exists(self.input_csv_path):
            raise FileNotFoundError(f"❌ CSV not found at {self.input_csv_path}")

        df = pd.read_csv(self.input_csv_path)

        documents = []
        for _, row in df.iterrows():
            text = self.format_for_embedding(row)
            doc = Document(page_content=text, metadata=row.to_dict())
            documents.append(doc)

        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embedder,
            persist_directory=self.persist_dir
        )
        print(f"✅ SMB Benchmark vector DB saved to: {self.persist_dir}")

if __name__ == "__main__":
    smb_vector_db = SMBBenchmarkVectorDB("data/global_smb_benchmark_dataset_5000.csv")
    smb_vector_db.build_and_persist()