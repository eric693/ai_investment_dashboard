"""pages/analysts.py — 7 AI analysts + bull/bear debate."""
import streamlit as st
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix,
    calc_rsi, calc_sma, calc_macd,
    claude_debate, claude_full_report, calc_dcf,
)


def build_analysts(ticker, quote, fund, vix) -> list:
    closes  = quote.get("closes", [])
    price   = quote.get("price",  0)
    rsi     = calc_rsi(closes)
    sma20   = calc_sma(closes, 20)
    sma50   = calc_sma(closes, 50)
    macd_v, sig_v, _ = calc_macd(closes)

    pe      = fund.get("pe") or 25
    fpe     = fund.get("forwardPE") or pe * 0.9
    gm      = fund.get("grossMargins") or 0
    om      = fund.get("operMargins") or 0
    pm      = fund.get("profitMargins") or 0
    dte     = fund.get("debtToEquity") or 0
    cr      = fund.get("currentRatio") or 0
    fcf     = fund.get("freeCashflow") or 0
    rg      = fund.get("revenueGrowth") or 0
    beta    = fund.get("beta") or 1
    target  = fund.get("targetMeanPrice") or price

    upside  = (target / price - 1) * 100 if price else 0

    # 1 Fundamental
    f_score = sum([gm > 0.40, om > 0.15, pm > 0.10, dte < 100, cr > 1.5, fcf > 0])
    f_sig   = "Bullish" if f_score >= 5 else "Bearish" if f_score <= 2 else "Neutral"
    analysts = [{
        "name":   "Fundamental Analysis",
        "signal": f_sig,
        "reason": (
            f"Gross {gm*100:.1f}% / Operating {om*100:.1f}% / Net {pm*100:.1f}% margins. "
            f"D/E {dte:.0f}, Current ratio {cr:.2f}. "
            f"FCF ${fcf/1e9:.2f}B. Score {f_score}/6."
        ),
    }]

    # 2 Technical
    tech_bull = sum([price > sma20, price > sma50, rsi < 65, rsi > 35, macd_v > sig_v])
    t_sig = "Bullish" if tech_bull >= 4 else "Bearish" if tech_bull <= 2 else "Neutral"
    analysts.append({
        "name":   "Technical Analysis",
        "signal": t_sig,
        "reason": (
            f"RSI {rsi:.1f}. Price vs SMA20: {((price/sma20-1)*100) if sma20 else 0:+.1f}%, "
            f"SMA50: {((price/sma50-1)*100) if sma50 else 0:+.1f}%. "
            f"MACD {macd_v:+.2f} vs signal {sig_v:.2f}. "
            f"{'Bullish crossover' if macd_v > sig_v else 'Bearish crossover'}."
        ),
    })

    # 3 News / Sentiment
    news_sig = "Bullish" if rg > 0.15 else "Bearish" if rg < -0.05 else "Neutral"
    analysts.append({
        "name":   "News Sentiment",
        "signal": news_sig,
        "reason": (
            f"Revenue growth {rg*100:+.1f}% YoY. "
            f"Analyst consensus: {fund.get('recommendKey','hold').replace('_',' ').title()}. "
            f"Mean target ${target:.0f} ({upside:+.1f}% upside)."
        ),
    })

    # 4 Market Sentiment
    mkt_sig = "Bullish" if vix < 18 else "Bearish" if vix > 28 else "Neutral"
    analysts.append({
        "name":   "Market Sentiment",
        "signal": mkt_sig,
        "reason": (
            f"VIX {vix:.1f} — {'risk-on, low fear environment' if vix < 18 else 'elevated fear, risk-off' if vix > 28 else 'moderate uncertainty'}. "
            f"Beta {beta:.2f} vs market. "
            f"{'High beta amplifies upside in risk-on' if beta > 1.3 else 'Low beta provides defensive characteristics' if beta < 0.8 else 'Market-correlated movement expected'}."
        ),
    })

    # 5 Investment Plan (long-term)
    iv_sig = "Strong Buy" if fpe < 18 and upside > 20 else "Buy" if fpe < 25 and upside > 10 else "Reduce" if fpe > 40 else "Hold"
    analysts.append({
        "name":   "Investment Plan (Long-term)",
        "signal": iv_sig,
        "reason": (
            f"Forward P/E {fpe:.1f}x. Analyst target ${target:.0f} ({upside:+.1f}% upside). "
            f"{'Attractive entry for 3-5Y horizon' if upside > 15 else 'Fair value at current levels' if abs(upside) < 10 else 'Overextended vs consensus target'}. "
            f"Kelly sizing recommendation: {'full position' if iv_sig in ('Strong Buy','Buy') else 'half position' if iv_sig == 'Hold' else 'no new positions'}."
        ),
    })

    # 6 Trader Plan (short-term)
    sup1  = sma50 * 0.97 if sma50 else price * 0.95
    res1  = price * 1.05
    stop  = price * 0.94
    tr_sig = "Buy Dip" if rsi < 45 and price > sma50 else "Sell Rip" if rsi > 70 else "Wait"
    analysts.append({
        "name":   "Trader Plan (Short-term)",
        "signal": tr_sig,
        "reason": (
            f"Support ${sup1:.0f} (SMA50 -3%), resistance ${res1:.0f} (+5%). "
            f"Stop-loss ${stop:.0f} (-6%). RSI {rsi:.0f} — "
            f"{'accumulate on weakness' if rsi < 45 else 'take partial profits' if rsi > 70 else 'hold; wait for breakout confirmation'}."
        ),
    })

    # 7 Final Decision
    bull_count = sum(1 for a in analysts if "Bull" in a["signal"] or "Buy" in a["signal"] or "Strong Buy" == a["signal"])
    bear_count = sum(1 for a in analysts if "Bear" in a["signal"] or "Sell" in a["signal"] or "Reduce" == a["signal"])
    if bull_count >= 5:
        final_sig = "Strong Buy"
    elif bull_count >= 4:
        final_sig = "Buy"
    elif bear_count >= 4:
        final_sig = "Strong Sell"
    elif bear_count >= 3:
        final_sig = "Reduce"
    else:
        final_sig = "Hold"
    analysts.append({
        "name":   "Final Decision",
        "signal": final_sig,
        "reason": (
            f"{bull_count}/6 analysts bullish, {bear_count}/6 bearish. "
            f"Consensus weights: fundamentals + technicals + macro. "
            f"{'High-conviction entry.' if final_sig == 'Strong Buy' else 'Wait for pullback.' if final_sig == 'Hold' else 'Trim on strength.' if 'Sell' in final_sig or 'Reduce' in final_sig else 'Add on weakness.'}"
        ),
    })
    return analysts


