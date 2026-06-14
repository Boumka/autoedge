"""
AutoEdge — marktprijzen.py
Berekent marktwaarden op basis van echte advertentiedata in de database.
Vult de marktprijzen-tabel met mediaan, P25 en P75 per segment.

Gebruik:
  python marktprijzen.py          # berekent alle segmenten
  python marktprijzen.py --min 5  # minimum 5 samples per segment
"""

import argparse
import db


# ─── KM KLASSEN ──────────────────────────────────────────────────────────────

KM_KLASSEN = [
    ("0-50k",    0,      50000),
    ("50-100k",  50000,  100000),
    ("100-150k", 100000, 150000),
    ("150-200k", 150000, 200000),
    ("200k+",    200000, 999999),
]


def km_klasse(km: int) -> str:
    """Geeft de km-klasse terug voor een gegeven kilometerstand."""
    for naam, minimum, maximum in KM_KLASSEN:
        if minimum <= km < maximum:
            return naam
    return "200k+"


# ─── MARKTPRIJZEN BEREKENEN ──────────────────────────────────────────────────

def bereken_marktprijzen(min_samples: int = 3):
    """
    Berekent mediaan, P25 en P75 prijzen per segment.
    Segment = merk_model + bouwjaar + km_klasse.
    Slaat resultaten op in de marktprijzen-tabel.
    """
    print("\n── AutoEdge Marktprijzen ───────────────────────────")
    print(f"  Minimum samples per segment: {min_samples}\n")

    # Alle actieve listings ophalen
    listings = db.fetchall("""
        SELECT merk, model, bouwjaar, km, prijs
        FROM listings
        WHERE actief = TRUE
          AND prijs > 0
          AND km > 0
          AND bouwjaar IS NOT NULL
        ORDER BY merk, model, bouwjaar, km
    """)

    if not listings:
        print("  ⚠️  Geen listings gevonden in database.")
        return

    print(f"  {len(listings)} listings geladen...\n")

    # Groeperen per segment
    segmenten = {}
    for l in listings:
        merk_model = f"{l['merk']} {l['model']}".strip().lower()
        bouwjaar   = int(l["bouwjaar"])
        km         = int(l["km"])
        prijs      = float(l["prijs"])
        klasse     = km_klasse(km)

        sleutel = (merk_model, bouwjaar, klasse)

        if sleutel not in segmenten:
            segmenten[sleutel] = []
        segmenten[sleutel].append(prijs)

    # Statistieken berekenen per segment
    opgeslagen = 0
    overgeslagen = 0

    for (merk_model, bouwjaar, klasse), prijzen in sorted(segmenten.items()):
        if len(prijzen) < min_samples:
            overgeslagen += 1
            continue

        # Sorteer voor percentiel-berekening
        prijzen.sort()
        n = len(prijzen)

        mediaan = prijzen[n // 2]
        p25     = prijzen[int(n * 0.25)]
        p75     = prijzen[int(n * 0.75)]

        # Opslaan of updaten in database
        db.execute("""
            INSERT INTO marktprijzen (
                merk_model, bouwjaar, km_klasse,
                mediaan_prijs, p25_prijs, p75_prijs,
                aantal_samples, bijgewerkt_op
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (merk_model, bouwjaar, km_klasse)
            DO UPDATE SET
                mediaan_prijs  = EXCLUDED.mediaan_prijs,
                p25_prijs      = EXCLUDED.p25_prijs,
                p75_prijs      = EXCLUDED.p75_prijs,
                aantal_samples = EXCLUDED.aantal_samples,
                bijgewerkt_op  = NOW()
        """, (
            merk_model, bouwjaar, klasse,
            mediaan, p25, p75, n
        ))

        print(f"  ✓ {merk_model:25} {bouwjaar}  {klasse:10}  "
              f"P25: €{p25:>8,.0f}  "
              f"Mediaan: €{mediaan:>8,.0f}  "
              f"P75: €{p75:>8,.0f}  "
              f"({n} samples)")
        opgeslagen += 1

    print(f"\n  ✓ {opgeslagen} segmenten opgeslagen")
    print(f"  ○ {overgeslagen} segmenten overgeslagen (te weinig data)")
    print("────────────────────────────────────────────────────\n")


def zoek_marktprijs(merk: str, model: str, bouwjaar: int, km: int) -> dict | None:
    """
    Zoekt de marktprijs op voor een specifieke wagen.
    Geeft mediaan, P25 en P75 terug, of None als niet gevonden.
    """
    merk_model = f"{merk} {model}".strip().lower()
    klasse     = km_klasse(km)

    # Exacte match
    resultaat = db.fetchone("""
        SELECT mediaan_prijs, p25_prijs, p75_prijs, aantal_samples
        FROM marktprijzen
        WHERE merk_model = %s
          AND bouwjaar   = %s
          AND km_klasse  = %s
    """, (merk_model, bouwjaar, klasse))

    if resultaat:
        return dict(resultaat)

    # Bouwjaar ±1 als fallback
    resultaat = db.fetchone("""
        SELECT mediaan_prijs, p25_prijs, p75_prijs, aantal_samples
        FROM marktprijzen
        WHERE merk_model = %s
          AND ABS(bouwjaar - %s) <= 1
          AND km_klasse = %s
        ORDER BY ABS(bouwjaar - %s)
        LIMIT 1
    """, (merk_model, bouwjaar, klasse, bouwjaar))

    if resultaat:
        return dict(resultaat)

    # Model-only als fallback (bv. "golf" in "vw golf")
    model_lower = model.lower()
    resultaat = db.fetchone("""
        SELECT mediaan_prijs, p25_prijs, p75_prijs, aantal_samples
        FROM marktprijzen
        WHERE merk_model LIKE %s
          AND ABS(bouwjaar - %s) <= 2
        ORDER BY ABS(bouwjaar - %s), aantal_samples DESC
        LIMIT 1
    """, (f"%{model_lower}%", bouwjaar, bouwjaar))

    return dict(resultaat) if resultaat else None


def toon_marktoverzicht():
    """Toont een overzicht van alle marktprijzen in de database."""
    resultaten = db.fetchall("""
        SELECT merk_model, bouwjaar, km_klasse,
               mediaan_prijs, p25_prijs, p75_prijs, aantal_samples
        FROM marktprijzen
        ORDER BY merk_model, bouwjaar, km_klasse
    """)

    if not resultaten:
        print("  Geen marktprijzen gevonden — voer eerst marktprijzen.py uit.")
        return

    print(f"\n── Marktoverzicht ({len(resultaten)} segmenten) ────────────────")
    huidig_model = None
    for r in resultaten:
        if r["merk_model"] != huidig_model:
            huidig_model = r["merk_model"]
            print(f"\n  {huidig_model.upper()}")
        print(f"    {r['bouwjaar']}  {r['km_klasse']:10}  "
              f"Mediaan: €{float(r['mediaan_prijs']):>8,.0f}  "
              f"({r['aantal_samples']} samples)")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoEdge marktprijzen berekening")
    parser.add_argument("--min", type=int, default=2,
                        help="Minimum aantal samples per segment (standaard: 2)")
    parser.add_argument("--overzicht", action="store_true",
                        help="Toon overzicht van bestaande marktprijzen")
    args = parser.parse_args()

    if args.overzicht:
        toon_marktoverzicht()
    else:
        bereken_marktprijzen(min_samples=args.min)
        toon_marktoverzicht()
