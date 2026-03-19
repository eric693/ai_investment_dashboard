"""pages/valuation.py"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils.data import (
    fetch_quote, fetch_fundamentals,
    calc_dcf, calc_sharpe, calc_max_drawdown,
    fetch_pe_history, claude_analyze,
)

ZH = {
    "title":       "估值與回測",
    "dcf_sec":     "DCF 折現現金流 2.0 — 動態 WACC + 終端價值",
    "adjust":      "調整 DCF 假設",
    "rg_slider":   "營收成長率 (5年)",
    "gt_slider":   "永續成長率",
    "dte_slider":  "負債/股東權益",
    "beta_slider": "Beta 值",
    "fcf":         "自由現金流 (TTM)",
    "g1":          "第一階段成長率",
    "gt":          "永續成長率",
    "ke":          "股權成本 (CAPM)",
    "wacc":        "WACC 加權平均資金成本",
    "pv_fcf":      "未來5年 FCF 現值",
    "pv_tv":       "終端價值現值",
    "intrinsic":   "每股內在價值",
    "cur_price":   "目前股價",
    "upside":      "安全邊際 / 空間",
    "dcf_water":   "DCF 瀑布圖",
    "sensitivity": "敏感度分析",
    "underval_s":  "低估 — 強力買入",
    "underval":    "略低估 — 買入",
    "overval_s":   "高估 — 減持",
    "overval":     "略高估 — 持有",
    "fair":        "合理估值 — 持有",
    "pe_sec":      "本益比歷史區間 (5年)",
    "pe_now":      "目前",
    "pe_avg":      "均值",
    "bt_sec":      "簡單回測 — 買進持有策略 vs 均線交叉策略",
    "bh_ret":      "買進持有報酬",
    "bh_sharpe":   "買進持有夏普",
    "sma_ret":     "均線策略報酬",
    "sma_sharpe":  "均線策略夏普",
    "bh_label":    "買進持有",
    "sma_label":   "均線交叉策略",
    "ai_fail":     "AI 失敗交易分析",
    "gen_fail":    "分析虧損交易...",
    "no_data":     "回測需要至少 30 天數據。",
    "loading":     "載入基本面數據中...",
    "above2s":     "高於 +2 標準差",
    "above1s":     "高於 +1 標準差",
    "below1s":     "低於 -1 標準差",
    "normal":      "正常區間",
}
EN = {
    "title":       "Valuation & Backtest",
    "dcf_sec":     "DCF Valuation 2.0 — Dynamic WACC + Terminal Value",
    "adjust":      "Adjust DCF Assumptions",
    "rg_slider":   "Revenue Growth (5Y)",
    "gt_slider":   "Terminal Growth Rate",
    "dte_slider":  "Debt/Equity ratio",
    "beta_slider": "Beta",
    "fcf":         "Free Cash Flow (TTM)",
    "g1":          "Revenue Growth (Stage 1)",
    "gt":          "Terminal Growth Rate",
    "ke":          "Cost of Equity (CAPM)",
    "wacc":        "WACC",
    "pv_fcf":      "PV of FCFs (5Y)",
    "pv_tv":       "PV of Terminal Value",
    "intrinsic":   "Intrinsic Value / Share",
    "cur_price":   "Current Price",
    "upside":      "Margin of Safety / Upside",
    "dcf_water":   "DCF Waterfall",
    "sensitivity": "Sensitivity Analysis",
    "underval_s":  "Undervalued — Strong Buy",
    "underval":    "Slightly Undervalued — Buy",
    "overval_s":   "Overvalued — Reduce",
    "overval":     "Slightly Overvalued — Hold",
    "fair":        "Fairly Valued — Hold",
    "pe_sec":      "P/E Band — 5 Year History",
    "pe_now":      "Now",
    "pe_avg":      "Avg",
    "bt_sec":      "Simple Backtest — Buy & Hold vs SMA Crossover",
    "bh_ret":      "B&H Return",
    "bh_sharpe":   "B&H Sharpe",
    "sma_ret":     "SMA Strat Return",
    "sma_sharpe":  "SMA Strat Sharpe",
    "bh_label":    "Buy & Hold",
    "sma_label":   "SMA Crossover",
    "ai_fail":     "AI Failure Analysis",
    "gen_fail":    "Analyzing losses...",
    "no_data":     "Need at least 30 days of price data for backtest.",
    "loading":     "Loading fundamentals...",
    "above2s":     "above +2σ",
    "above1s":     "above +1σ",
    "below1s":     "below -1σ",
    "normal":      "normal range",
}


def render():
    ticker = st.session_state.get("ticker", "TSM")
    lang   = st.session_state.get("lang", "zh")
    T      = ZH if lang == "zh" else EN

    st.markdown(f"## {ticker} — {T['title']}")

    with st.spinner(T["loading"]):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)

    price  = quote.get("price", 0)
    closes = quote.get("closes", [])

    st.markdown(f"<div class='section-header'>{T['dcf_sec']}</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        fcf  = fund.get("freeCashflow") or 1e9
        rg   = fund.get("revenueGrowth") or 0.10
        gm   = fund.get("grossMargins") or 0.40
        dte  = fund.get("debtToEquity") or 50
        beta = fund.get("beta") or 1.2
        shr  = fund.get("sharesOut") or 1e9

        rg_input   = float(min(max(rg, 0), 0.50))
        dte_input  = float(dte)
        beta_input = float(beta)

        with st.expander(T["adjust"], expanded=False):
            rg_input   = st.slider(T["rg_slider"],   0.0, 0.50,  rg_input,   0.01)
            dte_input  = st.slider(T["dte_slider"],  0.0, 300.0, dte_input,  5.0)
            beta_input = st.slider(T["beta_slider"], 0.3, 3.0,   beta_input, 0.1)

        dcf = calc_dcf(fcf, rg_input, gm, dte_input, beta_input, shr)
        intrinsic = dcf["intrinsic"]
        upside    = (intrinsic/price-1)*100 if price and intrinsic else 0

        rows = [
            (T["fcf"],      f"${fcf/1e9:.2f}B"),
            (T["g1"],       f"{dcf['g_stage1']*100:.1f}%"),
            (T["gt"],       f"{dcf['g_terminal']*100:.2f}%"),
            (T["ke"],       f"{dcf['cost_equity']*100:.2f}%"),
            (T["wacc"],     f"{dcf['wacc']*100:.2f}%"),
            (T["pv_fcf"],   f"${dcf['pv_fcf']/1e9:.2f}B"),
            (T["pv_tv"],    f"${dcf['pv_terminal']/1e9:.2f}B"),
            (T["intrinsic"],f"${intrinsic:.2f}"),
            (T["cur_price"],f"${price:.2f}"),
            (T["upside"],   f"{upside:+.1f}%"),
        ]
        key_rows = {T["intrinsic"], T["upside"], T["wacc"]}
        for label, val in rows:
            is_key = label in key_rows
            color = "#2a9d5c" if (label==T["upside"] and upside>0) else \
                    "#d94040" if (label==T["upside"] and upside<0) else "#111111"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;padding:9px 0;"
                f"border-bottom:1px solid #f0f0f0;font-size:13px'>"
                f"<span style='color:{'#111' if is_key else '#666'}'>{label}</span>"
                f"<span class='mono' style='font-weight:{'500' if is_key else '400'};color:{color}'>{val}</span>"
                f"</div>", unsafe_allow_html=True)

        if upside > 20:    verdict, cls = T["underval_s"], "alert-ok"
        elif upside > 5:   verdict, cls = T["underval"],   "alert-ok"
        elif upside < -20: verdict, cls = T["overval_s"],  "alert-danger"
        elif upside < -5:  verdict, cls = T["overval"],    "alert-warn"
        else:              verdict, cls = T["fair"],        "alert-warn"
        st.markdown(f"<div class='{cls}' style='margin-top:14px'><strong>{verdict}</strong></div>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"<div class='section-header'>{T['dcf_water']}</div>", unsafe_allow_html=True)
        fig_dcf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute","relative","total"],
            x=[T["pv_fcf"], T["pv_tv"], T["intrinsic"]],
            y=[dcf["pv_fcf"]/1e9, dcf["pv_terminal"]/1e9, 0],
            connector={"line":{"color":"#ccc"}},
            decreasing={"marker":{"color":"#d94040"}},
            increasing={"marker":{"color":"#2a9d5c"}},
            totals={"marker":{"color":"#111111"}},
            hovertemplate="%{x}: $%{y:.2f}B<extra></extra>",
        ))
        fig_dcf.update_layout(height=220, margin=dict(l=0,r=0,t=10,b=0),
            plot_bgcolor="white", paper_bgcolor="white",
            yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", ticksuffix="B", tickprefix="$"),
            xaxis=dict(tickfont=dict(size=10)))
        st.plotly_chart(fig_dcf, use_container_width=True)

        st.markdown(f"<div class='section-header'>{T['sensitivity']}</div>", unsafe_allow_html=True)
        sens_rows = []
        for g in [max(rg_input-0.05,0), rg_input, rg_input+0.05]:
            row = {"Growth" if lang=="en" else "成長率": f"{g*100:.0f}%"}
            for b_adj in [-0.2, 0, 0.2]:
                d2 = calc_dcf(fcf, g, gm, dte_input, beta_input+b_adj, shr)
                row[f"β{beta_input+b_adj:.1f}"] = f"${d2['intrinsic']:.0f}"
            sens_rows.append(row)
        idx_col = "Growth" if lang=="en" else "成長率"
        st.dataframe(pd.DataFrame(sens_rows).set_index(idx_col), use_container_width=True)

    st.markdown("---")
    st.markdown(f"<div class='section-header'>{T['pe_sec']}</div>", unsafe_allow_html=True)
    pe_series   = fetch_pe_history(ticker, 5)
    current_pe  = fund.get("pe")
    if len(pe_series) > 12 and current_pe:
        mean  = pe_series.mean()
        std   = pe_series.std()
        dates = pd.date_range(end=pd.Timestamp.today(), periods=len(pe_series), freq="MS")
        fig_pe = go.Figure()
        fig_pe.add_trace(go.Scatter(x=list(dates), y=[mean+2*std]*len(dates),
            fill=None, mode="lines", line=dict(color="rgba(0,0,0,0)")))
        fig_pe.add_trace(go.Scatter(x=list(dates), y=[mean-2*std]*len(dates),
            fill="tonexty", fillcolor="rgba(220,220,255,0.15)", mode="lines",
            line=dict(color="rgba(0,0,0,0)"), name="2σ"))
        fig_pe.add_trace(go.Scatter(x=list(dates), y=pe_series.tolist(),
            name="P/E", line=dict(color="#333", width=1.5),
            hovertemplate="%{x|%b %Y}: %{y:.1f}x<extra></extra>"))
        for y_val, lbl, clr in [
            (mean+2*std,"+2σ","#d94040"),(mean+std,"+1σ","#f0a500"),
            (mean,"Avg" if lang=="en" else "均值","#888"),(mean-std,"-1σ","#2a9d5c")]:
            fig_pe.add_hline(y=y_val, line=dict(color=clr, width=1, dash="dot"),
                annotation_text=f"{lbl} {y_val:.1f}x", annotation_position="right")
        fig_pe.add_hline(y=current_pe, line=dict(color="#111", width=2),
            annotation_text=f"{T['pe_now']} {current_pe:.1f}x", annotation_position="left")
        fig_pe.update_layout(height=280, margin=dict(l=0,r=80,t=10,b=0),
            plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
            yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", ticksuffix="x"),
            xaxis=dict(tickfont=dict(size=11)))
        st.plotly_chart(fig_pe, use_container_width=True)

        if current_pe > mean+2*std:   pos = T["above2s"]
        elif current_pe > mean+std:   pos = T["above1s"]
        elif current_pe < mean-std:   pos = T["below1s"]
        else:                          pos = T["normal"]
        clr = "#d94040" if "above" in pos or "高於" in pos else "#2a9d5c"
        st.markdown(f"<span style='font-size:12px;color:{clr}'>P/E {current_pe:.1f}x — {pos}</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div class='section-header'>{T['bt_sec']}</div>", unsafe_allow_html=True)

    if len(closes) >= 30:
        arr  = np.array(closes, dtype=float)
        rets = np.diff(arr) / arr[:-1]
        bh_eq     = np.cumprod(1+rets)
        bh_sharpe = calc_sharpe(rets.tolist())
        bh_mdd    = calc_max_drawdown(bh_eq.tolist())
        bh_total  = (bh_eq[-1]-1)*100

        sma20a = pd.Series(arr).rolling(20).mean().values
        sma50a = pd.Series(arr).rolling(50).mean().values
        signals= np.where(sma20a[:-1] > sma50a[:-1], 1, 0)
        str_rets= rets * signals
        str_eq  = np.cumprod(1+str_rets)
        str_sh  = calc_sharpe(str_rets.tolist())
        str_tot = (str_eq[-1]-1)*100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(T["bh_ret"],    f"{bh_total:+.1f}%")
        m2.metric(T["bh_sharpe"], f"{bh_sharpe:.2f}")
        m3.metric(T["sma_ret"],   f"{str_tot:+.1f}%")
        m4.metric(T["sma_sharpe"],f"{str_sh:.2f}")

        dates = pd.date_range(end=pd.Timestamp.today(), periods=len(bh_eq), freq="B")
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=list(dates), y=(bh_eq-1)*100,
            name=T["bh_label"], line=dict(color="#111", width=2),
            hovertemplate="%{y:+.1f}%<extra></extra>"))
        fig_bt.add_trace(go.Scatter(x=list(dates), y=(str_eq-1)*100,
            name=T["sma_label"], line=dict(color="#2a6dd9", width=1.5, dash="dot"),
            hovertemplate="%{y:+.1f}%<extra></extra>"))
        fig_bt.add_hline(y=0, line=dict(color="#ccc", width=1))
        fig_bt.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0),
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(font=dict(size=11), orientation="h", y=1.05),
            yaxis=dict(tickfont=dict(size=11), gridcolor="#f0f0f0", ticksuffix="%"),
            xaxis=dict(tickfont=dict(size=11)), hovermode="x unified")
        st.plotly_chart(fig_bt, use_container_width=True)

        if st.button(T["ai_fail"]):
            losing_days = int((rets < -0.02).sum())
            lang_instr  = " Reply in Traditional Chinese." if lang=="zh" else ""
            with st.spinner(T["gen_fail"]):
                analysis = claude_analyze(
                    f"Backtest for {ticker}: B&H {bh_total:+.1f}%, SMA {str_tot:+.1f}%. "
                    f"Sharpe {bh_sharpe:.2f}, Max DD {bh_mdd*100:.1f}%. "
                    f"{losing_days} sessions >2% daily loss. "
                    f"3 sentences: main strategy blind spots and whether losses were macro-driven or systematic.{lang_instr}",
                    system="You are a quant analyst. 3 sentences. Be specific."
                )
            st.markdown(
                f"<div style='background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;"
                f"padding:14px;font-size:13px;line-height:1.7;color:#333'>{analysis}</div>",
                unsafe_allow_html=True)
    else:
        st.info(T["no_data"])