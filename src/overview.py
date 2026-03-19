"""pages/overview.py"""
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
    "strongbuy":    ("Strong Buy",  "強力買入", "badge-strong"),
    "buy":          ("Buy",         "買入",     "badge-buy"),
    "hold":         ("Hold",        "持有",     "badge-hold"),
    "underperform": ("Reduce",      "減持",     "badge-sell"),
    "sell":         ("Strong Sell", "強力賣出", "badge-sell"),
}

ZH = {
    "snapshot":   "市場快照",
    "price":      "股價",
    "mcap":       "市值",
    "pe":         "本益比",
    "vix":        "波動指數",
    "beta":       "Beta 值",
    "low_fear":   "恐慌低",
    "high_fear":  "恐慌高",
    "moderate":   "中等",
    "chart":      "股價走勢 (3個月)",
    "rsi":        "RSI (14)",
    "macd":       "MACD",
    "bb_upper":   "布林上軌",
    "sma50":      "SMA50",
    "overbought": "超買",
    "oversold":   "超賣",
    "neutral":    "中性",
    "signal_sec": "最終 AI 訊號",
    "watchlist":  "觀察清單",
    "pe_band":    "本益比區間 (3年)",
    "loading":    "載入中...",
    "vs_sp500":   "vs 標普500",
    "fwd":        "預估",
}
EN = {
    "snapshot":   "Market Snapshot",
    "price":      "Price",
    "mcap":       "Market Cap",
    "pe":         "P/E (TTM)",
    "vix":        "VIX",
    "beta":       "Beta",
    "low_fear":   "Low fear",
    "high_fear":  "High fear",
    "moderate":   "Moderate",
    "chart":      "Price — 3 Months",
    "rsi":        "RSI (14)",
    "macd":       "MACD",
    "bb_upper":   "BB Upper",
    "sma50":      "SMA50",
    "overbought": "Overbought",
    "oversold":   "Oversold",
    "neutral":    "Neutral",
    "signal_sec": "Final AI Signal",
    "watchlist":  "Watchlist",
    "pe_band":    "P/E Band (3Y)",
    "loading":    "Loading...",
    "vs_sp500":   "vs S&P 500",
    "fwd":        "Fwd",
}


