"""pages/analysts.py"""
import streamlit as st
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix,
    calc_rsi, calc_sma, calc_macd,
    claude_debate, claude_full_report, calc_dcf,
)

ZH_NAMES = ["基本面分析","技術分析","新聞情緒","市場情緒","長線投資計劃","短線交易計劃","最終決策"]
EN_NAMES = ["Fundamental Analysis","Technical Analysis","News Sentiment","Market Sentiment","Investment Plan (Long-term)","Trader Plan (Short-term)","Final Decision"]

ZH = {
    "title":       "位分析師面板",
    "signals":     "分析師訊號",
    "debate":      "多空辯論 (AI驅動)",
    "run_debate":  "執行 AI 辯論",
    "bull":        "看多觀點",
    "bear":        "看空觀點",
    "verdict":     "裁決",
    "report":      "完整 AI 投資報告",
    "gen_report":  "生成完整報告",
    "waiting":     "點擊「執行 AI 辯論」以生成即時多空分析。",
    "loading":     "載入中...",
    "generating":  "生成多智能體辯論中...",
    "gen_rep":     "生成報告中...",
}
EN = {
    "title":       "Analyst Panel",
    "signals":     "Analyst Signals",
    "debate":      "Bull vs Bear Debate (AI-Powered)",
    "run_debate":  "Run AI Debate",
    "bull":        "Bull Case",
    "bear":        "Bear Case",
    "verdict":     "Verdict",
    "report":      "Full AI Investment Report",
    "gen_report":  "Generate Full Report",
    "waiting":     "Click 'Run AI Debate' to generate a live bull/bear analysis.",
    "loading":     "Loading...",
    "generating":  "Generating multi-agent debate...",
    "gen_rep":     "Generating report...",
}

SIGNAL_COLORS = {
    "Strong Buy":"#1a7a3a","Buy":"#2a9d5c","Buy Dip":"#2a9d5c",
    "Neutral":"#888888","Hold":"#9a6700","Wait":"#9a6700",
    "Sell Rip":"#c0392b","Reduce":"#c0392b","Bearish":"#c0392b",
    "Bullish":"#2a9d5c","Strong Sell":"#7a0000",
    "強力買入":"#1a7a3a","買入":"#2a9d5c","持有":"#9a6700",
    "減持":"#c0392b","強力賣出":"#7a0000","看多":"#2a9d5c","看空":"#c0392b",
}


