"""
AutoEdge — testdata.py
Vult de database met 20 nep-advertenties voor testdoeleinden.
Voer uit met: python testdata.py
"""

import random
import db
import scoring

# ─── NEP-ADVERTENTIES ────────────────────────────────────────────────────────

ADVERTENTIES = [
    {
        "merk": "VW", "model": "Golf", "bouwjaar": 2017, "km": 88000,
        "prijs": 13900, "brandstof": "benzine", "transmissie": "manueel",
        "regio": "Gent",
        "beschrijving": "Garagewagen, volledig onderhouden, geen schade, 1 eigenaar. Carpass aanwezig.",
        "dagen_online": 3,
    },
    {
        "merk": "BMW", "model": "3", "bouwjaar": 2018, "km": 110000,
        "prijs": 19500, "brandstof": "diesel", "transmissie": "automaat",
        "regio": "Antwerpen",
        "beschrijving": "Recent groot onderhoud, nieuwe banden, dealer onderhouden.",
        "dagen_online": 7,
    },
    {
        "merk": "Opel", "model": "Astra", "bouwjaar": 2016, "km": 145000,
        "prijs": 7500, "brandstof": "diesel", "transmissie": "manueel",
        "regio": "Luik",
        "beschrijving": "Kleine schade aan bumper, verder in goede staat.",
        "dagen_online": 45,
    },
    {
        "merk": "Toyota", "model": "Yaris", "bouwjaar": 2019, "km": 62000,
        "prijs": 14200, "brandstof": "hybride", "transmissie": "automaat",
        "regio": "Brussel",
        "beschrijving": "1 eigenaar, volledig onderhouden bij Toyota dealer. Geen schade.",
        "dagen_online": 2,
    },
    {
        "merk": "Ford", "model": "Focus", "bouwjaar": 2015, "km": 178000,
        "prijs": 5900, "brandstof": "benzine", "transmissie": "manueel",
        "regio": "Brugge",
        "beschrijving": "Hoog km-stand maar goed onderhouden. Zelf te herstellen kleine roestplek.",
        "dagen_online": 82,
    },
    {
        "merk": "Audi", "model": "A3", "bouwjaar": 2018, "km": 95000,
        "prijs": 16800, "brandstof": "benzine", "transmissie": "automaat",
        "regio": "Leuven",
        "beschrijving": "Uitstekende staat, garagewagen, volledig Audi dealer onderhoud.",
        "dagen_online": 5,
    },
    {
        "merk": "Renault", "model": "Clio", "bouwjaar": 2020, "km": 41000,
        "prijs": 13500, "brandstof": "benzine", "transmissie": "manueel",
        "regio": "Namen",
        "beschrijving": "Recent aangeschaft, weinig gereden. Geen schade, 1 eigenaar.",
        "dagen_online": 1,
    },
    {
        "merk": "Mercedes", "model": "C", "bouwjaar": 2016, "km": 132000,
        "prijs": 18900, "brandstof": "diesel", "transmissie": "automaat",
        "regio": "Antwerpen",
        "beschrijving": "Onderhouden bij Mercedes dealer. Kleine kras op achterbumper.",
        "dagen_online": 21,
    },
    {
        "merk": "Peugeot", "model": "208", "bouwjaar": 2019, "km": 55000,
        "prijs": 11900, "brandstof": "benzine", "transmissie": "manueel",
        "regio": "Kortrijk",
        "beschrijving": "Goed onderhouden, recent gekeurd. Carpass aanwezig.",
        "dagen_online": 9,
    },
    {
        "merk": "Skoda", "model": "Octavia", "bouwjaar": 2017, "km": 102000,
        "prijs": 10900, "brandstof": "diesel", "transmissie": "manueel",
        "regio": "Hasselt",
        "beschrijving": "Volledig onderhouden, trekhaak, geen schade. Gezinsauto.",
        "dagen_online": 14,
    },
    {
        "merk": "VW", "model": "Golf", "bouwjaar": 2016, "km": 159000,
        "prijs": 9200, "brandstof": "diesel", "transmissie": "manueel",
        "regio": "Mechelen",
        "beschrijving": "Hoog km maar regelmatig onderhouden. Kleine gebreken.",
        "dagen_online": 33,
    },
    {
        "merk": "BMW", "model": "3", "bouwjaar": 2015, "km": 185000,
        "prijs": 11500, "brandstof": "diesel", "transmissie": "automaat",
        "regio": "Gent",
        "beschrijving": "Motorproblemen gekend bij dit type. Verkoop als is.",
        "dagen_online": 95,
    },
    {
        "merk": "Toyota", "model": "Yaris", "bouwjaar": 2018, "km": 48000,
        "prijs": 16800, "brandstof": "hybride", "transmissie": "automaat",
        "regio": "Brussel",
        "beschrijving": "Nieuwstaat, 1 eigenaar, dealer onderhouden. Alle facturen aanwezig.",
        "dagen_online": 4,
    },
    {
        "merk": "Opel", "model": "Astra", "bouwjaar": 2018, "km": 78000,
        "prijs": 10200, "brandstof": "benzine", "transmissie": "manueel",
        "regio": "Aalst",
        "beschrijving": "Goed onderhouden, recent grote beurt gehad. Geen schade.",
        "dagen_online": 11,
    },
    {
        "merk": "Audi", "model": "A3", "bouwjaar": 2016, "km": 121000,
        "prijs": 14500, "brandstof": "diesel", "transmissie": "manueel",
        "regio": "Leuven",
        "beschrijving": "Onderhouden, lichte roest onder de drempels. As is.",
        "dagen_online": 67,
    },
    {
        "merk": "Ford", "model": "Focus", "bouwjaar": 2019, "km": 39000,
        "prijs": 14900, "brandstof": "benzine", "transmissie": "manueel",
        "regio": "Roeselare",
        "beschrijving": "Bijna nieuw, garagewagen, volledig dealer onderhouden. Geen schade.",
        "dagen_online": 2,
    },
    {
        "merk": "Renault", "model": "Clio", "bouwjaar": 2016, "km": 112000,
        "prijs": 6800, "brandstof": "benzine", "transmissie": "manueel",
        "regio": "Charleroi",
        "beschrijving": "Degelijke stadsauto, kleine kras op zij. Recent gekeurd.",
        "dagen_online": 28,
    },
    {
        "merk": "Mercedes", "model": "C", "bouwjaar": 2019, "km": 68000,
        "prijs": 27500, "brandstof": "benzine", "transmissie": "automaat",
        "regio": "Antwerpen",
        "beschrijving": "1 eigenaar, dealer onderhouden, volledig opties pakket. Nieuwstaat.",
        "dagen_online": 6,
    },
    {
        "merk": "Skoda", "model": "Octavia", "bouwjaar": 2019, "km": 71000,
        "prijs": 15900, "brandstof": "diesel", "transmissie": "automaat",
        "regio": "Gent",
        "beschrijving": "Trekhaak, navigatie, dealer onderhouden. Geen schade. Carpass aanwezig.",
        "dagen_online": 8,
    },
    {
        "merk": "Peugeot", "model": "208", "bouwjaar": 2017, "km": 93000,
        "prijs": 8400, "brandstof": "diesel", "transmissie": "manueel",
        "regio": "Turnhout",
        "beschrijving": "Goede staat, recent onderhoud. Kleine schade aan spiegel.",
        "dagen_online": 19,
    },
]


