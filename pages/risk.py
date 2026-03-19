"""pages/risk.py"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils.data import (
    fetch_quote, fetch_fundamentals, fetch_vix,
    calc_sharpe, calc_max_drawdown, isolation_forest_score, kelly_fraction,
    claude_risk_summary,
)

ZH = {
    "title":      "風險管理",
    "alerts":     "即時風險警報",
    "alert_bs":   "黑天鵝警報",
    "alert_bs_t": "VIX 達 {v:.1f}。孤立森林異常觸發。建議減少 30-50% 倉位。",
    "alert_el":   "波動率偏高",
    "alert_el_t": "VIX 達 {v:.1f}。密切監控部位，考慮收緊停損。",
    "alert_ok":   "正常市場環境",
    "alert_ok_t": "VIX 達 {v:.1f}。未偵測到異常。標準倉位管理適用。",
    "alert_spike":"盤中急漲急跌",
    "alert_sp_t": "{t} 今日變動 {r:+.1f}%。{'確認成交量' if True else ''}",
    "indicators": "風險指標",
    "vix_lbl":    "VIX 恐慌指數",
    "beta_lbl":   "Beta 值",
    "vol_lbl":    "年化波動率",
    "dd_lbl":     "最大回撤",
    "sharpe_lbl": "夏普比率",
    "ai_btn":     "人工智慧風險摘要",
    "kelly":      "凱利倉位規模",
    "kelly_sub":  "基於 AI 勝率估算",
    "win_rate":   "勝率預估：{w:.0f}%（基於市場普遍預期+VIX調整）",
    "wl_ratio":   "盈虧比：{r:.1f}倍",
    "full_k":     "全凱利",
    "half_k":     "半凱利（推薦）",
    "fixed_k":    "固定 2% 規則",
    "portfolio":  "投資組合規模（美元）",
    "rec_pos":    "建議倉位：${a:,.0f}（{p:.1f}%）",
    "full_kval":  "採用半凱利法。全凱利法 = ${v:,.0f} 美元。",
    "of_port":    "投資組合的",
    "anomaly":    "孤立森林 — 異常偵測（Z分數代理）",
    "n_anom":     "{n} 個交易日偵測到異常（共 {total} 日）",
    "high_risk":  "黑天鵝風險偏高。",
    "no_data":    "異常偵測需要至少 20 天數據。",
    "loading":    "載入風險數據中...",
    "generating": "生成 AI 風險摘要中...",
    "anomaly_thresh": "異常閾值 (2σ)",
}
EN = {
    "title":      "Risk Management",
    "alerts":     "Live Risk Alerts",
    "alert_bs":   "Black Swan Alert",
    "alert_bs_t": "VIX at {v:.1f}. Isolation Forest anomaly triggered. Recommend reducing exposure 30-50%.",
    "alert_el":   "Elevated Volatility",
    "alert_el_t": "VIX at {v:.1f}. Monitor positions closely. Consider tightening stop-losses.",
    "alert_ok":   "Normal Conditions",
    "alert_ok_t": "VIX at {v:.1f}. No anomalies detected. Standard position sizing applies.",
    "alert_spike":"Intraday Spike",
    "alert_sp_t": "{t} moved {r:+.1f}% today.",
    "indicators": "Risk Indicators",
    "vix_lbl":    "VIX",
    "beta_lbl":   "Beta",
    "vol_lbl":    "Ann. Volatility",
    "dd_lbl":     "Max Drawdown",
    "sharpe_lbl": "Sharpe Ratio",
    "ai_btn":     "AI Risk Summary",
    "kelly":      "Kelly Position Sizing",
    "kelly_sub":  "Based on AI win-rate estimate",
    "win_rate":   "Win rate estimate: {w:.0f}% (consensus + VIX adj.)",
    "wl_ratio":   "Win/Loss ratio: {r:.1f}x",
    "full_k":     "Full Kelly",
    "half_k":     "Half Kelly (recommended)",
    "fixed_k":    "Fixed 2% rule",
    "portfolio":  "Portfolio size ($)",
    "rec_pos":    "Recommended position: ${a:,.0f} ({p:.1f}%)",
    "full_kval":  "Using Half-Kelly. Full Kelly = ${v:,.0f}.",
    "of_port":    "of portfolio",
    "anomaly":    "Anomaly Detection — Isolation Forest (Z-Score Proxy)",
    "n_anom":     "{n} anomalous session(s) detected in {total}-day window.",
    "high_risk":  " Black swan risk elevated.",
    "no_data":    "Insufficient data for anomaly detection.",
    "loading":    "Loading risk data...",
    "generating": "Generating AI risk summary...",
    "anomaly_thresh": "Anomaly threshold (2σ)",
}


def render():
    ticker = st.session_state.get("ticker", "TSM")
    lang   = st.session_state.get("lang", "zh")
    T      = ZH if lang == "zh" else EN

    st.markdown(f"## {ticker} — {T['title']}")

    with st.spinner(T["loading"]):
        quote = fetch_quote(ticker)
        fund  = fetch_fundamentals(ticker)
        vix   = fetch_vix()

    closes  = quote.get("closes", []) or []
    price   = quote.get("price", 0)
    beta    = fund.get("beta") or 1.0

    # ── Alerts ────────────────────────────────────────────────────────────────
    st.markdown(f"<div class='section-header'>{T['alerts']}</div>", unsafe_allow_html=True)

    if vix > 30:
        st.markdown(f"<div class='alert-danger'><strong>{T['alert_bs']}</strong> — {T['alert_bs_t'].format(v=vix)}</div>", unsafe_allow_html=True)
    elif vix > 22:
        st.markdown(f"<div class='alert-warn'><strong>{T['alert_el']}</strong> — {T['alert_el_t'].format(v=vix)}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='alert-ok'><strong>{T['alert_ok']}</strong> — {T['alert_ok_t'].format(v=vix)}</div>", unsafe_allow_html=True)

    if len(closes) > 5:
        returns = np.diff(closes) / np.array(closes[:-1])
        if len(returns) > 0 and abs(returns[-1]) > 0.04:
            st.markdown(
                f"<div class='alert-warn'><strong>{T['alert_spike']}</strong> — "
                f"{ticker} {returns[-1]*100:+.1f}%</div>",
                unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"<div class='section-header'>{T['indicators']}</div>", unsafe_allow_html=True)

        if closes and len(closes) > 2:
            rets   = list(np.diff(closes) / np.array(closes[:-1]))
            sharpe = calc_sharpe(rets)
            mdd    = calc_max_drawdown(closes)
            ann_vol= float(np.std(rets) * np.sqrt(252) * 100)
        else:
            rets, sharpe, mdd, ann_vol = [], 0.0, 0.0, 0.0

        metrics = [
            (T["vix_lbl"],    f"{vix:.2f}",       min(vix/40, 1.0),       vix > 25),
            (T["beta_lbl"],   f"{beta:.2f}",       min(abs(beta)/2, 1),    abs(beta) > 1.5),
            (T["vol_lbl"],    f"{ann_vol:.1f}%",   min(ann_vol/60, 1),     ann_vol > 35),
            (T["dd_lbl"],     f"{mdd*100:.1f}%",   min(abs(mdd), 1),       mdd < -0.25),
            (T["sharpe_lbl"], f"{sharpe:.2f}",      max(0, 1-sharpe/3),    sharpe < 0.5),
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
                f"<div style='background:{bar_color};height:5px;border-radius:3px;width:{min(bar_pct,1)*100:.0f}%'></div>"
                f"</div></div>",
                unsafe_allow_html=True)

        if st.button(T["ai_btn"]):
            scores = isolation_forest_score(closes[-30:] if len(closes) >= 30 else closes)
            anomaly_score = max(scores) if scores else 0
            with st.spinner(T["generating"]):
                summary = claude_risk_summary(ticker, anomaly_score, vix, mdd, sharpe, lang=lang)
            st.session_state["risk_summary"] = summary

        if "risk_summary" in st.session_state:
            st.markdown(
                f"<div style='background:#fafafa;border:1px solid #e5e5e5;border-radius:8px;"
                f"padding:14px;font-size:13px;line-height:1.7;color:#333;margin-top:10px'>"
                f"{st.session_state['risk_summary']}</div>",
                unsafe_allow_html=True)

    with col2:
        st.markdown(f"<div class='section-header'>{T['kelly']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:12px;color:#888;margin-bottom:12px'>{T['kelly_sub']}</div>", unsafe_allow_html=True)

        rk = fund.get("recommendKey", "hold")
        base_wr = {"strongbuy":0.68,"buy":0.60,"hold":0.50,"underperform":0.40,"sell":0.32}.get(rk, 0.50)
        win_rate = base_wr * (1 - max(0, (vix-20)/100))
        wl_ratio = 1.5
        kelly_f  = kelly_fraction(win_rate, wl_ratio)
        half_k   = kelly_f / 2

        st.markdown(
            f"<div style='font-size:13px;color:#555;line-height:1.8;margin-bottom:16px'>"
            f"{T['win_rate'].format(w=win_rate*100)}<br>{T['wl_ratio'].format(r=wl_ratio)}"
            f"</div>", unsafe_allow_html=True)

        for label, pct in [(T["full_k"], kelly_f), (T["half_k"], half_k), (T["fixed_k"], 0.02)]:
            is_rec = T["half_k"] in label
            bar_color = "#111111" if is_rec else "#aaaaaa"
            st.markdown(
                f"<div style='margin-bottom:14px'>"
                f"<div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px'>"
                f"<span style='color:{'#111' if is_rec else '#888'}'>{label}</span>"
                f"<span class='mono' style='font-weight:500'>{pct*100:.1f}% {T['of_port']}</span>"
                f"</div>"
                f"<div style='background:#f0f0f0;border-radius:3px;height:8px'>"
                f"<div style='background:{bar_color};height:8px;border-radius:3px;width:{min(pct,0.5)*200:.0f}%'></div>"
                f"</div></div>",
                unsafe_allow_html=True)

        portfolio_size = st.number_input(T["portfolio"], value=100_000, step=10_000, format="%d")
        alloc = portfolio_size * half_k
        st.markdown(
            f"<div style='background:#f0faf4;border:1px solid #a8d8b8;border-radius:8px;"
            f"padding:14px;margin-top:8px;font-size:14px;color:#1a5c2a'>"
            f"{T['rec_pos'].format(a=alloc, p=half_k*100)}<br>"
            f"<span style='font-size:12px;color:#555'>{T['full_kval'].format(v=portfolio_size*kelly_f)}</span>"
            f"</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div class='section-header'>{T['anomaly']}</div>", unsafe_allow_html=True)

    if len(closes) >= 20:
        scores    = isolation_forest_score(closes)
        dates     = pd.date_range(end=pd.Timestamp.today(), periods=len(closes), freq="B")
        threshold = 2.0
        normal_x  = [dates[i] for i,s in enumerate(scores) if s < threshold]
        normal_y  = [scores[i] for i,s in enumerate(scores) if s < threshold]
        anom_x    = [dates[i] for i,s in enumerate(scores) if s >= threshold]
        anom_y    = [scores[i] for i,s in enumerate(scores) if s >= threshold]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(dates), y=closes, name="Price" if lang=="en" else "股價",
            line=dict(color="#111", width=1.5), yaxis="y2",
            hovertemplate="$%{y:.2f}<extra></extra>"))
        fig.add_trace(go.Bar(x=normal_x, y=normal_y,
            name="Normal" if lang=="en" else "正常",
            marker_color="rgba(42,157,92,0.5)", yaxis="y"))
        fig.add_trace(go.Bar(x=anom_x, y=anom_y,
            name="Anomaly" if lang=="en" else "異常",
            marker_color="rgba(217,64,64,0.8)", yaxis="y"))
        fig.add_hline(y=threshold, line=dict(color="#d94040", dash="dash", width=1),
            annotation_text=T["anomaly_thresh"], yref="y")
        fig.update_layout(
            height=280, margin=dict(l=0,r=60,t=10,b=0),
            plot_bgcolor="white", paper_bgcolor="white", barmode="overlay",
            yaxis=dict(title="Z-Score", tickfont=dict(size=11), gridcolor="#f0f0f0"),
            yaxis2=dict(title="Price ($)" if lang=="en" else "股價 ($)", overlaying="y", side="right",
                tickfont=dict(size=11), tickprefix="$"),
            xaxis=dict(tickfont=dict(size=11)),
            legend=dict(font=dict(size=11), orientation="h", y=1.05),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        n_anom = len(anom_x)
        extra  = T["high_risk"] if n_anom > 5 else ""
        st.markdown(
            f"<span style='font-size:12px;color:{'#d94040' if n_anom > 3 else '#555'}'>"
            f"{T['n_anom'].format(n=n_anom, total=len(closes))}{extra}</span>",
            unsafe_allow_html=True)
    else:
        st.info(T["no_data"])