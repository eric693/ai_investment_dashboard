"""pages/valuation.py — DCF 2.0, P/E band, backtest performance."""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix,
    calc_dcf, calc_sharpe, calc_max_drawdown,
    fetch_pe_history, claude_analyze,
)


def render():
    ticker = st.session_state.get("ticker", "TSM")
    st.markdown(f"## {ticker} — Valuation & Backtest")

    with st.spinner("Loading fundamentals..."):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)

    price    = quote.get("price", 0)
    closes   = quote.get("closes", [])

    # ── DCF ───────────────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>DCF Valuation 2.0 — Dynamic WACC + Terminal Value</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        fcf  = fund.get("freeCashflow") or 1e9
        rg   = fund.get("revenueGrowth") or 0.10
        gm   = fund.get("grossMargins") or 0.40
        dte  = fund.get("debtToEquity") or 50
        beta = fund.get("beta") or 1.2
        shr  = fund.get("sharesOut") or 1e9

        # Sliders for sensitivity — always visible in expander
        rg_input   = float(min(max(rg, 0), 0.50))
        dte_input  = float(dte)
        beta_input = float(beta)
        with st.expander("Adjust DCF Assumptions", expanded=False):
            rg_input   = st.slider("Revenue Growth (5Y)",  0.0, 0.50, rg_input,   0.01, format="%.2f")
            _gterm     = st.slider("Terminal Growth Rate", 0.0, 0.05, 0.025,      0.005, format="%.3f")
            dte_input  = st.slider("Debt/Equity ratio",   0.0, 300.0, dte_input,  5.0)
            beta_input = st.slider("Beta",                0.3, 3.0,   beta_input, 0.1)

        dcf = calc_dcf(fcf, rg_input, gm, dte_input, beta_input, shr)
        intrinsic = dcf["intrinsic"]
        upside    = (intrinsic / price - 1) * 100 if price and intrinsic else 0

        rows = [
            ("Free Cash Flow (TTM)",       f"${fcf/1e9:.2f}B"),
            ("Revenue Growth (Stage 1)",   f"{dcf['g_stage1']*100:.1f}%"),
            ("Terminal Growth Rate",       f"{dcf['g_terminal']*100:.2f}%"),
            ("Cost of Equity (CAPM)",      f"{dcf['cost_equity']*100:.2f}%"),
            ("WACC",                       f"{dcf['wacc']*100:.2f}%"),
            ("PV of FCFs (5Y)",            f"${dcf['pv_fcf']/1e9:.2f}B"),
            ("PV of Terminal Value",       f"${dcf['pv_terminal']/1e9:.2f}B"),
            ("Intrinsic Value / Share",    f"${intrinsic:.2f}"),
            ("Current Price",              f"${price:.2f}"),
            ("Margin of Safety / Upside",  f"{upside:+.1f}%"),
        ]
        for label, val in rows:
            is_key = label in ("Intrinsic Value / Share", "Margin of Safety / Upside", "WACC")
            color  = "#2a9d5c" if (label == "Margin of Safety / Upside" and upside > 0) else \
                     "#d94040" if (label == "Margin of Safety / Upside" and upside < 0) else \
                     "#111111"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;padding:9px 0;"
                f"border-bottom:1px solid #f0f0f0;font-size:13px'>"
                f"<span style='color:#{'111' if is_key else '666'}'>{label}</span>"
                f"<span class='mono' style='font-weight:{'500' if is_key else '400'};color:{color}'>{val}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Verdict
        if upside > 20:
            verdict, cls = "Undervalued — Strong Buy", "alert-ok"
        elif upside > 5:
            verdict, cls = "Slightly Undervalued — Buy", "alert-ok"
        elif upside < -20:
            verdict, cls = "Overvalued — Reduce", "alert-danger"
        elif upside < -5:
            verdict, cls = "Slightly Overvalued — Hold", "alert-warn"
        else:
            verdict, cls = "Fairly Valued — Hold", "alert-warn"
        st.markdown(f"<div class='{cls}' style='margin-top:14px'><strong>{verdict}</strong></div>", unsafe_allow_html=True)

    with col2:
        # DCF Waterfall chart
        st.markdown("<div class='section-header'>DCF Waterfall</div>", unsafe_allow_html=True)
        fig_dcf = go.Figure(go.Waterfall(
            name="DCF", orientation="v",
            measure=["absolute", "relative", "total"],
            x=["PV FCFs (5Y)", "PV Terminal", "Intrinsic Value"],
            y=[dcf["pv_fcf"]/1e9, dcf["pv_terminal"]/1e9, 0],
            connector={"line": {"color": "#ccc"}},
            decreasing={"marker": {"color": "#d94040"}},
            increasing={"marker": {"color": "#2a9d5c"}},
            totals={"marker": {"color": "#111111"}},
            hovertemplate="%{x}: $%{y:.2f}B<extra></extra>",
        ))
        fig_dcf.update_layout(
            height=220, margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", ticksuffix="B", tickprefix="$"),
            xaxis=dict(tickfont=dict(size=11)),
        )
        st.plotly_chart(fig_dcf, use_container_width=True)

        # Sensitivity table
        st.markdown("<div class='section-header'>Sensitivity Analysis</div>", unsafe_allow_html=True)
        sens_rows = []
        for g in [rg_input - 0.05, rg_input, rg_input + 0.05]:
            row = {}
            for w_adj in [-0.01, 0, 0.01]:
                d2 = calc_dcf(fcf, max(g, 0), gm, dte_input, beta_input + w_adj*10, shr)
                row[f"WACC{(d2['wacc'])*100:.1f}%"] = f"${d2['intrinsic']:.0f}"
            sens_rows.append({"Growth": f"{g*100:.0f}%", **row})
        st.dataframe(pd.DataFrame(sens_rows).set_index("Growth"), use_container_width=True)

    st.markdown("---")

    # ── P/E Band ──────────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>P/E Band — 5 Year History</div>", unsafe_allow_html=True)
    pe_series = fetch_pe_history(ticker, 5)
    current_pe = fund.get("pe")
    if len(pe_series) > 12 and current_pe:
        mean  = pe_series.mean()
        std   = pe_series.std()
        dates = pd.date_range(end=pd.Timestamp.today(), periods=len(pe_series), freq="MS")

        fig_pe = go.Figure()
        fig_pe.add_trace(go.Scatter(
            x=list(dates), y=[mean + 2*std]*len(dates),
            fill=None, mode="lines", line=dict(color="rgba(0,0,0,0)"), name="+2σ",
        ))
        fig_pe.add_trace(go.Scatter(
            x=list(dates), y=[mean - 2*std]*len(dates),
            fill="tonexty", fillcolor="rgba(220,220,255,0.15)", mode="lines",
            line=dict(color="rgba(0,0,0,0)"), name="2σ band",
        ))
        fig_pe.add_trace(go.Scatter(
            x=list(dates), y=[mean + std]*len(dates),
            fill=None, mode="lines", line=dict(color="rgba(0,0,0,0)"),
        ))
        fig_pe.add_trace(go.Scatter(
            x=list(dates), y=[mean - std]*len(dates),
            fill="tonexty", fillcolor="rgba(180,180,240,0.2)", mode="lines",
            line=dict(color="rgba(0,0,0,0)"), name="1σ band",
        ))
        fig_pe.add_trace(go.Scatter(
            x=list(dates), y=pe_series.tolist(),
            name="Hist P/E", line=dict(color="#333", width=1.5),
            hovertemplate="%{x|%b %Y}: %{y:.1f}x<extra></extra>",
        ))
        for y, label, color in [
            (mean + 2*std, "+2σ", "#d94040"),
            (mean + std,   "+1σ", "#f0a500"),
            (mean,         "Avg", "#888888"),
            (mean - std,   "-1σ", "#2a9d5c"),
        ]:
            fig_pe.add_hline(y=y, line=dict(color=color, width=1, dash="dot"),
                annotation_text=f"{label} {y:.1f}x", annotation_position="right")
        fig_pe.add_hline(y=current_pe, line=dict(color="#111", width=2),
            annotation_text=f"Now {current_pe:.1f}x", annotation_position="left")
        fig_pe.update_layout(
            height=280, margin=dict(l=0, r=80, t=10, b=0),
            plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
            yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", ticksuffix="x"),
            xaxis=dict(tickfont=dict(size=11)),
        )
        st.plotly_chart(fig_pe, use_container_width=True)

    st.markdown("---")

    # ── Backtest ──────────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Simple Backtest — Buy & Hold vs SMA Crossover</div>", unsafe_allow_html=True)

    if len(closes) >= 30:
        arr   = np.array(closes, dtype=float)
        rets  = np.diff(arr) / arr[:-1]

        # Buy & Hold
        bh_equity = np.cumprod(1 + rets)
        bh_sharpe = calc_sharpe(rets.tolist())
        bh_mdd    = calc_max_drawdown(bh_equity.tolist())
        bh_total  = (bh_equity[-1] - 1) * 100

        # SMA crossover strategy
        sma20arr = pd.Series(arr).rolling(20).mean().values
        sma50arr = pd.Series(arr).rolling(50).mean().values
        signals  = np.where(sma20arr[:-1] > sma50arr[:-1], 1, 0)
        strat_rets = rets * signals
        strat_eq  = np.cumprod(1 + strat_rets)
        strat_sharpe = calc_sharpe(strat_rets.tolist())
        strat_mdd    = calc_max_drawdown(strat_eq.tolist())
        strat_total  = (strat_eq[-1] - 1) * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("B&H Return",     f"{bh_total:+.1f}%")
        m2.metric("B&H Sharpe",     f"{bh_sharpe:.2f}")
        m3.metric("SMA Strat Return", f"{strat_total:+.1f}%")
        m4.metric("SMA Strat Sharpe", f"{strat_sharpe:.2f}")

        dates = pd.date_range(end=pd.Timestamp.today(), periods=len(bh_equity), freq="B")
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(
            x=list(dates), y=(bh_equity - 1) * 100,
            name="Buy & Hold", line=dict(color="#111", width=2),
            hovertemplate="%{y:+.1f}%<extra>Buy & Hold</extra>",
        ))
        fig_bt.add_trace(go.Scatter(
            x=list(dates), y=(strat_eq - 1) * 100,
            name="SMA Crossover", line=dict(color="#2a6dd9", width=1.5, dash="dot"),
            hovertemplate="%{y:+.1f}%<extra>SMA Strategy</extra>",
        ))
        fig_bt.add_hline(y=0, line=dict(color="#ccc", width=1))
        fig_bt.update_layout(
            height=260, margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(font=dict(size=11), orientation="h", y=1.05),
            yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", ticksuffix="%"),
            xaxis=dict(tickfont=dict(size=11)),
            hovermode="x unified",
        )
        st.plotly_chart(fig_bt, use_container_width=True)

        # AI failure analysis
        if st.button("AI Failure Analysis"):
            losing_days = int((rets < -0.02).sum())
            with st.spinner("Analyzing losses..."):
                analysis = claude_analyze(
                    f"Backtest for {ticker}: Buy&Hold {bh_total:+.1f}%, SMA strategy {strat_total:+.1f}%. "
                    f"Sharpe (B&H) {bh_sharpe:.2f}, Max DD {bh_mdd*100:.1f}%. "
                    f"{losing_days} sessions with >2% daily loss. "
                    f"In 3 sentences: identify the main strategy blind spots and whether losses were macro-driven or systematic.",
                    system="You are a quant analyst reviewing backtest failures. 3 sentences. Be specific."
                )
            st.markdown(
                f"<div style='background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;"
                f"padding:14px;font-size:13px;line-height:1.7;color:#333'>{analysis}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Need at least 30 days of price data for backtest.")
