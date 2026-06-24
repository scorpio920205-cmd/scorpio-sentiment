# USA 美股情緒警示燈

網頁版市場情緒警示燈號工具，每日自動抓取四個情緒指標並計算警示分數。

## 架構

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

## 自訂情緒警示模板與評分規則

本專案採用自訂的情緒評估模板。每天抓取四大指標後，會根據以下條件計算分數並決定警示燈號：

### 1. 評分加分方式
* **VIX 恐慌指數**：
  * `> 30`：加 **1 分**
  * `> 40`：加 **2 分**
* **CNN 恐慌與貪婪指數**：
  * `< 35`：加 **1 分**
  * `< 25`：加 **2 分**
* **NAAIM 經理人持倉指數**：
  * `< 55`：加 **1 分**
  * `< 30`：加 **2 分**
* **AAII 投資者情緒調查（看跌）**：
  * `看跌 > 45%`：加 **1 分**

*（評分累計上限為 7 分）*

### 2. 燈號判定門檻
根據各指標加總的累計總分，決定警示燈號顏色：
* **🔴 紅燈（高度警戒）**：累計總分 **$\ge$ 3 分**
* **🟡 黃燈（注意前方）**：累計總分 **$\ge$ 2 分**
* **🟢 綠燈（市場平靜）**：累計總分 **< 2 分**（即 0 分或 1 分）

所有評分與門檻邏輯皆實作於 `fetch_data.py` 中，如需調整可以直接修改該檔案中的評分與 `light_status` 函數，再 push 回 GitHub。

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

## 本地測試（選用）

如果想在自己電腦先測試抓取腳本是否正常（不透過 GitHub Actions）：

```bash
pip install requests
python3 fetch_data.py
```

成功的話會印出完整 JSON 結果，並更新本地的 `data.json`。
