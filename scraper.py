"""
AutoEdge — scraper.py
Haalt advertenties op van 2dehands.be via hun interne API.
Slaat nieuwe listings op in de database en berekent automatisch de deal-score.

Gebruik:
  python scraper.py                    # standaard zoekopdrachten
  python scraper.py --query "BMW 3"    # specifieke zoekopdracht
  python scraper.py --limit 50         # meer resultaten
"""

import httpx
import time
import argparse
import re
from datetime import datetime, timezone
import db
import scoring

# ─── INSTELLINGEN ────────────────────────────────────────────────────────────

BASE_URL = "https://www.2dehands.be/lrp/api/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept":     "application/json",
    "Referer":    "https://www.2dehands.be/",
}

# Standaard zoekopdrachten — pas aan naar wens
STANDAARD_ZOEKOPDRACHTEN = [
    {"query": "VW Golf",      "limit": 30, "categorie": 91},
    {"query": "BMW 3",        "limit": 30, "categorie": 91},
    {"query": "Toyota Yaris", "limit": 30, "categorie": 91},
    {"query": "Opel Astra",   "limit": 30, "categorie": 91},
    {"query": "Renault Clio", "limit": 30, "categorie": 91},
    {"query": "camionette",   "limit": 30, "categorie": 93},
    {"query": "moto",         "limit": 30, "categorie": 95},
    {"query": "Ford Transit",      "limit": 30, "categorie": 93},
    {"query": "Volkswagen Crafter", "limit": 30, "categorie": 93},
    {"query": "Mercedes Sprinter", "limit": 30, "categorie": 93},
    {"query": "Renault Master",    "limit": 30, "categorie": 93},
    {"query": "Peugeot Boxer",     "limit": 30, "categorie": 93},
    {"query": "Iveco Daily",       "limit": 30, "categorie": 93},
    {"query": "Honda CBR",         "limit": 30, "categorie": 95},
    {"query": "Yamaha MT",         "limit": 30, "categorie": 95},
    {"query": "BMW GS",            "limit": 30, "categorie": 95},
]


# Categorie 91 = Auto's op 2dehands.be
CATEGORIE_AUTO = 91  # Personenwagens (standaard)

ALLE_CATEGORIEEN = {
    91:  "Personenwagens",
    93:  "Camionettes",
    94:  "Vrachtwagens", 
    95:  "Motorfietsen",
    97:  "Caravans",
    98:  "Boten",
}


# ─── API AANROEPEN ───────────────────────────────────────────────────────────

def zoek_advertenties(query: str, limit: int = 30, offset: int = 0, categorie: int = 91) -> list:
    """Haalt advertenties op van 2dehands.be voor een zoekopdracht."""
    params = {
        "attributesByKey[]":      "Language:all-languages",
        "l1CategoryId":           categorie,
        "limit":                  limit,
        "offset":                 offset,
        "query":                  query,
        "searchInTitleAndDescription": "true",
        "viewOptions":            "list-view",
    }

    try:
        response = httpx.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("listings", [])
    except httpx.TimeoutException:
        print(f"  ⚠️  Timeout voor query '{query}'")
        return []
    except Exception as e:
        print(f"  ⚠️  Fout bij ophalen '{query}': {e}")
        return []


# ─── DATA VERWERKEN ──────────────────────────────────────────────────────────

def extraheer_attribuut(listing: dict, key: str) -> str | None:
    """Haalt een attribuut op uit de attributes lijst."""
    for attr in listing.get("attributes", []):
        if attr.get("key") == key:
            return attr.get("value")
    for attr in listing.get("extendedAttributes", []):
        if attr.get("key") == key:
            return attr.get("value")
    return None


def extraheer_km_uit_tekst(tekst: str) -> int | None:
    """Extraheert km-stand uit een tekst via regex."""
    patronen = [
        r'(\d{1,3}[\.\s]?\d{3})\s*km',
        r'(\d{4,6})\s*km',
    ]
    for patroon in patronen:
        match = re.search(patroon, tekst, re.IGNORECASE)
        if match:
            km_str = match.group(1).replace(".", "").replace(" ", "")
            km = int(km_str)
            if 1000 < km < 500000:
                return km
    return None


