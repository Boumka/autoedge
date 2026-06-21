"""
AutoEdge — link_analyse.py
Haalt een specifieke advertentie op van 2dehands.be via een link
en berekent de deal-score. Gebruikt door de AI Advisor agent.
"""

import re
import httpx
import db
import scoring
from scraper import (
    extraheer_km, extraheer_bouwjaar, extraheer_attribuut,
    HEADERS
)

DETAIL_URL = "https://www.2dehands.be/lrp/api/item/{item_id}"


def _extraheer_attribuut_waarde(listing: dict, key: str) -> str | None:
    """
    Zoekt een waarde op in de 'attributes' lijst van de 2dehands search-API
    op basis van de key (bv. 'mileage', 'constructionYear').
    Dit is de meest betrouwbare bron als de search-API deze meegeeft.
    """
    for attr in listing.get("attributes", []):
        if attr.get("key") == key:
            return attr.get("value")
    for attr in listing.get("extendedAttributes", []):
        if attr.get("key") == key:
            return attr.get("value")
    return None


def extraheer_item_id(url: str) -> str | None:
    """Extraheert het item-ID (bv. m2409712220) uit een 2dehands URL."""
    match = re.search(r'm\d{6,12}', url)
    return match.group(0) if match else None


def is_2dehands_link(tekst: str) -> str | None:
    """
    Zoekt naar een 2dehands.be link in een tekst.
    Geeft de volledige URL terug, of None.
    """
    match = re.search(r'https?://(?:www\.)?2dehands\.be/\S+', tekst)
    return match.group(0) if match else None


