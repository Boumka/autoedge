"""
AutoEdge — langchain_agent.py
Slimme AI-agent met geheugen gebouwd op LangChain + Groq.
Gebruikt de nieuwe LangChain 1.x aanpak zonder AgentExecutor.
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import db
import scoring

load_dotenv()

# ─── MODEL ───────────────────────────────────────────────────────────────────
# Claude als hoofdmodel, Groq als fallback

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

if ANTHROPIC_KEY:
    from langchain_anthropic import ChatAnthropic
    llm = ChatAnthropic(
        api_key=ANTHROPIC_KEY,
        model="claude-haiku-4-5-20251001",
        temperature=0.3,
        max_tokens=2000,
    )
else:
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0.3,
    )

# ─── KENNISBANK DISTRIBUTIE ──────────────────────────────────────────────────

DISTRIBUTIE_INFO = {
    "vw golf 1.6 tdi":          {"type": "riem",     "interval": 90000,  "kost": "€500-700"},
    "vw golf 2.0 tdi":          {"type": "riem",     "interval": 120000, "kost": "€500-700"},
    "vw golf 1.4 tsi":          {"type": "ketting",  "interval": None,   "kost": "nvt"},
    "vw golf 1.2 tsi":          {"type": "ketting",  "interval": None,   "kost": "nvt"},
    "bmw 3 2.0d":               {"type": "ketting",  "interval": None,   "kost": "nvt"},
    "toyota yaris":             {"type": "ketting",  "interval": None,   "kost": "nvt"},
    "opel astra 1.6 cdti":      {"type": "riem",     "interval": 100000, "kost": "€400-600"},
    "opel astra 1.4 turbo":     {"type": "ketting",  "interval": None,   "kost": "nvt"},
    "renault clio 1.5 dci":     {"type": "riem",     "interval": 120000, "kost": "€400-600"},
    "peugeot 208 1.2 puretech": {"type": "ketting",  "interval": None,   "kost": "€800-1200"},
    "peugeot 208 1.6 hdi":      {"type": "riem",     "interval": 120000, "kost": "€400-600"},
    "ford focus 1.6 tdci":      {"type": "riem",     "interval": 100000, "kost": "€500-700"},
    "skoda octavia 2.0 tdi":    {"type": "riem",     "interval": 120000, "kost": "€500-700"},
    "audi a3 2.0 tdi":          {"type": "riem",     "interval": 120000, "kost": "€600-900"},
    "mercedes c 2.2 cdi":       {"type": "ketting",  "interval": None,   "kost": "nvt"},
}

MODEL_INFO = {
    "vw golf": {
        "verbruik": "5.5-7.5L/100km (benzine) | 4.0-5.5L/100km (diesel)",
        "betrouwbaarheid": "Goed",
        "sterktes": ["Tijdloze stijl", "Sterke restwaarde", "Groot dealer-netwerk"],
        "zwaktes": ["DSG-problemen bij vroege modellen", "Dure onderdelen"],
        "beste_bouwjaar": "2017-2020",
    },
    "toyota yaris": {
        "verbruik": "4.0-5.5L/100km | 3.5L/100km (hybride)",
        "betrouwbaarheid": "Uitstekend",
        "sterktes": ["Extreem betrouwbaar", "Lage onderhoudskosten", "Zuinig"],
        "zwaktes": ["Minder sportief", "Kleine kofferruimte"],
        "beste_bouwjaar": "2017-2020",
    },
    "bmw 3": {
        "verbruik": "6.0-9.0L/100km (benzine) | 4.5-6.5L/100km (diesel)",
        "betrouwbaarheid": "Matig — hogere onderhoudskosten",
        "sterktes": ["Rijplezier", "Prestige", "Krachtige motoren"],
        "zwaktes": ["Hoge onderhoudskosten", "Elektronicaproblemen"],
        "beste_bouwjaar": "2015-2018 (F30)",
    },
    "opel astra": {
        "verbruik": "5.0-7.0L/100km (benzine) | 4.0-5.5L/100km (diesel)",
        "betrouwbaarheid": "Goed",
        "sterktes": ["Goede prijs-kwaliteit", "Comfortabel", "Ruim"],
        "zwaktes": ["Dalende restwaarde"],
        "beste_bouwjaar": "2016-2019",
    },
    "renault clio": {
        "verbruik": "4.5-6.5L/100km (benzine) | 3.5-5.0L/100km (diesel)",
        "betrouwbaarheid": "Matig",
        "sterktes": ["Stijlvol", "Zuinig", "Goede uitrusting"],
        "zwaktes": ["Elektronica-problemen", "Roestgevoelig"],
        "beste_bouwjaar": "2019-2022 (Clio V)",
    },
    "peugeot 208": {
        "verbruik": "4.5-6.5L/100km (benzine) | 3.5-5.0L/100km (diesel)",
        "betrouwbaarheid": "Goed bij nieuwere modellen",
        "sterktes": ["Stijlvol design", "Zuinig"],
        "zwaktes": ["1.2 PureTech kettingproblemen bij vroege versies"],
        "beste_bouwjaar": "2019+",
    },
}


# ─── TOOL FUNCTIES ───────────────────────────────────────────────────────────

def zoek_wagens(merk="", model="", max_prijs=0, min_score=0, limit=5):
    query = """
        SELECT l.merk, l.model, l.bouwjaar, l.km, l.prijs,
               l.brandstof, l.transmissie, l.regio,
               s.deal_score, s.marktwaarde, s.prijs_afwijking_pct
        FROM listings l
        JOIN scores s ON s.listing_id = l.id
        WHERE l.actief = TRUE
    """
    params = []
    if merk:
        query += " AND LOWER(l.merk) ILIKE %s"
        params.append(f"%{merk.lower()}%")
    if model:
        query += " AND LOWER(l.model) ILIKE %s"
        params.append(f"%{model.lower()}%")
    if max_prijs > 0:
        query += " AND l.prijs <= %s"
        params.append(max_prijs)
    if min_score > 0:
        query += " AND s.deal_score >= %s"
        params.append(min_score)
    query += " ORDER BY s.deal_score DESC LIMIT %s"
    params.append(limit)

    resultaten = db.fetchall(query, params)
    if not resultaten:
        return "Geen wagens gevonden."

    tekst = f"{len(resultaten)} wagen(s) gevonden:\n\n"
    for w in resultaten:
        tekst += (
            f"🚗 {w['merk']} {w['model']} ({w['bouwjaar']})\n"
            f"   💰 €{float(w['prijs']):,.0f} | Score: {w['deal_score']}/100\n"
            f"   📍 {w['regio']} | {int(w['km']):,} km | {w['brandstof']}\n"
            f"   📊 Marktwaarde: €{float(w['marktwaarde']):,.0f}\n\n"
        )
    return tekst


def analyseer_wagen(merk, model, bouwjaar, km, prijs, beschrijving=""):
    score = scoring.deal_score({
        "merk": merk, "model": model, "bouwjaar": bouwjaar,
        "km": km, "prijs": prijs, "beschrijving": beschrijving, "dagen_online": 0,
    })
    return (
        f"Deal-analyse: {merk} {model} ({bouwjaar})\n"
        f"Score: {score['deal_score']}/100 — {score['verdict']}\n"
        f"Marktwaarde: €{score['marktwaarde']:,.0f}\n"
        f"Afwijking: {score['prijs_afwijking_pct']}%\n"
        f"Signalen: {', '.join(score['risico_vlaggen'])}"
    )


def get_distributie_info(merk, model, motor=""):
    zoekterm = f"{merk} {model} {motor}".lower().strip()
    for sleutel, info in DISTRIBUTIE_INFO.items():
        if any(deel in zoekterm for deel in sleutel.split()):
            if sleutel.split()[0] in zoekterm and sleutel.split()[1] in zoekterm:
                dist_type = info["type"]
                if dist_type == "riem":
                    return (f"⚠️ DISTRIBUTIERIEM — vervangen elke {info['interval']:,} km | "
                            f"Kost: {info['kost']} | Vraag altijd of dit al gedaan is!")
                else:
                    return f"✅ DISTRIBUTIEKETTING — gaat normaal mee voor het leven van de motor"
    return f"Distributie-info voor {merk} {model} niet beschikbaar. Controleer bij de fabrikant."


def get_model_info(merk, model):
    sleutel = f"{merk} {model}".lower()
    for naam, info in MODEL_INFO.items():
        if naam in sleutel:
            return (
                f"Info {merk} {model}:\n"
                f"Verbruik: {info['verbruik']}\n"
                f"Betrouwbaarheid: {info['betrouwbaarheid']}\n"
                f"Beste bouwjaar: {info['beste_bouwjaar']}\n"
                f"Sterktes: {', '.join(info['sterktes'])}\n"
                f"Aandachtspunten: {', '.join(info['zwaktes'])}"
            )
    return f"Geen gedetailleerde info voor {merk} {model}."


def get_markt_stats():
    stats = db.fetchone("""
        SELECT COUNT(*) AS totaal,
               ROUND(AVG(l.prijs)::numeric,0) AS gem_prijs,
               ROUND(AVG(s.deal_score)::numeric,0) AS gem_score,
               MAX(s.deal_score) AS beste_score,
               COUNT(CASE WHEN s.deal_score >= 55 THEN 1 END) AS goede_deals
        FROM listings l JOIN scores s ON s.listing_id = l.id WHERE l.actief = TRUE
    """)
    if not stats:
        return "Geen data."
    return (f"Marktoverzicht: {stats['totaal']} advertenties | "
            f"Gem. prijs: €{float(stats['gem_prijs']):,.0f} | "
            f"Gem. score: {stats['gem_score']}/100 | "
            f"Goede deals: {stats['goede_deals']}")


# ─── AGENT MET GEHEUGEN ──────────────────────────────────────────────────────

SYSTEEM_PROMPT = """Je bent de AutoEdge AI-assistent — een persoonlijke wagenkoper-adviseur voor de Belgische markt.