def build_analysts(ticker, quote, fund, vix, lang):
    closes = quote.get("closes", [])
    price  = quote.get("price", 0)
    rsi    = calc_rsi(closes)
    sma20  = calc_sma(closes, 20)
    sma50  = calc_sma(closes, 50)
    macd_v, sig_v, _ = calc_macd(closes)

    pe   = fund.get("pe") or 25
    fpe  = fund.get("forwardPE") or pe*0.9
    gm   = fund.get("grossMargins") or 0
    om   = fund.get("operMargins") or 0
    pm   = fund.get("profitMargins") or 0
    dte  = fund.get("debtToEquity") or 0
    cr   = fund.get("currentRatio") or 0
    fcf  = fund.get("freeCashflow") or 0
    rg   = fund.get("revenueGrowth") or 0
    beta = fund.get("beta") or 1
    target = fund.get("targetMeanPrice") or price
    upside = (target/price-1)*100 if price else 0

    names = ZH_NAMES if lang=="zh" else EN_NAMES
    zh = lang=="zh"

    f_score = sum([gm>0.40, om>0.15, pm>0.10, dte<100, cr>1.5, fcf>0])
    f_sig = ("看多" if zh else "Bullish") if f_score>=5 else ("看空" if zh else "Bearish") if f_score<=2 else ("中性" if zh else "Neutral")
    analysts = [{
        "name": names[0], "signal": f_sig,
        "reason": f"毛利 {gm*100:.1f}% / 營業 {om*100:.1f}% / 淨利 {pm*100:.1f}%。D/E {dte:.0f}，流動比 {cr:.2f}，FCF ${fcf/1e9:.2f}B。評分 {f_score}/6。" if zh
                  else f"Gross {gm*100:.1f}% / Op {om*100:.1f}% / Net {pm*100:.1f}%. D/E {dte:.0f}, CR {cr:.2f}, FCF ${fcf/1e9:.2f}B. Score {f_score}/6.",
    }]

    tech_bull = sum([price>sma20, price>sma50, rsi<65, rsi>35, macd_v>sig_v])
    t_sig = ("看多" if zh else "Bullish") if tech_bull>=4 else ("看空" if zh else "Bearish") if tech_bull<=2 else ("中性" if zh else "Neutral")
    analysts.append({"name": names[1], "signal": t_sig,
        "reason": f"RSI {rsi:.1f}。股價 vs SMA20: {((price/sma20-1)*100) if sma20 else 0:+.1f}%，SMA50: {((price/sma50-1)*100) if sma50 else 0:+.1f}%。MACD {'金叉' if macd_v>sig_v else '死叉'}。" if zh
                  else f"RSI {rsi:.1f}. vs SMA20: {((price/sma20-1)*100) if sma20 else 0:+.1f}%, SMA50: {((price/sma50-1)*100) if sma50 else 0:+.1f}%. MACD {'bullish cross' if macd_v>sig_v else 'bearish cross'}.",
    })

    news_sig = ("看多" if zh else "Bullish") if rg>0.15 else ("看空" if zh else "Bearish") if rg<-0.05 else ("中性" if zh else "Neutral")
    analysts.append({"name": names[2], "signal": news_sig,
        "reason": f"營收年增 {rg*100:+.1f}%。分析師共識：{fund.get('recommendKey','hold').replace('_',' ').title()}。目標價 ${target:.0f}（{upside:+.1f}% 空間）。" if zh
                  else f"Revenue {rg*100:+.1f}% YoY. Consensus: {fund.get('recommendKey','hold').replace('_',' ').title()}. Target ${target:.0f} ({upside:+.1f}% upside).",
    })

    mkt_sig = ("看多" if zh else "Bullish") if vix<18 else ("看空" if zh else "Bearish") if vix>28 else ("中性" if zh else "Neutral")
    analysts.append({"name": names[3], "signal": mkt_sig,
        "reason": f"VIX {vix:.1f}：{'低恐慌，風險偏好' if vix<18 else '高恐慌，避險情緒' if vix>28 else '中性觀望'}。Beta {beta:.2f}。" if zh
                  else f"VIX {vix:.1f}: {'risk-on' if vix<18 else 'risk-off' if vix>28 else 'neutral'}. Beta {beta:.2f}.",
    })

    iv_sig = ("強力買入" if zh else "Strong Buy") if fpe<18 and upside>20 else ("買入" if zh else "Buy") if fpe<25 and upside>10 else ("減持" if zh else "Reduce") if fpe>40 else ("持有" if zh else "Hold")
    analysts.append({"name": names[4], "signal": iv_sig,
        "reason": f"預估本益比 {fpe:.1f}x。分析師目標 ${target:.0f}（{upside:+.1f}%）。{'3-5年良好進場點' if upside>15 else '合理估值' if abs(upside)<10 else '高於共識目標'}。" if zh
                  else f"Forward P/E {fpe:.1f}x. Target ${target:.0f} ({upside:+.1f}%). {'Good 3-5Y entry' if upside>15 else 'Fair value' if abs(upside)<10 else 'Above consensus target'}.",
    })

    sup1 = sma50*0.97 if sma50 else price*0.95
    res1 = price*1.05
    stop = price*0.94
    tr_sig = ("逢低買入" if zh else "Buy Dip") if rsi<45 and price>sma50 else ("高點減持" if zh else "Sell Rip") if rsi>70 else ("觀望" if zh else "Wait")
    analysts.append({"name": names[5], "signal": tr_sig,
        "reason": f"支撐 ${sup1:.0f}（SMA50 -3%），壓力 ${res1:.0f}（+5%）。停損 ${stop:.0f}（-6%）。RSI {rsi:.0f}。" if zh
                  else f"Support ${sup1:.0f}, resistance ${res1:.0f}. Stop-loss ${stop:.0f}. RSI {rsi:.0f}.",
    })

    bull_c = sum(1 for a in analysts if any(s in a["signal"] for s in ["看多","Buy","Bull","Strong Buy","買入","逢低"]))
    bear_c = sum(1 for a in analysts if any(s in a["signal"] for s in ["看空","Sell","Bear","Reduce","賣","減持"]))
    if bull_c>=5:   final = "強力買入" if zh else "Strong Buy"
    elif bull_c>=4: final = "買入" if zh else "Buy"
    elif bear_c>=4: final = "強力賣出" if zh else "Strong Sell"
    elif bear_c>=3: final = "減持" if zh else "Reduce"
    else:           final = "持有" if zh else "Hold"

    analysts.append({"name": names[6], "signal": final,
        "reason": f"{bull_c}/6 分析師看多，{bear_c}/6 看空。{'高確信進場。' if '強力買入' in final else '等待更好機會。' if '持有' in final else '逢高減碼。'}" if zh
                  else f"{bull_c}/6 bullish, {bear_c}/6 bearish. {'High conviction entry.' if 'Strong Buy' in final else 'Wait for catalyst.' if 'Hold' in final else 'Trim on strength.'}",
    })
    return analysts