# ─── INVOEGEN IN DATABASE ────────────────────────────────────────────────────

def voeg_testdata_in():
    print("\n── AutoEdge Testdata Generator ────────────────────")
    print(f"  {len(ADVERTENTIES)} advertenties worden ingevoerd...\n")

    ingevoerd = 0
    for i, adv in enumerate(ADVERTENTIES, 1):
        # 1. Listing invoegen
        result = db.fetchone("""
            INSERT INTO listings (
                source, external_id, merk, model, bouwjaar, km, prijs,
                brandstof, transmissie, regio, beschrijving,
                url, online_sinds
            ) VALUES (
                'testdata', %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, NOW() - INTERVAL '%s days'
            )
            ON CONFLICT (source, external_id) DO NOTHING
            RETURNING id
        """, (
            f"TEST-{i:03d}",
            adv["merk"], adv["model"], adv["bouwjaar"], adv["km"], adv["prijs"],
            adv["brandstof"], adv["transmissie"], adv["regio"], adv["beschrijving"],
            f"https://test.autoedge.be/{i}",
            adv["dagen_online"],
        ))

        if result is None:
            print(f"  [{i:02d}] Overgeslagen (al aanwezig): {adv['merk']} {adv['model']}")
            continue

        listing_id = result["id"]

        # 2. Score berekenen
        score = scoring.deal_score({
            "merk":         adv["merk"],
            "model":        adv["model"],
            "bouwjaar":     adv["bouwjaar"],
            "km":           adv["km"],
            "prijs":        adv["prijs"],
            "beschrijving": adv["beschrijving"],
            "dagen_online": adv["dagen_online"],
        })

        # 3. Score opslaan
        db.execute("""
            INSERT INTO scores (
                listing_id, deal_score, marktwaarde, prijs_afwijking_pct,
                winst_potentieel, score_prijs, score_km, score_staat,
                score_urgentie, risico_vlaggen
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            listing_id,
            score["deal_score"],
            score["marktwaarde"],
            score["prijs_afwijking_pct"],
            score["winst_potentieel"],
            score["score_prijs"],
            score["score_km"],
            score["score_staat"],
            score["score_urgentie"],
            score["risico_vlaggen"],
        ))

        print(f"  [{i:02d}] {adv['merk']:10} {adv['model']:12} "
              f"€{adv['prijs']:>7,.0f}  →  Score: {score['deal_score']:>3}/100  "
              f"{score['verdict']}")
        ingevoerd += 1

    print(f"\n  ✓ {ingevoerd} advertenties ingevoerd met scores.")
    print("───────────────────────────────────────────────────\n")


if __name__ == "__main__":
    voeg_testdata_in()
