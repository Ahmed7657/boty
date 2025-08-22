import json
import os

SIGNALS_FILE = "live_signals.json"

def load_signals():
    try:
        with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"❌ فشل في تحميل التوصيات: {e}")
        return []

def save_signals(signals):
    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(signals, f, ensure_ascii=False, indent=2)