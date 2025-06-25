import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


import pandas as pd
from pathlib import Path
from utils.granite import summarize_with_granite

LEDGER_PATH = Path("ledger/ledger.json")

def get_overview_metrics():
    if not LEDGER_PATH.exists():
        return 0, 0, 0, 0, 0, 0, 0, 0

    import json
    with open(LEDGER_PATH) as f:
        raw = json.load(f)

    df = pd.DataFrame(raw["history"])
    df.columns = [col.lower() for col in df.columns]

    if "date" not in df.columns:
        raise ValueError("Missing 'date' column in ledger history")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Normalize types to match income/expense logic
    df["type"] = df["type"].replace({"credit": "income", "debit": "expense"})
    df["month"] = df["date"].dt.to_period("M").astype(str)

    monthly = df.groupby(["month", "type"])["amount"].sum().unstack(fill_value=0).reset_index()
    monthly["net_profit"] = monthly.get("income", 0) - monthly.get("expense", 0)
    monthly["tax"] = 0.25 * monthly["net_profit"]

    if len(monthly) < 2:
        return 0, 0, 0, 0, 0, 0, 0, 0

    current = monthly.iloc[-1]
    previous = monthly.iloc[-2]

    def delta(cur, prev):
        if prev == 0:
            return 0
        return round(((cur - prev) / prev) * 100, 1)

    return (
        int(current["income"]),
        delta(current["income"], previous["income"]),
        int(current["expense"]),
        delta(current["expense"], previous["expense"]),
        int(current["net_profit"]),
        delta(current["net_profit"], previous["net_profit"]),
        int(current["tax"]),
        delta(current["tax"], previous["tax"]),
    )



def get_overview_narrative(revenue, expenses, profit, tax):
    prompt = f"""
        Based on the business ledger for the current month:
        - Revenue: ${revenue:,.0f}
        - Expenses: ${expenses:,.0f}
        - Net Profit: ${profit:,.0f}
        - Estimated Tax: ${tax:,.0f}
        
        Write a concise, professional summary (2–3 sentences) for a financial report.
        Ensure numbers and sentences are clearly separated and readable.
        """
    narrative = summarize_with_granite(prompt)
    narrative = narrative.replace(".", ". ").replace("  ", " ")
    print("narrative:::", narrative)
    return narrative


def get_monthly_overview():
    if not LEDGER_PATH.exists():
        return pd.DataFrame()

    import json
    with open(LEDGER_PATH) as f:
        raw = json.load(f)

    df = pd.DataFrame(raw["history"])
    df.columns = [col.lower() for col in df.columns]

    if "date" not in df.columns:
        raise ValueError("Missing 'date' column in ledger history")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["type"] = df["type"].replace({"credit": "income", "debit": "expense"})
    df["month"] = df["date"].dt.to_period("M").astype(str)

    summary = df.groupby(["month", "type"])["amount"].sum().unstack(fill_value=0).reset_index()
    summary["net_profit"] = summary.get("income", 0) - summary.get("expense", 0)
    summary["tax_liability"] = 0.25 * summary["net_profit"]
    return summary

import streamlit as st

def render_overview():
    (
        revenue, revenue_delta,
        expenses, expenses_delta,
        profit, profit_delta,
        tax, tax_delta
    ) = get_overview_metrics()

    st.title("📊 Accounting Bot Dashboard — Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Monthly Revenue", f"${revenue:,}", f"{revenue_delta}%")
        st.metric("Net Profit", f"${profit:,}", f"{profit_delta}%")
    with col2:
        st.metric("Total Expenses", f"${expenses:,}", f"{expenses_delta}%")
        st.metric("Tax Liability", f"${tax:,}", f"{tax_delta}%")

    st.markdown("---")
    st.subheader("📋 Monthly Financial Summary")

    narrative = get_overview_narrative(revenue, expenses, profit, tax)

    if narrative and isinstance(narrative, str) and narrative.strip():
        st.text(narrative.strip())
    else:
        st.warning("No summary generated.")

    st.markdown("---")
    st.subheader("📆 Monthly Breakdown")
    monthly_df = get_monthly_overview()
    st.dataframe(monthly_df, use_container_width=True)


if __name__ == "__main__":
    # Get financial metrics
    (
        revenue, revenue_delta,
        expenses, expenses_delta,
        profit, profit_delta,
        tax, tax_delta
    ) = get_overview_metrics()

    # Print raw numbers and percent change
    print("📊 Monthly Financial Metrics:")
    print(f"Revenue: ${revenue} ({revenue_delta}% change)")
    print(f"Expenses: ${expenses} ({expenses_delta}% change)")
    print(f"Net Profit: ${profit} ({profit_delta}% change)")
    print(f"Estimated Tax: ${tax} ({tax_delta}% change)")

    # Generate narrative
    narrative = get_overview_narrative(revenue, expenses, profit, tax)
    narrative = narrative.replace(".", ". ").replace("  ", " ")
    print("\n📝 Summary Narrative:")
    print(narrative)

    # Optionally display the monthly breakdown table
    print("\n📅 Monthly Breakdown:")
    print(get_monthly_overview())

