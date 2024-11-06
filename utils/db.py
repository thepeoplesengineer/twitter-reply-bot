import os
import sqlite3
import logging
import schedule
import tweepy
from datetime import datetime

# Set up Tweepy client
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Initialize databases for engagements, inventory, tweets, and replied tweets
def setup_engagement_inventory_db():
    """Set up the engagements and inventory tables."""
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

def setup_tweet_db():
    """Create tables to store tweets and replied tweet IDs for AI persona building and tracking replies."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    
    # Table for storing tweets for AI persona building
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT UNIQUE,
            username TEXT,
            tweet_text TEXT,
            created_at TIMESTAMP
        )
    """)

    # Table for tracking replied tweet IDs to prevent duplicate responses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS replied_tweets (
            tweet_id TEXT PRIMARY KEY,
            responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Function to store tweets in the database
def store_tweets_in_db(tweets, username):
    """Store fetched tweets in the database."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    new_tweets = []

    for tweet in tweets:
        tweet_id = tweet.id
        tweet_text = tweet.text
        created_at = tweet.created_at or datetime.utcnow()

        try:
            cursor.execute("""
                INSERT INTO tweets (tweet_id, username, tweet_text, created_at)
                VALUES (?, ?, ?, ?)
            """, (tweet_id, username, tweet_text, created_at))
            new_tweets.append(tweet)
            logging.info(f"Stored tweet from {username}: {tweet_text}")
        except sqlite3.IntegrityError:
            logging.info(f"Tweet {tweet_id} by {username} already in database; skipping.")

    conn.commit()
    conn.close()
    return new_tweets

# Functions to handle replied tweet IDs
def has_replied_to_tweet(tweet_id):
    """Check if a tweet ID has already been replied to."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM replied_tweets WHERE tweet_id = ?", (tweet_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_replied_tweet_id(tweet_id):
    """Save a tweet ID to the replied tweets table after replying."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO replied_tweets (tweet_id) VALUES (?)", (tweet_id,))
    conn.commit()
    conn.close()

# Retrieve user IDs for specified usernames
def get_user_ids(usernames):
    """Retrieve user IDs for specified usernames."""
    user_ids = {}
    for username in usernames:
        try:
            user = client.get_user(username=username)
            user_ids[username] = user.data.id
            logging.info(f"Username: {username}, User ID: {user.data.id}")
        except tweepy.TweepyException as e:
            logging.error(f"Error fetching user ID for {username}: {e}")
    return user_ids

# Fetch and store tweets using the reusable store_tweets_in_db function
def fetch_and_store_tweets(user_id, username, max_count=8):
    """Fetch recent tweets from a user and store them in the database."""
    response = client.get_users_tweets(id=user_id, max_results=max_count)
    if not response.data:
        logging.info(f"No tweets found for user {username}.")
        return

    store_tweets_in_db(response.data, username)  # Use the reusable function

# Schedule to fetch tweets from specified accounts every 8 hours
def schedule_tweet_updates():
    """Fetch and store tweets every 8 hours for a set list of users."""
    usernames = ["blknoiz06", "MustStopMurad", "notthreadguy"]
    user_ids = get_user_ids(usernames)

    for username, user_id in user_ids.items():
        fetch_and_store_tweets(user_id, username, max_count=8)

def initialize_tweet_data():
    """Set up databases and schedule tweet updates."""
    setup_engagement_inventory_db()
    setup_tweet_db()
    schedule_tweet_updates()  # Run initial update
    schedule.every(6).hours.do(schedule_tweet_updates)  # Schedule updates every 8 hours
