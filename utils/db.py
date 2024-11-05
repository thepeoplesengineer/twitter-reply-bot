# utils/db.py
import requests
import os
import sqlite3
import logging
from datetime import datetime
import schedule
import time

# Database setup function
def setup_database():
    """Set up the engagements and inventory tables if they do not exist."""
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

def setup_tweet_database():
    """Create a table to store tweets for AI persona building."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT UNIQUE,
            username TEXT,
            tweet_text TEXT,
            created_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Set your bearer token
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Function to fetch tweets from a user with pagination
def fetch_and_store_all_tweets(username, max_count=8):
    """Fetch recent tweets from a user and store them in the database."""
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    url = f"https://api.twitter.com/2/tweets/search/recent?query=from:{username}&max_results=10"
    tweet_count = 0

    while tweet_count < max_count:
        logging.info(f"Fetching tweets for {username}, batch starting at count {tweet_count}.")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to fetch tweets for {username}. Status: {response.status_code}")
            break

        data = response.json()
        tweets = data.get("data", [])
        new_tweets = store_tweets_in_db(tweets, username)

        tweet_count += len(new_tweets)  # Increment by the number of new tweets added
        logging.info(f"Added {len(new_tweets)} new tweets to the database.")

        if "meta" in data and "next_token" in data["meta"]:
            next_token = data["meta"]["next_token"]
            url = f"https://api.twitter.com/2/tweets/search/recent?query=from:{username}&max_results=10&pagination_token={next_token}"
        else:
            logging.info(f"No more tweets available for {username}.")
            break

def store_tweets_in_db(tweets, username):
    """Store fetched tweets in the database and return the count of new tweets added."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    new_tweets = []

    for tweet in tweets:
        tweet_id = tweet["id"]
        tweet_text = tweet["text"]
        created_at = datetime.strptime(tweet["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
        try:
            cursor.execute("""
                INSERT INTO tweets (tweet_id, username, tweet_text, created_at)
                VALUES (?, ?, ?, ?)
            """, (tweet_id, username, tweet_text, created_at))
            new_tweets.append(tweet)
            logging.info(f"Added tweet {tweet_id} from {created_at} to the database.")
        except sqlite3.IntegrityError:
            logging.info(f"Tweet {tweet_id} is already in the database, skipping.")

    conn.commit()
    conn.close()
    return new_tweets  # Return the new tweets added for logging

# Schedule to fetch tweets from specified accounts every 8 hours
def schedule_tweet_updates():
    usernames = ["blknoiz06", "MustStopMurad", "notthreadguy"]

    for username in usernames:
        fetch_and_store_all_tweets(username, max_count=8)

# Set up the recurring schedule
schedule.every(8).hours.do(schedule_tweet_updates)

# Main loop for scheduled tasks
if __name__ == "__main__":
    setup_database()
    setup_tweet_database()

    logging.basicConfig(level=logging.INFO)
    schedule_tweet_updates()

    while True:
        schedule.run_pending()
        time.sleep(1)
