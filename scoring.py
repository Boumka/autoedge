"""
AutoEdge — scoring.py
Deal-score algoritme. Berekent marktwaarde, deal-score en risicovlaggen.
"""

import db

MARKTWAARDES = {
    "vw golf":       {"basis": 18500, "km_penalty": 0.045, "jaar_bonus": 400},
    "bmw 3":         {"basis": 22000, "km_penalty": 0.055, "jaar_bonus": 500},
    "opel astra":    {"basis": 14000, "km_penalty": 0.040, "jaar_bonus": 350},
    "ford focus":    {"basis": 13500, "km_penalty": 0.040, "jaar_bonus": 350},
    "toyota yaris":  {"basis": 15000, "km_penalty": 0.042, "jaar_bonus": 380},
    "renault clio":  {"basis": 13000, "km_penalty": 0.038, "jaar_bonus": 330},
    "peugeot 208":   {"basis": 14500, "km_penalty": 0.040, "jaar_bonus": 360},
    "audi a3":       {"basis": 20000, "km_penalty": 0.050, "jaar_bonus": 450},
    "mercedes c":    {"basis": 23000, "km_penalty": 0.055, "jaar_bonus": 520},
    "skoda octavia": {"basis": 16000, "km_penalty": 0.042, "jaar_bonus": 380},
}

BASIS_JAAR = 2017
VERWACHTE_KM_PER_JAAR = 15000


def _clamp(waarde, minimum, maximum):
    return max(minimum, min(maximum, waarde))


def _zoek_marktwaarde_params(merk, model):
    merk_lower  = merk.lower().strip()
    model_lower = model.lower().strip()
    sleutel     = f"{merk_lower} {model_lower}"
    if sleutel in MARKTWAARDES:
        return MARKTWAARDES[sleutel]
    for naam, params in MARKTWAARDES.items():
        if model_lower in naam.split():
            return params
    for naam, params in MARKTWAARDES.items():
        if merk_lower in naam.split():
            return params
    gemiddelde_basis = sum(p["basis"] for p in MARKTWAARDES.values()) / len(MARKTWAARDES)
    return {"basis": gemiddelde_basis, "km_penalty": 0.042, "jaar_bonus": 380}


def bereken_marktwaarde(merk, model, bouwjaar, km):
    """Schat de marktwaarde op basis van merk, model, bouwjaar en km."""
    params         = _zoek_marktwaarde_params(merk, model)
    jaar_correctie = (bouwjaar - BASIS_JAAR) * params["jaar_bonus"]
    km_correctie   = km * params["km_penalty"]
    marktwaarde    = params["basis"] + jaar_correctie - km_correctie
    minimum        = params["basis"] * 0.10
    return round(max(marktwaarde, minimum), 2)


def _score_prijs(prijs, marktwaarde):
    if marktwaarde <= 0:
        return 0
    afwijking = (marktwaarde - prijs) / marktwaarde
    score = 40 * (0.5 + afwijking * 2)
    return int(_clamp(round(score), 0, 40))


def _score_km(km, bouwjaar):
    huidig_jaar  = 2025
    verwachte_km = (huidig_jaar - bouwjaar) * VERWACHTE_KM_PER_JAAR
    if verwachte_km <= 0:
        return 15
    km_ratio = km / verwachte_km
    score    = 25 * (1 - _clamp(km_ratio - 0.7, 0, 1))
    return int(_clamp(round(score), 0, 25))


def _score_staat(beschrijving):
    tekst = beschrijving.lower() if beschrijving else ""
    positief = ["onderhouden", "nieuwstaat", "garagewagen", "1 eigenaar",
                "een eigenaar", "geen schade", "volledig", "dealer",
                "recent", "gekeurd", "carpass"]
    negatief = ["schade", "ongeval", "roest", "motorproblemen",
                "olieverlies", "as is", "zelf te herstellen", "defect", "probleem"]
    netto = sum(1 for w in positief if w in tekst) - sum(1 for w in negatief if w in tekst)
    if netto >= 2:   return 20, "uitstekend"
    elif netto == 1: return 16, "goed"
    elif netto == 0: return 12, "matig"
    else:            return 5,  "slecht"


def _score_urgentie(dagen_online):
    if dagen_online <= 0:    return 10
    elif dagen_online <= 14: return 15
    elif dagen_online <= 45: return 8
    elif dagen_online <= 90: return 4
    else:                    return 1


def detecteer_risicovlaggen(prijs, marktwaarde, km, bouwjaar, dagen_online, staat, beschrijving):
    vlaggen = []
    afwijking_pct = (marktwaarde - prijs) / marktwaarde * 100 if marktwaarde > 0 else 0
    if km > 200000:           vlaggen.append("Zeer hoog km-stand (>200k)")
    elif km > 150000:         vlaggen.append("Hoog km-stand (>150k)")
    if dagen_online > 90:     vlaggen.append("Zeer lang online (>90 dagen)")
    elif dagen_online > 60:   vlaggen.append("Lang online (>60 dagen)")
    if afwijking_pct < -10:   vlaggen.append("Prijs boven marktwaarde")
    if staat == "slecht":     vlaggen.append("Negatieve signalen in beschrijving")
    if 2025 - bouwjaar > 12:  vlaggen.append("Oudere wagen (>12 jaar)")
    if afwijking_pct > 15:    vlaggen.append("Sterk ondergewaardeerd (>15% onder markt)")
    elif afwijking_pct > 8:   vlaggen.append("Ondergewaardeerd (>8% onder markt)")
    if dagen_online <= 1:     vlaggen.append("Vers online - reageer snel")
    if staat == "uitstekend": vlaggen.append("Uitstekende staat vermeld")
    if not vlaggen:           vlaggen.append("Geen opvallende risicos")
    return vlaggen


