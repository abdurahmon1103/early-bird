"""
Handles the small SQLite database that remembers, for each site,
the most recent post date we've already sent to Telegram.
"""

import sqlite3
from datetime import date

DB_PATH = "watcher.db"


def init_db():
    """Create the table if it doesn't exist yet"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS site_state (
            site_name TEXT PRIMARY KEY,
            last_seen_date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_last_seen_date(site_name: str) -> date | None:
    """
    Returns the last date we saw for this site, or None if
    we've never checked this site before (first run).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT last_seen_date FROM site_state WHERE site_name = ?",
        (site_name,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return date.fromisoformat(row[0])


def update_last_seen_date(site_name: str, new_date: date):
    """Saves the newest post date we've seen for this site."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO site_state (site_name, last_seen_date)
        VALUES (?, ?)
        ON CONFLICT(site_name) DO UPDATE SET last_seen_date = excluded.last_seen_date
    """, (site_name, new_date.isoformat()))
    conn.commit()
    conn.close()