def extraheer_km(listing: dict) -> int | None:
    """
    Extraheert de kilometerstand slim:
    1. Eerst uit de beschrijving (meest betrouwbaar)
    2. Dan uit de titel
    3. Vergelijkt beide — kiest de meest realistische waarde
    """
    titel       = listing.get("title", "")
    beschrijving = listing.get("description", "")

    km_beschrijving = extraheer_km_uit_tekst(beschrijving)
    km_titel        = extraheer_km_uit_tekst(titel)

    # Als beide beschikbaar: kies de waarde uit de beschrijving
    # want die bevat vaak de correcte info
    if km_beschrijving and km_titel:
        # Als ze sterk verschillen (>50%), gebruik beschrijving
        if km_titel > 0 and abs(km_beschrijving - km_titel) / km_titel > 0.5:
            return km_beschrijving
        return km_beschrijving

    return km_beschrijving or km_titel


def extraheer_bouwjaar(listing: dict) -> int | None:
    """Extraheert het bouwjaar uit de titel of beschrijving."""
    tekst = f"{listing.get('title', '')} {listing.get('description', '')}"

    match = re.search(r'\b(200[0-9]|201[0-9]|202[0-5])\b', tekst)
    if match:
        return int(match.group(1))
    return None


def extraheer_merk_model(listing: dict, query: str) -> tuple[str, str]:
    """Extraheert merk en model uit de listing of zoekopdracht."""
    # Probeer uit attributen
    model = extraheer_attribuut(listing, "model")

    # Merk uit zoekopdracht halen
    query_delen = query.strip().split()
    if len(query_delen) >= 2:
        merk  = query_delen[0]
        model = model or " ".join(query_delen[1:])
    elif len(query_delen) == 1:
        merk  = query_delen[0]
        model = model or ""
    else:
        merk  = "Onbekend"
        model = model or "Onbekend"

    return merk, model


def verwerk_listing(listing: dict, query: str) -> dict | None:
    """Verwerkt een ruwe API-listing naar een gestructureerd dict."""
    try:
        # Prijs (API geeft prijs in cents)
        prijs_info = listing.get("priceInfo", {})
        prijs_cents = prijs_info.get("priceCents", 0)
        prijs_type  = prijs_info.get("priceType", "")

        # Sla biedingen en gratis advertenties over
        if prijs_type in ("FREE", "SEE_DESCRIPTION") or prijs_cents <= 0:
            return None

        prijs = prijs_cents / 100

        # Filter onrealistische prijzen
        if prijs < 500 or prijs > 150000:
            return None

        # Basisvelden
        item_id     = listing.get("itemId", "")
        titel       = listing.get("title", "")
        beschrijving = listing.get("description", "")
        regio       = listing.get("location", {}).get("cityName", "")

        # Merk en model
        merk, model = extraheer_merk_model(listing, query)

        # Km en bouwjaar uit tekst
        km       = extraheer_km(listing)
        bouwjaar = extraheer_bouwjaar(listing)

        # Sla over als essentiële data ontbreekt
        if not km or not bouwjaar:
            return None

        # Foto's
        foto_urls = listing.get("imageUrls", [])
        foto_urls = [f"https:{url}" if url.startswith("//") else url
                     for url in foto_urls[:5]]

        # URL
        vip_url = listing.get("vipUrl", "")
        url = f"https://www.2dehands.be{vip_url}" if vip_url else f"https://www.2dehands.be/v/{item_id}"

        return {
            "external_id":  item_id,
            "merk":         merk,
            "model":        model,
            "bouwjaar":     bouwjaar,
            "km":           km,
            "prijs":        prijs,
            "brandstof":    None,
            "transmissie":  None,
            "regio":        regio,
            "beschrijving": f"{titel}. {beschrijving}".strip(),
            "url":          url,
            "foto_urls":    foto_urls,
        }

    except Exception as e:
        print(f"  ⚠️  Fout bij verwerken listing: {e}")
        return None


