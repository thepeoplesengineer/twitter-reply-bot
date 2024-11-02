import sqlite3
import logging

# List of resources for rotation
item_options = ["Wood", "Bacon", "Stone", "Iron", "Water"]
current_reward = None  # This will be updated via shuffle_reward()

def award_item(username, reward_item):
    """
    Award a specific item to the user's inventory.
    """
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (username, item, quantity)
        VALUES (?, ?, 1)
        ON CONFLICT(username, item) DO UPDATE SET quantity = quantity + 1
    """, (username, reward_item))
    conn.commit()
    conn.close()
    logging.info(f"[AWARD] {username} received 1 '{reward_item}' as a reward.")

