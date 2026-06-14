"""
AutoEdge — alerts/matcher.py
Vergelijkt een nieuwe listing met alle actieve alerts.
Wordt aangeroepen telkens een nieuwe advertentie binnenkomt.
"""

import db
import scoring


def verwerk_nieuwe_listing(listing_id: str):
    """
    Hoofdfunctie — berekent score en stuurt alerts voor een nieuwe listing.
    Aanroepen na elke nieuwe INSERT in de listings-tabel.
    """
    # 1. Listing ophalen
    listing = db.fetchone(
        "SELECT * FROM listings WHERE id = %s", (listing_id,)
    )
    if not listing:
        print(f"⚠️  Listing {listing_id} niet gevonden.")
        return

    # 2. Score berekenen
    score = scoring.deal_score({
        "merk":         listing["merk"],
        "model":        listing["model"],
        "bouwjaar":     listing["bouwjaar"],
        "km":           listing["km"],
        "prijs":        listing["prijs"],
        "beschrijving": listing["beschrijving"] or "",
        "dagen_online": 0,  # gloednieuw
    })

    # 3. Score opslaan
    scoring.sla_score_op(listing_id, score)

    print(f"✓ Score berekend: {listing['merk']} {listing['model']} "
          f"— {score['deal_score']}/100 ({score['verdict']})")

    # 4. Matchende alerts ophalen (nog niet eerder gematcht)
    matches = db.fetchall("""
        SELECT a.*, u.email, u.telegram_chat_id
        FROM alerts a
        JOIN users u ON u.id = a.user_id
        WHERE a.actief = TRUE
          AND (a.merk  IS NULL OR LOWER(a.merk)  = LOWER(%s))
          AND (a.model IS NULL OR LOWER(a.model) = LOWER(%s))
          AND (a.bouwjaar_min IS NULL OR %s >= a.bouwjaar_min)
          AND (a.bouwjaar_max IS NULL OR %s <= a.bouwjaar_max)
          AND (a.prijs_max    IS NULL OR %s <= a.prijs_max)
          AND (a.km_max       IS NULL OR %s <= a.km_max)
          AND %s >= a.min_score
          AND NOT EXISTS (
              SELECT 1 FROM alert_matches am
              WHERE am.alert_id   = a.id
                AND am.listing_id = %s
          )
    """, (
        listing["merk"], listing["model"],
        listing["bouwjaar"], listing["bouwjaar"],
        float(listing["prijs"]), listing["km"],
        score["deal_score"], listing_id,
    ))

    if not matches:
        print(f"  Geen alerts gematcht.")
        return

    print(f"  {len(matches)} alert(s) gematcht — notificaties versturen...")

    # 5. Notificaties versturen
    from alerts.notifier import stuur_notificatie
    import asyncio

    for alert in matches:
        asyncio.run(stuur_notificatie(dict(alert), dict(listing), score))

        # Match opslaan zodat duplicaten geblokkeerd worden
        db.execute("""
            INSERT INTO alert_matches (alert_id, listing_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (alert["id"], listing_id))

        print(f"  ✓ Alert verstuurd: {alert['naam']} → {alert['kanaal']}")
