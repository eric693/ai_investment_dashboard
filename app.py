import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="智投 AI",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

DARK_CSS = (
    "html,body,[class*='css']{font-family:'Inter',-apple-system,sans-serif;}"
    "body{background:#0d1117!important;}"
    ".main{background:#0d1117!important;}"
    ".main .block-container{padding:1.2rem 1.5rem;max-width:1600px;background:#0d1117;}"
    # Sidebar
    "[data-testid='stSidebar']{background:#161b22!important;border-right:1px solid #21262d!important;min-width:200px!important;max-width:220px!important;}"
    "[data-testid='stSidebar'] *{color:#c9d1d9!important;}"
    "[data-testid='stSidebar'] .stRadio label{font-size:13px!important;padding:8px 12px!important;border-radius:6px!important;cursor:pointer!important;display:block!important;}"
    "[data-testid='stSidebar'] .stRadio label:hover{background:#21262d!important;}"
    "[data-testid='stSidebar'] hr{border-color:#21262d!important;}"
    # Metrics
    "[data-testid='metric-container']{background:#161b22!important;border:1px solid #21262d!important;border-radius:10px!important;padding:16px 18px!important;}"
    "[data-testid='stMetricLabel']{font-size:11px!important;color:#8b949e!important;text-transform:uppercase;letter-spacing:.06em;}"
    "[data-testid='stMetricValue']{font-size:22px!important;font-weight:600!important;color:#e6edf3!important;}"
    "[data-testid='stMetricDelta']{font-size:12px!important;}"
    # Headings
    "h1,h2,h3,h4{color:#e6edf3!important;}"
    "h1{font-size:18px!important;font-weight:600!important;}"
    "h2{font-size:15px!important;font-weight:600!important;}"
    # Buttons
    ".stButton>button{background:#1f6feb!important;color:#fff!important;border:none!important;border-radius:8px!important;font-size:13px!important;font-weight:500!important;padding:8px 20px!important;width:100%!important;transition:all .15s!important;}"
    ".stButton>button:hover{background:#388bfd!important;}"
    # Select / input
    ".stSelectbox>div>div{background:#161b22!important;border:1px solid #30363d!important;color:#e6edf3!important;border-radius:8px!important;}"
    "input,textarea{background:#0d1117!important;color:#e6edf3!important;border:1px solid #30363d!important;border-radius:6px!important;}"
    # Expander
    ".streamlit-expanderHeader{background:#161b22!important;color:#e6edf3!important;border:1px solid #21262d!important;border-radius:8px!important;}"
    ".streamlit-expanderContent{background:#161b22!important;border:1px solid #21262d!important;}"
    # Tables / dataframes
    "[data-testid='stDataFrame']{border:1px solid #21262d!important;border-radius:8px!important;}"
    # Spinner
    ".stSpinner>div{border-top-color:#1f6feb!important;}"
    # Divider
    "hr{border-color:#21262d!important;}"
    # Tabs
    "[data-testid='stHorizontalBlock']{gap:0.75rem!important;}"
    # Custom classes
    ".card{background:#161b22;border:1px solid #21262d;border-radius:12px;padding:18px 20px;margin-bottom:12px;}"
    ".card-title{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:#8b949e;margin-bottom:14px;}"
    ".sec-header{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:#8b949e;margin:1rem 0 .6rem;}"
    ".kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px;}"
    ".kpi{background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:14px 16px;}"
    ".kpi-label{font-size:10px;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;}"
    ".kpi-val{font-size:20px;font-weight:700;color:#e6edf3;letter-spacing:-.02em;}"
    ".kpi-sub{font-size:11px;margin-top:3px;}"
    ".pos{color:#3fb950;}"
    ".neg{color:#f85149;}"
    ".neu{color:#8b949e;}"
    ".warn{color:#d29922;}"
    ".badge{display:inline-block;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;letter-spacing:.03em;}"
    ".badge-buy{background:#1a4731;color:#3fb950;border:1px solid #2ea043;}"
    ".badge-hold{background:#2d2208;color:#d29922;border:1px solid #9e6a03;}"
    ".badge-sell{background:#3d1a1a;color:#f85149;border:1px solid #da3633;}"
    ".badge-strong{background:#1f6feb;color:#fff;}"
    ".analyst-card{background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:14px 16px;margin-bottom:10px;}"
    ".analyst-name{font-size:10px;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;}"
    ".analyst-signal{font-size:16px;font-weight:600;margin-bottom:5px;}"
    ".analyst-reason{font-size:11px;color:#8b949e;line-height:1.5;}"
    ".debate-bull{background:#0d2818;border-left:3px solid #3fb950;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:10px;font-size:13px;line-height:1.7;color:#c9d1d9;}"
    ".debate-bear{background:#2d1515;border-left:3px solid #f85149;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:10px;font-size:13px;line-height:1.7;color:#c9d1d9;}"
    ".debate-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;}"
    ".alert-warn{background:#2d2208;border:1px solid #9e6a03;border-radius:8px;padding:12px 16px;font-size:13px;color:#d29922;margin-bottom:10px;}"
    ".alert-danger{background:#3d1a1a;border:1px solid #da3633;border-radius:8px;padding:12px 16px;font-size:13px;color:#f85149;margin-bottom:10px;}"
    ".alert-ok{background:#0d2818;border:1px solid #2ea043;border-radius:8px;padding:12px 16px;font-size:13px;color:#3fb950;margin-bottom:10px;}"
    ".mono{font-family:'JetBrains Mono','Courier New',monospace;}"
    "@media(max-width:768px){"
        ".main .block-container{padding:.8rem .6rem!important;}"
        "[data-testid='stHorizontalBlock']{flex-direction:column!important;}"
        "[data-testid='stHorizontalBlock']>div{width:100%!important;min-width:0!important;}"
        "[data-testid='stSidebar']{min-width:85vw!important;max-width:90vw!important;}"
    "}"
)

