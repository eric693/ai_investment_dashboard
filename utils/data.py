"""
utils/data.py  —  All data fetching: Yahoo Finance, FRED, Claude AI
"""
import os
import requests
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from anthropic import Anthropic

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

_client = None

def get_client():
    global _client
    if _client is not None:
        return _client
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None
    try:
        _client = Anthropic(api_key=key)
        return _client
    except Exception:
        return None


# ─── Yahoo Finance ────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_quote(symbol: str) -> dict:
    """Fetch latest quote + 1-month daily closes from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "3mo"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        result = data["chart"]["result"][0]
        meta   = result["meta"]
        closes = result["indicators"]["quote"][0]["close"]
        volumes= result["indicators"]["quote"][0].get("volume", [])
        timestamps = result.get("timestamp", [])
        closes  = [c for c in closes  if c is not None]
        volumes = [v for v in volumes if v is not None]
        return {
            "symbol":    symbol,
            "price":     meta.get("regularMarketPrice", 0),
            "prev":      meta.get("chartPreviousClose", 0),
            "high52":    meta.get("fiftyTwoWeekHigh", 0),
            "low52":     meta.get("fiftyTwoWeekLow", 0),
            "currency":  meta.get("currency", "USD"),
            "closes":    closes,
            "volumes":   volumes,
            "timestamps": timestamps,
        }
    except Exception as e:
        return {"symbol": symbol, "price": 0, "prev": 0, "closes": [], "volumes": [], "error": str(e)}


@st.cache_data(ttl=300)
def fetch_fundamentals(symbol: str) -> dict:
    """Fetch P/E, market cap, beta, revenue growth, margins, etc."""
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
    params = {"modules": "summaryDetail,defaultKeyStatistics,financialData,incomeStatementHistory"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        d = r.json()["quoteSummary"]["result"][0]
        sd  = d.get("summaryDetail", {})
        ks  = d.get("defaultKeyStatistics", {})
        fd  = d.get("financialData", {})
        return {
            "pe":              _raw(sd, "trailingPE"),
            "forwardPE":       _raw(sd, "forwardPE"),
            "pb":              _raw(ks, "priceToBook"),
            "marketCap":       _raw(sd, "marketCap"),
            "beta":            _raw(sd, "beta"),
            "eps":             _raw(ks, "trailingEps"),
            "revenueGrowth":   _raw(fd, "revenueGrowth"),
            "grossMargins":    _raw(fd, "grossMargins"),
            "operMargins":     _raw(fd, "operatingMargins"),
            "profitMargins":   _raw(fd, "profitMargins"),
            "debtToEquity":    _raw(fd, "debtToEquity"),
            "currentRatio":    _raw(fd, "currentRatio"),
            "freeCashflow":    _raw(fd, "freeCashflow"),
            "targetMeanPrice": _raw(fd, "targetMeanPrice"),
            "recommendKey":    fd.get("recommendationKey", ""),
            "totalRevenue":    _raw(fd, "totalRevenue"),
            "totalDebt":       _raw(ks, "totalDebt"),
            "sharesOut":       _raw(ks, "sharesOutstanding"),
            "bookValue":       _raw(ks, "bookValue"),
        }
    except Exception as e:
        return {"error": str(e)}


def _raw(d, key):
    v = d.get(key, {})
    if isinstance(v, dict):
        return v.get("raw")
    return v


@st.cache_data(ttl=300)
def fetch_vix() -> float:
    q = fetch_quote("^VIX")
    return q.get("price", 18.5)


@st.cache_data(ttl=300)
def fetch_watchlist(symbols: list) -> list:
    out = []
    for sym in symbols:
        q = fetch_quote(sym)
        if q.get("price"):
            ch  = q["price"] - q["prev"]
            pct = ch / q["prev"] * 100 if q["prev"] else 0
            out.append({"symbol": sym, "price": q["price"], "change": ch, "pct": pct})
    return out


@st.cache_data(ttl=300)
def fetch_pe_history(symbol: str, years: int = 5) -> pd.Series:
    """Approximate historical P/E from price history + TTM EPS (Yahoo)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1mo", "range": f"{years}y"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        d = r.json()["chart"]["result"][0]
        closes = d["indicators"]["quote"][0]["close"]
        closes = pd.Series([c for c in closes if c is not None])
        fund   = fetch_fundamentals(symbol)
        eps    = fund.get("eps") or 5
        pe_series = closes / eps
        return pe_series
    except Exception:
        # Fallback synthetic data
        rng = np.random.default_rng(42)
        return pd.Series(15 + rng.normal(0, 4, 60))


