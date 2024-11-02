import random
import logging
import sqlite3

# Define items and rotating reward
item_options = ["Wood", "Bacon", "Stone", "Iron", "Water"]
current_reward = random.choice(item_options)  # Start with a random reward

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

def shuffle_reward():
    global current_reward
    current_reward = random.choice(item_options)
    logging.info(f"Next reward shuffled to: {current_reward}")