st.markdown(f"<style>{DARK_CSS}</style>", unsafe_allow_html=True)

from src import overview, analysts, macro, risk, valuation

LABELS = {
    "zh": {
        "brand":    "智投 AI",
        "nav":      ["總覽", "7位分析師", "總經", "風險", "估值"],
        "pages":    ["Overview", "7 Analysts", "Macro", "Risk", "Valuation"],
        "ticker":   "選擇股票",
        "cap1":     "Yahoo Finance · FRED · Claude AI",
        "lang_btn": "EN",
    },
    "en": {
        "brand":    "AI Invest",
        "nav":      ["Overview", "7 Analysts", "Macro", "Risk", "Valuation"],
        "pages":    ["Overview", "7 Analysts", "Macro", "Risk", "Valuation"],
        "ticker":   "Select Ticker",
        "cap1":     "Yahoo Finance · FRED · Claude AI",
        "lang_btn": "中文",
    },
}

PAGES = {
    "Overview":   overview,
    "7 Analysts": analysts,
    "Macro":      macro,
    "Risk":       risk,
    "Valuation":  valuation,
}

if "lang" not in st.session_state:
    st.session_state["lang"] = "zh"

with st.sidebar:
    lang = st.session_state["lang"]
    L    = LABELS[lang]

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;padding:8px 0 16px'>"
        f"<div style='width:32px;height:32px;background:#1f6feb;border-radius:8px;"
        f"display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;color:#fff'>A</div>"
        f"<span style='font-size:15px;font-weight:600;color:#e6edf3'>{L['brand']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    nav_labels    = L["nav"]
    page_keys     = L["pages"]
    selected_label= st.radio("nav", nav_labels, label_visibility="collapsed")
    selected_page = page_keys[nav_labels.index(selected_label)]

    st.markdown("---")
    ticker = st.selectbox(L["ticker"],
        ["TSM", "NVDA", "AAPL", "MSFT", "META", "AVGO", "AMD", "GOOGL",
         "2330.TW", "2454.TW", "2317.TW", "2412.TW"],
        index=0)
    st.session_state["ticker"] = ticker

    st.markdown("---")
    if st.button(L["lang_btn"]):
        st.session_state["lang"] = "en" if lang == "zh" else "zh"
        st.rerun()

    st.markdown(
        f"<div style='font-size:10px;color:#484f58;margin-top:8px;line-height:1.6'>"
        f"{L['cap1']}<br>Cache: 5 min</div>",
        unsafe_allow_html=True,
    )

PAGES[selected_page].render()