def render():
    ticker = st.session_state.get("ticker", "TSM")
    lang   = st.session_state.get("lang", "zh")
    T      = ZH if lang == "zh" else EN

    with st.spinner(T["loading"]):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)
        vix   = fetch_vix()

    price = quote.get("price", 0)
    prev  = quote.get("prev",  0)
    ch    = price - prev
    pct   = ch / prev * 100 if prev else 0

    st.markdown(f"## {ticker} — {T['snapshot']}")
    st.markdown(f"<div class='section-header'>{T['snapshot']}</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(T["price"],   f"${price:,.2f}",  f"{ch:+.2f} ({pct:+.2f}%)")
    mcap = fund.get("marketCap") or 0
    c2.metric(T["mcap"],    fmt_mcap(mcap),     fund.get("recommendKey","").replace("_"," ").title() or "-")
    pe = fund.get("pe")
    fpe = fund.get("forwardPE")
    c3.metric(T["pe"],      f"{pe:.1f}" if pe else "-",  f"{T['fwd']} {fpe:.1f}" if fpe else "-")
    c4.metric(T["vix"],     f"{vix:.2f}", T["low_fear"] if vix < 18 else T["high_fear"] if vix > 28 else T["moderate"])
    beta = fund.get("beta")
    c5.metric(T["beta"],    f"{beta:.2f}" if beta else "-", T["vs_sp500"])

    st.markdown("---")
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown(f"<div class='section-header'>{T['chart']}</div>", unsafe_allow_html=True)
        closes = quote.get("closes", [])
        if closes:
            dates  = pd.date_range(end=pd.Timestamp.today(), periods=len(closes), freq="B")
            sma20  = [calc_sma(closes[:i+1], 20) for i in range(len(closes))]
            sma50  = [calc_sma(closes[:i+1], 50) for i in range(len(closes))]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=list(dates), y=closes, name=ticker,
                line=dict(color="#111111", width=2), hovertemplate="$%{y:.2f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=list(dates), y=sma20, name="SMA 20",
                line=dict(color="#2a9d5c", width=1, dash="dot")))
            fig.add_trace(go.Scatter(x=list(dates), y=sma50, name="SMA 50",
                line=dict(color="#d94040", width=1, dash="dot")))
            fig.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0),
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(font=dict(size=11), orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", tickprefix="$"),
                xaxis=dict(tickfont=dict(size=11)), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            rsi_val = calc_rsi(closes)
            macd_v, sig_v, _ = calc_macd(closes)
            bb_up, bb_mid, _ = calc_bollinger(closes)
            t1, t2, t3, t4 = st.columns(4)
            t1.metric(T["rsi"],      f"{rsi_val:.1f}", T["overbought"] if rsi_val>70 else T["oversold"] if rsi_val<30 else T["neutral"])
            t2.metric(T["macd"],     f"{macd_v:+.2f}", f"Signal {sig_v:.2f}")
            t3.metric(T["bb_upper"], f"${bb_up:.2f}",  f"Mid ${bb_mid:.2f}")
            t4.metric(T["sma50"],    f"${calc_sma(closes,50):.2f}", f"{((price/calc_sma(closes,50))-1)*100:+.1f}%")

        st.markdown(f"<div class='section-header'>{T['signal_sec']}</div>", unsafe_allow_html=True)
        with st.spinner(T["loading"]):
            rk = fund.get("recommendKey", "hold")
            sig_en, sig_zh, sig_cls = SIGNAL_MAP.get(rk, ("Hold","持有","badge-hold"))
            sig_label = sig_zh if lang == "zh" else sig_en
            target = fund.get("targetMeanPrice")
            upside = (target/price-1)*100 if target and price else None
            rsi_val = calc_rsi(closes) if closes else 50
            prompt = (
                f"In 2 sentences justify a '{sig_en}' rating for {ticker}. "
                f"P/E={pe}, RSI={rsi_val:.0f}, revenue growth={(fund.get('revenueGrowth') or 0)*100:.1f}%, "
                f"{'upside '+str(round(upside,1))+'%' if upside else ''}. Be specific. "
                + ("Reply in Traditional Chinese." if lang=="zh" else "")
            )
            ai_text = claude_analyze(prompt)
        st.markdown(
            f"<span class='badge {sig_cls}'>{sig_label}</span>&nbsp;&nbsp;"
            f"<span style='font-size:13px;color:#555'>{ai_text}</span>",
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(f"<div class='section-header'>{T['watchlist']}</div>", unsafe_allow_html=True)
        with st.spinner(T["loading"]):
            wl = fetch_watchlist(WATCHLIST)
        for row in wl:
            ca, cb = st.columns([1,1])
            with ca:
                st.markdown(f"**{row['symbol']}**")
            with cb:
                sign  = "+" if row["pct"] >= 0 else ""
                color = "#2a9d5c" if row["pct"] >= 0 else "#d94040"
                st.markdown(
                    f"<div style='text-align:right'>"
                    f"<span class='mono' style='font-size:13px'>${row['price']:.2f}</span>&nbsp;"
                    f"<span style='font-size:12px;color:{color}'>{sign}{row['pct']:.2f}%</span>"
                    f"</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:4px 0;border-color:#f0f0f0'>", unsafe_allow_html=True)

        st.markdown(f"<div class='section-header'>{T['pe_band']}</div>", unsafe_allow_html=True)
        pe_series = fetch_pe_history(ticker, 3)
        if len(pe_series) > 5 and pe:
            mean  = pe_series.mean()
            std   = pe_series.std()
            months= pd.date_range(end=pd.Timestamp.today(), periods=len(pe_series), freq="MS")
            fig2  = go.Figure()
            fig2.add_hrect(y0=mean-2*std, y1=mean+2*std, fillcolor="rgba(220,220,255,0.2)", line_width=0)
            fig2.add_hrect(y0=mean-std,   y1=mean+std,   fillcolor="rgba(180,180,240,0.25)", line_width=0)
            fig2.add_trace(go.Scatter(x=list(months), y=pe_series.tolist(), name="P/E",
                line=dict(color="#333", width=1.5)))
            fig2.add_hline(y=float(pe), line=dict(color="#d94040", width=2, dash="dash"),
                annotation_text=f"Now {pe:.1f}x", annotation_position="right")
            fig2.add_hline(y=float(mean), line=dict(color="#888", width=1, dash="dot"),
                annotation_text=f"Avg {mean:.1f}x", annotation_position="left")
            pos_zh = "高於+2標準差" if pe>mean+2*std else "高於+1標準差" if pe>mean+std else "低於-1標準差" if pe<mean-std else "正常區間"
            pos_en = "above +2sd" if pe>mean+2*std else "above +1sd" if pe>mean+std else "below -1sd" if pe<mean-std else "normal range"
            pos    = pos_zh if lang=="zh" else pos_en
            fig2.update_layout(height=200, margin=dict(l=0,r=60,t=10,b=0),
                plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
                yaxis=dict(tickfont=dict(size=10), gridcolor="#f0f0f0"),
                xaxis=dict(tickfont=dict(size=10)))
            st.plotly_chart(fig2, use_container_width=True)
            clr = "#d94040" if "above" in pos_en else "#2a9d5c"
            st.markdown(f"<span style='font-size:12px;color:{clr}'>P/E {pe:.1f}x — {pos}</span>", unsafe_allow_html=True)


def fmt_mcap(v):
    if not v: return "-"
    if v >= 1e12: return f"${v/1e12:.2f}T"
    if v >= 1e9:  return f"${v/1e9:.1f}B"
    return f"${v/1e6:.0f}M"