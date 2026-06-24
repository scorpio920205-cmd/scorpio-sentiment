# USA 美股情緒警示燈

一個現代化的網頁版美股情緒監控與警示燈號儀表板。本工具每日定時自動抓取市場上最關鍵的四大情绪指標（VIX、CNN Fear & Greed、AAII、NAAIM），並根據內建的情緒加權模板計算總體恐慌分數，藉由「紅、黃、綠」三色燈號為投資人提供直觀的市場恐慌程度警示。

### 🌟 核心特色
* **📊 四大關鍵情緒整合**：完整收錄並呈現 VIX 恐慌指數、CNN 恐慌與貪婪指數、AAII 散戶情緒調查以及 NAAIM 專業經理人曝險指數。
* **🎨 漸層視覺與極致美學**：採用半透明玻璃擬物化（Glassmorphism）與深色主題設計，VIX 與 CNN 指數大數字會隨著當前數值在進度條中的區間進行**色彩平滑漸層過渡**（如橘紅、黃綠等），讓視覺辨識更快速直觀。
* **🤖 零維護自動排程**：透過 GitHub Actions 每天在美股開盤前 30 分鐘定時自動執行抓取腳本，自動 commit 更新最新資料並部署網頁，無須額外付費伺服器。
* **🛠️ 完善的 Fallback 與手動更新**：當部分來源網站改版或因防火牆封鎖導致自動化抓取失敗時，程式將自動加載上一期快取；同時提供手動 CLI 更新工具（`update_manual.py`），允許隨時手動輸入數值。

## 📁 專案架構與檔案說明

```
你的 GitHub repo
├── fetch_data.py          ← 抓資料、計算分數，寫出 data.json
├── data.json              ← 最新一次抓取結果（由 Actions 自動更新）
├── index.html             ← 前端頁面，讀 data.json 畫出燈號
└── .github/workflows/
    └── update.yml          ← 排程設定：每天美股開盤前自動跑一次
```

流程：GitHub Actions 排程觸發 → 跑 `fetch_data.py` 抓四個來源 → 寫入
`data.json` → 自動 commit 推回 repo → GitHub Pages 上的 `index.html`
讀取同目錄的 `data.json` 顯示燈號。因為前端只讀**同一個 repo** 裡的
靜態檔案，完全不會碰到 CORS 問題。

## 部署步驟

### 1. 建立 GitHub repo

1. 到 GitHub 建立一個新的 public repo（例如 `usa-sentiment`）
2. 把這個資料夾裡的四個東西上傳上去（保留資料夾結構）：
   - `fetch_data.py`
   - `data.json`
   - `index.html`
   - `.github/workflows/update.yml`

最簡單的方式，在這個資料夾內執行：

```bash
git init
git add .
git commit -m "init: USA 美股情緒警示燈"
git branch -M main
git remote add origin https://github.com/<你的帳號>/usa-sentiment.git
git push -u origin main
```

### 2. 開啟 GitHub Pages

1. 到 repo 的 **Settings → Pages**
2. Source 選 **Deploy from a branch**
3. Branch 選 **main**，資料夾選 **/ (root)**
4. 儲存後，幾分鐘內會得到一個網址，例如：
   `https://<你的帳號>.github.io/usa-sentiment/`

這就是你長期使用的網址，可以加到手機主畫面或瀏覽器書籤。

### 3. 確認 Actions 權限

1. 到 **Settings → Actions → General**
2. 在「Workflow permissions」選擇 **Read and write permissions**
   （這樣 Actions 才能自動 commit 更新後的 `data.json` 回 repo）

### 4. 手動測試一次

1. 到 repo 的 **Actions** 分頁
2. 左側選 **Update USA Sentiment Data**
3. 點右側 **Run workflow** 手動觸發一次
4. 跑完後檢查 repo 裡的 `data.json` 是否被更新、`Actions` 紀錄是否成功

之後它會依排程設定的時間（預設週一到週五 UTC 13:00，對應夏令時間
紐約時間早上 9 點開盤前）自動執行，不需要手動操作。

## 調整排程時間

打開 `.github/workflows/update.yml`，修改這一行的 cron 設定：

```yaml
- cron: "0 13 * * 1-5"
```

cron 時間是 **UTC**，注意：
- 紐約夏令時間（約 3 月～11 月）= UTC - 4
- 紐約冬令時間（約 11 月～3 月）= UTC - 5

如果想要更精確跟著夏令/冬令切換，可以設定兩個 cron（一個給夏令、一個
給冬令），或接受每年兩次、相差一小時的誤差（多數情況下不影響判讀）。

## 📊 自訂情緒警示模板與評分規則

