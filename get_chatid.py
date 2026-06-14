import httpx
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_TOKEN")
r = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates")
print(r.json())