def render():
    ticker = st.session_state.get("ticker", "TSM")
    lang   = st.session_state.get("lang", "zh")
    T      = ZH if lang=="zh" else EN

    st.markdown(f"## {ticker} — 7 {T['title']}")

    with st.spinner(T["loading"]):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)
        vix   = fetch_vix()

    analysts = build_analysts(ticker, quote, fund, vix, lang)

    st.markdown(f"<div class='section-header'>{T['signals']}</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, a in enumerate(analysts[:6]):
        with cols[i%3]:
            color = SIGNAL_COLORS.get(a["signal"], "#555555")
            st.markdown(
                f"<div class='analyst-card'>"
                f"<div class='analyst-name'>{a['name']}</div>"
                f"<div class='analyst-signal' style='color:{color}'>{a['signal']}</div>"
                f"<div class='analyst-reason'>{a['reason']}</div>"
                f"</div>", unsafe_allow_html=True)

    final = analysts[-1]
    fcolor = SIGNAL_COLORS.get(final["signal"], "#555")
    st.markdown(
        f"<div class='analyst-card' style='border:2px solid {fcolor}20;background:{fcolor}08'>"
        f"<div class='analyst-name'>{final['name']}</div>"
        f"<div class='analyst-signal' style='font-size:22px;color:{fcolor}'>{final['signal']}</div>"
        f"<div class='analyst-reason'>{final['reason']}</div>"
        f"</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div class='section-header'>{T['debate']}</div>", unsafe_allow_html=True)

    if st.button(T["run_debate"]):
        with st.spinner(T["generating"]):
            from utils.data import claude_debate
            debate = claude_debate(ticker, fund, quote, vix, lang=lang)
        st.session_state[f"debate_{ticker}"] = debate
        _render_debate(debate, T)
    elif f"debate_{ticker}" in st.session_state:
        _render_debate(st.session_state[f"debate_{ticker}"], T)
    else:
        st.markdown(f"<p style='color:#aaa;font-size:13px'>{T['waiting']}</p>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div class='section-header'>{T['report']}</div>", unsafe_allow_html=True)
    if st.button(T["gen_report"]):
        with st.spinner(T["gen_rep"]):
            dcf = calc_dcf(fund.get("freeCashflow") or 1e9, fund.get("revenueGrowth") or 0.08,
                fund.get("grossMargins") or 0.4, fund.get("debtToEquity") or 50,
                fund.get("beta") or 1.2, fund.get("sharesOut") or 1e9)
            report = claude_full_report(ticker, analysts, fund, {}, dcf, lang=lang)
        st.markdown(
            f"<div style='background:#f9f9f9;border:1px solid #e5e5e5;border-radius:10px;"
            f"padding:20px 24px;font-size:14px;line-height:1.8;color:#222'>{report}</div>",
            unsafe_allow_html=True)


def _render_debate(debate, T):
    st.markdown(f"<div class='debate-bull'><div class='debate-label' style='color:#1a7a3a'>{T['bull']}</div>{debate.get('bull','—')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='debate-bear'><div class='debate-label' style='color:#c0392b'>{T['bear']}</div>{debate.get('bear','—')}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:#f5f5f5;border:1px solid #ddd;border-radius:8px;padding:14px 16px;"
        f"font-size:13px;line-height:1.7;color:#333'>"
        f"<div style='font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.05em;color:#888;margin-bottom:6px'>{T['verdict']}</div>"
        f"{debate.get('verdict','')}</div>", unsafe_allow_html=True)