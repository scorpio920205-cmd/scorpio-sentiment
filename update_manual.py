import json
import argparse
from datetime import datetime, timezone
from fetch_data import score_vix, score_cnn, score_aaii_bearish, score_naaim, light_status

def main():
    parser = argparse.ArgumentParser(description="手動更新美股情緒警示燈指標數值")
    parser.add_argument("--vix", type=float, help="VIX 恐慌指數")
    parser.add_argument("--cnn", type=float, help="CNN 恐慌與貪婪分數 (0-100)")
    parser.add_argument("--naaim", type=float, help="NAAIM 經理人持倉分數 (0-100)")
    parser.add_argument("--bullish", type=float, help="AAII 看漲百分比 (0-100)")
    parser.add_argument("--neutral", type=float, help="AAII 中性百分比 (0-100)")
    parser.add_argument("--bearish", type=float, help="AAII 看跌百分比 (0-100)")
    args = parser.parse_args()

    # 讀取現有資料
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {
            "updated_at": "",
            "total_score": 0,
            "status": {},
            "indicators": {
                "vix": {"value": None, "score": 0, "threshold": ">30 +1分 / >40 +2分", "info": {}},
                "cnn_fear_greed": {"value": None, "score": 0, "threshold": "<35 +1分 / <25 +2分", "info": {}},
                "aaii_bearish": {"value": None, "score": 0, "threshold": ">45% +1分", "info": {}},
                "naaim": {"value": None, "score": 0, "threshold": "<55 +1分 / <30 +2分", "info": {}}
            },
            "errors": []
        }

    # 更新 VIX
    if args.vix is not None:
        data["indicators"]["vix"]["value"] = args.vix
        data["indicators"]["vix"]["info"] = {"source": "manual_update"}

    # 更新 CNN
    if args.cnn is not None:
        data["indicators"]["cnn_fear_greed"]["value"] = args.cnn
        rating = "neutral"
        if args.cnn < 25: rating = "extreme fear"
        elif args.cnn < 45: rating = "fear"
        elif args.cnn < 55: rating = "neutral"
        elif args.cnn < 75: rating = "greed"
        else: rating = "extreme greed"
        data["indicators"]["cnn_fear_greed"]["info"] = {
            "rating": rating,
            "source": "manual_update"
        }

    # 更新 NAAIM
    if args.naaim is not None:
        data["indicators"]["naaim"]["value"] = args.naaim
        data["indicators"]["naaim"]["info"] = {"source": "manual_update"}

    # 更新 AAII
    if args.bearish is not None or args.bullish is not None or args.neutral is not None:
        old_info = data["indicators"]["aaii_bearish"].get("info") or {}
        bull = args.bullish if args.bullish is not None else old_info.get("bullish", 0.0)
        neu = args.neutral if args.neutral is not None else old_info.get("neutral", 0.0)
        bear = args.bearish if args.bearish is not None else old_info.get("bearish", 0.0)
        
        data["indicators"]["aaii_bearish"]["value"] = bear
        data["indicators"]["aaii_bearish"]["info"] = {
            "bullish": bull,
            "neutral": neu,
            "bearish": bear,
            "source": "manual_update"
        }

    # 重新計算分數與燈號
    v_vix = data["indicators"]["vix"]["value"]
    v_cnn = data["indicators"]["cnn_fear_greed"]["value"]
    v_aaii = data["indicators"]["aaii_bearish"]["value"]
    v_naaim = data["indicators"]["naaim"]["value"]

    s_vix = score_vix(v_vix)
    s_cnn = score_cnn(v_cnn)
    s_aaii = score_aaii_bearish(v_aaii)
    s_naaim = score_naaim(v_naaim)

    data["indicators"]["vix"]["score"] = s_vix
    data["indicators"]["cnn_fear_greed"]["score"] = s_cnn
    data["indicators"]["aaii_bearish"]["score"] = s_aaii
    data["indicators"]["naaim"]["score"] = s_naaim

    total = s_vix + s_cnn + s_aaii + s_naaim
    data["total_score"] = total
    data["status"] = light_status(total)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["errors"] = []

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("成功手動更新 data.json！")
    print(f"目前總分: {total} ({data['status']['label']}) - {data['status']['desc']}")

if __name__ == "__main__":
    main()
