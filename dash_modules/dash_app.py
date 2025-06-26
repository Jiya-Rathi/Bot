# dash_modules/dash_app.py
import streamlit as st
from overview.overview import render_overview
from analytics.analytics import render_analysis
#from reports.reports import render_reports  # Comment if unavailable
from automation.invoice_ui import render_automation
from reports.reports import render_reports
from industry_specific.industry_benchmark import render_industry_benchmark

st.set_page_config(page_title="Accounting Bot Dashboard", layout="wide")

# Sticky CSS header bar
st.markdown("""
    <style>
    .reportview-container .main .block-container {
        padding-top: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 999;
        border-bottom: 1px solid #e6e6e6;
        padding-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Heading (optional)
st.markdown("## 📊 Accounting Bot Dashboard", unsafe_allow_html=True)

# Horizontal top tabs
tabs = st.tabs(["Overview", "Analytics", "Automation","Reports", "Industry Data"])

with tabs[0]:
    render_overview()

with tabs[1]:
    render_analysis()

with tabs[2]:
    render_automation()

with tabs[3]:
    render_reports()

with tabs[4]:
    render_industry_benchmark()
    

