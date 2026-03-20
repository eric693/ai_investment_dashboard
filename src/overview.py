"""src/overview.py — Dark theme overview"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix, fetch_watchlist,
    fetch_pe_history, calc_rsi, calc_sma, calc_macd, calc_bollinger, claude_analyze,
)

WATCHLIST = ["TSM", "NVDA", "AAPL", "MSFT", "META", "AVGO", "AMD", "GOOGL"]

SIGNAL_MAP = {
    "strongbuy":    ("Strong Buy",  "強力買入", "badge-strong"),
    "buy":          ("Buy",         "買入",     "badge-buy"),
    "hold":         ("Hold",        "持有",     "badge-hold"),
    "underperform": ("Reduce",      "減持",     "badge-sell"),
    "sell":         ("Strong Sell", "強力賣出", "badge-sell"),
}

PLOT = dict(
    plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
    font=dict(color="#8b949e", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(gridcolor="#21262d", linecolor="#21262d", tickfont=dict(color="#8b949e")),
    yaxis=dict(gridcolor="#21262d", linecolor="#21262d", tickfont=dict(color="#8b949e")),
    hovermode="x unified",
    legend=dict(font=dict(size=11, color="#8b949e"), bgcolor="rgba(0,0,0,0)"),
)


def fmt_mcap(v):
    if not v: return "—"
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9:  return f"${v/1e9:.1f}B"
    return f"${v/1e6:.0f}M"


def render():
    ticker = st.session_state.get("ticker", "TSM")
    lang   = st.session_state.get("lang", "zh")
    zh     = lang == "zh"

    with st.spinner("載入中..." if zh else "Loading..."):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)
        vix   = fetch_vix()

    price  = quote.get("price", 0) or 0
    prev   = quote.get("prev",  0) or 0
    ch     = price - prev
    pct    = ch / prev * 100 if prev else 0
    closes = quote.get("closes", []) or []

    # ── Top bar ───────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:16px;margin-bottom:4px'>"
        f"<span style='font-size:22px;font-weight:700;color:#e6edf3'>{ticker}</span>"
        f"<span style='font-size:28px;font-weight:700;color:#e6edf3'>${price:,.2f}</span>"
        f"<span style='font-size:15px;font-weight:600;color:{'#3fb950' if ch>=0 else '#f85149'}'>"
        f"{'▲' if ch>=0 else '▼'} {abs(ch):.2f} ({abs(pct):.2f}%)</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── KPI row ───────────────────────────────────────────────────────────────
    pe   = fund.get("pe")
    fpe  = fund.get("forwardPE")
    beta = fund.get("beta")
    mcap = fund.get("marketCap") or 0

    kpis = [
        ("市值" if zh else "Mkt Cap",   fmt_mcap(mcap),                  ""),
        ("本益比" if zh else "P/E",      f"{pe:.1f}x" if pe else "—",     f"預估 {fpe:.1f}x" if fpe else ""),
        ("VIX",                          f"{vix:.2f}",                     "低恐慌" if vix<18 else "高恐慌" if vix>28 else "中性"),
        ("Beta",                         f"{beta:.2f}" if beta else "—",   "vs S&P 500"),
        ("52W 高" if zh else "52W Hi",   f"${quote.get('high52',0):.2f}", ""),
        ("52W 低" if zh else "52W Lo",   f"${quote.get('low52',0):.2f}",  ""),
    ]
    cols = st.columns(len(kpis))
    for i, (label, val, sub) in enumerate(kpis):
        vix_color = "neg" if vix > 25 else "pos" if vix < 18 else "warn"
        sub_class = vix_color if label == "VIX" else ("pos" if "低" in sub or "Low" in sub else "neu")
        cols[i].markdown(
            f"<div class='kpi'><div class='kpi-label'>{label}</div>"
            f"<div class='kpi-val'>{val}</div>"
            f"<div class='kpi-sub {sub_class}'>{sub}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Main content ──────────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 1], gap="medium")

    with col_left:
        # Price chart
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'股價走勢 (3個月)' if zh else 'Price Chart — 3 Months'}</div>", unsafe_allow_html=True)
        if closes:
            dates = pd.date_range(end=pd.Timestamp.today(), periods=len(closes), freq="B")
            sma20 = [calc_sma(closes[:i+1], 20) for i in range(len(closes))]
            sma50 = [calc_sma(closes[:i+1], 50) for i in range(len(closes))]

            fig = go.Figure()
            # Area fill
            fig.add_trace(go.Scatter(
                x=list(dates), y=closes, name=ticker,
                line=dict(color="#1f6feb", width=2),
                fill="tozeroy", fillcolor="rgba(31,111,235,0.08)",
                hovertemplate="$%{y:.2f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(x=list(dates), y=sma20, name="SMA20",
                line=dict(color="#3fb950", width=1, dash="dot"),
                hovertemplate="SMA20: $%{y:.2f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=list(dates), y=sma50, name="SMA50",
                line=dict(color="#f85149", width=1, dash="dot"),
                hovertemplate="SMA50: $%{y:.2f}<extra></extra>"))
            fig.update_layout(**PLOT, height=280,
                yaxis=dict(**PLOT["yaxis"], tickprefix="$"),
                legend=dict(**PLOT["legend"], orientation="h", y=1.05, x=0))
            st.plotly_chart(fig, use_container_width=True)

            # Technicals mini-row
            rsi_val = calc_rsi(closes)
            macd_v, sig_v, hist_v = calc_macd(closes)
            bb_up, bb_mid, bb_lo = calc_bollinger(closes)
            sma50_val = calc_sma(closes, 50)

            tc = st.columns(4)
            def _tech(col, label, val, sub, ok):
                col.markdown(
                    f"<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px 12px'>"
                    f"<div style='font-size:10px;color:#8b949e;margin-bottom:4px'>{label}</div>"
                    f"<div style='font-size:16px;font-weight:600;color:{'#3fb950' if ok else '#f85149' if ok is False else '#e6edf3'}'>{val}</div>"
                    f"<div style='font-size:10px;color:#8b949e;margin-top:2px'>{sub}</div>"
                    f"</div>", unsafe_allow_html=True)

            _tech(tc[0], "RSI (14)", f"{rsi_val:.1f}",
                  "超買" if zh and rsi_val>70 else "超賣" if zh and rsi_val<30 else "Overbought" if rsi_val>70 else "Oversold" if rsi_val<30 else "Neutral",
                  None if 30<=rsi_val<=70 else (False if rsi_val>70 else True))
            _tech(tc[1], "MACD", f"{macd_v:+.2f}", f"Signal {sig_v:.2f}", macd_v > sig_v)
            _tech(tc[2], "布林上軌" if zh else "BB Upper", f"${bb_up:.2f}", f"Mid ${bb_mid:.2f}", None)
            _tech(tc[3], "SMA 50", f"${sma50_val:.2f}",
                  f"{((price/sma50_val-1)*100):+.1f}% vs price" if sma50_val else "—",
                  price > sma50_val if sma50_val else None)
        st.markdown("</div>", unsafe_allow_html=True)

        # AI Signal
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'最終 AI 訊號' if zh else 'Final AI Signal'}</div>", unsafe_allow_html=True)
        rk = fund.get("recommendKey", "hold")
        sig_en, sig_zh, sig_cls = SIGNAL_MAP.get(rk, ("Hold","持有","badge-hold"))
        sig_label = sig_zh if zh else sig_en
        target = fund.get("targetMeanPrice")
        upside = (target/price-1)*100 if target and price else None
        rsi_now = calc_rsi(closes) if closes else 50
        lang_instr = " Reply in Traditional Chinese." if zh else ""
        with st.spinner("AI 分析中..." if zh else "Analyzing..."):
            prompt = (
                f"In 2 sentences justify a '{sig_en}' rating for {ticker}. "
                f"P/E={pe}, RSI={rsi_now:.0f}, revenue growth={(fund.get('revenueGrowth') or 0)*100:.1f}%, "
                f"{'upside '+str(round(upside,1))+'%' if upside else ''}. Be specific.{lang_instr}"
            )
            ai_text = claude_analyze(prompt)
        st.markdown(
            f"<div style='display:flex;align-items:flex-start;gap:12px'>"
            f"<span class='badge {sig_cls}' style='margin-top:2px;white-space:nowrap'>{sig_label}</span>"
            f"<span style='font-size:13px;color:#c9d1d9;line-height:1.7'>{ai_text}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        # Watchlist
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'觀察清單' if zh else 'Watchlist'}</div>", unsafe_allow_html=True)
        wl = fetch_watchlist(WATCHLIST)
        for row in wl:
            color = "#3fb950" if row["pct"] >= 0 else "#f85149"
            sign  = "+" if row["pct"] >= 0 else ""
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:8px 0;border-bottom:1px solid #21262d'>"
                f"<span style='font-size:13px;font-weight:600;color:#e6edf3'>{row['symbol']}</span>"
                f"<div style='text-align:right'>"
                f"<div style='font-size:13px;font-weight:600;color:#e6edf3'>${row['price']:.2f}</div>"
                f"<div style='font-size:11px;color:{color}'>{sign}{row['pct']:.2f}%</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # P/E Band
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'本益比區間 (3年)' if zh else 'P/E Band (3Y)'}</div>", unsafe_allow_html=True)
        pe_series = fetch_pe_history(ticker, 3)
        if len(pe_series) > 5 and pe:
            mean  = pe_series.mean()
            std   = pe_series.std()
            months= pd.date_range(end=pd.Timestamp.today(), periods=len(pe_series), freq="MS")
            fig2  = go.Figure()
            fig2.add_hrect(y0=mean-2*std, y1=mean+2*std, fillcolor="rgba(31,111,235,0.08)", line_width=0)
            fig2.add_hrect(y0=mean-std,   y1=mean+std,   fillcolor="rgba(31,111,235,0.12)", line_width=0)
            fig2.add_trace(go.Scatter(x=list(months), y=pe_series.tolist(),
                line=dict(color="#e6edf3", width=1.5), showlegend=False,
                hovertemplate="%{x|%b %Y}: %{y:.1f}x<extra></extra>"))
            fig2.add_hline(y=float(pe), line=dict(color="#1f6feb", width=2, dash="dash"),
                annotation_text=f"Now {pe:.1f}x", annotation_font_color="#1f6feb")
            fig2.add_hline(y=float(mean), line=dict(color="#8b949e", width=1, dash="dot"),
                annotation_text=f"Avg {mean:.1f}x", annotation_font_color="#8b949e")
            fig2.update_layout(**PLOT, height=180,
                yaxis=dict(**PLOT["yaxis"], ticksuffix="x"))
            st.plotly_chart(fig2, use_container_width=True)
            pos_label = ("高於+2σ" if zh else "Above +2σ") if pe > mean+2*std else \
                        ("高於+1σ" if zh else "Above +1σ") if pe > mean+std else \
                        ("低於-1σ" if zh else "Below -1σ") if pe < mean-std else \
                        ("正常區間" if zh else "Normal range")
            clr = "#f85149" if pe > mean+std else "#3fb950" if pe < mean-std else "#8b949e"
            st.markdown(f"<span style='font-size:11px;color:{clr}'>{pos_label}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)