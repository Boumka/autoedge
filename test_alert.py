"""
AutoEdge — test_alert.py
Test het volledige alert-systeem van begin tot eind.
Voer uit met: python test_alert.py

Wat dit script doet:
1. Maakt een testgebruiker aan
2. Maakt een alert aan voor VW Golf
3. Voegt een nieuwe listing in die de alert triggert
4. Controleert of de notificatie verstuurd wordt
"""

import db
from alerts.matcher import verwerk_nieuwe_listing


def test_alert_systeem():
    print("\n── AutoEdge Alert Test ─────────────────────────────")

    # 1. Testgebruiker aanmaken
    print("\n[1] Testgebruiker aanmaken...")
    user = db.fetchone("""
        INSERT INTO users (email, telegram_chat_id, profiel_type)
        VALUES (%s, %s, %s)
        ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
        RETURNING id, email
    """, ("test@autoedge.be", "8829165692", "particulier"))

    if not user:
        user = db.fetchone("SELECT id, email FROM users WHERE email = %s",
                           ("test@autoedge.be",))

    print(f"  ✓ Gebruiker: {user['email']} (id: {user['id']})")

    # 2. Alert aanmaken voor VW Golf
    print("\n[2] Alert aanmaken voor VW Golf...")
    alert = db.fetchone("""
        INSERT INTO alerts (user_id, naam, merk, model, bouwjaar_min, bouwjaar_max,
                            prijs_max, km_max, min_score, kanaal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, naam
    """, (
        user["id"], "Mijn Golf zoekopdracht",
        "VW", "Golf", 2015, 2020,
        20000, 150000, 50,
        "Telegram",   # kanaal: 'email', 'telegram', of 'beide'
    ))
    print(f"  ✓ Alert: '{alert['naam']}' (id: {alert['id']})")

    # 3. Nieuwe listing invoegen die de alert triggert
    print("\n[3] Nieuwe listing invoegen...")
    listing = db.fetchone("""
        INSERT INTO listings (
            source, external_id, merk, model, bouwjaar, km, prijs,
            brandstof, transmissie, regio, beschrijving, url
        ) VALUES (
            'test', 'ALERT-TEST-001',
            'VW', 'Golf', 2018, 75000, 14500,
            'benzine', 'manueel', 'Gent',
            'Garagewagen, volledig onderhouden, geen schade. Carpass aanwezig.',
            'https://test.autoedge.be/alert-test'
        )
        ON CONFLICT (source, external_id) DO UPDATE
            SET merk = EXCLUDED.merk
        RETURNING id, merk, model, prijs
    """)
    print(f"  ✓ Listing: {listing['merk']} {listing['model']} "
          f"€{float(listing['prijs']):,.0f} (id: {listing['id']})")

    # 4. Alert-matcher uitvoeren
    print("\n[4] Alert-matcher uitvoeren...")
    verwerk_nieuwe_listing(str(listing["id"]))

    # 5. Controleren of match opgeslagen is
    print("\n[5] Controleren in database...")
    match = db.fetchone("""
        SELECT am.*, a.naam
        FROM alert_matches am
        JOIN alerts a ON a.id = am.alert_id
        WHERE am.listing_id = %s
    """, (listing["id"],))

    if match:
        print(f"  ✓ Match opgeslagen: alert '{match['naam']}' → listing {match['listing_id']}")
    else:
        print(f"  ⚠️  Geen match gevonden in alert_matches")

    # 6. Opruimen
    print("\n[6] Testdata opruimen...")
    db.execute("DELETE FROM listings WHERE source = 'test' AND external_id = 'ALERT-TEST-001'")
    db.execute("DELETE FROM alerts WHERE user_id = %s", (user["id"],))
    db.execute("DELETE FROM users WHERE email = 'test@autoedge.be'")
    print("  ✓ Testdata verwijderd")

    print("\n── Test voltooid ───────────────────────────────────\n")


if __name__ == "__main__":
    test_alert_systeem()
