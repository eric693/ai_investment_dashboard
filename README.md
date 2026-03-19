# AI Investment Dashboard

A multi-agent AI investment analysis dashboard built with Streamlit, Claude AI, Yahoo Finance, and FRED.

## Features

- **7 AI Analysts**: Fundamental, Technical, News, Sentiment, Investment Plan, Trader Plan, Final Decision
- **Bull/Bear Debate**: Multi-agent AI debate for each ticker
- **DCF Valuation 2.0**: Dynamic WACC + terminal value + sensitivity analysis
- **P/E Band**: 5-year historical P/E with standard deviation bands
- **Macro Dashboard**: Fed rate, CPI, unemployment, yield spread from FRED
- **Risk Management**: Anomaly detection, Kelly sizing, Sharpe ratio, max drawdown
- **Backtest**: Buy & hold vs SMA crossover with AI failure analysis

## Deploy on Render

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/ai-investment-dashboard.git
git push -u origin main
```

### 2. Create Render Web Service

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo
3. Settings:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py`
   - **Plan**: Free or Starter

### 3. Set Environment Variables

In Render dashboard → Environment:

| Key | Value | Required |
|-----|-------|----------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Yes |
| `FRED_API_KEY` | your FRED key | No (uses fallback data) |

Get your Claude API key: https://console.anthropic.com
Get your FRED API key: https://fred.stlouisfed.org/docs/api/api_key.html

### 4. Deploy

Render auto-deploys on push. App will be at: `https://your-app.onrender.com`

## Local Development

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
streamlit run app.py
```

## Architecture

```
app.py                  Main entry, sidebar navigation
├── pages/
│   ├── overview.py     Price chart, watchlist, P/E band, AI signal
│   ├── analysts.py     7 AI analysts + bull/bear debate
│   ├── macro.py        FRED macro data + AI narrative
│   ├── risk.py         Anomaly detection, Kelly sizing, alerts
│   └── valuation.py    DCF 2.0, sensitivity, backtest
├── utils/
│   └── data.py         Yahoo Finance, FRED, Claude AI, indicators
└── static/css/
    └── style.css       IBM Plex Sans typography, clean minimal UI
```

## Data Sources

- **Price data**: Yahoo Finance (free, no API key needed)
- **Macro data**: FRED St. Louis Fed (free API key)
- **AI analysis**: Anthropic Claude Sonnet (API key required)
