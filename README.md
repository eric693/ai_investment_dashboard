# AI 投資儀表板

一個由 Claude AI 驅動的全自動投資分析系統，整合即時股市數據、總經指標、7位 AI 分析師辯論機制，以及風險管理模組。

---

## 目錄

1. [這是什麼](#這是什麼)
2. [功能總覽](#功能總覽)
3. [專案結構](#專案結構)
4. [部署教學（Render）](#部署教學render)
5. [本地端執行](#本地端執行)
6. [API Key 申請](#api-key-申請)
7. [常見問題](#常見問題)

---

## 這是什麼

這個儀表板模擬一個「AI 投資研究團隊」，自動幫你完成以下工作：

- 抓取台美股即時報價（Yahoo Finance）
- 分析 Fed 利率、CPI、失業率等總經數據（FRED）
- 讓 7 位 AI 分析師從不同角度分析同一支股票
- 模擬「看多派 vs 看空派」辯論，過濾過度樂觀的判斷
- 計算 DCF 內在價值、P/E 歷史區間
- 偵測黑天鵝事件（異常波動預警）
- 用凱利公式建議每筆交易的最佳倉位大小

---

## 功能總覽

### 總覽頁 (Overview)
- 即時股價、市值、本益比、VIX 恐慌指數
- 3個月 K 線圖（含 SMA20、SMA50 均線）
- RSI、MACD、布林通道技術指標
- 觀察清單（多支股票同時追蹤）
- P/E 歷史區間圖（判斷目前估值高低）
- AI 最終訊號（買入/持有/減持）

### 7位分析師 (7 Analysts)
| 分析師 | 分析角度 |
|--------|----------|
| 基本面分析師 | 財務三率、負債比、現金流 |
| 技術分析師 | 均線、RSI、MACD 背離 |
| 新聞情緒分析師 | 營收成長、分析師共識 |
| 市場情緒分析師 | VIX、Beta、恐貪指數 |
| 長線投資計劃 | 預估本益比、目標價空間 |
| 短線交易計劃 | 支撐壓力位、停損點 |
| 最終決策 | 綜合所有分析的最終建議 |

點擊「執行 AI 辯論」可讓 Claude 分別扮演看多、看空兩個角色，進行真實辯論並給出最終裁決。

### 總經 (Macro)
- Fed 基準利率走勢圖
- CPI 通膨率（YoY 年增率）
- 失業率趨勢
- 10年-2年殖利率利差（衰退預警指標）
- 非農就業人數月增
- AI 市場環境判定（擴張期 / 收縮期 / 過渡期）

### 風險 (Risk)
- VIX 即時警報（>22 黃色警告，>30 紅色緊急）
- 年化波動率、最大回撤、夏普比率
- 孤立森林異常偵測（識別非典型波動日）
- 凱利公式倉位建議（根據 AI 勝率自動計算）
- AI 風險摘要

### 估值 (Valuation)
- DCF 折現現金流模型（動態 WACC + 終端價值）
- 參數調整滑桿（成長率、負債比、Beta）
- 敏感度分析表格
- P/E 5年歷史區間（1σ / 2σ 標準差帶）
- 買進持有 vs SMA 均線交叉策略回測
- AI 失敗交易分析

---

## 專案結構

```
ai-investment-dashboard/
│
├── app.py                  # 主程式：頁面配置、CSS、側欄導覽、語言切換
│
├── pages/                  # 各頁面模組
│   ├── __init__.py
│   ├── overview.py         # 總覽頁
│   ├── analysts.py         # 7位分析師 + 辯論
│   ├── macro.py            # 總經數據
│   ├── risk.py             # 風險管理
│   └── valuation.py        # 估值模型 + 回測
│
├── utils/
│   ├── __init__.py
│   └── data.py             # 所有數據抓取與 AI 呼叫
│
├── requirements.txt        # Python 套件清單
├── render.yaml             # Render 部署設定
└── README.md               # 本文件
```

---

## 部署教學（Render）

> Render 是一個免費的雲端平台，可以把 Python 程式部署成網站。以下是完整步驟，初學者也能完成。

### 步驟一：建立 GitHub 帳號

如果沒有，先去 [github.com](https://github.com) 註冊免費帳號。

### 步驟二：建立新的 Repository

1. 登入 GitHub，點右上角 `+` → `New repository`
2. Repository name 填入：`ai-investment-dashboard`
3. 選 `Private`（私人，保護你的程式碼）
4. 點 `Create repository`

### 步驟三：上傳程式碼

把下載的 `ai-investment-dashboard` 資料夾，用以下方式上傳：

**方法 A：直接拖曳（最簡單）**
1. 進入你剛建立的 GitHub repo 頁面
2. 把整個資料夾的檔案拖進瀏覽器視窗
3. 點 `Commit changes`

**方法 B：使用 Git 指令（進階）**
```bash
cd ai-investment-dashboard
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/你的帳號/ai-investment-dashboard.git
git push -u origin main
```

### 步驟四：建立 Render 帳號

去 [render.com](https://render.com) 用 GitHub 帳號登入（直接授權，最方便）。

### 步驟五：建立 Web Service

1. 點 `New +` → `Web Service`
2. 選 `Build and deploy from a Git repository`
3. 連接你的 GitHub，選剛剛建立的 repo
4. 填寫以下設定：

| 欄位 | 填入內容 |
|------|----------|
| Name | `ai-investment-dashboard`（任意） |
| Region | `Singapore`（台灣用戶選這個最快） |
| Branch | `main` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `streamlit run app.py --server.port $PORT --server.address 0.0.0.0` |
| Instance Type | `Free`（免費方案） |

### 步驟六：設定環境變數（重要）

在同一個頁面往下滑，找到 `Environment Variables`，點 `Add Environment Variable`：

**必填：**
| Key | Value | 說明 |
|-----|-------|------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | Claude AI 金鑰，AI 功能需要這個 |
| `PYTHON_VERSION` | `3.12.9` | 指定 Python 版本，避免相容性問題 |

**選填（有才有即時總經數據）：**
| Key | Value | 說明 |
|-----|-------|------|
| `FRED_API_KEY` | `your_fred_key` | FRED 總經數據庫金鑰 |

### 步驟七：部署

點 `Create Web Service`，等待 3-5 分鐘建置完成。

建置成功後，Render 會給你一個網址，例如：
```
https://ai-investment-dashboard.onrender.com
```

> **注意：** 免費方案的 Render 服務在 15 分鐘無人使用後會進入休眠，下次訪問需要等約 30 秒重新啟動。付費方案（$7/月）可以避免這個問題。

### 步驟八：之後更新程式碼

只要把修改後的檔案推上 GitHub，Render 就會自動重新部署：

```bash
git add .
git commit -m "更新說明"
git push
```

---

## 本地端執行

如果想在自己電腦上跑，不需要 Render：

### 安裝 Python

去 [python.org](https://www.python.org/downloads/) 下載 Python 3.12，安裝時記得勾選 `Add Python to PATH`。

### 安裝套件

打開終端機（Windows 用 CMD 或 PowerShell，Mac 用 Terminal）：

```bash
cd ai-investment-dashboard
pip install -r requirements.txt
```

### 設定 API Key

在專案資料夾建立一個 `.env` 檔案（沒有副檔名）：

```
ANTHROPIC_API_KEY=sk-ant-api03-你的金鑰
FRED_API_KEY=你的FRED金鑰
```

### 啟動

```bash
streamlit run app.py
```

瀏覽器會自動打開 `http://localhost:8501`。

---

## API Key 申請

### Anthropic API Key（必填）

1. 去 [console.anthropic.com](https://console.anthropic.com) 註冊帳號
2. 左側選單點 `API Keys`
3. 點 `Create Key`，複製金鑰（`sk-ant-api03-...` 開頭）
4. **注意：金鑰只顯示一次，請立即複製保存**
5. 新帳號有免費額度，用完後需要綁定信用卡（按用量計費，一般使用每月約 $1-5 美元）

### FRED API Key（選填）

1. 去 [fred.stlouisfed.org](https://fred.stlouisfed.org) 點右上角 `My Account` → 註冊
2. 登入後到 `My Account` → `API Keys`
3. 點 `Request API Key`，填寫用途（填「personal research」即可）
4. 通常幾分鐘內就會收到 Email 確認，金鑰是 32 位英數字串
5. **完全免費，無需信用卡**

> 沒有 FRED Key 也沒關係，總經頁面會使用內建的近期快照數據，只是不會即時更新歷史走勢圖。

---

## 常見問題

**Q：部署後出現 `ModuleNotFoundError`？**
A：確認 `requirements.txt` 裡有列出所有套件，然後在 Render 觸發重新部署（Settings → Manual Deploy）。

**Q：AI 分析顯示「AI analysis requires ANTHROPIC_API_KEY」？**
A：環境變數沒有設定成功。到 Render → 你的服務 → Environment，確認 `ANTHROPIC_API_KEY` 有設定且值正確（`sk-ant-` 開頭）。

**Q：股價顯示 0 或載入失敗？**
A：Yahoo Finance 偶爾會限制請求，等幾分鐘後重新整理。這是免費 API 的正常現象。

**Q：Render 免費方案有什麼限制？**
A：每月 750 小時免費運行時間（一個服務大約夠用），15 分鐘無活動後休眠，每次冷啟動需要 30 秒。

**Q：想新增台股（例如 2330）？**
A：在 `app.py` 的 selectbox 清單加入 `2330.TW`（Yahoo Finance 台股格式），例如：
```python
["TSM", "NVDA", "AAPL", "2330.TW", "2454.TW", "2317.TW", ...]
```

**Q：`NotFoundError: Failed to execute 'removeChild'` 是什麼？**
A：這是 Streamlit 前端的已知 DOM 更新 bug，不影響數據和功能，重新整理頁面即可消除。

---

## 數據來源

| 數據 | 來源 | 更新頻率 |
|------|------|----------|
| 股價、基本面 | Yahoo Finance（免費） | 即時（15分鐘延遲） |
| Fed 利率、CPI 等 | FRED（免費） | 每月更新 |
| AI 分析報告 | Anthropic Claude | 每次點擊即時生成 |

---

## 授權

本專案僅供學習與個人研究使用，不構成投資建議。所有 AI 生成的分析內容僅供參考，投資決策請自行負責。