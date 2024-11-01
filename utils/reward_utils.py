# utils/reward_utils.py

import random
import logging
import sqlite3
from config.config import ITEM_OPTIONS

current_reward = None

def shuffle_reward():
    global current_reward
    current_reward = random.choice(ITEM_OPTIONS)
    logging.info(f"Next reward shuffled to: {current_reward}")

def award_item(username):
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (username, item, quantity)
        VALUES (?, ?, 1)
        ON CONFLICT(username, item) DO UPDATE SET quantity = quantity + 1
    """, (username, current_reward))
    conn.commit()
    conn.close()
    logging.info(f"[Award] {username} received 1 '{current_reward}' as a reward.")
