import requests
import json
import os
from datetime import datetime, timezone, timedelta

# 環境變數
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

# 監控的交易對
MONITORS = [
    {"exchange": "binance", "symbol": "RIVERUSDT", "name": "RIVER"},
    {"exchange": "okx", "symbol": "RIVER-USDT-SWAP", "name": "RIVER"},
]

UTC8 = timezone(timedelta(hours=8))
STATE_FILE = "state.json"


def get_binance_recent_funding(symbol, limit=5):
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    try:
        resp = requests.get(url, params={"symbol": symbol, "limit": limit}, timeout=10)
        data = resp.json()
        if isinstance(data, list) and len(data) >= 2:
            return data
    except Exception as e:
        print(f"[Binance] Error: {e}")
    return None


def get_okx_recent_funding(inst_id, limit=5):
    url = "https://www.okx.com/api/v5/public/funding-rate-history"
    try:
        resp = requests.get(url, params={"instId": inst_id, "limit": limit}, timeout=10)
        result = resp.json()
        if result.get("code") == "0" and result.get("data"):
            return result["data"]
    except Exception as e:
        print(f"[OKX] Error: {e}")
    return None


def calculate_interval(data, exchange):
    if not data or len(data) < 2:
        return None, None
    
    if exchange == "binance":
        latest = data[-1]
        prev = data[-2]
        ts_latest = int(latest["fundingTime"])
        ts_prev = int(prev["fundingTime"])
        price = float(latest.get("markPrice", 0))
    else:
        latest = data[0]
        prev = data[1]
        ts_latest = int(latest["fundingTime"])
        ts_prev = int(prev["fundingTime"])
        price = 0
    
    interval_hours = round((ts_latest - ts_prev) / (1000 * 3600), 1)
    return interval_hours, price


def classify_interval(hours):
    if hours is None:
        return None
    if hours <= 1.5:
        return "1h"
    elif hours <= 5:
        return "4h"
    else:
        return "8h"


def send_telegram(message):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print(f"[TG not configured] {message}")
        return False
    
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        result = resp.json()
        if result.get("ok"):
            print("[TG] Sent successfully")
        else:
            print(f"[TG] Failed: {result}")
        return result.get("ok", False)
    except Exception as e:
        print(f"[TG Error] {e}")
        return False


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    now = datetime.now(UTC8)
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Starting monitor...")
    
    state = load_state()
    alerts = []
    
    for monitor in MONITORS:
        exchange = monitor["exchange"]
        symbol = monitor["symbol"]
        name = monitor["name"]
        key = f"{exchange}_{symbol}"
        
        if exchange == "binance":
            data = get_binance_recent_funding(symbol)
        else:
            data = get_okx_recent_funding(symbol)
        
        if not data:
            continue
        
        interval_hours, price = calculate_interval(data, exchange)
        interval_mode = classify_interval(interval_hours)
        
        if interval_mode is None:
            continue
        
        prev_mode = state.get(key, {}).get("mode")
        
        print(f"  [{exchange.upper()}] {name}: {interval_hours}h ({interval_mode})", end="")
        
        if prev_mode and prev_mode != interval_mode:
            change_msg = f"⚡ <b>{exchange.upper()} {name}</b>\n"
            change_msg += f"結算間隔變化: <b>{prev_mode} → {interval_mode}</b>\n"
            change_msg += f"時間: {now.strftime('%Y-%m-%d %H:%M')} (UTC+8)"
            if price:
                change_msg += f"\n價格: ${price:.2f}"
            
            alerts.append(change_msg)
            print(f" ⚡ CHANGED!")
        else:
            print()
        
        state[key] = {
            "mode": interval_mode,
            "interval_hours": interval_hours,
            "updated": now.isoformat()
        }
    
    save_state(state)
    
    for alert in alerts:
        print(f"\nSending alert:\n{alert}\n")
        send_telegram(alert)
    
    if not alerts:
        print("No changes")


if __name__ == "__main__":
    main()
