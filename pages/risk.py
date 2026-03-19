"""pages/risk.py — Risk management: VIX, anomaly detection, Kelly sizing, drawdown."""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix,
    calc_sharpe, calc_max_drawdown, isolation_forest_score, kelly_fraction,
    claude_risk_summary,
)


def render():
    ticker = st.session_state.get("ticker", "TSM")
    st.markdown(f"## {ticker} — Risk Management")

    with st.spinner("Loading risk data..."):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)
        vix   = fetch_vix()

    closes  = quote.get("price") and quote.get("closes", [])
    closes  = closes if closes else []
    volumes = quote.get("volumes", [])
    price   = quote.get("price", 0)
    beta    = fund.get("beta") or 1.0

    # ── Alerts ────────────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Live Risk Alerts</div>", unsafe_allow_html=True)

    if vix > 30:
        st.markdown(f"<div class='alert-danger'><strong>Black Swan Alert</strong> — VIX at {vix:.1f}. Isolation Forest anomaly triggered. Recommend reducing exposure by 30-50%.</div>", unsafe_allow_html=True)
    elif vix > 22:
        st.markdown(f"<div class='alert-warn'><strong>Elevated Volatility</strong> — VIX at {vix:.1f}. Monitor positions closely. Consider tightening stop-losses.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='alert-ok'><strong>Normal Conditions</strong> — VIX at {vix:.1f}. No anomalies detected. Standard position sizing applies.</div>", unsafe_allow_html=True)

    if len(closes) > 5:
        returns = np.diff(closes) / closes[:-1]
        if len(returns) > 0 and abs(returns[-1]) > 0.04:
            direction = "down" if returns[-1] < 0 else "up"
            st.markdown(
                f"<div class='alert-warn'><strong>Intraday Spike</strong> — {ticker} moved {returns[-1]*100:+.1f}% today. "
                f"Volume confirmation {'required' if direction == 'up' else 'suggests distribution'}.</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='section-header'>Risk Indicators</div>", unsafe_allow_html=True)

        if closes and len(closes) > 2:
            rets   = list(np.diff(closes) / np.array(closes[:-1]))
            sharpe = calc_sharpe(rets)
            mdd    = calc_max_drawdown(closes)
        else:
            sharpe, mdd = 0.0, 0.0

        ann_vol = float(np.std(rets) * np.sqrt(252) * 100) if closes and len(closes) > 2 else 0

        metrics = [
            ("VIX",             f"{vix:.2f}",          min(vix / 40, 1.0),    vix > 25),
            ("Beta",            f"{beta:.2f}",          min(abs(beta) / 2, 1), abs(beta) > 1.5),
            ("Ann. Volatility", f"{ann_vol:.1f}%",      min(ann_vol / 60, 1),  ann_vol > 35),
            ("Max Drawdown",    f"{mdd*100:.1f}%",      min(abs(mdd), 1),      mdd < -0.25),
            ("Sharpe Ratio",    f"{sharpe:.2f}",        max(0, 1 - sharpe/3),  sharpe < 0.5),
        ]

        for label, value, bar_pct, is_warn in metrics:
            bar_color = "#d94040" if is_warn else "#2a9d5c"
            st.markdown(
                f"<div style='margin-bottom:14px'>"
                f"<div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px'>"
                f"<span style='color:#555'>{label}</span>"
                f"<span class='mono' style='font-weight:500;color:{'#d94040' if is_warn else '#111'}'>{value}</span>"
                f"</div>"
                f"<div style='background:#f0f0f0;border-radius:3px;height:5px'>"
                f"<div style='background:{bar_color};height:5px;border-radius:3px;width:{bar_pct*100:.0f}%'></div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # AI risk summary
        if st.button("AI Risk Summary"):
            scores = isolation_forest_score(closes[-30:] if len(closes) >= 30 else closes)
            anomaly_score = max(scores) if scores else 0
            with st.spinner("Generating..."):
                summary = claude_risk_summary(ticker, anomaly_score, vix, mdd, sharpe)
            st.session_state["risk_summary"] = summary

        if "risk_summary" in st.session_state:
            st.markdown(
                f"<div style='background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;"
                f"padding:14px;font-size:13px;line-height:1.7;color:#333;margin-top:10px'>"
                f"{st.session_state['risk_summary']}</div>",
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown("<div class='section-header'>Kelly Position Sizing</div>", unsafe_allow_html=True)

        rk = fund.get("recommendKey", "hold")
        base_winrate = {"strongbuy": 0.68, "buy": 0.60, "hold": 0.50, "underperform": 0.40, "sell": 0.32}.get(rk, 0.50)
        # Adjust for VIX
        win_rate = base_winrate * (1 - max(0, (vix - 20) / 100))
        win_loss_ratio = 1.5   # typical for equities

        kelly_f = kelly_fraction(win_rate, win_loss_ratio)
        half_kelly = kelly_f / 2  # half-Kelly is safer in practice

        st.markdown(
            f"<div style='font-size:13px;color:#555;line-height:1.7;margin-bottom:16px'>"
            f"Win rate estimate: <strong>{win_rate*100:.0f}%</strong> "
            f"(based on {rk.replace('_',' ')} consensus + VIX adjustment)<br>"
            f"Win/Loss ratio: <strong>{win_loss_ratio:.1f}x</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )

        for label, pct in [("Full Kelly", kelly_f), ("Half Kelly (recommended)", half_kelly), ("Fixed 2% rule", 0.02)]:
            bar_color = "#111111" if "recommend" in label else "#888888"
            st.markdown(
                f"<div style='margin-bottom:14px'>"
                f"<div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px'>"
                f"<span style='color:#{'111' if 'recommend' in label else '888'}'>{label}</span>"
                f"<span class='mono' style='font-weight:500'>{pct*100:.1f}% of portfolio</span>"
                f"</div>"
                f"<div style='background:#f0f0f0;border-radius:3px;height:8px'>"
                f"<div style='background:{bar_color};height:8px;border-radius:3px;width:{min(pct,0.5)*200:.0f}%'></div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        portfolio_size = st.number_input("Portfolio size ($)", value=100_000, step=10_000, format="%d")
        alloc = portfolio_size * half_kelly
        st.markdown(
            f"<div style='background:#f0faf4;border:1px solid #a8d8b8;border-radius:8px;padding:14px;"
            f"margin-top:8px;font-size:14px;color:#1a5c2a'>"
            f"Recommended position: <strong>${alloc:,.0f}</strong> ({half_kelly*100:.1f}%)<br>"
            f"<span style='font-size:12px;color:#555'>Using Half-Kelly. Full Kelly = ${portfolio_size*kelly_f:,.0f}.</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("<div class='section-header'>Anomaly Detection — Isolation Forest (Z-Score Proxy)</div>", unsafe_allow_html=True)

    if len(closes) >= 20:
        scores   = isolation_forest_score(closes)
        dates    = pd.date_range(end=pd.Timestamp.today(), periods=len(closes), freq="B")
        threshold = 2.0

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(dates), y=closes,
            name="Price", line=dict(color="#111", width=1.5),
            yaxis="y2", hovertemplate="$%{y:.2f}<extra></extra>",
        ))
        normal_x = [dates[i] for i, s in enumerate(scores) if s < threshold]
        normal_y = [scores[i] for i, s in enumerate(scores) if s < threshold]
        anom_x   = [dates[i] for i, s in enumerate(scores) if s >= threshold]
        anom_y   = [scores[i] for i, s in enumerate(scores) if s >= threshold]

        fig.add_trace(go.Bar(x=normal_x, y=normal_y, name="Normal", marker_color="rgba(42,157,92,0.5)", yaxis="y"))
        fig.add_trace(go.Bar(x=anom_x,   y=anom_y,   name="Anomaly", marker_color="rgba(217,64,64,0.8)", yaxis="y"))
        fig.add_hline(y=threshold, line=dict(color="#d94040", dash="dash", width=1),
            annotation_text="Anomaly threshold (2σ)", yref="y")

        fig.update_layout(
            height=280, margin=dict(l=0, r=60, t=10, b=0),
            plot_bgcolor="white", paper_bgcolor="white",
            barmode="overlay",
            yaxis=dict(title="Z-Score", tickfont=dict(size=11), gridcolor="#f0f0f0"),
            yaxis2=dict(title="Price ($)", overlaying="y", side="right", tickfont=dict(size=11), tickprefix="$"),
            xaxis=dict(tickfont=dict(size=11)),
            legend=dict(font=dict(size=11), orientation="h", y=1.05),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
        n_anom = len(anom_x)
        st.markdown(
            f"<span style='font-size:12px;color:#{'d94040' if n_anom > 3 else '555'}'>"
            f"{n_anom} anomalous session{'s' if n_anom != 1 else ''} detected in {len(closes)}-day window."
            f"{'  Black swan risk elevated.' if n_anom > 5 else ''}"
            f"</span>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Insufficient data for anomaly detection.")
