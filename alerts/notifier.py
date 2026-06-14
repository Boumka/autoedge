"""
AutoEdge — alerts/notifier.py
Verstuurt notificaties via Telegram en e-mail (SendGrid).
"""

import os
import asyncio
import httpx
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
SENDGRID_KEY     = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM    = os.getenv("SENDGRID_FROM_EMAIL", "alerts@autoedge.be")


# ─── BERICHT OPBOUWEN ────────────────────────────────────────────────────────

def bouw_bericht(listing: dict, score: dict) -> str:
    """Bouwt de tekst op die verstuurd wordt via Telegram en e-mail."""
    vlaggen = "\n".join(f"  {v}" for v in score["risico_vlaggen"]) or "  Geen"
    afwijking = score["prijs_afwijking_pct"]
    teken = "▼" if afwijking >= 0 else "▲"

    return f"""
🚗 *AutoEdge Alert* — Score {score['deal_score']}/100 — {score['verdict']}

*{listing['merk']} {listing['model']}* ({listing['bouwjaar']})
Prijs:        €{float(listing['prijs']):,.0f}
Marktwaarde:  €{score['marktwaarde']:,.0f}
Verschil:     {teken} {abs(afwijking):.1f}%
Km-stand:     {int(listing['km']):,} km
Regio:        {listing['regio']}

💰 Winstpotentieel: ~€{score['winst_potentieel']:,.0f}

🚩 Signalen:
{vlaggen}

🔗 {listing['url'] or 'Geen link beschikbaar'}
""".strip()


def bouw_html_email(listing: dict, score: dict, alert_naam: str) -> str:
    """Bouwt een eenvoudige HTML e-mail op."""
    tekst = bouw_bericht(listing, score)
    tekst_html = tekst.replace("\n", "<br>").replace("*", "")

    return f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #534AB7; padding: 20px; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🚗 AutoEdge</h1>
        <p style="color: #CECBF6; margin: 4px 0 0;">Alert: {alert_naam}</p>
      </div>
      <div style="background: #f9f9f9; padding: 24px; border-radius: 0 0 8px 8px; border: 1px solid #eee;">
        <p style="font-size: 15px; line-height: 1.7; color: #333;">{tekst_html}</p>
        <div style="margin-top: 24px; text-align: center;">
          <a href="{listing['url'] or '#'}"
             style="background: #534AB7; color: white; padding: 12px 28px;
                    border-radius: 6px; text-decoration: none; font-weight: bold;">
            Bekijk advertentie →
          </a>
        </div>
        <p style="margin-top: 24px; font-size: 12px; color: #999; text-align: center;">
          AutoEdge — TradingView voor Belgische occasiewagens
        </p>
      </div>
    </body></html>
    """


# ─── TELEGRAM ────────────────────────────────────────────────────────────────

async def stuur_telegram(chat_id: str, tekst: str):
    """Verstuurt een bericht via Telegram Bot API."""
    if not TELEGRAM_TOKEN:
        print("  ⚠️  TELEGRAM_TOKEN niet ingesteld in .env")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "chat_id":    chat_id,
            "text":       tekst,
            "parse_mode": "Markdown",
        })
        if response.status_code == 200:
            print(f"  ✓ Telegram verstuurd naar {chat_id}")
        else:
            print(f"  ✗ Telegram fout: {response.text}")


# ─── E-MAIL ──────────────────────────────────────────────────────────────────

async def stuur_email(naar: str, alert_naam: str, listing: dict, score: dict):
    """Verstuurt een e-mail via SendGrid."""
    if not SENDGRID_KEY:
        print("  ⚠️  SENDGRID_API_KEY niet ingesteld in .env")
        return

    bericht = Mail(
        from_email=SENDGRID_FROM,
        to_emails=naar,
        subject=f"AutoEdge alert: {alert_naam} — Score {score['deal_score']}/100",
        plain_text_content=bouw_bericht(listing, score),
        html_content=bouw_html_email(listing, score, alert_naam),
    )

    try:
        sg = SendGridAPIClient(SENDGRID_KEY)
        sg.send(bericht)
        print(f"  ✓ E-mail verstuurd naar {naar}")
    except Exception as e:
        print(f"  ✗ E-mail fout: {e}")


# ─── HOOFDFUNCTIE ────────────────────────────────────────────────────────────

async def stuur_notificatie(alert: dict, listing: dict, score: dict):
    """
    Verstuurt notificatie via het juiste kanaal (telegram, email, of beide).
    """
    taken = []
    tekst = bouw_bericht(listing, score)
    kanaal = alert.get("kanaal", "telegram")

    if kanaal in ("telegram", "beide") and alert.get("telegram_chat_id"):
        taken.append(stuur_telegram(alert["telegram_chat_id"], tekst))

    if kanaal in ("email", "beide") and alert.get("email"):
        taken.append(stuur_email(
            alert["email"], alert.get("naam", "Zoekopdracht"), listing, score
        ))

    if taken:
        await asyncio.gather(*taken)
    else:
        print(f"  ⚠️  Geen geldig kanaal of contactgegevens voor alert {alert.get('naam')}")
