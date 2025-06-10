# ─── config/settings.py ────────────────────────────────────────────────────────

import os

# Granite credentials
GRANITE_API_KEY     = os.getenv("GRANITE_API_KEY", "Q64AAxJfpKRQzuXuSyTM7YyeAXkaGeZZ7HJYYCpwHV-3")
GRANITE_ENDPOINT = os.getenv("GRANITE_ENDPOINT", "https://us-south.ml.cloud.ibm.com")
GRANITE_MODEL_NAME  = "ibm/granite-13b-instruct-v2"
GRANITE_PROJECT_ID = os.getenv("GRANITE_PROJECT_ID", "6e2f5a1b-5e91-45e7-95c1-4d81614418e4")

SBA_VECTOR_INDEX_PATH = "../loan/loan_faiss.index"

# Path to a (local) vector index containing global tax‐code documents.
# For demo/hackathon, you could fingerprint a small set of PDF/text files
# about SMB tax rules per country, compute embeddings, and store them here.
TAX_VECTOR_INDEX_PATH = os.getenv("TAX_VECTOR_INDEX_PATH", "tax_vector_index.pkl")

# Prophet forecast default periods
PROPHET_DEFAULT_PERIODS = 30  # days to forecast
