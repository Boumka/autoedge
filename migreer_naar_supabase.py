"""
AutoEdge — migreer_naar_supabase.py
Kopieert alle data van lokale PostgreSQL naar Supabase.
Voer eenmalig uit: python migreer_naar_supabase.py
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ─── VERBINDINGEN ────────────────────────────────────────────────────────────

def lokale_db():
    """Verbinding met lokale PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "autoedge"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def supabase_client():
    """Verbinding met Supabase."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY")
    return create_client(url, key)


# ─── MIGRATIE ────────────────────────────────────────────────────────────────

def migreer_tabel(lokaal, supabase, tabel, kolommen):
    """Migreert één tabel van lokaal naar Supabase."""
    print(f"\n  📋 {tabel}...")

    # Data ophalen uit lokale DB
    with lokaal.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"SELECT {', '.join(kolommen)} FROM {tabel}")
        rijen = cur.fetchall()

    if not rijen:
        print(f"  ○ Geen data in {tabel}")
        return 0

    print(f"  → {len(rijen)} rijen gevonden")

    # Converteren naar lijst van dicts
    data = []
    for rij in rijen:
        rij_dict = {}
        for k, v in dict(rij).items():
            if v is None:
                rij_dict[k] = None
            elif hasattr(v, 'isoformat'):
                rij_dict[k] = v.isoformat()
            elif isinstance(v, list):
                rij_dict[k] = v
            else:
                rij_dict[k] = str(v) if not isinstance(v, (int, float, bool)) else v
        data.append(rij_dict)

    # Uploaden naar Supabase in batches van 100
    batch_size = 100
    ingevoerd = 0

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        try:
            supabase.table(tabel).upsert(batch).execute()
            ingevoerd += len(batch)
            print(f"  ✓ Batch {i//batch_size + 1}: {len(batch)} rijen")
        except Exception as e:
            print(f"  ✗ Fout bij batch {i//batch_size + 1}: {e}")

    return ingevoerd


def run_migratie():
    print("\n── AutoEdge Migratie ───────────────────────────────")
    print("  Van: Lokale PostgreSQL")
    print("  Naar: Supabase\n")

    try:
        lokaal = lokale_db()
        print("  ✓ Lokale database verbonden")
    except Exception as e:
        print(f"  ✗ Lokale database fout: {e}")
        return

    try:
        supabase = supabase_client()
        print("  ✓ Supabase verbonden")
    except Exception as e:
        print(f"  ✗ Supabase fout: {e}")
        return

    # Tabellen in volgorde migreren (foreign keys!)
    tabellen = [
        ("listings", [
            "id", "source", "external_id", "merk", "model", "bouwjaar",
            "km", "prijs", "brandstof", "transmissie", "regio",
            "beschrijving", "url", "foto_urls", "online_sinds",
            "gezien_op", "actief"
        ]),
        ("scores", [
            "id", "listing_id", "deal_score", "marktwaarde",
            "prijs_afwijking_pct", "winst_potentieel", "score_prijs",
            "score_km", "score_staat", "score_urgentie",
            "risico_vlaggen", "berekend_op"
        ]),
        ("marktprijzen", [
            "id", "merk_model", "bouwjaar", "km_klasse",
            "mediaan_prijs", "p25_prijs", "p75_prijs",
            "aantal_samples", "bijgewerkt_op"
        ]),
        ("users", [
            "id", "email", "telegram_chat_id", "profiel_type", "aangemaakt_op"
        ]),
        ("alerts", [
            "id", "user_id", "naam", "merk", "model", "bouwjaar_min",
            "bouwjaar_max", "prijs_max", "km_max", "min_score",
            "kanaal", "actief", "aangemaakt_op"
        ]),
        ("alert_matches", [
            "id", "alert_id", "listing_id", "verstuurd_op"
        ]),
    ]

    totaal = 0
    for tabel, kolommen in tabellen:
        ingevoerd = migreer_tabel(lokaal, supabase, tabel, kolommen)
        totaal += ingevoerd

    lokaal.close()

    print(f"\n── Migratie voltooid ───────────────────────────────")
    print(f"  Totaal gemigreerd: {totaal} rijen")
    print("────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    run_migratie()