# ─── FRED ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_fred(series_id: str, limit: int = 24) -> pd.DataFrame:
    """Fetch a FRED data series. Falls back to synthetic if no API key."""
    if not FRED_API_KEY:
        return _fred_fallback(series_id, limit)
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id":    series_id,
        "api_key":      FRED_API_KEY,
        "file_type":    "json",
        "limit":        limit,
        "sort_order":   "desc",
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        obs = r.json()["observations"]
        df  = pd.DataFrame(obs)[["date", "value"]].copy()
        df["date"]  = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna().sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        return _fred_fallback(series_id, limit)


def _fred_fallback(series_id: str, limit: int) -> pd.DataFrame:
    """Hardcoded recent data when FRED key unavailable."""
    SNAPSHOTS = {
        "FEDFUNDS": 4.33,   # Fed Funds Rate
        "CPIAUCSL": 315.6,  # CPI (Index)
        "UNRATE":   4.1,    # Unemployment %
        "T10Y2Y":   0.28,   # 10Y-2Y Spread
        "PAYEMS":   159400, # Nonfarm Payrolls (thousands)
        "M2SL":     21200,  # M2 Money Supply (billions)
    }
    base = SNAPSHOTS.get(series_id, 100.0)
    dates = pd.date_range(end=datetime.today(), periods=limit, freq="MS")
    rng   = np.random.default_rng(hash(series_id) % (2**31))
    vals  = base + rng.normal(0, base * 0.01, limit).cumsum()
    return pd.DataFrame({"date": dates, "value": vals})


@st.cache_data(ttl=3600)
def get_macro_snapshot() -> dict:
    """Return latest single values for key macro indicators."""
    series = {
        "Fed Funds Rate (%)":   "FEDFUNDS",
        "CPI YoY (%)":          "CPIAUCSL",
        "Unemployment (%)":     "UNRATE",
        "10Y-2Y Spread (bps)":  "T10Y2Y",
        "Nonfarm Payrolls (k)": "PAYEMS",
    }
    snap = {}
    for label, sid in series.items():
        df = fetch_fred(sid, limit=2)
        if len(df) >= 2:
            snap[label] = {"current": df["value"].iloc[-1], "prev": df["value"].iloc[-2]}
        elif len(df) == 1:
            snap[label] = {"current": df["value"].iloc[-1], "prev": df["value"].iloc[-1]}
    return snap


# ─── Technical Indicators ─────────────────────────────────────────────────────

def calc_rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    arr    = np.array(closes, dtype=float)
    deltas = np.diff(arr)
    gains  = np.maximum(deltas, 0)
    losses = np.maximum(-deltas, 0)
    avg_g  = gains[-period:].mean()
    avg_l  = losses[-period:].mean()
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))


def calc_macd(closes: list):
    if len(closes) < 26:
        return 0, 0, 0
    arr   = pd.Series(closes, dtype=float)
    ema12 = arr.ewm(span=12, adjust=False).mean()
    ema26 = arr.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    signal= macd.ewm(span=9, adjust=False).mean()
    hist  = macd - signal
    return float(macd.iloc[-1]), float(signal.iloc[-1]), float(hist.iloc[-1])


