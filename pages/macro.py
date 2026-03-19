"""pages/macro.py"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.data import fetch_fred, get_macro_snapshot, fetch_vix, claude_macro_narrative

ZH = {
    "title":      "總體經濟",
    "indicators": "美國經濟指標 (FRED)",
    "fed_chart":  "聯準會基準利率 (24個月)",
    "cpi_chart":  "CPI 通膨率 YoY (24個月)",
    "unemp":      "失業率 (24個月)",
    "spread":     "10年-2年殖利率利差 (24個月)",
    "nfp":        "非農就業人數月增 (12個月)",
    "env":        "AI 市場環境判定",
    "gen_btn":    "生成總經敘述",
    "loading":    "載入總經數據中...",
    "generating": "分析總經環境中...",
    "waiting":    "點擊「生成總經敘述」以獲得 AI 環境判定。",
    "target":     "Fed 目標 2%",
    "regime_exp": "擴張期 — 風險偏好",
    "regime_con": "緊縮期 — 風險規避",
    "regime_tran":"過渡期 — 混合訊號",
    "fed_label":  "聯準會基準利率 (%)",
    "cpi_label":  "CPI 指數",
    "unemp_label":"失業率 (%)",
    "spread_label":"10Y-2Y 利差 (bps)",
    "nfp_label":  "非農就業 (千人)",
}
EN = {
    "title":      "Macro",
    "indicators": "US Economic Indicators (FRED)",
    "fed_chart":  "Fed Funds Rate (24M)",
    "cpi_chart":  "CPI Index (24M)",
    "unemp":      "Unemployment Rate (24M)",
    "spread":     "10Y–2Y Yield Spread (24M)",
    "nfp":        "Nonfarm Payrolls (12M)",
    "env":        "AI Market Environment Assessment",
    "gen_btn":    "Generate Macro Narrative",
    "loading":    "Fetching macro data...",
    "generating": "Analyzing macro environment...",
    "waiting":    "Click 'Generate Macro Narrative' for AI assessment.",
    "target":     "Fed Target 2%",
    "regime_exp": "Easing Cycle — Risk On",
    "regime_con": "Tightening Cycle — Risk Off",
    "regime_tran":"Transitional — Mixed Signals",
    "fed_label":  "Fed Funds Rate (%)",
    "cpi_label":  "CPI Index",
    "unemp_label":"Unemployment (%)",
    "spread_label":"10Y-2Y Spread (bps)",
    "nfp_label":  "Nonfarm Payrolls (k)",
}

SNAP_LABELS_ZH = {
    "Fed Funds Rate (%)":   "聯準會利率 (%)",
    "CPI YoY (%)":          "CPI 年增率 (%)",
    "Unemployment (%)":     "失業率 (%)",
    "10Y-2Y Spread (bps)":  "10Y-2Y 利差",
    "Nonfarm Payrolls (k)": "非農就業 (千人)",
}


def render():
    lang = st.session_state.get("lang", "zh")
    T    = ZH if lang == "zh" else EN

    st.markdown(f"## {T['title']}")
    st.markdown(f"<div class='section-header'>{T['indicators']}</div>", unsafe_allow_html=True)

    with st.spinner(T["loading"]):
        snap = get_macro_snapshot()
        vix  = fetch_vix()

    cols = st.columns(len(snap))
    for i, (label, vals) in enumerate(snap.items()):
        cur  = vals["current"]
        prev = vals["prev"]
        diff = cur - prev
        unit = "%" if "%" in label else "k" if "(k)" in label else ""
        display_label = SNAP_LABELS_ZH.get(label, label) if lang == "zh" else label.split("(")[0].strip()
        cols[i].metric(display_label, f"{cur:.2f}{unit}", f"{diff:+.2f}{unit}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<div class='section-header'>{T['fed_chart']}</div>", unsafe_allow_html=True)
        df = fetch_fred("FEDFUNDS", 24)
        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["value"],
                fill="tozeroy", fillcolor="rgba(30,30,30,0.06)",
                line=dict(color="#111111", width=2),
                hovertemplate="%{x|%b %Y}: %{y:.2f}%<extra></extra>",
            ))
            fig.update_layout(**_layout(260, ysuffix="%"))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"<div class='section-header'>{T['cpi_chart']}</div>", unsafe_allow_html=True)
        df2 = fetch_fred("CPIAUCSL", 24)
        if not df2.empty:
            pct = df2["value"].pct_change(12) * 100
            valid = pct.dropna()
            if len(valid) > 0:
                colors = ["#d94040" if v > 3 else "#2a9d5c" if v < 2 else "#f0a500" for v in valid]
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=df2["date"][12:], y=valid,
                    marker_color=colors,
                    hovertemplate="%{x|%b %Y}: %{y:.2f}% YoY<extra></extra>",
                ))
                fig2.add_hline(y=2.0, line=dict(color="#888", dash="dot", width=1),
                    annotation_text=T["target"], annotation_position="right")
                fig2.update_layout(**_layout(260, ysuffix="%"))
                st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(f"<div class='section-header'>{T['unemp']}</div>", unsafe_allow_html=True)
        df3 = fetch_fred("UNRATE", 24)
        if not df3.empty:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=df3["date"], y=df3["value"],
                line=dict(color="#d94040", width=2),
                hovertemplate="%{x|%b %Y}: %{y:.1f}%<extra></extra>",
            ))
            fig3.update_layout(**_layout(220, ysuffix="%"))
            st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.markdown(f"<div class='section-header'>{T['spread']}</div>", unsafe_allow_html=True)
        df4 = fetch_fred("T10Y2Y", 24)
        if not df4.empty:
            colors = ["#d94040" if v < 0 else "#2a9d5c" for v in df4["value"]]
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(
                x=df4["date"], y=df4["value"],
                marker_color=colors,
                hovertemplate="%{x|%b %Y}: %{y:.2f} bps<extra></extra>",
            ))
            fig4.add_hline(y=0, line=dict(color="#333", width=1))
            fig4.update_layout(**_layout(220))
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.markdown(f"<div class='section-header'>{T['env']}</div>", unsafe_allow_html=True)

    if st.button(T["gen_btn"]):
        with st.spinner(T["generating"]):
            narrative = claude_macro_narrative(snap, vix, lang=lang)
        st.session_state["macro_narrative"] = narrative
        st.session_state["macro_narrative_lang"] = lang

    if "macro_narrative" in st.session_state:
        narrative = st.session_state["macro_narrative"]
        text_lower = narrative.lower()
        if any(w in text_lower for w in ["easing","rate cut","golden","降息","黃金","寬鬆"]):
            regime, badge_cls = T["regime_exp"], "alert-ok"
        elif any(w in text_lower for w in ["tighten","hawkish","contraction","縮表","緊縮","升息"]):
            regime, badge_cls = T["regime_con"], "alert-danger"
        else:
            regime, badge_cls = T["regime_tran"], "alert-warn"

        st.markdown(f"<div class='{badge_cls}'><strong>{regime}</strong></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='background:#fafafa;border:1px solid #ebebeb;border-radius:10px;"
            f"padding:18px 22px;font-size:14px;line-height:1.8;color:#222'>{narrative}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"<p style='color:#aaa;font-size:13px'>{T['waiting']}</p>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div class='section-header'>{T['nfp']}</div>", unsafe_allow_html=True)
    df5 = fetch_fred("PAYEMS", 13)
    if not df5.empty and len(df5) > 1:
        mom = df5["value"].diff().dropna()
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=df5["date"][1:], y=mom,
            marker_color=["#2a9d5c" if v > 0 else "#d94040" for v in mom],
            hovertemplate="%{x|%b %Y}: %{y:,.0f}k<extra></extra>",
        ))
        fig5.update_layout(**_layout(200))
        st.plotly_chart(fig5, use_container_width=True)


def _layout(height, ysuffix=""):
    return dict(
        height=height, margin=dict(l=0,r=0,t=10,b=0),
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", ticksuffix=ysuffix),
        xaxis=dict(tickfont=dict(size=11)),
        hovermode="x unified",
    )