def bereken_winst_potentieel(prijs, marktwaarde):
    winst = (marktwaarde - prijs) * 0.70 - 500
    return round(winst, 2)


def deal_score(advertentie):
    merk         = advertentie.get("merk", "")
    model        = advertentie.get("model", "")
    bouwjaar     = int(advertentie.get("bouwjaar", 2015))
    km           = int(advertentie.get("km", 100000))
    prijs        = float(advertentie.get("prijs", 0))
    beschrijving = advertentie.get("beschrijving", "")
    dagen_online = int(advertentie.get("dagen_online", 7))

    # Marktwaarde: eerst database, dan algoritme als fallback
    try:
        from marktprijzen import zoek_marktprijs
        db_markt = zoek_marktprijs(merk, model, bouwjaar, km)
        if db_markt and db_markt["aantal_samples"] >= 3:
            marktwaarde = float(db_markt["mediaan_prijs"])
        else:
            marktwaarde = bereken_marktwaarde(merk, model, bouwjaar, km)
    except Exception:
        marktwaarde = bereken_marktwaarde(merk, model, bouwjaar, km)

    s_prijs              = _score_prijs(prijs, marktwaarde)
    s_km                 = _score_km(km, bouwjaar)
    s_staat, staat_label = _score_staat(beschrijving)
    s_urgentie           = _score_urgentie(dagen_online)
    totaal               = s_prijs + s_km + s_staat + s_urgentie

    if totaal >= 75:   verdict = "Uitstekende deal"
    elif totaal >= 55: verdict = "Goede deal"
    elif totaal >= 35: verdict = "Marktconform"
    else:              verdict = "Opgepast"

    afwijking_pct = round((marktwaarde - prijs) / marktwaarde * 100, 1) if marktwaarde > 0 else 0
    vlaggen = detecteer_risicovlaggen(
        prijs, marktwaarde, km, bouwjaar, dagen_online, staat_label, beschrijving
    )

    return {
        "deal_score":          totaal,
        "verdict":             verdict,
        "marktwaarde":         marktwaarde,
        "prijs_afwijking_pct": afwijking_pct,
        "winst_potentieel":    bereken_winst_potentieel(prijs, marktwaarde),
        "score_prijs":         s_prijs,
        "score_km":            s_km,
        "score_staat":         s_staat,
        "score_urgentie":      s_urgentie,
        "staat_label":         staat_label,
        "risico_vlaggen":      vlaggen,
    }


def sla_score_op(listing_id, score):
    db.execute("""
        INSERT INTO scores (
            listing_id, deal_score, marktwaarde, prijs_afwijking_pct,
            winst_potentieel, score_prijs, score_km, score_staat,
            score_urgentie, risico_vlaggen
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (listing_id) DO UPDATE SET
            deal_score           = EXCLUDED.deal_score,
            marktwaarde          = EXCLUDED.marktwaarde,
            prijs_afwijking_pct  = EXCLUDED.prijs_afwijking_pct,
            winst_potentieel     = EXCLUDED.winst_potentieel,
            score_prijs          = EXCLUDED.score_prijs,
            score_km             = EXCLUDED.score_km,
            score_staat          = EXCLUDED.score_staat,
            score_urgentie       = EXCLUDED.score_urgentie,
            risico_vlaggen       = EXCLUDED.risico_vlaggen,
            berekend_op          = NOW()
    """, (
        listing_id,
        score["deal_score"], score["marktwaarde"], score["prijs_afwijking_pct"],
        score["winst_potentieel"], score["score_prijs"], score["score_km"],
        score["score_staat"], score["score_urgentie"], score["risico_vlaggen"],
    ))


if __name__ == "__main__":
    tests = [
        {"merk": "Skoda", "model": "Octavia", "bouwjaar": 2016, "km": 165300, "prijs": 6950},
        {"merk": "VW",    "model": "Golf",    "bouwjaar": 2017, "km": 88000,  "prijs": 13900},
        {"merk": "BMW",   "model": "3",       "bouwjaar": 2018, "km": 110000, "prijs": 19500},
    ]
    print("\n── Marktwaarde check ───────────────────────────────")
    for t in tests:
        mv = bereken_marktwaarde(t["merk"], t["model"], t["bouwjaar"], t["km"])
        print(f"  {t['merk']:10} {t['model']:10} ({t['bouwjaar']})  "
              f"{t['km']:>7,} km  →  marktwaarde: EUR{mv:>8,.0f}")
    print()
