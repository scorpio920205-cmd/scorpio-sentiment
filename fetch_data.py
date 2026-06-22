#!/usr/bin/env python3
"""
USA 美股情緒警示燈號 - 資料抓取腳本

抓取四個市場情緒指標並依照閾值表計算總分:
  - VIX 恐慌指數          (Yahoo Finance)
  - CNN 恐慌與貪婪指數     (CNN 非官方資料端點)
  - AAII 投資者情緒調查    (AAII 公開頁面)
  - NAAIM 經理人持倉指數   (NAAIM 公開頁面)

輸出 data.json,供前端 index.html 讀取顯示。
"""

import json
import re
import sys
import traceback
from datetime import datetime, timezone

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 15


# ---------------------------------------------------------------------------
# 個別資料來源抓取函式
# 每個函式回傳 (value, raw_info, error) 三元組
# 任何一個來源失敗都不應該讓整個腳本中斷 -> 用 try/except 包起來
# ---------------------------------------------------------------------------

def fetch_vix():
    """從 Yahoo Finance 取得 VIX 最新收盤/即時值。"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        value = meta.get("regularMarketPrice")
        if value is None:
            # fallback: 用最後一個收盤價
            closes = result["indicators"]["quote"][0]["close"]
            value = next(c for c in reversed(closes) if c is not None)
        return float(value), {"source": "yahoo_finance_chart_api"}, None
    except Exception as e:
        return None, None, f"VIX fetch failed: {e}"


def fetch_cnn_fear_greed():
    """從 CNN 非官方資料端點取得 Fear & Greed 指數分數 (0-100)。"""
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        fg = data["fear_and_greed"]
        score = fg["score"]
        rating = fg.get("rating", "")
        return float(score), {
            "rating": rating,
            "previous_close": fg.get("previous_close"),
            "previous_1_week": fg.get("previous_1_week"),
            "previous_1_month": fg.get("previous_1_month"),
            "previous_1_year": fg.get("previous_1_year"),
            "source": "cnn_dataviz_api"
        }, None
    except Exception as e:
        return None, None, f"CNN Fear&Greed fetch failed: {e}"


def fetch_naaim():
    """
    從 NAAIM 公開頁面解析最新一期 NAAIM Exposure Index 數值。
    NAAIM 沒有公開 API，頁面結構若改版需要調整這裡的解析邏輯。
    """
    url = "https://www.naaim.org/programs/naaim-exposure-index/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text

        # NAAIM 頁面上數值通常以類似 "NAAIM Number: 79.30" 或表格形式出現。
        # 這裡用較寬鬆的正規表示式抓「NAAIM Number」附近的數字，
        # 若改版失敗，會在 error 欄位中明確標示，方便之後手動修正。
        m = re.search(r"NAAIM\s*Number[^0-9\-]*(-?\d+\.?\d*)", html, re.IGNORECASE)
        if not m:
            # 備用模式：抓頁面上第一個獨立的浮點數（在表格 cell 內）
            m = re.search(r'class="[^"]*naaim[^"]*"[^>]*>\s*(-?\d+\.?\d*)', html, re.IGNORECASE)
        if not m:
            raise ValueError("無法在頁面中找到 NAAIM Number，網站結構可能已變更")

        value = float(m.group(1))
        return value, {"source": "naaim_org_scrape"}, None
    except Exception as e:
        return None, None, f"NAAIM fetch failed: {e}"


def fetch_aaii():
    """
    從 AAII 公開頁面解析最新一週的看漲/中性/看跌百分比。
    AAII 完整歷史數據為會員付費內容，這裡只抓首頁公開顯示的最新數字。
    """
    url = "https://www.aaii.com/sentimentsurvey"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text

        # AAII 頁面慣常以 "Bullish 36.6%" / "Bearish 39.4%" 之類文字呈現。
        bullish_m = re.search(r"Bullish[^0-9]{0,20}(\d+\.?\d*)\s*%", html, re.IGNORECASE)
        bearish_m = re.search(r"Bearish[^0-9]{0,20}(\d+\.?\d*)\s*%", html, re.IGNORECASE)
        neutral_m = re.search(r"Neutral[^0-9]{0,20}(\d+\.?\d*)\s*%", html, re.IGNORECASE)

        if not bearish_m:
            raise ValueError("無法在頁面中找到 Bearish 百分比，網站結構可能已變更或需要 JS 渲染")

        bearish = float(bearish_m.group(1))
        bullish = float(bullish_m.group(1)) if bullish_m else None
        neutral = float(neutral_m.group(1)) if neutral_m else None

        return bearish, {
            "bullish": bullish,
            "neutral": neutral,
            "bearish": bearish,
            "source": "aaii_org_scrape",
        }, None
    except Exception as e:
        return None, None, f"AAII fetch failed: {e}"


# ---------------------------------------------------------------------------
# 評分邏輯 — 對應截圖中的閾值表
# ---------------------------------------------------------------------------

def score_vix(value):
    if value is None:
        return 0
    if value > 40:
        return 2
    if value > 30:
        return 1
    return 0


def score_cnn(value):
    if value is None:
        return 0
    if value < 25:
        return 2
    if value < 35:
        return 1
    return 0


def score_aaii_bearish(value):
    if value is None:
        return 0
    if value > 45:
        return 1
    return 0


def score_naaim(value):
    if value is None:
        return 0
    if value < 30:
        return 2
    if value < 55:
        return 1
    return 0


def light_status(total_score):
    """依總分決定燈號顏色與文字提示。"""
    if total_score >= 3:
        return {"color": "red", "label": "高度警戒", "desc": "多項恐慌指標同時觸發，留意風險"}
    if total_score >= 2:
        return {"color": "yellow", "label": "注意前方", "desc": "恐慌指標開始累積，留意加碼機會"}
    return {"color": "green", "label": "市場平靜", "desc": "目前未見明顯恐慌訊號"}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    errors = []

    # 讀取舊資料作為抓取失敗時的備份 (fallback)
    prev_data = {}
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            prev_data = json.load(f)
    except Exception:
        pass

    def get_fallback(key, current_val, current_info):
        if current_val is None and prev_data:
            try:
                prev_ind = prev_data["indicators"][key]
                return prev_ind.get("value"), prev_ind.get("info"), True
            except Exception:
                pass
        return current_val, current_info, False

    vix_value, vix_info, vix_err = fetch_vix()
    vix_value, vix_info, vix_is_fallback = get_fallback("vix", vix_value, vix_info)
    if vix_err:
        errors.append(vix_err)

    cnn_value, cnn_info, cnn_err = fetch_cnn_fear_greed()
    cnn_value, cnn_info, cnn_is_fallback = get_fallback("cnn_fear_greed", cnn_value, cnn_info)
    if cnn_err:
        errors.append(cnn_err)

    naaim_value, naaim_info, naaim_err = fetch_naaim()
    naaim_value, naaim_info, naaim_is_fallback = get_fallback("naaim", naaim_value, naaim_info)
    if naaim_err:
        errors.append(naaim_err)

    aaii_value, aaii_info, aaii_err = fetch_aaii()
    aaii_value, aaii_info, aaii_is_fallback = get_fallback("aaii_bearish", aaii_value, aaii_info)
    if aaii_err:
        errors.append(aaii_err)

    s_vix = score_vix(vix_value)
    s_cnn = score_cnn(cnn_value)
    s_aaii = score_aaii_bearish(aaii_value)
    s_naaim = score_naaim(naaim_value)
    total = s_vix + s_cnn + s_aaii + s_naaim

    status = light_status(total)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_score": total,
        "status": status,
        "indicators": {
            "vix": {
                "value": vix_value,
                "score": s_vix,
                "threshold": ">30 +1分 / >40 +2分",
                "info": vix_info,
            },
            "cnn_fear_greed": {
                "value": cnn_value,
                "score": s_cnn,
                "threshold": "<35 +1分 / <25 +2分",
                "info": cnn_info,
            },
            "aaii_bearish": {
                "value": aaii_value,
                "score": s_aaii,
                "threshold": ">45% +1分",
                "info": aaii_info,
            },
            "naaim": {
                "value": naaim_value,
                "score": s_naaim,
                "threshold": "<55 +1分 / <30 +2分",
                "info": naaim_info,
            },
        },
        "errors": errors,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(json.dumps(output, ensure_ascii=False, indent=2))

    # 若四個來源全部失敗才視為嚴重錯誤（讓 GitHub Actions 標記為失敗，方便察覺）
    if len(errors) == 4:
        print("ERROR: 全部資料來源抓取失敗", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
