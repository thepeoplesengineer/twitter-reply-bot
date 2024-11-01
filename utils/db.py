# utils/db.py

import sqlite3
import logging

def setup_database():
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS engagements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            engagement_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            username TEXT NOT NULL,
            item TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            last_checked TIMESTAMP,
            UNIQUE(username, item)
        )
    """)
    conn.commit()
    conn.close()

def log_database_state():
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    logging.info("[Database] Current engagements:")
    cursor.execute("SELECT * FROM engagements")
    engagements = cursor.fetchall()
    for engagement in engagements:
        logging.info(engagement)

    logging.info("[Database] Current inventory:")
    cursor.execute("SELECT * FROM inventory")
    inventory = cursor.fetchall()
    for item in inventory:
        logging.info(item)

    conn.close()
