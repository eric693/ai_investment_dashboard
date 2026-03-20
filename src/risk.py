"""src/risk.py — Dark theme risk"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix,
    calc_sharpe, calc_max_drawdown, isolation_forest_score, kelly_fraction,
    claude_risk_summary,
)

PLOT = dict(
    plot_bgcolor="#0d1117", paper_bgcolor="#161b22",
    font=dict(color="#8b949e", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(gridcolor="#21262d", linecolor="#21262d", tickfont=dict(color="#8b949e")),
    yaxis=dict(gridcolor="#21262d", linecolor="#21262d", tickfont=dict(color="#8b949e")),
    hovermode="x unified",
)


def render():
    ticker = st.session_state.get("ticker", "TSM")
    lang   = st.session_state.get("lang", "zh")
    zh     = lang == "zh"

    with st.spinner("載入中..." if zh else "Loading..."):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)
        vix   = fetch_vix()

    closes = quote.get("closes", []) or []
    price  = quote.get("price", 0) or 0
    beta   = fund.get("beta") or 1.0

    st.markdown(f"<div style='font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:16px'>{ticker} — {'風險管理' if zh else 'Risk Management'}</div>", unsafe_allow_html=True)

    # Alerts
    st.markdown(f"<div class='card-title'>{'即時風險警報' if zh else 'Live Risk Alerts'}</div>", unsafe_allow_html=True)
    if vix > 30:
        st.markdown(f"<div class='alert-danger'><strong>{'黑天鵝警報' if zh else 'Black Swan Alert'}</strong> — VIX {vix:.1f}. {'建議減少 30-50% 倉位。' if zh else 'Recommend reducing exposure 30-50%.'}</div>", unsafe_allow_html=True)
    elif vix > 22:
        st.markdown(f"<div class='alert-warn'><strong>{'波動率偏高' if zh else 'Elevated Volatility'}</strong> — VIX {vix:.1f}. {'密切監控，收緊停損。' if zh else 'Monitor closely. Tighten stop-losses.'}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='alert-ok'><strong>{'正常環境' if zh else 'Normal Conditions'}</strong> — VIX {vix:.1f}. {'未偵測到異常。' if zh else 'No anomalies detected.'}</div>", unsafe_allow_html=True)

    if len(closes) > 5:
        rets = np.diff(closes) / np.array(closes[:-1])
        if len(rets) > 0 and abs(rets[-1]) > 0.04:
            st.markdown(f"<div class='alert-warn'><strong>{'盤中急動' if zh else 'Price Spike'}</strong> — {ticker} {rets[-1]*100:+.1f}% today.</div>", unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'風險指標' if zh else 'Risk Indicators'}</div>", unsafe_allow_html=True)

        if closes and len(closes) > 2:
            rets   = list(np.diff(closes) / np.array(closes[:-1]))
            sharpe = calc_sharpe(rets)
            mdd    = calc_max_drawdown(closes)
            ann_vol= float(np.std(rets) * np.sqrt(252) * 100)
        else:
            rets, sharpe, mdd, ann_vol = [], 0.0, 0.0, 0.0

        metrics = [
            ("VIX",                              f"{vix:.2f}",       min(vix/40,1),      vix>25),
            ("Beta",                             f"{beta:.2f}",       min(abs(beta)/2,1), abs(beta)>1.5),
            ("年化波動率" if zh else "Ann. Vol",  f"{ann_vol:.1f}%",  min(ann_vol/60,1),  ann_vol>35),
            ("最大回撤" if zh else "Max Drawdown",f"{mdd*100:.1f}%",  min(abs(mdd),1),    mdd<-0.25),
            ("夏普比率" if zh else "Sharpe",      f"{sharpe:.2f}",    max(0,1-sharpe/3),  sharpe<0.5),
        ]
        for label, value, bar_pct, is_bad in metrics:
            bar_color = "#f85149" if is_bad else "#3fb950"
            st.markdown(
                f"<div style='margin-bottom:14px'>"
                f"<div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px'>"
                f"<span style='color:#8b949e'>{label}</span>"
                f"<span style='font-weight:600;color:{'#f85149' if is_bad else '#e6edf3'};font-family:monospace'>{value}</span>"
                f"</div>"
                f"<div style='background:#21262d;border-radius:3px;height:4px'>"
                f"<div style='background:{bar_color};height:4px;border-radius:3px;width:{min(bar_pct,1)*100:.0f}%'></div>"
                f"</div></div>", unsafe_allow_html=True)

        if st.button("AI 風險摘要" if zh else "AI Risk Summary"):
            scores = isolation_forest_score(closes[-30:] if len(closes)>=30 else closes)
            with st.spinner("分析中..." if zh else "Analyzing..."):
                summary = claude_risk_summary(ticker, max(scores) if scores else 0, vix, mdd, sharpe, lang=lang)
            st.session_state["risk_summary"] = summary
        if "risk_summary" in st.session_state:
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid #30363d;border-radius:8px;"
                f"padding:12px;font-size:13px;line-height:1.7;color:#8b949e;margin-top:8px'>"
                f"{st.session_state['risk_summary']}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'凱利公式倉位建議' if zh else 'Kelly Position Sizing'}</div>", unsafe_allow_html=True)
        rk = fund.get("recommendKey","hold")
        base_wr = {"strongbuy":0.68,"buy":0.60,"hold":0.50,"underperform":0.40,"sell":0.32}.get(rk,0.50)
        win_rate= base_wr * (1 - max(0,(vix-20)/100))
        wl_ratio= 1.5
        kelly_f = kelly_fraction(win_rate, wl_ratio)
        half_k  = kelly_f / 2

        st.markdown(
            f"<div style='font-size:13px;color:#8b949e;margin-bottom:14px'>"
            f"{'勝率預估' if zh else 'Win rate'}: <strong style='color:#e6edf3'>{win_rate*100:.0f}%</strong> &nbsp;|&nbsp; "
            f"{'盈虧比' if zh else 'W/L ratio'}: <strong style='color:#e6edf3'>{wl_ratio:.1f}x</strong></div>",
            unsafe_allow_html=True)

        for label, pct in [
            ("全凱利" if zh else "Full Kelly", kelly_f),
            ("半凱利（推薦）" if zh else "Half Kelly (recommended)", half_k),
            ("固定 2% 規則" if zh else "Fixed 2% rule", 0.02),
        ]:
            is_rec = "推薦" in label or "recommend" in label.lower()
            st.markdown(
                f"<div style='margin-bottom:14px'>"
                f"<div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px'>"
                f"<span style='color:{'#e6edf3' if is_rec else '#8b949e'};font-weight:{'600' if is_rec else '400'}'>{label}</span>"
                f"<span style='color:#e6edf3;font-family:monospace;font-weight:600'>{pct*100:.1f}%</span>"
                f"</div>"
                f"<div style='background:#21262d;border-radius:3px;height:6px'>"
                f"<div style='background:{'#1f6feb' if is_rec else '#30363d'};height:6px;border-radius:3px;width:{min(pct,0.5)*200:.0f}%'></div>"
                f"</div></div>", unsafe_allow_html=True)

        portfolio_size = st.number_input("投資組合規模 ($)" if zh else "Portfolio size ($)", value=100_000, step=10_000, format="%d")
        alloc = portfolio_size * half_k
        st.markdown(
            f"<div style='background:#0d2818;border:1px solid #2ea043;border-radius:8px;padding:14px;margin-top:8px'>"
            f"<div style='font-size:14px;font-weight:600;color:#3fb950'>{'建議倉位' if zh else 'Recommended position'}: ${alloc:,.0f} ({half_k*100:.1f}%)</div>"
            f"<div style='font-size:11px;color:#8b949e;margin-top:4px'>{'採用半凱利法。全凱利法' if zh else 'Using Half-Kelly. Full Kelly'} = ${portfolio_size*kelly_f:,.0f}</div>"
            f"</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Anomaly chart
    st.markdown("---")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='card-title'>{'孤立森林異常偵測' if zh else 'Isolation Forest — Anomaly Detection'}</div>", unsafe_allow_html=True)
    if len(closes) >= 20:
        scores    = isolation_forest_score(closes)
        dates     = pd.date_range(end=pd.Timestamp.today(), periods=len(closes), freq="B")
        threshold = 2.0
        nx = [dates[i] for i,s in enumerate(scores) if s < threshold]
        ny = [scores[i] for i,s in enumerate(scores) if s < threshold]
        ax = [dates[i] for i,s in enumerate(scores) if s >= threshold]
        ay = [scores[i] for i,s in enumerate(scores) if s >= threshold]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(dates), y=closes, name="Price" if lang=="en" else "股價",
            line=dict(color="#e6edf3", width=1.5), yaxis="y2", hovertemplate="$%{y:.2f}<extra></extra>"))
        fig.add_trace(go.Bar(x=nx, y=ny, name="Normal" if lang=="en" else "正常",
            marker_color="rgba(63,185,80,0.5)", yaxis="y"))
        fig.add_trace(go.Bar(x=ax, y=ay, name="Anomaly" if lang=="en" else "異常",
            marker_color="rgba(248,81,73,0.85)", yaxis="y"))
        fig.add_hline(y=threshold, line=dict(color="#f85149", dash="dash", width=1),
            yref="y", annotation_text="2σ", annotation_font_color="#f85149")
        fig.update_layout(**PLOT, height=260, barmode="overlay",
            yaxis=dict(**PLOT["yaxis"], title="Z-Score"),
            yaxis2=dict(overlaying="y", side="right", tickprefix="$",
                tickfont=dict(color="#8b949e"), gridcolor="#21262d"),
            legend=dict(font=dict(size=11, color="#8b949e"), bgcolor="rgba(0,0,0,0)",
                orientation="h", y=1.05))
        st.plotly_chart(fig, use_container_width=True)
        n = len(ax)
        clr = "#f85149" if n>3 else "#8b949e"
        st.markdown(f"<span style='font-size:12px;color:{clr}'>{'偵測到' if zh else 'Detected'} {n} {'個異常交易日' if zh else 'anomalous sessions'}{'，黑天鵝風險偏高。' if n>5 and zh else '. Black swan risk elevated.' if n>5 else ''}</span>", unsafe_allow_html=True)
    else:
        st.info("需要至少 20 天數據。" if zh else "Need at least 20 days of data.")
    st.markdown("</div>", unsafe_allow_html=True)