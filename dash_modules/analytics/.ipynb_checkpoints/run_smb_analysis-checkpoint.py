from dash_modules.analytics.smb_health_analyzer import SMBFinancialHealthAnalyzer
import json
import pandas as pd
from pathlib import Path

LEDGER_PATH = Path("ledger/ledger.json")


def load_ledger():
    if not LEDGER_PATH.exists():
        return pd.DataFrame()
    with open(LEDGER_PATH) as f:
        raw = json.load(f)
    data = raw.get("history", [])
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ValueError("Invalid ledger format. Expected list of dicts under 'history'.")
    df = pd.DataFrame(data)
    df.columns = df.columns.str.lower()
    df["type"] = df["type"].replace({"credit": "income", "debit": "expense"})
    return df


def derive_metrics(df):
    total_income = df[df["type"] == "income"]["amount"].sum()
    total_expense = df[df["type"] == "expense"]["amount"].sum()
    net_profit = total_income - total_expense
    net_profit_margin = net_profit / total_income if total_income > 0 else 0

    monthly_expense = df[df["type"] == "expense"].groupby(
        df["date"].apply(lambda x: pd.to_datetime(x).to_period("M"))
    ).sum()["amount"].mean()

    ending_cash = total_income - total_expense
    cash_runway = ending_cash / monthly_expense if monthly_expense else 0

    return {
        "annual_revenue": total_income,
        "net_profit_margin": round(net_profit_margin, 3),
        "cash_runway": round(cash_runway, 2),
    }


def run_smb_analysis(user_inputs):
    analyzer = SMBFinancialHealthAnalyzer()
    df = load_ledger()
    derived = derive_metrics(df)

    company_profile = {
        "name": user_inputs["name"],
        "industry": user_inputs["industry"],
        "country": user_inputs["country"],
        "region": user_inputs["region"],
        "employees": user_inputs["employees"],
        "years_in_business": user_inputs["years"],

        # Derived financials
        "annual_revenue": derived["annual_revenue"],
        "net_profit_margin": derived["net_profit_margin"],
        "cash_runway": derived["cash_runway"],
        "business_model": "B2B",

        # Fixed defaults (for now)
        "churn_rate": 0.2,
        "recurring_revenue": 0.3,
        "revenue_predictability": 0.6,
        "revenue_concentration": 0.25,
    }

    score_result = analyzer.calculate_smb_health_score(company_profile)
    insights = analyzer.generate_smb_specific_insights(company_profile, score_result)
    peers = analyzer._get_smb_peer_data(company_profile)
    benchmarking = analyzer.generate_benchmarking_report(company_profile, score_result, peers)

    summary = f"""
Company: {company_profile['name']}
Industry: {company_profile['industry']} ({company_profile['country']})
Financial Health: {score_result['overall_score']}/100 ({score_result['health_rating']})

Key Metrics:
- Cash Runway: {company_profile['cash_runway']} months
- Profit Margin: {company_profile['net_profit_margin']*100:.1f}%
- Customer Churn: {company_profile['churn_rate']*100:.1f}%
- Revenue Predictability: {company_profile['revenue_predictability']*100:.1f}%

Recommendation: {"Immediate attention required" if score_result['overall_score'] < 60 else "Monitor and optimize" if score_result['overall_score'] < 80 else "Strong position, focus on growth"}
    """

    return {
        "score": score_result,
        "ai_analysis": score_result["ai_analysis"],
        "insights": insights,
        "benchmarking": benchmarking,
        "summary": summary.strip(),
    }