def calc_sma(closes: list, period: int) -> float:
    if len(closes) < period:
        return closes[-1] if closes else 0
    return float(np.mean(closes[-period:]))


def calc_bollinger(closes: list, period: int = 20):
    if len(closes) < period:
        p = closes[-1] if closes else 0
        return p, p, p
    arr   = np.array(closes[-period:], dtype=float)
    mid   = arr.mean()
    std   = arr.std()
    return float(mid + 2*std), float(mid), float(mid - 2*std)


def calc_sharpe(returns: list, rf: float = 0.043) -> float:
    if len(returns) < 2:
        return 0.0
    r   = np.array(returns, dtype=float)
    exc = r - rf / 252
    if exc.std() == 0:
        return 0.0
    return float(exc.mean() / exc.std() * np.sqrt(252))


def calc_max_drawdown(closes: list) -> float:
    if len(closes) < 2:
        return 0.0
    arr     = np.array(closes, dtype=float)
    peak    = np.maximum.accumulate(arr)
    dd      = (arr - peak) / peak
    return float(dd.min())


def isolation_forest_score(values: list) -> list:
    """Simple z-score anomaly proxy (no sklearn dependency for Render)."""
    if len(values) < 10:
        return [0.0] * len(values)
    arr    = np.array(values, dtype=float)
    mean   = arr.mean()
    std    = arr.std() or 1
    scores = np.abs((arr - mean) / std)
    return scores.tolist()


def kelly_fraction(win_rate: float, win_loss_ratio: float) -> float:
    """Kelly Criterion: f = (bp - q) / b"""
    b = win_loss_ratio
    p = win_rate
    q = 1 - p
    if b == 0:
        return 0.0
    f = (b * p - q) / b
    return max(0.0, min(f, 0.5))   # cap at 50% for safety


# ─── DCF ─────────────────────────────────────────────────────────────────────

def calc_dcf(
    free_cashflow: float,
    revenue_growth: float,
    gross_margin: float,
    debt_to_equity: float,
    beta: float,
    shares_outstanding: float,
) -> dict:
    """
    Simplified DCF:
      - Stage 1: 5 years at dynamic g (revenue_growth)
      - Stage 2: terminal value at perpetual g
      - WACC from CAPM + debt cost
    """
    risk_free   = 0.043          # current 10Y treasury
    market_prem = 0.055
    beta        = beta or 1.2

    cost_equity = risk_free + beta * market_prem
    cost_debt   = 0.05           # approximate
    tax_rate    = 0.21
    dte         = (debt_to_equity or 50) / 100
    w_e         = 1 / (1 + dte)
    w_d         = dte / (1 + dte)
    wacc        = w_e * cost_equity + w_d * cost_debt * (1 - tax_rate)

    # Dynamic growth: blend analyst growth + industry regression to mean
    g_stage1    = min(max(revenue_growth or 0.08, 0.0), 0.40)
    g_terminal  = min(g_stage1 * 0.3, 0.04)   # terminal never > 4%

    fcf = free_cashflow or 1e9
    pv  = 0
    for yr in range(1, 6):
        fcf_yr = fcf * (1 + g_stage1) ** yr
        pv    += fcf_yr / (1 + wacc) ** yr

    terminal_fcf = fcf * (1 + g_stage1) ** 5 * (1 + g_terminal)
    terminal_val = terminal_fcf / (wacc - g_terminal) if wacc > g_terminal else 0
    pv_terminal  = terminal_val / (1 + wacc) ** 5
    total_pv     = pv + pv_terminal

    shares = shares_outstanding or 1e9
    intrinsic = total_pv / shares

    return {
        "wacc":        wacc,
        "g_stage1":    g_stage1,
        "g_terminal":  g_terminal,
        "cost_equity": cost_equity,
        "pv_fcf":      pv,
        "pv_terminal": pv_terminal,
        "intrinsic":   intrinsic,
    }


# ─── Claude AI ────────────────────────────────────────────────────────────────