本專案採用自訂的恐慌情緒權重模型。每日抓取數據後，系統會檢測四大指標是否觸發對應的恐慌閾值，加總計算出總分（上限為 7 分）並判定警示燈號。

### 1. 評分加分細則

| 市場指標 | 觸發閾值 (恐慌訊號) | 累計得分 | 說明與判讀意義 |
| :--- | :--- | :---: | :--- |
| **VIX 恐慌指數**<br>*(CBOE Volatility Index)* | VIX $> 30$<br>VIX $> 40$ | **+1 分**<br>**+2 分** | 高於 30 代表市場進入恐慌避險狀態；高於 40 則為非理性恐慌，通常對應中長期底部。 |
| **CNN 恐慌與貪婪指數**<br>*(Fear & Greed Index)* | CNN $< 35$<br>CNN $< 25$ | **+1 分**<br>**+2 分** | 指數越低越恐慌。低於 35 為恐慌區，低於 25 進入極度恐慌區。 |
| **NAAIM 專業經理人持倉**<br>*(NAAIM Exposure Index)* | NAAIM $< 55$<br>NAAIM $< 30$ | **+1 分**<br>**+2 分** | 反映專業法人的持倉水位。低於 55% 開始加分；低於 30% 顯示法人的曝險已達極度悲觀。 |
| **AAII 散戶情緒調查**<br>*(AAII Sentiment Survey)* | 看跌 (Bearish) $> 45\%$ | **+1 分** | 散戶的看跌比例若高於 45%，代表散戶市場的情緒過度悲觀。 |

### 2. 燈號判定門檻

系統會加總上述指標的得分，並根據總分直接投射出對應的警示燈號：

* **🔴 紅燈（高度警戒）**：累計總分 **$\ge 3$ 分** —— 代表市場有多個恐慌指標同時亮起，極度恐慌中常伴隨著極佳的逆向投資機會。
* **🟡 黃燈（注意前方）**：累計總分 **$\ge 2$ 分** —— 恐慌情緒開始累積，此時需留意加碼布局機會。
* **🟢 綠燈（市場平靜）**：累計總分 **$< 2$ 分**（即 0 分或 1 分） —— 市場表現平靜，未見明顯的極端恐慌訊號。

所有的評分加權與燈號轉換邏輯均實作於 `fetch_data.py` 與 `index.html` 中，若有調整需求可以直接修改對應函數後 Push 回儲存庫。

## 已知風險與注意事項

這個工具用到的四個資料來源中，只有 **VIX**（Yahoo Finance）是相對
穩定的公開資料介面，其他三個都有各自的限制：

| 來源 | 風險 |
|---|---|
| **VIX** | 較穩定，但 Yahoo 內部 API 並非正式對外承諾的服務，理論上仍可能變動 |
| **CNN Fear & Greed** | 使用非官方資料端點（`production.dataviz.cnn.io`），CNN 改版網站時可能失效，需要重新尋找端點 |
| **NAAIM** | 用 HTML 正規表示式解析頁面數字，網站改版會直接讓解析失敗（`fetch_data.py` 會在 `errors` 欄位標示出來，但不會讓整個流程中斷） |
| **AAII** | 同樣是 HTML 解析，且完整歷史數據是付費會員內容，這裡只能抓首頁公開顯示的最新一週數字；若頁面改用 JS 動態渲染，解析會失敗 |

建議養成習慣：偶爾打開頁面時留意一下 `errors` 區塊（畫面上會以紅色
警示框顯示），如果某個來源連續好幾天抓取失敗，代表對方網站結構變了，
需要回到 `fetch_data.py` 裡對應的 `fetch_xxx()` 函式更新解析邏輯。

## 💻 本地測試與手動數據維護（選用）

### 1. 本地執行測試
如果您想在自己電腦先測試資料抓取腳本是否正常（不透過 GitHub Actions 自動排程）：

```bash
pip install requests
python fetch_data.py
```
成功執行後將在控制台印出最新的 JSON 數據，並覆寫本地的 `data.json`。

### 2. 手動填寫數據與修正 (`update_manual.py`)
如果發生官方網站暫時失效、或因 IP 封鎖導致自動化抓取暫時無法工作，您可以使用我們內建的 CLI 手動更新腳本。這允許您直接輸入最新的指標數值，並由系統重新計算評分與燈號：

```bash
# 基本用法：指定各指標數值 (未設定的指標將沿用原有快取數值)
python update_manual.py --vix 19.50 --cnn 27 --naaim 92.83 --bearish 39.4 --bullish 36.6 --neutral 24.1
```

執行手動更新後，將會自動清除 `data.json` 中的爬蟲錯誤訊息，並更新為您指定的數值與當前時間。將更新後的 `data.json` Commit 並 Push 回 GitHub 後，網頁即可立刻顯示您填寫的正確數據。
