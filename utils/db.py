# utils/db.py

import sqlite3
import logging
from datetime import datetime, timedelta

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

def show_inventory(username, tweet_id, twitter_api_v2):
    """
    Sends the user's inventory info via DM and replies to the original tweet to confirm the DM.
    """
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    
    # Retrieve last checked time for cooldown
    cursor.execute("SELECT last_checked FROM inventory WHERE username = ?", (username,))
    result = cursor.fetchone()
    now = datetime.utcnow()
    
    # Check if cooldown period is still active
    if result and result[0] and now < datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
        remaining_time = (datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24)) - now
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes = remainder // 60
        response_dm = f"Hi @{username}, you can check your inventory again in {hours} hours and {minutes} minutes."
    else:
        # Fetch inventory items if cooldown is over
        cursor.execute("SELECT item, quantity FROM inventory WHERE username = ?", (username,))
        inventory = cursor.fetchall()
        inventory_message = ", ".join([f"{item}: {qty}" for item, qty in inventory]) if inventory else "No items"
        response_dm = f"Hi @{username}, here’s your current inventory: {inventory_message}"
        
        # Update last_checked time in the database
        cursor.execute("UPDATE inventory SET last_checked = ? WHERE username = ?", (now.strftime("%Y-%m-%d %H:%M:%S"), username))
    
    conn.commit()
    conn.close()

    # Send DM with inventory information using Twitter API v2 endpoint
    try:
        # First, retrieve user ID from username
        user = twitter_api_v2.get_user(username=username)
        user_id = user.data.id
        
        # Send the DM to the user
        dm_endpoint = f"https://api.twitter.com/2/dm_conversations/with/{user_id}/messages"
        message_data = {
            "text": response_dm
        }
        response = twitter_api_v2.request("POST", dm_endpoint, json=message_data)
        
        if response.status_code == 201:
            # Reply to the mention confirming that the DM was sent
            confirmation_reply = f"@{username}, your inventory info has been DM'd."
            twitter_api_v2.create_tweet(text=confirmation_reply, in_reply_to_tweet_id=tweet_id)
            logging.info(f"Inventory DM sent to @{username} with message: {response_dm}")
        else:
            logging.error(f"Failed to send DM to @{username}: {response.text}")

    except Exception as e:
        logging.error(f"Failed to send DM to @{username}: {e}")