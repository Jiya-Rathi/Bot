import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

# Load FAISS index and metadata
faiss_index_path = "dash_modules/smb_faiss_index.faiss"
metadata_path = "dash_modules/smb_faiss_metadata.pkl"

print("📦 Loading FAISS index and metadata...")
index = faiss.read_index(faiss_index_path)
with open(metadata_path, "rb") as f:
    metadata = pickle.load(f)

# Load sentence transformer
print("🧠 Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Define your company profile as a natural language query
query_text = (
    "Retail SMB in India (Urban) with 25 employees, $2,000,000 revenue, "
    "5 years, model: B2C, cash runway: 2.5 months, profit margin: 0.08, "
    "churn: 0.18, recurring revenue: 0.4, revenue predictability: 0.6, "
    "concentration: 0.3, cash flow: adequate"
)

# Embed and search
print("🔍 Searching for similar SMBs...")
query_vector = model.encode([query_text]).astype("float32")
distances, indices = index.search(query_vector, k=5)

# Show top-k results
print("\n🎯 Top 5 Similar SMBs:")
for rank, i in enumerate(indices[0], 1):
    doc = metadata[i]
    print(f"{rank}. {doc['industry']} in {doc['country']} | Revenue: ${doc['revenue']:,} | "
          f"Employees: {doc['employees']} | Margin: {doc['net_profit_margin']} | "
          f"Runway: {doc['cash_runway_months']} mo | Flow: {doc['cash_flow_rating']}")
