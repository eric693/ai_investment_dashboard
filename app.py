import streamlit as st
import os

st.set_page_config(
    page_title="AI Investment Dashboard",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
with open("static/css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from pages import overview, analysts, macro, risk, valuation

PAGES = {
    "Overview": overview,
    "7 Analysts": analysts,
    "Macro": macro,
    "Risk": risk,
    "Valuation": valuation,
}

with st.sidebar:
    st.markdown("## AI Investment Dashboard")
    st.markdown("---")
    selected = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
    st.markdown("---")
    ticker = st.selectbox(
        "Select Ticker",
        ["TSM", "NVDA", "AAPL", "MSFT", "META", "AVGO", "AMD", "GOOGL"],
        index=0,
    )
    st.session_state["ticker"] = ticker
    st.markdown("---")
    st.caption("Data: Yahoo Finance · FRED · Claude AI")
    st.caption("Auto-refresh every 5 min")

PAGES[selected].render()