Je hebt toegang tot deze functies (roep ze aan als JSON in je antwoord):
- zoek_wagens(merk, model, max_prijs, min_score, limit)
- analyseer_wagen(merk, model, bouwjaar, km, prijs, beschrijving)
- get_distributie_info(merk, model, motor)
- get_model_info(merk, model)
- get_markt_stats()

Gedragsregels:
1. Stel vragen als info ontbreekt (budget, gebruik, km/jaar)
2. Geef ALTIJD distributie-info bij een specifiek model
3. Antwoord in het Nederlands
4. Onthoud wat de gebruiker eerder zei
5. Wees concreet en praktisch

Als je een functie wil aanroepen, schrijf dan:
[TOOL: functienaam(parameters)]
Ik voer de functie uit en geef het resultaat terug.
"""


class AutoEdgeAgent:
    """AI-agent met gespreksgeheugen."""

    def __init__(self):
        self.geschiedenis = []
        self.llm = llm

    def _voer_tool_uit(self, tool_call: str) -> str:
        """Voert een tool-aanroep uit op basis van tekst."""
        import re
        match = re.search(r'\[TOOL:\s*(\w+)\((.*?)\)\]', tool_call, re.DOTALL)
        if not match:
            return ""

        naam = match.group(1)
        args_str = match.group(2)

        try:
            # Simpele argument parsing
            args = {}
            for deel in args_str.split(","):
                deel = deel.strip()
                if "=" in deel:
                    k, v = deel.split("=", 1)
                    k = k.strip().strip('"\'')
                    v = v.strip().strip('"\'')
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                    args[k] = v

            if naam == "zoek_wagens":
                return zoek_wagens(**{k: v for k, v in args.items()
                                     if k in ["merk","model","max_prijs","min_score","limit"]})
            elif naam == "analyseer_wagen":
                return analyseer_wagen(**{k: v for k, v in args.items()})
            elif naam == "get_distributie_info":
                return get_distributie_info(**{k: v for k, v in args.items()})
            elif naam == "get_model_info":
                return get_model_info(**{k: v for k, v in args.items()})
            elif naam == "get_markt_stats":
                return get_markt_stats()
            else:
                return f"Onbekende tool: {naam}"
        except Exception as e:
            return f"Fout bij tool {naam}: {e}"

    def chat(self, vraag: str) -> str:
        """Stuurt een vraag naar de agent met volledige gesprekshistoriek."""
        # Bouw berichten op
        berichten = [SystemMessage(content=SYSTEEM_PROMPT)]
        for msg in self.geschiedenis:
            if msg["rol"] == "gebruiker":
                berichten.append(HumanMessage(content=msg["inhoud"]))
            else:
                berichten.append(AIMessage(content=msg["inhoud"]))
        berichten.append(HumanMessage(content=vraag))

        # Eerste AI-respons
        respons = self.llm.invoke(berichten)
        antwoord = respons.content

        # Tool-aanroepen uitvoeren
        import re
        tool_calls = re.findall(r'\[TOOL:.*?\]', antwoord, re.DOTALL)

        if tool_calls:
            tool_resultaten = []
            for tc in tool_calls:
                resultaat = self._voer_tool_uit(tc)
                tool_resultaten.append(resultaat)

            antwoord_zonder_tools = antwoord
            for tc in tool_calls:
                antwoord_zonder_tools = antwoord_zonder_tools.replace(tc, "")

            alle_resultaten = "\n\n".join(tool_resultaten)
            berichten.append(AIMessage(content=antwoord_zonder_tools.strip()))
            berichten.append(HumanMessage(content=(
                f"Hier zijn de resultaten van de database:\n\n{alle_resultaten}\n\n"
                f"Geef nu een volledig antwoord aan de gebruiker op basis van deze data. "
                f"Presenteer de resultaten duidelijk en geef advies."
            )))

            respons2 = self.llm.invoke(berichten)
            antwoord = respons2.content

        # Geschiedenis bijwerken (laatste 10 berichten)
        self.geschiedenis.append({"rol": "gebruiker", "inhoud": vraag})
        self.geschiedenis.append({"rol": "assistent", "inhoud": antwoord})
        if len(self.geschiedenis) > 20:
            self.geschiedenis = self.geschiedenis[-20:]

        return antwoord


def maak_agent_met_geheugen():
    """Maakt een nieuwe AutoEdge agent aan."""
    return AutoEdgeAgent()


def chat(vraag: str, agent) -> str:
    """Compatibiliteitsfunctie voor langchain_chat.py."""
    return agent.chat(vraag)


# ─── TEST ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n── AutoEdge Agent Test ─────────────────────────────")
    agent = AutoEdgeAgent()

    vragen = [
        "Hoi! Wat zijn de beste deals?",
        "Heeft een VW Golf TDI een distributieriem of ketting?",
        "Analyseer: VW Golf 2018, 95.000 km, €14.500",
    ]

    for vraag in vragen:
        print(f"\n👤 {vraag}")
        antwoord = agent.chat(vraag)
        print(f"🤖 {antwoord[:300]}...")

    print("\n────────────────────────────────────────────────────\n")
