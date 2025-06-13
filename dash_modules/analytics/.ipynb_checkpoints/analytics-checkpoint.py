# modules/analytics.py
import pandas as pd
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta

LEDGER_PATH = Path("ledger/active_ledger.csv")

def get_top_customers_and_expenses():
    if not LEDGER_PATH.exists():
        return [], []

    df = pd.read_csv(LEDGER_PATH)
    
    # Optional: unify column casing
    df.columns = df.columns.str.lower()
    
    if "source" not in df.columns:
        df["source"] = "Unknown"
    if "category" not in df.columns:
        df["category"] = "Uncategorized"

    # Top 3 customers (by income)
    top_customers = (
        df[df["type"] == "income"]
        .groupby("source")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
        .reset_index()
        .to_dict(orient="records")
    )

    # Top 3 expenses (by category/vendor)
    top_expenses = (
        df[df["type"] == "expense"]
        .groupby("source")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
        .reset_index()
        .to_dict(orient="records")
    )

    return top_customers, top_expenses

def explain_top_customers(customers):
    names = ", ".join([c["source"] for c in customers])
    total = sum(c["amount"] for c in customers)

    prompt = f"""
    The top 3 revenue sources this month were: {names}, totaling ${total}.
    Write a short analysis about what this might mean for business focus.
    """
    return summarize_with_granite(prompt)
