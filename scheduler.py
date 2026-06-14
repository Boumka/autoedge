"""
AutoEdge — scheduler.py
Automatische planning voor scraper, marktprijzen en cleanup.
Bedoeld voor cloud hosting (Railway, Render, etc.)

Gebruik:
  python scheduler.py         # start de scheduler
  python scheduler.py --once  # voer alle taken eenmalig uit (handig voor testen)

Cloud deployment:
  Railway/Render: voeg toe als aparte service naast de Streamlit app.
  Procfile:
    web: streamlit run app.py --server.port $PORT
    worker: python scheduler.py
"""

import schedule
import time
import argparse
from datetime import datetime


def log(bericht: str):
    """Print een bericht met timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {bericht}")


def taak_scraper():
    """Haalt nieuwe advertenties op van 2dehands.be."""
    log("🔍 Scraper gestart...")
    try:
        from scraper import run_scraper, STANDAARD_ZOEKOPDRACHTEN
        nieuw = run_scraper(STANDAARD_ZOEKOPDRACHTEN, verbose=False)
        log(f"✓ Scraper klaar — {nieuw} nieuwe advertenties")
    except Exception as e:
        log(f"✗ Scraper fout: {e}")


def taak_marktprijzen():
    """Herberekent de marktprijzen op basis van actuele data."""
    log("📊 Marktprijzen herberekenen...")
    try:
        from marktprijzen import bereken_marktprijzen
        bereken_marktprijzen(min_samples=3)
        log("✓ Marktprijzen bijgewerkt")
    except Exception as e:
        log(f"✗ Marktprijzen fout: {e}")


def taak_herbereken_scores():
    """Herberekent alle scores met de nieuwe marktprijzen."""
    log("🔄 Scores herberekenen...")
    try:
        import db, scoring
        listings = db.fetchall("""
            SELECT l.id, l.merk, l.model, l.bouwjaar, l.km, l.prijs, l.beschrijving
            FROM listings l
            WHERE l.actief = TRUE
        """)
        for l in listings:
            score = scoring.deal_score({
                "merk":         l["merk"],
                "model":        l["model"],
                "bouwjaar":     l["bouwjaar"],
                "km":           l["km"],
                "prijs":        float(l["prijs"]),
                "beschrijving": l["beschrijving"] or "",
                "dagen_online": 7,
            })
            scoring.sla_score_op(str(l["id"]), score)
        log(f"✓ {len(listings)} scores herberekend")
    except Exception as e:
        log(f"✗ Score herberekening fout: {e}")


def taak_cleanup():
    """Kuist oude en inactieve advertenties op."""
    log("🧹 Cleanup gestart...")
    try:
        from cleanup import cleanup
        cleanup(dry_run=False)
        log("✓ Cleanup klaar")
    except Exception as e:
        log(f"✗ Cleanup fout: {e}")


def alle_taken():
    """Voert alle taken in volgorde uit."""
    taak_scraper()
    taak_marktprijzen()
    taak_herbereken_scores()


def start_scheduler():
    """Start de automatische planning."""
    log("🚀 AutoEdge Scheduler gestart")
    log("   Planning:")
    log("   - Scraper:      elke 6 uur")
    log("   - Marktprijzen: elke nacht om 02:00")
    log("   - Cleanup:      elke nacht om 03:00")

    # Scraper elke 6 uur
    schedule.every(6).hours.do(taak_scraper)

    # Marktprijzen elke nacht om 02:00
    schedule.every().day.at("02:00").do(taak_marktprijzen)

    # Scores herberekenen na marktprijzen om 02:30
    schedule.every().day.at("02:30").do(taak_herbereken_scores)

    # Cleanup elke nacht om 03:00
    schedule.every().day.at("03:00").do(taak_cleanup)

    # Direct één keer uitvoeren bij opstarten
    log("📋 Eerste run bij opstarten...")
    alle_taken()

    # Daarna op schema
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoEdge scheduler")
    parser.add_argument("--once", action="store_true",
                        help="Voer alle taken eenmalig uit")
    args = parser.parse_args()

    if args.once:
        log("Eenmalige run...")
        alle_taken()
        taak_cleanup()
    else:
        start_scheduler()
