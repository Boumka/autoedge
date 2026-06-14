"""
AutoEdge — cleanup.py
Kuist oude en inactieve advertenties op.
Wordt automatisch aangeroepen door scheduler.py.

Gebruik:
  python cleanup.py           # standaard cleanup
  python cleanup.py --dry-run # toon wat verwijderd zou worden zonder te verwijderen
"""

import argparse
from datetime import datetime
import db


def cleanup(dry_run: bool = False):
    """
    Voert de volledige cleanup uit:
    1. Markeer listings ouder dan 90 dagen als inactief
    2. Verwijder listings ouder dan 1 jaar volledig
    3. Verwijder verweesde scores (zonder listing)
    """
    print("\n── AutoEdge Cleanup ────────────────────────────────")
    print(f"  Modus: {'DRY RUN (geen wijzigingen)' if dry_run else 'LIVE'}")
    print(f"  Tijd:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. Tel listings ouder dan 90 dagen die nog actief zijn
    te_deactiveren = db.fetchone("""
        SELECT COUNT(*) as aantal
        FROM listings
        WHERE actief = TRUE
          AND gezien_op < NOW() - INTERVAL '90 days'
    """)
    print(f"  Ouder dan 90 dagen (deactiveren): {te_deactiveren['aantal']}")

    if not dry_run and te_deactiveren['aantal'] > 0:
        db.execute("""
            UPDATE listings
            SET actief = FALSE
            WHERE actief = TRUE
              AND gezien_op < NOW() - INTERVAL '90 days'
        """)
        print(f"  ✓ {te_deactiveren['aantal']} listings gedeactiveerd")

    # 2. Tel listings ouder dan 1 jaar
    te_verwijderen = db.fetchone("""
        SELECT COUNT(*) as aantal
        FROM listings
        WHERE gezien_op < NOW() - INTERVAL '1 year'
    """)
    print(f"  Ouder dan 1 jaar (verwijderen):   {te_verwijderen['aantal']}")

    if not dry_run and te_verwijderen['aantal'] > 0:
        db.execute("""
            DELETE FROM listings
            WHERE gezien_op < NOW() - INTERVAL '1 year'
        """)
        print(f"  ✓ {te_verwijderen['aantal']} listings verwijderd")

    # 3. Verweesde scores opruimen
    verweesde_scores = db.fetchone("""
        SELECT COUNT(*) as aantal
        FROM scores s
        LEFT JOIN listings l ON l.id = s.listing_id
        WHERE l.id IS NULL
    """)
    print(f"  Verweesde scores (verwijderen):   {verweesde_scores['aantal']}")

    if not dry_run and verweesde_scores['aantal'] > 0:
        db.execute("""
            DELETE FROM scores
            WHERE listing_id NOT IN (SELECT id FROM listings)
        """)
        print(f"  ✓ {verweesde_scores['aantal']} verweesde scores verwijderd")

    # 4. Database statistieken
    stats = db.fetchone("""
        SELECT
            COUNT(*) FILTER (WHERE actief = TRUE)  AS actief,
            COUNT(*) FILTER (WHERE actief = FALSE) AS inactief,
            COUNT(*)                                AS totaal
        FROM listings
    """)

    print(f"\n  Database status:")
    print(f"  Actieve listings:   {stats['actief']}")
    print(f"  Inactieve listings: {stats['inactief']}")
    print(f"  Totaal:             {stats['totaal']}")
    print("────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoEdge cleanup")
    parser.add_argument("--dry-run", action="store_true",
                        help="Toon wat verwijderd zou worden zonder te verwijderen")
    args = parser.parse_args()
    cleanup(dry_run=args.dry_run)