def haal_advertentie_op(url: str) -> dict | None:
    """
    Haalt de volledige advertentiedata op voor een specifieke 2dehands URL.
    Gebruikt de zoek-API met het item-ID als filter, want de directe
    detail-API vereist soms extra headers.
    """
    item_id = extraheer_item_id(url)
    if not item_id:
        return None

    try:
        # We gebruiken de search API met de itemId als query om de
        # volledige advertentiedata terug te krijgen
        response = httpx.get(
            "https://www.2dehands.be/lrp/api/search",
            params={
                "attributesByKey[]": "Language:all-languages",
                "limit": 1,
                "offset": 0,
                "query": item_id,
            },
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        listings = data.get("listings", [])

        # Zoek de listing met exact dit item_id
        for listing in listings:
            if listing.get("itemId") == item_id:
                return listing

        # Als niet gevonden via search, probeer de pagina direct te lezen
        return _haal_via_pagina(url, item_id)

    except Exception as e:
        print(f"Fout bij ophalen advertentie: {e}")
        return None


def _haal_via_pagina(url: str, item_id: str) -> dict | None:
    """Fallback: leest de advertentiepagina direct en extraheert basisdata."""
    try:
        response = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        response.raise_for_status()
        html = response.text

        # Titel uit de <title> tag
        titel_match = re.search(r'<title>(.*?)</title>', html)
        titel = titel_match.group(1).split('|')[0].strip() if titel_match else ""

        # Prijs zoeken
        prijs_match = re.search(r'"priceCents":(\d+)', html)
        prijs_cents = int(prijs_match.group(1)) if prijs_match else 0

        # Beschrijving uit de ld+json beschrijving (meest volledige tekst)
        json_desc_match = re.search(r'"description":"((?:[^"\\]|\\.)*)"', html)
        beschrijving = ""
        if json_desc_match:
            beschrijving = json_desc_match.group(1).encode().decode('unicode_escape')

        # ── Gestructureerde extractie via de 2dehands attributen-blokken ──
        # 2dehands toont kenmerken als:
        # <div class="CarAttributesMainGroup-label">Bouwjaar</div>
        # <div class="CarAttributesMainGroup-value">2004 </div>
        bouwjaar_struct = None
        bouwjaar_match = re.search(
            r'CarAttributesMainGroup-label">Bouwjaar</div>'
            r'<div class="CarAttributesMainGroup-value">\s*(\d{4})',
            html
        )
        if bouwjaar_match:
            bouwjaar_struct = int(bouwjaar_match.group(1))

        km_struct = None
        km_match = re.search(
            r'CarAttributesMainGroup-label">Kilometerstand</div>'
            r'<div class="CarAttributesMainGroup-value">\s*([\d.,\s]+)',
            html
        )
        if km_match:
            km_ruw = re.sub(r'[^\d]', '', km_match.group(1))
            if km_ruw:
                km_struct = int(km_ruw)

        if not titel or prijs_cents == 0:
            return None

        return {
            "itemId": item_id,
            "title": titel,
            "description": beschrijving,
            "priceInfo": {"priceCents": prijs_cents, "priceType": "FIXED"},
            "location": {"cityName": ""},
            "vipUrl": url.replace("https://www.2dehands.be", ""),
            "imageUrls": [],
            "_bouwjaar_struct": bouwjaar_struct,
            "_km_struct": km_struct,
        }
    except Exception as e:
        print(f"Fout bij pagina-fallback: {e}")
        return None


def analyseer_link(url: str) -> dict:
    """
    Hoofdfunctie — analyseert een 2dehands link end-to-end.
    Geeft een dict terug met succes-status, score, en alle gegevens.
    """
    item_id = extraheer_item_id(url)
    if not item_id:
        return {
            "succes": False,
            "fout": "Geen geldig 2dehands.be item-ID gevonden in deze link.",
        }

    # Controleer of we deze advertentie al hebben
    bestaand = db.fetchone("""
        SELECT l.*, s.deal_score, s.marktwaarde, s.prijs_afwijking_pct,
               s.winst_potentieel, s.risico_vlaggen
        FROM listings l
        LEFT JOIN scores s ON s.listing_id = l.id
        WHERE l.external_id = %s AND l.source = '2dehands'
    """, (item_id,))

    if bestaand and bestaand.get("deal_score"):
        return {
            "succes":  True,
            "uit_cache": True,
            "merk":    bestaand["merk"],
            "model":   bestaand["model"],
            "bouwjaar": bestaand["bouwjaar"],
            "km":      bestaand["km"],
            "prijs":   float(bestaand["prijs"]),
            "deal_score": bestaand["deal_score"],
            "marktwaarde": float(bestaand["marktwaarde"]),
            "prijs_afwijking_pct": float(bestaand["prijs_afwijking_pct"]),
            "winst_potentieel": float(bestaand["winst_potentieel"]),
            "risico_vlaggen": bestaand["risico_vlaggen"],
            "url": bestaand["url"],
        }

    # Nieuwe advertentie ophalen
    raw = haal_advertentie_op(url)
    if not raw:
        return {
            "succes": False,
            "fout": "Kon de advertentie niet ophalen. Mogelijk is de link verlopen of offline.",
        }

    # Data verwerken
    prijs_info = raw.get("priceInfo", {})
    prijs_cents = prijs_info.get("priceCents", 0)
    if prijs_cents <= 0:
        return {
            "succes": False,
            "fout": "Geen geldige prijs gevonden voor deze advertentie.",
        }
    prijs = prijs_cents / 100

    titel = raw.get("title", "")
    beschrijving = raw.get("description", "")
    volledige_tekst = f"{titel}. {beschrijving}"

    # Eerst proberen via de gestructureerde attributen die de 2dehands
    # search-API soms direct meegeeft (constructionYear, mileage keys)
    km = _extraheer_attribuut_waarde(raw, "mileage")
    bouwjaar = _extraheer_attribuut_waarde(raw, "constructionYear")

    # Anders via de pagina-fallback structuur (_km_struct/_bouwjaar_struct)
    if not km:
        km = raw.get("_km_struct")
    if not bouwjaar:
        bouwjaar = raw.get("_bouwjaar_struct")

    # Laatste redmiddel: tekst-gebaseerde extractie uit titel/beschrijving
    if not km:
        km = extraheer_km(raw)
    if not bouwjaar:
        bouwjaar = extraheer_bouwjaar(raw)

    if km:
        km = int(km)
    if bouwjaar:
        bouwjaar = int(bouwjaar)

    if not km or not bouwjaar:
        return {
            "succes": False,
            "fout": "Kon kilometerstand of bouwjaar niet uit de advertentie halen. "
                    "Geef deze gegevens handmatig door zodat ik de wagen kan analyseren.",
            "titel": titel,
            "prijs": prijs,
        }

    # Merk/model uit titel afleiden (simpele heuristiek)
    delen = titel.split()
    merk  = delen[0] if delen else "Onbekend"
    model = " ".join(delen[1:3]) if len(delen) > 1 else "Onbekend"

    regio = raw.get("location", {}).get("cityName", "")
    vip_url = raw.get("vipUrl", "")
    volledige_url = f"https://www.2dehands.be{vip_url}" if vip_url else url

    # Score berekenen
    score = scoring.deal_score({
        "merk":         merk,
        "model":        model,
        "bouwjaar":     bouwjaar,
        "km":           km,
        "prijs":        prijs,
        "beschrijving": volledige_tekst,
        "dagen_online":  0,
    })

    # Opslaan in database
    result = db.fetchone("""
        INSERT INTO listings (
            source, external_id, merk, model, bouwjaar, km, prijs,
            regio, beschrijving, url, online_sinds
        ) VALUES (
            '2dehands', %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
        )
        ON CONFLICT (source, external_id) DO UPDATE SET
            url = EXCLUDED.url
        RETURNING id
    """, (item_id, merk, model, bouwjaar, km, prijs, regio,
          volledige_tekst, volledige_url))

    if result:
        scoring.sla_score_op(str(result["id"]), score)

    return {
        "succes":   True,
        "uit_cache": False,
        "merk":     merk,
        "model":    model,
        "bouwjaar": bouwjaar,
        "km":       km,
        "prijs":    prijs,
        "deal_score": score["deal_score"],
        "verdict":  score["verdict"],
        "marktwaarde": score["marktwaarde"],
        "prijs_afwijking_pct": score["prijs_afwijking_pct"],
        "winst_potentieel": score["winst_potentieel"],
        "risico_vlaggen": score["risico_vlaggen"],
        "url": volledige_url,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"\nAnalyseren: {test_url}\n")
        resultaat = analyseer_link(test_url)
        for k, v in resultaat.items():
            print(f"  {k}: {v}")
    else:
        print("Gebruik: python link_analyse.py <2dehands-url>")
