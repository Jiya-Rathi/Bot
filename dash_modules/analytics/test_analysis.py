import pandas as pd
from pathlib import Path
from utils.granite import summarize_with_granite
import json
from dash_modules.analytics.run_smb_analysis import run_smb_analysis
from cashflow_forecasting.forecasting_engine import CashFlowForecaster, ForecastExplainer
from granite.client import GraniteAPI
from utils.business_profile import load_profile, save_profile, needs_profile_info


if __name__ == "__main__":
        business_profile = load_profile()
        print("business_profile ", business_profile)

        result = run_smb_analysis(business_profile)

        #st.markdown("### 🎯 Financial Health Score")
        score = result["score"]
        print(f"""
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

        print("### 💡 Insights")
        print("LLM Insights", result["insights"])

        print("### 💡 AI Analysis")
        print("LLM Analysis", result["ai_analysis"])

        print("### 📊 Benchmarking")
        print("Peer Comparison", result["benchmarking"])