# ─── OPSLAAN IN DATABASE ─────────────────────────────────────────────────────

def sla_listing_op(data: dict) -> str | None:
    """
    Slaat een listing op in de database.
    Geeft de listing ID terug, of None als het al bestond.
    """
    result = db.fetchone("""
        INSERT INTO listings (
            source, external_id, merk, model, bouwjaar, km, prijs,
            brandstof, transmissie, regio, beschrijving, url, foto_urls,
            online_sinds
        ) VALUES (
            '2dehands', %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            NOW()
        )
        ON CONFLICT (source, external_id) DO NOTHING
        RETURNING id
    """, (
        data["external_id"],
        data["merk"], data["model"], data["bouwjaar"],
        data["km"], data["prijs"],
        data["brandstof"], data["transmissie"],
        data["regio"], data["beschrijving"],
        data["url"], data["foto_urls"],
    ))

    return str(result["id"]) if result else None


# ─── HOOFDFUNCTIE ────────────────────────────────────────────────────────────

def run_scraper(zoekopdrachten: list = None, verbose: bool = True):
    """
    Voert de scraper uit voor een lijst van zoekopdrachten.
    Slaat nieuwe listings op en berekent automatisch de deal-score.
    """
    if not zoekopdrachten:
        zoekopdrachten = STANDAARD_ZOEKOPDRACHTEN

    totaal_nieuw   = 0
    totaal_gezien  = 0

    print("\n── AutoEdge Scraper ────────────────────────────────")
    print(f"  {len(zoekopdrachten)} zoekopdracht(en) — start...\n")

    for opdracht in zoekopdrachten:
        query = opdracht["query"]
        limit = opdracht.get("limit", 30)

        print(f"  🔍 '{query}' (max {limit} resultaten)")

        listings = zoek_advertenties(query, limit=limit, categorie=opdracht.get("categorie", 91))
        nieuw = 0

        for raw in listings:
            totaal_gezien += 1
            data = verwerk_listing(raw, query)

            if not data:
                continue

            # Opslaan in database
            listing_id = sla_listing_op(data)

            if not listing_id:
                continue  # Al aanwezig

            # Score berekenen
            score = scoring.deal_score({
                "merk":         data["merk"],
                "model":        data["model"],
                "bouwjaar":     data["bouwjaar"],
                "km":           data["km"],
                "prijs":        data["prijs"],
                "beschrijving": data["beschrijving"],
                "dagen_online": 0,
            })

            # Score opslaan
            scoring.sla_score_op(listing_id, score)

            nieuw          += 1
            totaal_nieuw   += 1

            if verbose:
                print(f"    ✓ {data['merk']:8} {data['model']:10} "
                      f"({data['bouwjaar']}) "
                      f"€{data['prijs']:>8,.0f}  "
                      f"{data['km']:>7,} km  "
                      f"Score: {score['deal_score']:>3}/100  "
                      f"{score['verdict']}")

        print(f"  → {nieuw} nieuwe advertenties opgeslagen\n")

        # Kleine pauze tussen zoekopdrachten
        time.sleep(2)

    print(f"── Klaar ───────────────────────────────────────────")
    print(f"  Gezien:    {totaal_gezien} advertenties")
    print(f"  Nieuw:     {totaal_nieuw} opgeslagen")
    print(f"  Tijd:      {datetime.now().strftime('%H:%M:%S')}")
    print("────────────────────────────────────────────────────\n")

    return totaal_nieuw


# ─── COMMAND LINE ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoEdge 2dehands scraper")
    parser.add_argument("--query", type=str, help="Specifieke zoekopdracht")
    parser.add_argument("--limit", type=int, default=30, help="Max resultaten")
    args = parser.parse_args()

    if args.query:
        run_scraper([{"query": args.query, "limit": args.limit}])
    else:
        run_scraper()