def claude_analyze(prompt: str, system: str = "", max_tokens: int = 600) -> str:
    client = get_client()
    if not client:
        return "AI analysis requires ANTHROPIC_API_KEY to be set in Render environment variables."
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-5-20251001",
            max_tokens=max_tokens,
            system=system or "You are a concise, data-driven financial analyst. Use plain text, no markdown headers, no bullet points. Be direct.",
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI analysis error: {str(e)}"


def claude_debate(ticker: str, fund: dict, quote: dict, vix: float) -> dict:
    """Run a bull-vs-bear debate through Claude."""
    ctx = f"""
Ticker: {ticker}
Price: ${quote.get('price', 0):.2f}
P/E: {fund.get('pe', 'N/A')}
Forward P/E: {fund.get('forwardPE', 'N/A')}
Revenue Growth: {(fund.get('revenueGrowth') or 0)*100:.1f}%
Gross Margin: {(fund.get('grossMargins') or 0)*100:.1f}%
Debt/Equity: {fund.get('debtToEquity', 'N/A')}
Free Cash Flow: ${(fund.get('freeCashflow') or 0)/1e9:.2f}B
VIX: {vix:.1f}
52W High: ${quote.get('high52', 0):.2f}  Low: ${quote.get('low52', 0):.2f}
"""
    bull = claude_analyze(
        f"Make the strongest bullish case for {ticker} in 3 sentences. Be specific using the data.\n\nData:\n{ctx}",
        system="You are a bullish equity analyst. 3 sentences max. No disclaimers. Use specific numbers."
    )
    bear = claude_analyze(
        f"Make the strongest bearish case for {ticker} in 3 sentences. Be specific using the data.\n\nData:\n{ctx}",
        system="You are a bearish short-seller. 3 sentences max. No disclaimers. Use specific numbers."
    )
    verdict = claude_analyze(
        f"Given this bull/bear debate about {ticker}, give a final verdict in 2 sentences.\nBull: {bull}\nBear: {bear}\nData: {ctx}",
        system="You are a senior portfolio manager. 2 sentences verdict. End with one of: STRONG BUY / BUY / HOLD / REDUCE / STRONG SELL."
    )
    return {"bull": bull, "bear": bear, "verdict": verdict}


def claude_macro_narrative(macro: dict, vix: float) -> str:
    macro_str = "\n".join([f"{k}: {v['current']:.2f}" for k, v in macro.items()])
    return claude_analyze(
        f"Given these macro conditions, characterize the current market environment in 3 sentences. Is it expansionary or contractionary? What does it mean for equities?\n\n{macro_str}\nVIX: {vix:.1f}",
        system="You are a macro strategist. 3 sentences. Be direct and specific."
    )


def claude_risk_summary(ticker: str, anomaly_score: float, vix: float, dd: float, sharpe: float) -> str:
    return claude_analyze(
        f"Risk summary for {ticker}: VIX={vix:.1f}, anomaly_score={anomaly_score:.2f}, max_drawdown={dd*100:.1f}%, sharpe={sharpe:.2f}. In 2 sentences, assess the risk level and any recommended action.",
        system="You are a risk manager. 2 sentences. Be direct."
    )


def claude_full_report(ticker: str, analysts_data: list, fund: dict, macro: dict, dcf: dict) -> str:
    analyst_summary = "\n".join([f"{a['name']}: {a['signal']} — {a['reason']}" for a in analysts_data])
    return claude_analyze(
        f"Generate a brief investment report for {ticker}.\n\nAnalyst Consensus:\n{analyst_summary}\n\nDCF Intrinsic Value: ${dcf.get('intrinsic', 0):.2f}\nWACC: {dcf.get('wacc', 0)*100:.1f}%\n\nWrite 4 sentences covering: signal consensus, valuation, key risk, and final recommendation.",
        system="You are a research analyst writing a professional investment memo. 4 sentences. End with a clear rating.",
        max_tokens=400,
    )