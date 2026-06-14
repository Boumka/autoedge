"""
AutoEdge — ai_agent.py
AI-agent die in gewone taal praat over de occasiemarkt.
Heeft toegang tot de database en kan advertenties analyseren.
Gebruik: wordt geïmporteerd in app.py als extra pagina.
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv
import db
import scoring

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"

# ─── DATABASE TOOLS ──────────────────────────────────────────────────────────

def zoek_wagens(merk=None, model=None, max_prijs=None, min_score=None, limit=5):
    """Zoekt wagens in de database op basis van criteria."""
    query  = """
        SELECT l.merk, l.model, l.bouwjaar, l.km, l.prijs,
               l.brandstof, l.regio, s.deal_score, s.marktwaarde,
               s.prijs_afwijking_pct, s.winst_potentieel, s.risico_vlaggen
        FROM listings l
        JOIN scores s ON s.listing_id = l.id
        WHERE l.actief = TRUE
    """
    params = []
    if merk:
        query += " AND LOWER(l.merk) = LOWER(%s)"
        params.append(merk)
    if model:
        query += " AND LOWER(l.model) ILIKE %s"
        params.append(f"%{model}%")
    if max_prijs:
        query += " AND l.prijs <= %s"
        params.append(max_prijs)
    if min_score:
        query += " AND s.deal_score >= %s"
        params.append(min_score)
    query += " ORDER BY s.deal_score DESC LIMIT %s"
    params.append(limit)
    return db.fetchall(query, params)


def markt_statistieken():
    """Geeft algemene statistieken over de markt in de database."""
    stats = db.fetchone("""
        SELECT
            COUNT(*)                          AS totaal,
            ROUND(AVG(l.prijs)::numeric, 0)   AS gem_prijs,
            ROUND(AVG(s.deal_score)::numeric, 0) AS gem_score,
            MAX(s.deal_score)                 AS beste_score,
            COUNT(CASE WHEN s.deal_score >= 55 THEN 1 END) AS goede_deals
        FROM listings l
        JOIN scores s ON s.listing_id = l.id
        WHERE l.actief = TRUE
    """)
    return dict(stats) if stats else {}


def analyseer_advertentie(merk, model, bouwjaar, km, prijs, beschrijving=""):
    """Berekent de deal-score voor een gegeven advertentie."""
    return scoring.deal_score({
        "merk":         merk,
        "model":        model,
        "bouwjaar":     bouwjaar,
        "km":           km,
        "prijs":        prijs,
        "beschrijving": beschrijving,
        "dagen_online": 0,
    })


# ─── TOOL DEFINITIES VOOR DE AGENT ───────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "zoek_wagens",
            "description": "Zoekt wagens in de AutoEdge database op basis van merk, model, prijs en minimum deal-score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merk":      {"type": "string",  "description": "Merk van de wagen, bv. VW, BMW, Toyota"},
                    "model":     {"type": "string",  "description": "Model van de wagen, bv. Golf, 3-reeks"},
                    "max_prijs": {"type": "number",  "description": "Maximum vraagprijs in euro"},
                    "min_score": {"type": "integer", "description": "Minimum deal-score (0-100)"},
                    "limit":     {"type": "integer", "description": "Aantal resultaten (standaard 5)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "markt_statistieken",
            "description": "Geeft algemene statistieken over de wagens in de database: gemiddelde prijs, score, aantal goede deals.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyseer_advertentie",
            "description": "Berekent de deal-score voor een specifieke wagen op basis van merk, model, bouwjaar, km en prijs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merk":        {"type": "string",  "description": "Merk van de wagen"},
                    "model":       {"type": "string",  "description": "Model van de wagen"},
                    "bouwjaar":    {"type": "integer", "description": "Bouwjaar van de wagen"},
                    "km":          {"type": "integer", "description": "Kilometerstand"},
                    "prijs":       {"type": "number",  "description": "Vraagprijs in euro"},
                    "beschrijving":{"type": "string",  "description": "Beschrijving van de advertentie"},
                },
                "required": ["merk", "model", "bouwjaar", "km", "prijs"],
            },
        },
    },
]

# ─── TOOL UITVOEREN ──────────────────────────────────────────────────────────

def voer_tool_uit(naam: str, argumenten: dict) -> str:
    """Voert een tool uit en geeft het resultaat terug als string."""
    try:
        if naam == "zoek_wagens":
            resultaten = zoek_wagens(**argumenten)
            if not resultaten:
                return "Geen wagens gevonden met deze criteria."
            tekst = f"{len(resultaten)} wagen(s) gevonden:\n\n"
            for w in resultaten:
                tekst += (
                    f"• {w['merk']} {w['model']} ({w['bouwjaar']}) — "
                    f"€{float(w['prijs']):,.0f} — Score: {w['deal_score']}/100\n"
                    f"  Marktwaarde: €{float(w['marktwaarde']):,.0f} | "
                    f"Km: {int(w['km']):,} | Regio: {w['regio']}\n"
                )
            return tekst

        elif naam == "markt_statistieken":
            s = markt_statistieken()
            if not s:
                return "Geen data beschikbaar."
            return (
                f"Database statistieken:\n"
                f"• Totaal advertenties: {s['totaal']}\n"
                f"• Gemiddelde prijs: €{float(s['gem_prijs']):,.0f}\n"
                f"• Gemiddelde deal-score: {s['gem_score']}/100\n"
                f"• Beste score: {s['beste_score']}/100\n"
                f"• Goede deals (score ≥ 55): {s['goede_deals']}\n"
            )

        elif naam == "analyseer_advertentie":
            score = analyseer_advertentie(**argumenten)
            return (
                f"Deal-analyse:\n"
                f"• Score: {score['deal_score']}/100 — {score['verdict']}\n"
                f"• Marktwaarde: €{score['marktwaarde']:,.0f}\n"
                f"• Afwijking: {score['prijs_afwijking_pct']}%\n"
                f"• Winstpotentieel: €{score['winst_potentieel']:,.0f}\n"
                f"• Signalen: {', '.join(score['risico_vlaggen'])}\n"
            )
        else:
            return f"Onbekende tool: {naam}"
    except Exception as e:
        return f"Fout bij uitvoeren van {naam}: {e}"


# ─── AGENT LOOP ──────────────────────────────────────────────────────────────

SYSTEEM_PROMPT = """Je bent de AutoEdge AI-assistent — een expert in de Belgische tweedehandswagenmarkt.

