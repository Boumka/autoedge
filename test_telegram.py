import httpx
import os
from dotenv import load_dotenv

load_dotenv()

token   = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
    "chat_id":    chat_id,
    "text":       "🚗 *AutoEdge* — Testbericht\n\nJe alerts werken correct!",
    "parse_mode": "Markdown",
})
print(r.json())