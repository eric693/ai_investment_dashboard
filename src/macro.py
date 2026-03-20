"""src/macro.py — Dark theme macro"""
import streamlit as st
import plotly.graph_objects as go
from utils.data import fetch_fred, get_macro_snapshot, fetch_vix, claude_macro_narrative

PLOT = dict(
    plot_bgcolor="#0d1117", paper_bgcolor="#161b22",
    font=dict(color="#8b949e", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(gridcolor="#21262d", linecolor="#21262d", tickfont=dict(color="#8b949e")),
    yaxis=dict(gridcolor="#21262d", linecolor="#21262d", tickfont=dict(color="#8b949e")),
    hovermode="x unified",
    showlegend=False,
)

SNAP_ZH = {
    "Fed Funds Rate (%)":   "聯準會利率 (%)",
    "CPI YoY (%)":          "CPI 年增率 (%)",
    "Unemployment (%)":     "失業率 (%)",
    "10Y-2Y Spread (bps)":  "10Y-2Y 利差",
    "Nonfarm Payrolls (k)": "非農就業 (千人)",
}


def render():
    lang = st.session_state.get("lang", "zh")
    zh   = lang == "zh"

    st.markdown(f"<div style='font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:16px'>{'總體經濟' if zh else 'Macro Environment'}</div>", unsafe_allow_html=True)

    with st.spinner("載入總經數據..." if zh else "Fetching macro data..."):
        snap = get_macro_snapshot()
        vix  = fetch_vix()

    # KPI row
    st.markdown("<div class='kpi-grid'>", unsafe_allow_html=True)
    cols = st.columns(len(snap) + 1)
    for i, (label, vals) in enumerate(snap.items()):
        cur  = vals["current"]
        prev = vals["prev"]
        diff = cur - prev
        unit = "%" if "%" in label else "k" if "(k)" in label else ""
        disp = SNAP_ZH.get(label, label) if zh else label.split("(")[0].strip()
        clr  = "#3fb950" if diff >= 0 else "#f85149"
        sign = "+" if diff >= 0 else ""
        cols[i].markdown(
            f"<div class='kpi'><div class='kpi-label'>{disp}</div>"
            f"<div class='kpi-val'>{cur:.2f}{unit}</div>"
            f"<div class='kpi-sub' style='color:{clr}'>{sign}{diff:.2f}{unit}</div></div>",
            unsafe_allow_html=True)
    cols[-1].markdown(
        f"<div class='kpi'><div class='kpi-label'>VIX</div>"
        f"<div class='kpi-val'>{vix:.2f}</div>"
        f"<div class='kpi-sub' style='color:{'#3fb950' if vix<18 else '#f85149' if vix>28 else '#d29922'}'>{'低' if zh else 'Low'} {'中' if 18<=vix<=28 else ''} {'高' if vix>28 else ''}</div></div>",
        unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Charts 2x2
    c1, c2 = st.columns(2, gap="medium")

    with c1:
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'聯準會基準利率 (24個月)' if zh else 'Fed Funds Rate (24M)'}</div>", unsafe_allow_html=True)
        df = fetch_fred("FEDFUNDS", 24)
        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["date"], y=df["value"],
                fill="tozeroy", fillcolor="rgba(31,111,235,0.12)",
                line=dict(color="#1f6feb", width=2),
                hovertemplate="%{x|%b %Y}: %{y:.2f}%<extra></extra>"))
            fig.update_layout(**PLOT, height=200, yaxis=dict(**PLOT["yaxis"], ticksuffix="%"))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'CPI 通膨率 YoY' if zh else 'CPI Inflation YoY'}</div>", unsafe_allow_html=True)
        df2 = fetch_fred("CPIAUCSL", 24)
        if not df2.empty:
            pct = df2["value"].pct_change(12) * 100
            valid = pct.dropna()
            if len(valid):
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=df2["date"][12:], y=valid,
                    marker_color=["#f85149" if v>3 else "#3fb950" if v<2 else "#d29922" for v in valid],
                    hovertemplate="%{x|%b %Y}: %{y:.2f}%<extra></extra>"))
                fig2.add_hline(y=2.0, line=dict(color="#484f58", dash="dot", width=1),
                    annotation_text="2%", annotation_font_color="#484f58")
                fig2.update_layout(**PLOT, height=200, yaxis=dict(**PLOT["yaxis"], ticksuffix="%"))
                st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    c3, c4 = st.columns(2, gap="medium")

    with c3:
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'失業率 (24個月)' if zh else 'Unemployment (24M)'}</div>", unsafe_allow_html=True)
        df3 = fetch_fred("UNRATE", 24)
        if not df3.empty:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=df3["date"], y=df3["value"],
                line=dict(color="#f85149", width=2),
                hovertemplate="%{x|%b %Y}: %{y:.1f}%<extra></extra>"))
            fig3.update_layout(**PLOT, height=200, yaxis=dict(**PLOT["yaxis"], ticksuffix="%"))
            st.plotly_chart(fig3, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c4:
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'10Y-2Y 殖利率利差' if zh else '10Y–2Y Yield Spread'}</div>", unsafe_allow_html=True)
        df4 = fetch_fred("T10Y2Y", 24)
        if not df4.empty:
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(x=df4["date"], y=df4["value"],
                marker_color=["#f85149" if v<0 else "#3fb950" for v in df4["value"]],
                hovertemplate="%{x|%b %Y}: %{y:.2f}<extra></extra>"))
            fig4.add_hline(y=0, line=dict(color="#484f58", width=1))
            fig4.update_layout(**PLOT, height=200)
            st.plotly_chart(fig4, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div class='card-title'>{'AI 市場環境判定' if zh else 'AI Market Environment'}</div>", unsafe_allow_html=True)
    if st.button("生成總經敘述" if zh else "Generate Macro Narrative"):
        with st.spinner("分析中..." if zh else "Analyzing..."):
            narrative = claude_macro_narrative(snap, vix, lang=lang)
        st.session_state["macro_narrative"] = narrative

    if "macro_narrative" in st.session_state:
        txt = st.session_state["macro_narrative"]
        lower = txt.lower()
        if any(w in lower for w in ["easing","rate cut","golden","降息","黃金","寬鬆"]):
            regime, cls = ("擴張期 — 風險偏好" if zh else "Easing Cycle — Risk On"), "alert-ok"
        elif any(w in lower for w in ["tighten","hawkish","contraction","縮表","緊縮","升息"]):
            regime, cls = ("緊縮期 — 風險規避" if zh else "Tightening — Risk Off"), "alert-danger"
        else:
            regime, cls = ("過渡期 — 混合訊號" if zh else "Transitional — Mixed"), "alert-warn"
        st.markdown(f"<div class='{cls}'><strong>{regime}</strong></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='background:#161b22;border:1px solid #21262d;border-radius:10px;"
            f"padding:16px 20px;font-size:14px;line-height:1.8;color:#c9d1d9'>{txt}</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color:#484f58;font-size:13px'>{'點擊按鈕獲得 AI 環境判定。' if zh else 'Click to generate AI narrative.'}</p>", unsafe_allow_html=True)