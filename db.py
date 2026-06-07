"""
AutoEdge — db.py
Database-connectiemodule. Alle andere bestanden importeren dit.
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Maak een verbinding met de PostgreSQL database."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "autoedge"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def fetchall(query: str, params=None):
    """Voer een SELECT-query uit en geef alle rijen terug als lijst van dicts."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetchone(query: str, params=None):
    """Voer een SELECT-query uit en geef één rij terug als dict."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()


def execute(query: str, params=None):
    """Voer een INSERT/UPDATE/DELETE-query uit."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()


def executemany(query: str, params_list: list):
    """Voer dezelfde query uit voor een lijst van parameters (bulk insert)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, params_list)
        conn.commit()


def test_connectie():
    """Test of de database bereikbaar is."""
    try:
        conn = get_connection()
        conn.close()
        print("✓ Database-connectie geslaagd!")
        return True
    except Exception as e:
        print(f"✗ Database-connectie mislukt: {e}")
        return False


if __name__ == "__main__":
    test_connectie()
