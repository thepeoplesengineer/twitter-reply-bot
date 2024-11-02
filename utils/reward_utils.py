import sqlite3
import logging

from item_award import execute_with_retry

def show_inventory(username, tweet_id, twitter_api_v2):
    query = "SELECT item, quantity FROM inventory WHERE username = ?"
    inventory = None
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    try:
        # Set WAL mode for concurrent read/write
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")

        # Fetch inventory
        cursor.execute(query, (username,))
        inventory = cursor.fetchall()
        inventory_message = ", ".join([f"{item}: {qty}" for item, qty in inventory]) if inventory else "No items"
        response = f"@{username}, here’s your current inventory: {inventory_message}"
        
        # Send response
        twitter_api_v2.create_tweet(text=response, in_reply_to_tweet_id=tweet_id)
    except sqlite3.OperationalError as e:
        logging.error(f"[DB ERROR] Inventory check failed for @{username}: {e}")
    finally:
        conn.close()




