# utils/reward_utils.py

import sqlite3
import logging
import random
from datetime import datetime

item_options = ["Wood", "Bacon", "Stone", "Iron", "Water"]
current_reward = random.choice(item_options)  # Start with a random reward

def shuffle_reward():
    """Randomly select a new reward item."""
    global current_reward
    current_reward = random.choice(item_options)
    logging.info(f"Next reward shuffled to: {current_reward}")

def award_item(username):
    """Award a current reward item to the user."""
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (username, item, quantity)
        VALUES (?, ?, 1)
        ON CONFLICT(username, item) DO UPDATE SET quantity = quantity + 1
    """, (username, current_reward))
    conn.commit()
    conn.close()
    logging.info(f"Awarded {current_reward} to user {username}")

def distribute_rewards(tweet_id):
    """Distribute rewards to users engaging with a specific tweet."""
    # Implement the reward distribution logic here, for example:
    logging.info(f"Distributing rewards for tweet {tweet_id}")
    # Fetch engaged users and call `award_item` for each.

