import streamlit as st
from dash_modules.reports.tax_assistant import TaxAssistant
from utils.business_profile import load_profile
from ledger.ledger_utils import load_ledger_summary
from pathlib import Path
import json

FORMS = [
    {"name": "1120 - Corporate Income Tax", "form": "1120"},
    {"name": "Schedule C - Profit/Loss", "form": "Schedule C"},
    {"name": "Form 941 - Quarterly Tax", "form": "Form 941"},
]

def render_reports():
    st.markdown("### 🧾 Tax Form Preparation Assistant")
    profile = load_profile()  # from utils.business_profile
    ledger_summary = load_ledger_summary()  # from ledger/ledger_utils.py

    country = profile.get("country", "USA")
    income = ledger_summary.get("gross_income", 0.0)

    for idx, form_info in enumerate(FORMS):
        form_type = form_info["form"]
        form_name = form_info["name"]

        ta = TaxAssistant(country=country, income=income, form_type=form_type)
        tax_json = ta.run_tax_fill()

        try:
            result = json.loads(tax_json)
            complete_pct = 95 - (idx * 15)
            status = "READY" if complete_pct >= 90 else "IN PROGRESS" if complete_pct >= 70 else "PENDING"
            color = {"READY": "green", "IN PROGRESS": "orange", "PENDING": "gray"}[status]
            tag = f"<span style='background-color:{color}; color:white; padding:2px 8px; border-radius:4px'>{status}</span>"

            with st.container():
                st.markdown(f"**{form_name}** &nbsp;&nbsp; {tag}", unsafe_allow_html=True)
                st.progress(complete_pct, text=f"{complete_pct}% complete")
                st.download_button(
                    label="⬇️ Download JSON",
                    data=tax_json,
                    file_name=f"{form_type.replace(' ', '_').lower()}_filled.json",
                    mime="application/json",
                    key=f"download_{form_type}"
                )
        except Exception as e:
            st.error(f"❌ Failed to load {form_name}: {e}")

    # Divider
    st.markdown("---")
    st.markdown("### 📊 Customizable Financial Reports")

    # Display placeholder customizable reports
    financial_reports = [
        {"name": "P&L Statement", "desc": "Monthly • PDF", "file": "reports/pnl_statement.pdf"},
        {"name": "Cash Flow Report", "desc": "Weekly • Excel", "file": "reports/cash_flow.xlsx"},
    ]

    col1, col2 = st.columns([3, 1])
    with col1:
        for r in financial_reports:
            st.markdown(f"**{r['name']}**  \n*{r['desc']}*")
    with col2:
        for r in financial_reports:
            path = Path(r["file"])
            if path.exists():
                with open(path, "rb") as f:
                    st.download_button(
                        label="📥",
                        data=f,
                        file_name=path.name,
                        mime="application/octet-stream",
                        key=f"custom_download_{r['name']}"
                    )
            else:
                st.info("Coming soon")

    st.button("➕ Create New Report", type="primary")
