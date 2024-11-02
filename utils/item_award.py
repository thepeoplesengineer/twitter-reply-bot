import sqlite3
import time
import logging

# Optimized function with retry mechanism
def execute_with_retry(query, params=(), retries=5, delay=0.1):
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    for attempt in range(retries):
        try:
            cursor.execute(query, params)
            conn.commit()
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < retries - 1:
                time.sleep(delay)
            else:
                logging.error(f"[DB ERROR] Failed to execute query '{query}': {e}")
                raise
    conn.close()

def award_item(username, reward_item):
    """
    Award a specific item to the user's inventory.
    """
    query = """
    INSERT INTO inventory (username, item, quantity)
    VALUES (?, ?, 1)
    ON CONFLICT(username, item) DO UPDATE SET quantity = quantity + 1
    """
    execute_with_retry(query, (username, reward_item))
    logging.info(f"[AWARD] {username} received 1 '{reward_item}' as a reward.")

