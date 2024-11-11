import os
import sqlite3
import time
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
            created_at TIMESTAMP,
            category TEXT
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

def fetch_and_store_hashtag_tweets(hashtag, max_count=5, category="general"):
    """Fetch recent tweets with a specified hashtag and store them in the database."""
    try:
        response = client.search_recent_tweets(query=f"#{hashtag}", max_results=max_count, tweet_fields=["created_at"])
        
        if not response.data:
            logging.info(f"No recent tweets found with #{hashtag}.")
            return

        tweets = []
        for tweet in response.data:
            tweet_data = {
                "id": tweet.id,
                "text": tweet.text,
                "created_at": tweet.created_at,
                "username": tweet.author_id,
                "category": category
            }
            tweets.append(tweet_data)
        
        # Store the fetched tweets in the database with the specified category
        store_tweets_in_db(tweets, category)
        logging.info(f"Stored #{hashtag} tweets in the database under category '{category}'.")

    except tweepy.TweepyException as e:
        logging.error(f"Error fetching #{hashtag} tweets: {e}")

def store_tweets_in_db(tweets, category="general"):
    """Store fetched tweets in the database under a specific category."""
    conn = sqlite3.connect("pig_bot.db")
    cursor = conn.cursor()
    new_tweets = []

    for tweet in tweets:
        tweet_id = tweet["id"]
        tweet_text = tweet.get("text", "")
        created_at = tweet.get("created_at") or datetime.utcnow()
        username = tweet.get("username", "")  # Use get() to avoid KeyError

        # If the username is not available, fetch it by using the author_id
        if not username and "author_id" in tweet:
            author_id = tweet["author_id"]
            try:
                user = client.get_user(id=author_id)
                username = user.data.username
            except Exception as e:
                logging.error(f"Error fetching username for author_id {author_id}: {e}")
                username = "Unknown"

        try:
            cursor.execute("""
                INSERT INTO tweets (tweet_id, username, tweet_text, created_at, category)
                VALUES (?, ?, ?, ?, ?)
            """, (tweet_id, username, tweet_text, created_at, category))
            new_tweets.append(tweet)
            logging.info(f"Stored tweet from {username} in category '{category}': {tweet_text}")
        except sqlite3.IntegrityError:
            logging.info(f"Tweet {tweet_id} by {username} already in database; skipping.")

    conn.commit()
    conn.close()
    return new_tweets


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

def update_tweet_database():
    """Fetch recent tweets from specified influencers and hashtags, and store them in the database."""
    usernames = ["blknoiz06", "MustStopMurad", "notthreadguy"]
    user_ids = get_user_ids(usernames)

    for username, user_id in user_ids.items():
        fetch_and_store_tweets(user_id, username, max_count=8)
        time.sleep(5)  # Add a 5-second delay between requests to different users

    # Fetch and store tweets for #piglore and #pigIQ hashtags
    fetch_and_store_hashtag_tweets("piglore", max_count=10, category="piglore")
    fetch_and_store_hashtag_tweets("pigIQ", max_count=10, category="pigIQ")


def initialize_tweet_data():
    """Set up databases and schedule tweet updates, including hashtags and influencer tweets."""
    setup_engagement_inventory_db()
    setup_tweet_db()
    
    # Initial tweet data collection for influencers and hashtags
    update_tweet_database()
    
    # Schedule future updates every 8 hours
    schedule.every(8).hours.do(update_tweet_database)


