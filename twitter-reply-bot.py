import tweepy
import sqlite3
import threading
import schedule
import time
import os
import random
from datetime import datetime, timedelta
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize SQLite for engagements and inventory
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
        item TEXT,
        quantity INTEGER DEFAULT 0,
        last_checked TIMESTAMP
    )
""")
conn.commit()
conn.close()

# Define items and daily rotating rewards
item_options = ["Wood", "Bacon", "Stone", "Iron", "Water"]
reward_map = {"like": None, "retweet": None, "comment": None}

# Function to rotate rewards daily
def rotate_rewards():
    daily_items = random.sample(item_options, 3)
    reward_map["like"], reward_map["retweet"], reward_map["comment"] = daily_items
    logging.info(f"Today's rewards: Like = {reward_map['like']}, Retweet = {reward_map['retweet']}, Comment = {reward_map['comment']}")

# Logging each engagement and awarding items
def award_item(username, interaction_type):
    item = reward_map.get(interaction_type)
    if item:
        conn = sqlite3.connect("engagements.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory (username, item, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(username, item) DO UPDATE SET quantity = quantity + 1
        """, (username, item))
        conn.commit()
        conn.close()
        logging.info(f"[Award] {username} received 1 '{item}' for a '{interaction_type}'.")

# Check all engagements on bot's posts
def check_engagements():
    logging.info("Checking engagements on bot's recent tweets.")
    # Retrieve bot's recent tweets
    bot_tweets = bot.twitter_api.get_users_tweets(id=bot.twitter_me_id, max_results=5)  # Adjust max_results as needed

    for tweet in bot_tweets.data:
        tweet_id = tweet.id
        try:
            # Check likes
            likers = bot.twitter_api.get_liking_users(id=tweet_id)
            for user in likers.data:
                award_item(user.username, "like")
                logging.info(f"[Like] {user.username} liked tweet {tweet_id}")

            # Check retweets
            retweeters = bot.twitter_api.get_retweeters(id=tweet_id)
            for user in retweeters.data:
                award_item(user.username, "retweet")
                logging.info(f"[Retweet] {user.username} retweeted tweet {tweet_id}")

            # Check comments
            replies = bot.twitter_api.get_tweet_replies(id=tweet_id)  # Hypothetical API call
            for reply in replies.data:
                award_item(reply.author_id, "comment")
                logging.info(f"[Comment] {reply.author_id} commented on tweet {tweet_id}")

        except tweepy.TweepError as e:
            logging.error(f"[Error] Failed to fetch engagements for tweet {tweet_id}: {e}")
    
    log_database_state()

# Function to log the current state of the database tables
def log_database_state():
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    # Log engagements table
    logging.info("[Database] Current engagements:")
    cursor.execute("SELECT * FROM engagements")
    engagements = cursor.fetchall()
    for engagement in engagements:
        logging.info(engagement)

    # Log inventory table
    logging.info("[Database] Current inventory:")
    cursor.execute("SELECT * FROM inventory")
    inventory = cursor.fetchall()
    for item in inventory:
        logging.info(item)

    conn.close()

class TwitterBot:
    def __init__(self):
        self.twitter_api = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN,
                                         consumer_key=TWITTER_API_KEY,
                                         consumer_secret=TWITTER_API_SECRET,
                                         access_token=TWITTER_ACCESS_TOKEN,
                                         access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                                         wait_on_rate_limit=True)
        self.llm = ChatOpenAI(temperature=0.6, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')
        self.twitter_me_id = self.get_me_id()

    def get_me_id(self):
        return self.twitter_api.get_me().data.id

# Scheduling tasks
bot = TwitterBot()
rotate_rewards()  # Set initial reward rotation

# Schedule daily reward rotation at midnight
schedule.every().day.at("00:00").do(rotate_rewards)

# Schedule hourly check for engagements
schedule.every().hour.do(check_engagements)

while True:
    schedule.run_pending()
    time.sleep(1)
