"""pages/macro.py — Macro indicators, Fed rate history, AI environment narrative."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.data import fetch_fred, get_macro_snapshot, fetch_vix, claude_macro_narrative


FRED_SERIES = {
    "Fed Funds Rate (%)":    ("FEDFUNDS",   "Monthly",  "%",   "#333333"),
    "CPI (Index)":           ("CPIAUCSL",   "Monthly",  "",    "#2a6dd9"),
    "Unemployment (%)":      ("UNRATE",     "Monthly",  "%",   "#d94040"),
    "10Y-2Y Spread (bps)":  ("T10Y2Y",     "Daily",    "bps", "#9b59b6"),
    "Nonfarm Payrolls (k)": ("PAYEMS",     "Monthly",  "k",   "#2a9d5c"),
}


def render():
    ticker = st.session_state.get("ticker", "TSM")
    st.markdown("## Macro Environment")
    st.markdown(f"<div class='section-header'>US Economic Indicators (FRED)</div>", unsafe_allow_html=True)

    with st.spinner("Fetching macro data..."):
        snap = get_macro_snapshot()
        vix  = fetch_vix()

    # ── Snapshot metrics ──────────────────────────────────────────────────────
    cols = st.columns(len(snap))
    indicators = list(snap.items())
    for i, (label, vals) in enumerate(indicators):
        cur  = vals["current"]
        prev = vals["prev"]
        diff = cur - prev
        unit = "%" if "%" in label else "k" if "(k)" in label else ""
        cols[i].metric(label.split("(")[0].strip(), f"{cur:.2f}{unit}", f"{diff:+.2f}{unit}")

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='section-header'>Fed Funds Rate (24M)</div>", unsafe_allow_html=True)
        df = fetch_fred("FEDFUNDS", 24)
        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["value"],
                fill="tozeroy", fillcolor="rgba(30,30,30,0.06)",
                line=dict(color="#111111", width=2),
                hovertemplate="%{x|%b %Y}: %{y:.2f}%<extra></extra>",
            ))
            fig.update_layout(**_chart_layout(260, yprefix="", ysuffix="%"))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("<div class='section-header'>CPI Index (24M)</div>", unsafe_allow_html=True)
        df2 = fetch_fred("CPIAUCSL", 24)
        if not df2.empty:
            pct = df2["value"].pct_change(12) * 100
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=df2["date"][12:], y=pct[12:],
                marker_color=["#d94040" if v > 3 else "#2a9d5c" if v < 2 else "#f0a500" for v in pct[12:]],
                hovertemplate="%{x|%b %Y}: %{y:.2f}% YoY<extra></extra>",
            ))
            fig2.add_hline(y=2.0, line=dict(color="#888", dash="dot", width=1),
                annotation_text="Fed Target 2%", annotation_position="right")
            fig2.update_layout(**_chart_layout(260, yprefix="", ysuffix="%"))
            st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("<div class='section-header'>Unemployment Rate (24M)</div>", unsafe_allow_html=True)
        df3 = fetch_fred("UNRATE", 24)
        if not df3.empty:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=df3["date"], y=df3["value"],
                line=dict(color="#d94040", width=2),
                hovertemplate="%{x|%b %Y}: %{y:.1f}%<extra></extra>",
            ))
            fig3.update_layout(**_chart_layout(220, yprefix="", ysuffix="%"))
            st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.markdown("<div class='section-header'>10Y–2Y Yield Spread (24M)</div>", unsafe_allow_html=True)
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
            fig4.update_layout(**_chart_layout(220))
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # ── AI Narrative ──────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>AI Market Environment Assessment</div>", unsafe_allow_html=True)

    if st.button("Generate Macro Narrative"):
        with st.spinner("Analyzing macro environment..."):
            narrative = claude_macro_narrative(snap, vix)
        st.session_state["macro_narrative"] = narrative

    if "macro_narrative" in st.session_state:
        narrative = st.session_state["macro_narrative"]
        # Determine regime badge
        text_lower = narrative.lower()
        if "golden" in text_lower or "easing" in text_lower or "rate cut" in text_lower:
            regime, badge_cls = "Easing Cycle — Risk On", "alert-ok"
        elif "tighten" in text_lower or "hawkish" in text_lower or "contraction" in text_lower:
            regime, badge_cls = "Tightening Cycle — Risk Off", "alert-danger"
        else:
            regime, badge_cls = "Transitional — Mixed Signals", "alert-warn"

        st.markdown(f"<div class='{badge_cls}'><strong>{regime}</strong></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='background:#fafafa;border:1px solid #ebebeb;border-radius:10px;"
            f"padding:18px 22px;font-size:14px;line-height:1.8;color:#222'>{narrative}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<p style='color:#aaa;font-size:13px'>Click 'Generate Macro Narrative' for AI assessment.</p>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div class='section-header'>Nonfarm Payrolls (12M)</div>", unsafe_allow_html=True)
    df5 = fetch_fred("PAYEMS", 13)
    if not df5.empty and len(df5) > 1:
        mom = df5["value"].diff().dropna()
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            x=df5["date"][1:], y=mom,
            marker_color=["#2a9d5c" if v > 0 else "#d94040" for v in mom],
            hovertemplate="%{x|%b %Y}: +%{y:,.0f}k<extra></extra>",
        ))
        fig5.update_layout(**_chart_layout(200))
        st.plotly_chart(fig5, use_container_width=True)


def _chart_layout(height: int, yprefix: str = "", ysuffix: str = "") -> dict:
    return dict(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        yaxis=dict(
            tickfont=dict(size=11), gridcolor="#f0f0f0",
            tickprefix=yprefix, ticksuffix=ysuffix,
        ),
        xaxis=dict(tickfont=dict(size=11)),
        hovermode="x unified",
    )
