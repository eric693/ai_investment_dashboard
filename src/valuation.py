"""src/valuation.py — Dark theme valuation"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils.data import (
    fetch_quote, fetch_fundamentals,
    calc_dcf, calc_sharpe, calc_max_drawdown,
    fetch_pe_history, claude_analyze,
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

    price  = quote.get("price", 0) or 0
    closes = quote.get("closes", []) or []

    st.markdown(f"<div style='font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:16px'>{ticker} — {'估值與回測' if zh else 'Valuation & Backtest'}</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'DCF 折現現金流模型' if zh else 'DCF Valuation Model'}</div>", unsafe_allow_html=True)

        fcf  = fund.get("freeCashflow") or 1e9
        rg   = fund.get("revenueGrowth") or 0.10
        gm   = fund.get("grossMargins") or 0.40
        dte  = fund.get("debtToEquity") or 50
        beta = fund.get("beta") or 1.2
        shr  = fund.get("sharesOut") or 1e9

        rg_i   = float(min(max(rg, 0), 0.50))
        dte_i  = float(dte)
        beta_i = float(beta)

        with st.expander("調整假設" if zh else "Adjust Assumptions", expanded=False):
            rg_i   = st.slider("營收成長率" if zh else "Revenue Growth", 0.0, 0.50, rg_i,   0.01)
            dte_i  = st.slider("負債/權益" if zh else "Debt/Equity",     0.0, 300.0, dte_i, 5.0)
            beta_i = st.slider("Beta",                                    0.3, 3.0,   beta_i, 0.1)

        dcf       = calc_dcf(fcf, rg_i, gm, dte_i, beta_i, shr)
        intrinsic = dcf["intrinsic"]
        upside    = (intrinsic/price-1)*100 if price and intrinsic else 0

        rows = [
            ("FCF (TTM)",                             f"${fcf/1e9:.2f}B"),
            ("成長率 Stage 1" if zh else "Growth Stage 1", f"{dcf['g_stage1']*100:.1f}%"),
            ("永續成長率" if zh else "Terminal Growth",    f"{dcf['g_terminal']*100:.2f}%"),
            ("WACC",                                   f"{dcf['wacc']*100:.2f}%"),
            ("股權成本" if zh else "Cost of Equity",   f"{dcf['cost_equity']*100:.2f}%"),
            ("FCF 現值 (5Y)" if zh else "PV FCFs (5Y)", f"${dcf['pv_fcf']/1e9:.2f}B"),
            ("終端價值現值" if zh else "PV Terminal",   f"${dcf['pv_terminal']/1e9:.2f}B"),
            ("每股內在價值" if zh else "Intrinsic/Share", f"${intrinsic:.2f}"),
            ("目前股價" if zh else "Current Price",    f"${price:.2f}"),
            ("安全邊際" if zh else "Upside / Margin",  f"{upside:+.1f}%"),
        ]
        is_key = {"每股內在價值","Intrinsic/Share","安全邊際","Upside / Margin","WACC"}
        for label, val in rows:
            key = label in is_key
            up_color = "#3fb950" if (label in ("安全邊際","Upside / Margin") and upside>0) else \
                       "#f85149" if (label in ("安全邊際","Upside / Margin") and upside<0) else "#e6edf3"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;padding:8px 0;"
                f"border-bottom:1px solid #21262d;font-size:13px'>"
                f"<span style='color:{'#e6edf3' if key else '#8b949e'}'>{label}</span>"
                f"<span style='font-weight:{'700' if key else '400'};color:{up_color};font-family:monospace'>{val}</span>"
                f"</div>", unsafe_allow_html=True)

        if upside>20:    verdict,cls="低估 — 強力買入" if zh else "Undervalued — Strong Buy","alert-ok"
        elif upside>5:   verdict,cls="略低估 — 買入" if zh else "Slightly Undervalued — Buy","alert-ok"
        elif upside<-20: verdict,cls="高估 — 減持" if zh else "Overvalued — Reduce","alert-danger"
        elif upside<-5:  verdict,cls="略高估 — 持有" if zh else "Slightly Overvalued — Hold","alert-warn"
        else:            verdict,cls="合理估值 — 持有" if zh else "Fairly Valued — Hold","alert-warn"
        st.markdown(f"<div class='{cls}' style='margin-top:12px'><strong>{verdict}</strong></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-title'>{'DCF 瀑布圖' if zh else 'DCF Waterfall'}</div>", unsafe_allow_html=True)
        labels = ["FCF 現值" if zh else "PV FCFs", "終端價值" if zh else "PV Terminal", "內在價值" if zh else "Intrinsic"]
        fig_w = go.Figure(go.Waterfall(
            orientation="v", measure=["absolute","relative","total"],
            x=labels, y=[dcf["pv_fcf"]/1e9, dcf["pv_terminal"]/1e9, 0],
            connector={"line":{"color":"#30363d"}},
            decreasing={"marker":{"color":"#f85149"}},
            increasing={"marker":{"color":"#3fb950"}},
            totals={"marker":{"color":"#1f6feb"}},
            hovertemplate="%{x}: $%{y:.2f}B<extra></extra>",
        ))
        fig_w.update_layout(**PLOT, height=220,
            yaxis=dict(**PLOT["yaxis"], ticksuffix="B", tickprefix="$"))
        st.plotly_chart(fig_w, use_container_width=True)

        st.markdown(f"<div class='card-title' style='margin-top:12px'>{'敏感度分析' if zh else 'Sensitivity'}</div>", unsafe_allow_html=True)
        sens = []
        for g in [max(rg_i-0.05,0), rg_i, rg_i+0.05]:
            row = {"g": f"{g*100:.0f}%"}
            for b_adj in [-0.2, 0, 0.2]:
                d2 = calc_dcf(fcf, g, gm, dte_i, beta_i+b_adj, shr)
                row[f"β{beta_i+b_adj:.1f}"] = f"${d2['intrinsic']:.0f}"
            sens.append(row)
        st.dataframe(pd.DataFrame(sens).set_index("g"), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # P/E Band
    st.markdown("---")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='card-title'>{'本益比歷史區間 (5年)' if zh else 'P/E Band — 5 Year History'}</div>", unsafe_allow_html=True)
    pe_series  = fetch_pe_history(ticker, 5)
    current_pe = fund.get("pe")
    if len(pe_series) > 12 and current_pe:
        mean  = pe_series.mean()
        std   = pe_series.std()
        dates = pd.date_range(end=pd.Timestamp.today(), periods=len(pe_series), freq="MS")
        fig_pe = go.Figure()
        fig_pe.add_trace(go.Scatter(x=list(dates), y=[mean+2*std]*len(dates), fill=None, mode="lines", line=dict(color="rgba(0,0,0,0)")))
        fig_pe.add_trace(go.Scatter(x=list(dates), y=[mean-2*std]*len(dates),
            fill="tonexty", fillcolor="rgba(31,111,235,0.08)", mode="lines", line=dict(color="rgba(0,0,0,0)")))
        fig_pe.add_trace(go.Scatter(x=list(dates), y=pe_series.tolist(), name="P/E",
            line=dict(color="#c9d1d9", width=1.5),
            hovertemplate="%{x|%b %Y}: %{y:.1f}x<extra></extra>"))
        for y_val, lbl, clr in [(mean+2*std,"+2σ","#f85149"),(mean+std,"+1σ","#d29922"),
                                 (mean,"Avg","#484f58"),(mean-std,"-1σ","#3fb950")]:
            fig_pe.add_hline(y=y_val, line=dict(color=clr, width=1, dash="dot"),
                annotation_text=f"{lbl} {y_val:.1f}x", annotation_font_color=clr)
        fig_pe.add_hline(y=current_pe, line=dict(color="#1f6feb", width=2),
            annotation_text=f"Now {current_pe:.1f}x", annotation_font_color="#1f6feb")
        fig_pe.update_layout(**PLOT, height=260, yaxis=dict(**PLOT["yaxis"], ticksuffix="x"), showlegend=False)
        st.plotly_chart(fig_pe, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Backtest
    st.markdown("---")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='card-title'>{'回測：買進持有 vs 均線交叉' if zh else 'Backtest: Buy & Hold vs SMA Crossover'}</div>", unsafe_allow_html=True)
    if len(closes) >= 30:
        arr  = np.array(closes, dtype=float)
        rets = np.diff(arr) / arr[:-1]
        bh_eq    = np.cumprod(1+rets)
        bh_sh    = calc_sharpe(rets.tolist())
        bh_mdd   = calc_max_drawdown(bh_eq.tolist())
        bh_tot   = (bh_eq[-1]-1)*100

        sma20a   = pd.Series(arr).rolling(20).mean().values
        sma50a   = pd.Series(arr).rolling(50).mean().values
        signals  = np.where(sma20a[:-1]>sma50a[:-1], 1, 0)
        str_rets = rets * signals
        str_eq   = np.cumprod(1+str_rets)
        str_sh   = calc_sharpe(str_rets.tolist())
        str_tot  = (str_eq[-1]-1)*100

        m1,m2,m3,m4 = st.columns(4)
        for col, label, val, ref in [
            (m1,"買進持有報酬" if zh else "B&H Return",    f"{bh_tot:+.1f}%", bh_tot>0),
            (m2,"買進持有夏普" if zh else "B&H Sharpe",    f"{bh_sh:.2f}",   bh_sh>1),
            (m3,"均線策略報酬" if zh else "SMA Return",    f"{str_tot:+.1f}%",str_tot>0),
            (m4,"均線策略夏普" if zh else "SMA Sharpe",    f"{str_sh:.2f}",  str_sh>1),
        ]:
            col.markdown(
                f"<div class='kpi'><div class='kpi-label'>{label}</div>"
                f"<div class='kpi-val' style='font-size:18px;color:{'#3fb950' if ref else '#f85149'}'>{val}</div></div>",
                unsafe_allow_html=True)

        dates = pd.date_range(end=pd.Timestamp.today(), periods=len(bh_eq), freq="B")
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=list(dates), y=(bh_eq-1)*100,
            name="買進持有" if zh else "Buy & Hold", line=dict(color="#1f6feb", width=2),
            hovertemplate="%{y:+.1f}%<extra></extra>"))
        fig_bt.add_trace(go.Scatter(x=list(dates), y=(str_eq-1)*100,
            name="均線策略" if zh else "SMA Strategy", line=dict(color="#3fb950", width=1.5, dash="dot"),
            hovertemplate="%{y:+.1f}%<extra></extra>"))
        fig_bt.add_hline(y=0, line=dict(color="#30363d", width=1))
        fig_bt.update_layout(**PLOT, height=240,
            yaxis=dict(**PLOT["yaxis"], ticksuffix="%"),
            legend=dict(font=dict(size=11, color="#8b949e"), bgcolor="rgba(0,0,0,0)",
                orientation="h", y=1.05))
        st.plotly_chart(fig_bt, use_container_width=True)

        if st.button("AI 失敗交易分析" if zh else "AI Failure Analysis"):
            losing = int((rets < -0.02).sum())
            lang_i = " Reply in Traditional Chinese." if zh else ""
            with st.spinner("分析中..." if zh else "Analyzing..."):
                r = claude_analyze(
                    f"Backtest {ticker}: B&H {bh_tot:+.1f}%, SMA {str_tot:+.1f}%. "
                    f"Sharpe {bh_sh:.2f}, MaxDD {bh_mdd*100:.1f}%. {losing} sessions >2% loss. "
                    f"3 sentences: blind spots and whether losses were macro or systematic.{lang_i}",
                    system="You are a quant analyst. 3 sentences.")
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid #30363d;border-radius:8px;"
                f"padding:14px;font-size:13px;line-height:1.7;color:#8b949e'>{r}</div>",
                unsafe_allow_html=True)
    else:
        st.info("需要至少 30 天數據。" if zh else "Need at least 30 days of data.")
    st.markdown("</div>", unsafe_allow_html=True)