Je helpt gebruikers om:
- Goede deals te vinden in de database
- Specifieke wagens te analyseren op prijs en waarde
- Marktinzichten te geven over prijzen en trends
- Risico's te identificeren bij bepaalde advertenties

Je hebt toegang tot tools om de database te doorzoeken en advertenties te analyseren.
Antwoord altijd in het Nederlands. Wees concreet en praktisch.
Als iemand een wagen beschrijft, gebruik dan de analyseer_advertentie tool.
Als iemand zoekt naar een bepaald type wagen, gebruik dan zoek_wagens.
"""


def chat(berichten: list) -> tuple[str, list]:
    """
    Stuurt een conversatie naar de AI-agent en geeft het antwoord terug.
    Voert automatisch tools uit als de agent dat vraagt.
    
    Returns: (antwoord_tekst, bijgewerkte_berichten)
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEEM_PROMPT}] + berichten,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=1500,
    )

    bericht = response.choices[0].message

    # Geen tool-aanroepen — gewoon antwoord teruggeven
    if not bericht.tool_calls:
        antwoord = bericht.content
        berichten.append({"role": "assistant", "content": antwoord})
        return antwoord, berichten

    # Tool-aanroepen uitvoeren
    berichten.append({
        "role": "assistant",
        "content": bericht.content or "",
        "tool_calls": [
            {
                "id":       tc.id,
                "type":     "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments}
            }
            for tc in bericht.tool_calls
        ]
    })

    for tool_call in bericht.tool_calls:
        naam       = tool_call.function.name
        argumenten = json.loads(tool_call.function.arguments)
        resultaat  = voer_tool_uit(naam, argumenten)

        berichten.append({
            "role":         "tool",
            "tool_call_id": tool_call.id,
            "content":      resultaat,
        })

    # Tweede call met tool-resultaten
    response2 = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEEM_PROMPT}] + berichten,
        max_tokens=1500,
    )

    antwoord = response2.choices[0].message.content
    berichten.append({"role": "assistant", "content": antwoord})
    return antwoord, berichten


# ─── SNELLE TEST ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n── AutoEdge AI Agent Test ──────────────────────────")
    berichten = []

    vragen = [
        "Wat zijn de beste deals in de database?",
        "Analyseer deze wagen: VW Golf 2018, 95.000 km, €14.500",
        "Hoeveel goede deals zijn er momenteel?",
    ]

    for vraag in vragen:
        print(f"\n👤 {vraag}")
        antwoord, berichten = chat(berichten + [{"role": "user", "content": vraag}])
        berichten = berichten
        print(f"🤖 {antwoord}")

    print("\n───────────────────────────────────────────────────\n")
