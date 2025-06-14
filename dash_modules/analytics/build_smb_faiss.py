import pandas as pd
import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer

def format_for_embedding(row):
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

def main():
    df = pd.read_csv("data/global_smb_benchmark_dataset_5000.csv")
    
    df["embedding_text"] = df.apply(format_for_embedding, axis=1)

    print("Generating vector embeddings")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(df["embedding_text"].tolist(), show_progress_bar=True)

    print("Building FAISS index")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))

    print("Saving index and metadata")
    faiss.write_index(index, "dash_modules/smb_faiss_index.faiss")
    with open("dash_modules/smb_faiss_metadata.pkl", "wb") as f:
        pickle.dump(df.to_dict(orient="records"), f)

    print("✅ FAISS index and metadata saved!")

if __name__ == "__main__":
    main()
