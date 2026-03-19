import streamlit as st
import os

st.set_page_config(
    page_title="AI 投資儀表板",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="auto",
)

# Inject CSS via components to avoid f-string / encoding issues
import streamlit.components.v1 as components

CSS = (
    "@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');"
    "html,body,[class*='css']{font-family:'IBM Plex Sans',sans-serif;font-weight:400;}"
    "[data-testid='stSidebar']{background-color:#0a0a0a;border-right:1px solid #1e1e1e;min-width:220px!important;max-width:260px!important;}"
    "[data-testid='stSidebar'] *{color:#e0e0e0!important;}"
    "[data-testid='stSidebar'] .stRadio label{font-size:14px;padding:6px 0;cursor:pointer;}"
    "[data-testid='stSidebar'] h2{font-size:15px!important;font-weight:500!important;letter-spacing:0.04em;color:#ffffff!important;}"
    ".main .block-container{padding:1.5rem 1.5rem;max-width:1400px;}"
    "h1{font-size:20px!important;font-weight:500!important;letter-spacing:-0.02em;color:#111111;margin-bottom:0.25rem!important;}"
    "h2{font-size:16px!important;font-weight:500!important;color:#111111;}"
    "h3{font-size:13px!important;font-weight:500!important;color:#555555;text-transform:uppercase;letter-spacing:0.06em;}"
    "[data-testid='metric-container']{background:#f7f7f7;border:1px solid #ebebeb;border-radius:8px;padding:12px 14px;}"
    "[data-testid='stMetricLabel']{font-size:11px!important;color:#888888!important;text-transform:uppercase;letter-spacing:0.05em;}"
    "[data-testid='stMetricValue']{font-size:20px!important;font-weight:500!important;font-family:'IBM Plex Mono',monospace!important;color:#111111!important;word-break:break-all;}"
    "[data-testid='stMetricDelta']{font-size:11px!important;font-family:'IBM Plex Mono',monospace!important;}"
    "[data-testid='stDataFrame']{border:1px solid #ebebeb;border-radius:8px;overflow:hidden;max-width:100%;}"
    ".stButton>button{background:#111111;color:#ffffff;border:none;border-radius:6px;font-size:13px;font-weight:500;padding:8px 18px;width:100%;font-family:'IBM Plex Sans',sans-serif;transition:background 0.15s;}"
    ".stButton>button:hover{background:#333333;}"
    ".stSelectbox>div{border-radius:6px;}"
    ".streamlit-expanderHeader{font-size:14px;font-weight:500;color:#333333;}"
    "hr{border:none;border-top:1px solid #ebebeb;margin:1rem 0;}"
    ".badge{display:inline-block;font-size:11px;font-weight:500;padding:3px 10px;border-radius:4px;letter-spacing:0.04em;font-family:'IBM Plex Sans',sans-serif;white-space:nowrap;}"
    ".badge-buy{background:#e6f4ea;color:#1a7a3a;}"
    ".badge-hold{background:#fff8e6;color:#9a6700;}"
    ".badge-sell{background:#fdecea;color:#b71c1c;}"
    ".badge-watch{background:#f0f0f0;color:#666666;}"
    ".badge-strong{background:#111111;color:#ffffff;}"
    ".analyst-card{background:#ffffff;border:1px solid #ebebeb;border-radius:10px;padding:14px 16px;margin-bottom:10px;word-break:break-word;}"
    ".analyst-name{font-size:11px;color:#888888;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;}"
    ".analyst-signal{font-size:17px;font-weight:500;color:#111111;margin-bottom:6px;}"
    ".analyst-reason{font-size:12px;color:#555555;line-height:1.6;}"
    ".debate-bull{background:#f0faf4;border-left:3px solid #2a9d5c;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:10px;font-size:13px;line-height:1.7;color:#111111;word-break:break-word;}"
    ".debate-bear{background:#fdf2f2;border-left:3px solid #d94040;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:10px;font-size:13px;line-height:1.7;color:#111111;word-break:break-word;}"
    ".debate-label{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;}"
    ".alert-warn{background:#fffbe6;border:1px solid #ffe57a;border-radius:8px;padding:12px 16px;font-size:13px;color:#7a5500;margin-bottom:10px;word-break:break-word;}"
    ".alert-danger{background:#fdecea;border:1px solid #f5a0a0;border-radius:8px;padding:12px 16px;font-size:13px;color:#7a1a1a;margin-bottom:10px;word-break:break-word;}"
    ".alert-ok{background:#e6f4ea;border:1px solid #7fd0a0;border-radius:8px;padding:12px 16px;font-size:13px;color:#1a5c2a;margin-bottom:10px;word-break:break-word;}"
    ".section-header{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:0.08em;color:#aaaaaa;margin:1.2rem 0 0.6rem;}"
    ".mono{font-family:'IBM Plex Mono',monospace;}"
    ".stSpinner>div{border-top-color:#111111!important;}"
    "div[data-testid='stVerticalBlock']{gap:0.4rem;}"
    ".js-plotly-plot,.plotly,.plot-container{max-width:100%!important;}"
    "@media(max-width:768px){"
        ".main .block-container{padding:1rem 0.75rem!important;}"
        "h1{font-size:17px!important;}"
        "h2{font-size:14px!important;}"
        "[data-testid='stMetricValue']{font-size:16px!important;}"
        "[data-testid='metric-container']{padding:10px 12px;}"
        "[data-testid='stHorizontalBlock']{flex-direction:column!important;gap:0.5rem!important;}"
        "[data-testid='stHorizontalBlock']>div{width:100%!important;min-width:0!important;flex:1 1 100%!important;}"
        ".analyst-signal{font-size:15px;}"
        ".analyst-reason{font-size:11px;}"
        ".debate-bull,.debate-bear{font-size:12px;padding:12px 14px;}"
        ".alert-warn,.alert-danger,.alert-ok{font-size:12px;}"
        "[data-testid='stDataFrame']{overflow-x:auto!important;}"
        "[data-testid='stSidebar']{min-width:80vw!important;max-width:90vw!important;}"
    "}"
    "@media(max-width:480px){"
        ".main .block-container{padding:0.75rem 0.5rem!important;}"
        "h1{font-size:15px!important;}"
        "[data-testid='stMetricValue']{font-size:14px!important;}"
        "[data-testid='stMetricDelta']{font-size:10px!important;}"
    "}"
)

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

