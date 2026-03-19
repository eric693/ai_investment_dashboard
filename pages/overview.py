"""pages/overview.py — Dashboard home: price, signal, watchlist, P/E band."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix, fetch_watchlist,
    fetch_pe_history, calc_rsi, calc_sma, calc_macd, calc_bollinger,
    claude_analyze,
)

WATCHLIST = ["TSM", "NVDA", "AAPL", "MSFT", "META", "AVGO", "AMD", "GOOGL"]

SIGNAL_MAP = {
    "strongbuy": ("Strong Buy",   "badge-strong"),
    "buy":       ("Buy",          "badge-buy"),
    "hold":      ("Hold",         "badge-hold"),
    "underperform": ("Reduce",    "badge-sell"),
    "sell":      ("Strong Sell",  "badge-sell"),
}


def render():
    ticker = st.session_state.get("ticker", "TSM")

    with st.spinner("Fetching market data..."):
        quote  = fetch_quote(ticker)
        fund   = fetch_fundamentals(ticker)
        vix    = fetch_vix()

    price  = quote.get("price", 0)
    prev   = quote.get("prev",  0)
    ch     = price - prev
    pct    = ch / prev * 100 if prev else 0

    # ── Top metrics ───────────────────────────────────────────────────────────
    st.markdown(f"## {ticker} — Overview")
    st.markdown(f"<div class='section-header'>Market Snapshot</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Price",       f"${price:,.2f}",  f"{ch:+.2f} ({pct:+.2f}%)")
    mcap = fund.get("marketCap") or 0
    c2.metric("Market Cap",  fmt_mcap(mcap),     fund.get("recommendKey", "").replace("_"," ").title() or "—")
    pe = fund.get("pe")
    c3.metric("P/E (TTM)",   f"{pe:.1f}" if pe else "—",  f"Fwd {fund.get('forwardPE') or '—':.1f}" if fund.get('forwardPE') else "—")
    c4.metric("VIX",         f"{vix:.2f}",       "Low fear" if vix < 18 else "High fear" if vix > 28 else "Moderate")
    beta = fund.get("beta")
    c5.metric("Beta",        f"{beta:.2f}" if beta else "—",  "vs S&P 500")

    st.markdown("---")

    # ── Price chart + Watchlist ────────────────────────────────────────────────
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("<div class='section-header'>Price — 3 Months</div>", unsafe_allow_html=True)
        closes  = quote.get("closes", [])
        if closes:
            dates   = pd.date_range(end=pd.Timestamp.today(), periods=len(closes), freq="B")
            sma20   = [calc_sma(closes[:i+1], 20) for i in range(len(closes))]
            sma50   = [calc_sma(closes[:i+1], 50) for i in range(len(closes))]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=list(dates), y=closes, name=ticker,
                line=dict(color="#111111", width=2), hovertemplate="$%{y:.2f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=list(dates), y=sma20, name="SMA 20",
                line=dict(color="#2a9d5c", width=1, dash="dot"), hovertemplate="SMA20: $%{y:.2f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=list(dates), y=sma50, name="SMA 50",
                line=dict(color="#d94040", width=1, dash="dot"), hovertemplate="SMA50: $%{y:.2f}<extra></extra>"))
            fig.update_layout(
                height=260, margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(font=dict(size=11), orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", tickprefix="$"),
                xaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0"),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Technicals row
            rsi_val = calc_rsi(closes)
            macd_v, sig_v, hist_v = calc_macd(closes)
            bb_up, bb_mid, bb_lo = calc_bollinger(closes)
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("RSI (14)",    f"{rsi_val:.1f}", "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral")
            t2.metric("MACD",        f"{macd_v:+.2f}", f"Signal {sig_v:.2f}")
            t3.metric("BB Upper",    f"${bb_up:.2f}",  f"Mid ${bb_mid:.2f}")
            t4.metric("SMA50",       f"${calc_sma(closes,50):.2f}", f"{((price/calc_sma(closes,50))-1)*100:+.1f}% vs price")
        else:
            st.info("Price data unavailable.")

        # ── Final AI Signal ────────────────────────────────────────────────────
        st.markdown("<div class='section-header'>Final AI Signal</div>", unsafe_allow_html=True)
        with st.spinner("Generating signal..."):
            rk  = fund.get("recommendKey", "hold")
            sig_label, sig_cls = SIGNAL_MAP.get(rk, ("Hold", "badge-hold"))
            rsi_val  = calc_rsi(closes) if closes else 50
            target   = fund.get("targetMeanPrice")
            upside   = (target / price - 1) * 100 if target and price else None
            prompt   = (
                f"In 2 sentences, justify a '{sig_label}' rating for {ticker}. "
                f"P/E={pe}, RSI={rsi_val:.0f}, revenue growth={(fund.get('revenueGrowth') or 0)*100:.1f}%, "
                f"{'upside to target '+str(round(upside,1))+'%' if upside else ''}. Be specific."
            )
            ai_text = claude_analyze(prompt)

        st.markdown(
            f"<span class='badge {sig_cls}'>{sig_label}</span>&nbsp;&nbsp;"
            f"<span style='font-size:13px;color:#555'>{ai_text}</span>",
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown("<div class='section-header'>Watchlist</div>", unsafe_allow_html=True)
        with st.spinner("Loading watchlist..."):
            wl = fetch_watchlist(WATCHLIST)
        for row in wl:
            sym  = row["symbol"]
            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.markdown(f"**{sym}**")
            with col_b:
                sign = "+" if row["pct"] >= 0 else ""
                color = "#2a9d5c" if row["pct"] >= 0 else "#d94040"
                st.markdown(
                    f"<div style='text-align:right'>"
                    f"<span class='mono' style='font-size:13px'>${row['price']:.2f}</span>&nbsp;"
                    f"<span style='font-size:12px;color:{color}'>{sign}{row['pct']:.2f}%</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("<hr style='margin:4px 0;border-color:#f0f0f0'>", unsafe_allow_html=True)

        # ── P/E Band ──────────────────────────────────────────────────────────
        st.markdown("<div class='section-header'>P/E Band (3Y)</div>", unsafe_allow_html=True)
        pe_series = fetch_pe_history(ticker, 3)
        if len(pe_series) > 5 and pe:
            mean   = pe_series.mean()
            std    = pe_series.std()
            lo1    = mean - std
            hi1    = mean + std
            lo2    = mean - 2*std
            hi2    = mean + 2*std
            months = pd.date_range(end=pd.Timestamp.today(), periods=len(pe_series), freq="MS")
            fig2   = go.Figure()
            fig2.add_hrect(y0=lo2, y1=hi2, fillcolor="rgba(220,220,255,0.2)", line_width=0)
            fig2.add_hrect(y0=lo1, y1=hi1, fillcolor="rgba(180,180,240,0.25)", line_width=0)
            fig2.add_trace(go.Scatter(x=list(months), y=pe_series.tolist(), name="P/E",
                line=dict(color="#333", width=1.5)))
            fig2.add_hline(y=float(pe), line=dict(color="#d94040", width=2, dash="dash"),
                annotation_text=f"Now {pe:.1f}x", annotation_position="right")
            fig2.add_hline(y=float(mean), line=dict(color="#888", width=1, dash="dot"),
                annotation_text=f"Avg {mean:.1f}x", annotation_position="left")
            pos = "above +2σ" if pe > hi2 else "above +1σ" if pe > hi1 else "below -1σ" if pe < lo1 else "within normal range"
            fig2.update_layout(
                height=200, margin=dict(l=0, r=60, t=10, b=0),
                plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
                yaxis=dict(tickfont=dict(size=10), gridcolor="#f0f0f0"),
                xaxis=dict(tickfont=dict(size=10)),
            )
            st.plotly_chart(fig2, use_container_width=True)
            clr = "#d94040" if "above" in pos else "#2a9d5c"
            st.markdown(f"<span style='font-size:12px;color:{clr}'>Current P/E {pe:.1f}x — {pos}</span>", unsafe_allow_html=True)
        else:
            st.info("Insufficient P/E history.")


def fmt_mcap(v):
    if not v: return "—"
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9:  return f"${v/1e9:.1f}B"
    return f"${v/1e6:.0f}M"
