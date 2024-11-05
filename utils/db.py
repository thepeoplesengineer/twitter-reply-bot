import tweepy
import os
import sqlite3
import logging
from datetime import datetime
import schedule

# Set up Tweepy client
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Database setup function for engagements and inventory
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

# Tweet database setup for AI persona building
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

# Retrieve user IDs for specified usernames
def get_user_ids(usernames):
    """Retrieve and log user IDs for specified usernames."""
    user_ids = {}
    for username in usernames:
        try:
            user = client.get_user(username=username)
            user_ids[username] = user.data.id
            logging.info(f"Username: {username}, User ID: {user.data.id}")
        except tweepy.TweepyException as e:
            logging.error(f"Error fetching user ID for {username}: {e}")
    return user_ids

# Function to fetch tweets from user timeline
def fetch_and_store_all_tweets(user_id, username, max_count=8):
    """Fetch recent tweets from a user and store them in the database."""
    try:
        response = client.get_users_tweets(id=user_id, max_results=max_count)
        if not response.data:
            logging.info(f"No tweets found for user {username}.")
            return

        # Store the tweets
        store_tweets_in_db(response.data, username)
    except tweepy.TweepyException as e:
        logging.error(f"Error fetching tweets for {username}: {e}")

# Store tweets in database
def store_tweets_in_db(tweets, username):
    """Store fetched tweets in the database and return the count of new tweets added."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    new_tweets = []

    for tweet in tweets:
        tweet_id = tweet.id
        tweet_text = tweet.text
        created_at = tweet.created_at if tweet.created_at else datetime.utcnow()

        # Insert into database with duplicate checking
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
    logging.info(f"Added {len(new_tweets)} new tweets for {username} to the database.")
    return new_tweets

# Schedule to fetch tweets from specified accounts every 8 hours
def schedule_tweet_updates():
    usernames = ["blknoiz06", "MustStopMurad", "notthreadguy"]
    user_ids = get_user_ids(usernames)

    for username, user_id in user_ids.items():
        fetch_and_store_all_tweets(user_id, username, max_count=8)

# Main function to be called from main.py
def initialize_tweet_data():
    """Setup databases, logging, and run the initial tweet collection."""
    setup_database()
    setup_tweet_database()
    logging.info("Running tweet collection immediately on startup...")
    schedule_tweet_updates()  # Initial run on deployment

    # Set up recurring schedule for the tweet collection
    schedule.every(8).hours.do(schedule_tweet_updates)