SIGNAL_COLORS = {
    "Strong Buy":  "#1a7a3a",
    "Buy":         "#2a9d5c",
    "Buy Dip":     "#2a9d5c",
    "Neutral":     "#888888",
    "Hold":        "#9a6700",
    "Wait":        "#9a6700",
    "Sell Rip":    "#c0392b",
    "Reduce":      "#c0392b",
    "Bearish":     "#c0392b",
    "Bullish":     "#2a9d5c",
    "Strong Sell": "#7a0000",
}


def render():
    ticker = st.session_state.get("ticker", "TSM")
    st.markdown(f"## {ticker} — 7 Analyst Panel")

    with st.spinner("Loading market data..."):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)
        vix   = fetch_vix()

    analysts = build_analysts(ticker, quote, fund, vix)

    st.markdown("<div class='section-header'>Analyst Signals</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, a in enumerate(analysts[:6]):
        with cols[i % 3]:
            color = SIGNAL_COLORS.get(a["signal"], "#555555")
            st.markdown(
                f"<div class='analyst-card'>"
                f"<div class='analyst-name'>{a['name']}</div>"
                f"<div class='analyst-signal' style='color:{color}'>{a['signal']}</div>"
                f"<div class='analyst-reason'>{a['reason']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Final decision full-width
    final = analysts[-1]
    fcolor = SIGNAL_COLORS.get(final["signal"], "#555")
    st.markdown(
        f"<div class='analyst-card' style='border:2px solid {fcolor}20;background:{fcolor}08'>"
        f"<div class='analyst-name'>{final['name']}</div>"
        f"<div class='analyst-signal' style='font-size:22px;color:{fcolor}'>{final['signal']}</div>"
        f"<div class='analyst-reason'>{final['reason']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("<div class='section-header'>Bull vs Bear Debate (AI-Powered)</div>", unsafe_allow_html=True)

    if st.button("Run AI Debate"):
        with st.spinner("Generating multi-agent debate..."):
            debate = claude_debate(ticker, fund, quote, vix)
        _render_debate(debate)
        st.session_state[f"debate_{ticker}"] = debate
    elif f"debate_{ticker}" in st.session_state:
        _render_debate(st.session_state[f"debate_{ticker}"])
    else:
        st.markdown("<p style='color:#aaa;font-size:13px'>Click 'Run AI Debate' to generate a live bull/bear analysis.</p>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div class='section-header'>Full AI Investment Report</div>", unsafe_allow_html=True)
    if st.button("Generate Full Report"):
        with st.spinner("Generating report..."):
            dcf = calc_dcf(
                fund.get("freeCashflow") or 1e9,
                fund.get("revenueGrowth") or 0.08,
                fund.get("grossMargins") or 0.4,
                fund.get("debtToEquity") or 50,
                fund.get("beta") or 1.2,
                fund.get("sharesOut") or 1e9,
            )
            macro_stub = {}
            report = claude_full_report(ticker, analysts, fund, macro_stub, dcf)
        st.markdown(
            f"<div style='background:#f9f9f9;border:1px solid #e5e5e5;border-radius:10px;padding:20px 24px;"
            f"font-size:14px;line-height:1.8;color:#222'>{report}</div>",
            unsafe_allow_html=True,
        )


def _render_debate(debate):
    st.markdown(
        f"<div class='debate-bull'>"
        f"<div class='debate-label' style='color:#1a7a3a'>Bull Case</div>"
        f"{debate.get('bull','—')}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='debate-bear'>"
        f"<div class='debate-label' style='color:#c0392b'>Bear Case</div>"
        f"{debate.get('bear','—')}"
        f"</div>",
        unsafe_allow_html=True,
    )
    verdict = debate.get("verdict", "")
    st.markdown(
        f"<div style='background:#f5f5f5;border:1px solid #ddd;border-radius:8px;padding:14px 16px;"
        f"font-size:13px;line-height:1.7;color:#333'>"
        f"<div style='font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.05em;color:#888;margin-bottom:6px'>Verdict</div>"
        f"{verdict}"
        f"</div>",
        unsafe_allow_html=True,
    )
