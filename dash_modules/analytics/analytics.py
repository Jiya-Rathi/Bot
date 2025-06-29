# modules/analytics.py
import pandas as pd
from pathlib import Path
from utils.granite import summarize_with_granite
import json
import streamlit as st
from dash_modules.analytics.run_smb_analysis import run_smb_analysis
from cashflow_forecasting.forecasting_engine import CashFlowForecaster, ForecastExplainer
from granite.client import GraniteAPI
from utils.business_profile import load_profile, save_profile, needs_profile_info

LEDGER_PATH = Path("ledger/ledger.json")

def get_top_customers_and_expenses():
    if not LEDGER_PATH.exists():
        return [], []

    with open(LEDGER_PATH) as f:
        raw = json.load(f)

    df = pd.DataFrame(raw["history"])

    if df.empty:
        return [], []

    df.columns = df.columns.str.lower()
    df["type"] = df["type"].replace({"credit": "income", "debit": "expense"})
    df["source"] = df["desc"].fillna("Unknown")

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

    # Top 3 expenses (by source)
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
    The top 3 revenue sources this month were: {names}, totaling ${total:,.0f}.
    Write a short analysis about what this might mean for business focus.
    """
    return summarize_with_granite(prompt)

def render_top_entities(title, data):
    st.subheader(title)
    if not data:
        st.write("No data available.")
        return

    import pandas as pd
    df = pd.DataFrame(data)
    df["amount"] = df["amount"].map("${:,.2f}".format)  # format with $ and commas
    df.rename(columns={"source": "Source", "amount": "Amount"}, inplace=True)
    st.table(df)  # or use st.dataframe(df) for interactive version

def render_analysis():
    st.title("📊 Analytics")

    top_customers, top_expenses = get_top_customers_and_expenses()

    col1, col2 = st.columns(2)
    with col1:
        render_top_entities("🏅 Top 3 Revenue Sources", top_customers)
    with col2:
        render_top_entities("💸 Top 3 Expense Sources", top_expenses)

    # Optional explanation
    if top_customers:
        names = ", ".join([c["source"] for c in top_customers])
        total = sum(c["amount"] for c in top_customers)
        prompt = f"""
        The top 3 revenue sources this month were: {names}, totaling ${total:,.0f}.
        Write a short analysis about what this might mean for business focus.
        """
        narrative = summarize_with_granite(prompt)
        st.markdown("---")
        st.subheader("📝 Revenue Insight (LLM-generated)")
        st.markdown(narrative)

    st.markdown("---")
    st.subheader("📉 Cash Flow Forecast")

    # Forecast Section
    with open(LEDGER_PATH) as f:
        raw = json.load(f)

    df = pd.DataFrame(raw["history"])
    df.columns = df.columns.str.lower()

    # Filter only credit and debit
    df = df[df["type"].isin(["credit", "debit"])]

    # Parse date and clean
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Convert to 'Credit' and 'Debit' format expected by forecaster
    df["credit"] = df.apply(lambda row: row["amount"] if row["type"] == "credit" else 0, axis=1)
    df["debit"] = df.apply(lambda row: row["amount"] if row["type"] == "debit" else 0, axis=1)

    # Rename for forecaster
    df = df.rename(columns={"date": "Date", "credit": "Credit", "debit": "Debit"})

    # Run forecast
    forecaster = CashFlowForecaster()
    forecast_df = forecaster.forecast(df, days=30)

    # Streamlit plot
    st.line_chart(forecast_df.set_index("ds")["yhat"])

    # Forecast explainer
    granite = GraniteAPI()
    explainer = ForecastExplainer(granite)

    forecast_narrative = explainer.explain_forecast(forecast_df)
    st.markdown("### 🔍 Forecast Explanation")
    st.markdown(forecast_narrative)

    st.markdown("---")
    st.subheader("📈 Financial Health Report")

    with st.expander("Run full SMB financial analysis"):
        business_profile = load_profile()

        result = run_smb_analysis(business_profile)

        st.markdown("### 🎯 Financial Health Score")
        score = result["score"]
        st.text(f"""
        Overall Score: {score['overall_score']}/100
        Health Rating: {score['health_rating']}
        Peer Comparisons: {score['peer_count']} similar companies

        Detailed Breakdown:
          • Liquidity Score: {score['detailed_scores']['liquidity_score']:.1f}/100
          • Profitability Score: {score['detailed_scores']['profitability_score']:.1f}/100
          • Growth Potential: {score['detailed_scores']['growth_potential']:.1f}/100
          • Risk Management: {score['detailed_scores']['risk_score']:.1f}/100
          • Operational Efficiency: {score['detailed_scores']['efficiency_score']:.1f}/100
        """)

        st.markdown("### 💡 Insights")
        st.text_area("LLM Insights", result["insights"], height=200)

        st.markdown("### 💡 AI Analysis")
        st.text_area("LLM Analysis", result["ai_analysis"], height=200)

        st.markdown("### 📊 Benchmarking")
        st.text_area("Peer Comparison", result["benchmarking"], height=200)