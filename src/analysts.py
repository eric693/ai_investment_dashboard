"""src/analysts.py — Dark theme 7 analysts"""
import streamlit as st
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix,
    calc_rsi, calc_sma, calc_macd, claude_debate, claude_full_report, calc_dcf,
)

ZH_NAMES = ["基本面分析","技術分析","新聞情緒","市場情緒","長線投資","短線交易","最終決策"]
EN_NAMES = ["Fundamental","Technical","News Sentiment","Market Sentiment","Investment Plan","Trader Plan","Final Decision"]

SIG_COLOR = {
    "看多":"#3fb950","Bullish":"#3fb950","Buy":"#3fb950","Strong Buy":"#3fb950",
    "買入":"#3fb950","強力買入":"#3fb950","逢低買入":"#3fb950",
    "中性":"#8b949e","Neutral":"#8b949e","Hold":"#9a6700","持有":"#d29922","Wait":"#8b949e","觀望":"#8b949e",
    "看空":"#f85149","Bearish":"#f85149","Reduce":"#f85149","Strong Sell":"#f85149",
    "減持":"#f85149","強力賣出":"#f85149","高點減持":"#f85149",
}


def build_analysts(ticker, quote, fund, vix, lang):
    zh     = lang == "zh"
    closes = quote.get("closes", []) or []
    price  = quote.get("price", 0) or 0
    rsi    = calc_rsi(closes)
    sma20  = calc_sma(closes, 20)
    sma50  = calc_sma(closes, 50)
    macd_v, sig_v, _ = calc_macd(closes)

    pe   = fund.get("pe") or 25
    fpe  = fund.get("forwardPE") or pe * 0.9
    gm   = fund.get("grossMargins") or 0
    om   = fund.get("operMargins") or 0
    pm   = fund.get("profitMargins") or 0
    dte  = fund.get("debtToEquity") or 0
    cr   = fund.get("currentRatio") or 0
    fcf  = fund.get("freeCashflow") or 0
    rg   = fund.get("revenueGrowth") or 0
    beta = fund.get("beta") or 1
    target = fund.get("targetMeanPrice") or price
    upside = (target / price - 1) * 100 if price else 0
    names  = ZH_NAMES if zh else EN_NAMES

    f_score = sum([gm>0.40, om>0.15, pm>0.10, dte<100, cr>1.5, fcf>0])
    f_sig   = ("看多" if zh else "Bullish") if f_score>=5 else ("看空" if zh else "Bearish") if f_score<=2 else ("中性" if zh else "Neutral")
    out = [{"name": names[0], "signal": f_sig,
        "reason": f"毛利 {gm*100:.1f}% / 營業 {om*100:.1f}% / 淨利 {pm*100:.1f}%。D/E {dte:.0f}，FCF ${fcf/1e9:.2f}B。{f_score}/6 分。" if zh
                  else f"Gross {gm*100:.1f}% / Op {om*100:.1f}% / Net {pm*100:.1f}%. D/E {dte:.0f}, FCF ${fcf/1e9:.2f}B. {f_score}/6."}]

    tech_bull = sum([price>sma20, price>sma50, rsi<65, rsi>35, macd_v>sig_v])
    t_sig = ("看多" if zh else "Bullish") if tech_bull>=4 else ("看空" if zh else "Bearish") if tech_bull<=2 else ("中性" if zh else "Neutral")
    out.append({"name": names[1], "signal": t_sig,
        "reason": f"RSI {rsi:.1f}。SMA20 偏離 {((price/sma20-1)*100) if sma20 else 0:+.1f}%，SMA50 偏離 {((price/sma50-1)*100) if sma50 else 0:+.1f}%。MACD {'金叉' if macd_v>sig_v else '死叉'}。" if zh
                  else f"RSI {rsi:.1f}. vs SMA20: {((price/sma20-1)*100) if sma20 else 0:+.1f}%, SMA50: {((price/sma50-1)*100) if sma50 else 0:+.1f}%. MACD {'cross up' if macd_v>sig_v else 'cross down'}."})

    news_sig = ("看多" if zh else "Bullish") if rg>0.15 else ("看空" if zh else "Bearish") if rg<-0.05 else ("中性" if zh else "Neutral")
    out.append({"name": names[2], "signal": news_sig,
        "reason": f"營收年增 {rg*100:+.1f}%。共識：{fund.get('recommendKey','hold').replace('_',' ').title()}。目標價 ${target:.0f}（{upside:+.1f}%）。" if zh
                  else f"Revenue {rg*100:+.1f}% YoY. Consensus: {fund.get('recommendKey','hold').replace('_',' ').title()}. Target ${target:.0f} ({upside:+.1f}%)."})

    mkt_sig = ("看多" if zh else "Bullish") if vix<18 else ("看空" if zh else "Bearish") if vix>28 else ("中性" if zh else "Neutral")
    out.append({"name": names[3], "signal": mkt_sig,
        "reason": f"VIX {vix:.1f}：{'低恐慌，風偏高' if vix<18 else '恐慌高，避險' if vix>28 else '中性'}。Beta {beta:.2f}。" if zh
                  else f"VIX {vix:.1f}: {'risk-on' if vix<18 else 'risk-off' if vix>28 else 'neutral'}. Beta {beta:.2f}."})

    iv_sig = ("強力買入" if zh else "Strong Buy") if fpe<18 and upside>20 else ("買入" if zh else "Buy") if fpe<25 and upside>10 else ("減持" if zh else "Reduce") if fpe>40 else ("持有" if zh else "Hold")
    out.append({"name": names[4], "signal": iv_sig,
        "reason": f"預估 P/E {fpe:.1f}x。目標 ${target:.0f}（{upside:+.1f}%）。{'3-5年良好進場' if upside>15 else '合理估值' if abs(upside)<10 else '高於目標'}。" if zh
                  else f"Fwd P/E {fpe:.1f}x. Target ${target:.0f} ({upside:+.1f}%). {'Good 3-5Y entry' if upside>15 else 'Fair value' if abs(upside)<10 else 'Above target'}."})

    sup = sma50*0.97 if sma50 else price*0.95
    res = price*1.05
    stop= price*0.94
    tr_sig = ("逢低買入" if zh else "Buy Dip") if rsi<45 and price>sma50 else ("高點減持" if zh else "Sell Rip") if rsi>70 else ("觀望" if zh else "Wait")
    out.append({"name": names[5], "signal": tr_sig,
        "reason": f"支撐 ${sup:.0f}，壓力 ${res:.0f}，停損 ${stop:.0f}（-6%）。RSI {rsi:.0f}。" if zh
                  else f"Support ${sup:.0f}, resistance ${res:.0f}, stop ${stop:.0f} (-6%). RSI {rsi:.0f}."})

    bull_c = sum(1 for a in out if any(s in a["signal"] for s in ["看多","Buy","Bull","買入","逢低"]))
    bear_c = sum(1 for a in out if any(s in a["signal"] for s in ["看空","Sell","Bear","減持","賣"]))
    if bull_c>=5:    final = "強力買入" if zh else "Strong Buy"
    elif bull_c>=4:  final = "買入" if zh else "Buy"
    elif bear_c>=4:  final = "強力賣出" if zh else "Strong Sell"
    elif bear_c>=3:  final = "減持" if zh else "Reduce"
    else:            final = "持有" if zh else "Hold"
    out.append({"name": names[6], "signal": final,
        "reason": f"{bull_c}/6 看多，{bear_c}/6 看空。{'高確信進場。' if '強力買入'==final else '等待催化劑。' if '持有'==final else '逢高減碼。'}" if zh
                  else f"{bull_c}/6 bullish, {bear_c}/6 bearish. {'High conviction entry.' if 'Strong Buy'==final else 'Wait for catalyst.' if 'Hold'==final else 'Trim on strength.'}"})
    return out