from pages import overview, analysts, macro, risk, valuation

# ── Language toggle ──────────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state["lang"] = "zh"

LABELS = {
    "zh": {
        "title":     "AI 投資儀表板",
        "nav":       ["總覽", "7位分析師", "總經", "風險", "估值"],
        "pages":     ["Overview", "7 Analysts", "Macro", "Risk", "Valuation"],
        "ticker":    "選擇股票代碼",
        "caption1":  "數據來源：雅虎財經、FRED、Claude AI",
        "caption2":  "快取每 5 分鐘刷新一次",
        "lang_btn":  "English",
    },
    "en": {
        "title":     "AI Investment Dashboard",
        "nav":       ["Overview", "7 Analysts", "Macro", "Risk", "Valuation"],
        "pages":     ["Overview", "7 Analysts", "Macro", "Risk", "Valuation"],
        "ticker":    "Select Ticker",
        "caption1":  "Data: Yahoo Finance · FRED · Claude AI",
        "caption2":  "Cache refreshes every 5 min",
        "lang_btn":  "中文",
    },
}

PAGES = {
    "Overview":   overview,
    "7 Analysts": analysts,
    "Macro":      macro,
    "Risk":       risk,
    "Valuation":  valuation,
}

with st.sidebar:
    lang = st.session_state["lang"]
    L = LABELS[lang]

    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown(f"## {L['title']}")
    with col_btn:
        st.markdown("<div style='padding-top:18px'>", unsafe_allow_html=True)
        if st.button(L["lang_btn"], key="lang_toggle"):
            st.session_state["lang"] = "en" if lang == "zh" else "zh"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    nav_labels = L["nav"]
    page_keys  = L["pages"]
    selected_label = st.radio("nav", nav_labels, label_visibility="collapsed")
    selected_page  = page_keys[nav_labels.index(selected_label)]

    st.markdown("---")
    ticker = st.selectbox(
        L["ticker"],
        ["TSM", "NVDA", "AAPL", "MSFT", "META", "AVGO", "AMD", "GOOGL"],
        index=0,
    )
    st.session_state["ticker"] = ticker
    st.session_state["lang_labels"] = L
    st.markdown("---")
    st.caption(L["caption1"])
    st.caption(L["caption2"])

PAGES[selected_page].render()