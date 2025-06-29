import os
import json
from langchain_core.documents import Document
from langchain_ibm import WatsonxEmbeddings
from langchain.vectorstores import Chroma
from config.settings import GRANITE_API_KEY,GRANITE_ENDPOINT,GRANITE_PROJECT_ID
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes

class LoanVectorDB:
    def __init__(self, json_path: str, persist_dir: str = "loan"):
        self.json_path = json_path
        self.persist_dir = persist_dir
        self.docs = []
        self.vectorstore = None

        self.embedder = WatsonxEmbeddings(
            model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
            url=GRANITE_ENDPOINT,
            apikey=GRANITE_API_KEY,
            project_id=GRANITE_PROJECT_ID
        )

    def load_loan_data(self):
        with open(self.json_path, "r") as f:
            data = json.load(f)

        documents = []
        for country, loans in data.items():
            for loan in loans:
                content = f"""
Loan Name: {loan['loan_name']}
Bank: {loan['bank_name']}
Country: {country}
Eligibility: {loan['eligibility_criteria']}
Amount Range: {loan['min_amount']} – {loan['max_amount']}
Interest Rate: {loan.get('interest_rate', 'N/A')}
Tenure: {loan.get('tenure', 'N/A')}
Collateral Required: {loan.get('collateral_required', 'N/A')}
Repayment Terms: {loan.get('repayment_terms', 'N/A')}
                """.strip()

                metadata = {
                    "country": country,
                    "loan_name": loan['loan_name'],
                    "bank_name": loan['bank_name']
                }

                documents.append(Document(page_content=content, metadata=metadata))

        self.docs = documents

    def build_and_persist(self):
        self.load_loan_data()
        self.vectorstore = Chroma.from_documents(
            documents=self.docs,
            embedding=self.embedder,
            persist_directory=self.persist_dir
        )