def render():
    ticker = st.session_state.get("ticker", "TSM")
    lang   = st.session_state.get("lang", "zh")
    zh     = lang == "zh"

    with st.spinner("載入中..." if zh else "Loading..."):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)
        vix   = fetch_vix()

    analysts = build_analysts(ticker, quote, fund, vix, lang)

    st.markdown(f"<div style='font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:16px'>"
                f"{ticker} — {'7 位分析師面板' if zh else '7 Analyst Panel'}</div>", unsafe_allow_html=True)

    # 6 analysts in 3x2 grid
    rows = [analysts[:3], analysts[3:6]]
    for row in rows:
        cols = st.columns(3, gap="small")
        for i, a in enumerate(row):
            color = SIG_COLOR.get(a["signal"], "#8b949e")
            with cols[i]:
                st.markdown(
                    f"<div class='analyst-card'>"
                    f"<div class='analyst-name'>{a['name']}</div>"
                    f"<div class='analyst-signal' style='color:{color}'>{a['signal']}</div>"
                    f"<div class='analyst-reason'>{a['reason']}</div>"
                    f"</div>", unsafe_allow_html=True)

    # Final decision — full width highlighted
    final = analysts[-1]
    fc    = SIG_COLOR.get(final["signal"], "#8b949e")
    st.markdown(
        f"<div style='background:#161b22;border:2px solid {fc}40;border-radius:12px;"
        f"padding:18px 22px;margin:12px 0'>"
        f"<div style='font-size:10px;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px'>{final['name']}</div>"
        f"<div style='font-size:24px;font-weight:700;color:{fc};margin-bottom:6px'>{final['signal']}</div>"
        f"<div style='font-size:13px;color:#8b949e'>{final['reason']}</div>"
        f"</div>", unsafe_allow_html=True)

    # Debate
    st.markdown("---")
    st.markdown(f"<div class='card-title'>{'多空辯論 (AI 驅動)' if zh else 'Bull vs Bear Debate (AI)'}</div>", unsafe_allow_html=True)
    if st.button("執行 AI 辯論" if zh else "Run AI Debate"):
        with st.spinner("生成多智能體辯論中..." if zh else "Generating debate..."):
            debate = claude_debate(ticker, fund, quote, vix, lang=lang)
        st.session_state[f"debate_{ticker}"] = debate

    if f"debate_{ticker}" in st.session_state:
        d = st.session_state[f"debate_{ticker}"]
        st.markdown(f"<div class='debate-bull'><div class='debate-label' style='color:#3fb950'>{'看多觀點' if zh else 'Bull Case'}</div>{d.get('bull','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='debate-bear'><div class='debate-label' style='color:#f85149'>{'看空觀點' if zh else 'Bear Case'}</div>{d.get('bear','')}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px 16px;"
            f"font-size:13px;line-height:1.7;color:#c9d1d9'>"
            f"<div style='font-size:10px;color:#8b949e;text-transform:uppercase;margin-bottom:6px'>{'裁決' if zh else 'Verdict'}</div>"
            f"{d.get('verdict','')}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color:#484f58;font-size:13px'>{'點擊按鈕生成即時多空分析。' if zh else 'Click to generate live bull/bear analysis.'}</p>", unsafe_allow_html=True)

    # Full report
    st.markdown("---")
    st.markdown(f"<div class='card-title'>{'完整 AI 投資報告' if zh else 'Full AI Investment Report'}</div>", unsafe_allow_html=True)
    if st.button("生成完整報告" if zh else "Generate Full Report"):
        with st.spinner("生成報告中..." if zh else "Generating report..."):
            dcf = calc_dcf(fund.get("freeCashflow") or 1e9, fund.get("revenueGrowth") or 0.08,
                fund.get("grossMargins") or 0.4, fund.get("debtToEquity") or 50,
                fund.get("beta") or 1.2, fund.get("sharesOut") or 1e9)
            report = claude_full_report(ticker, analysts, fund, {}, dcf, lang=lang)
        st.markdown(
            f"<div style='background:#161b22;border:1px solid #21262d;border-radius:10px;"
            f"padding:20px 24px;font-size:14px;line-height:1.8;color:#c9d1d9'>{report}</div>",
            unsafe_allow_html=True)