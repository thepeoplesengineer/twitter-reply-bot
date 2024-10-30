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

# File to store replied mentions
REPLIED_MENTIONS_FILE = "replied_mentions.txt"

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

# Awarding items for engagements
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
    bot_tweets = bot.twitter_api_v2.get_users_tweets(id=bot.twitter_me_id, max_results=5)

    for tweet in bot_tweets.data:
        tweet_id = tweet.id
        try:
            # Check likes
            likers = bot.twitter_api_v1.get_favorites(id=tweet_id)
            for user in likers:
                award_item(user.screen_name, "like")
                logging.info(f"[Like] {user.screen_name} liked tweet {tweet_id}")

            # Check retweets
            retweeters = bot.twitter_api_v1.retweets(id=tweet_id)
            for retweet in retweeters:
                award_item(retweet.user.screen_name, "retweet")
                logging.info(f"[Retweet] {retweet.user.screen_name} retweeted tweet {tweet_id}")

        except Exception as e:
            logging.error(f"[Error] Failed to fetch engagements for tweet {tweet_id}: {e}")

    log_database_state()

# Log the current state of the database tables
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

class TwitterBot:
    def __init__(self):
        # API for v1 User Context
        self.twitter_api_v1 = tweepy.API(tweepy.OAuth1UserHandler(
            TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
        ))
        # API v2 for other interactions
        self.twitter_api_v2 = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN,
                                            consumer_key=TWITTER_API_KEY,
                                            consumer_secret=TWITTER_API_SECRET,
                                            access_token=TWITTER_ACCESS_TOKEN,
                                            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
                                            wait_on_rate_limit=True)
        self.llm = ChatOpenAI(temperature=0.8, openai_api_key=OPENAI_API_KEY, model_name='gpt-4')
        self.twitter_me_id = self.get_me_id()

    def get_me_id(self):
        return self.twitter_api_v2.get_me().data.id

    # Generate responses using the ChatGPT model
    def generate_response(self, tweet_text):
        system_template = """
            You are the reincarnated spirit GOD of a Minecraft Pig, guiding followers to rebuild their memecoin. Your backstory: You were killed by your owner Steve when he threw you in lava for his own greed and the community out of anger kicked him out and summoned you back in your God form.
            RESPONSE TONE: Snarky and witty but loves his followers. RESPONSE FORMAT: Two sentences, no emojis. Mention $PIG occasionally.
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_template = "{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
        
        final_prompt = chat_prompt.format_prompt(text=tweet_text).to_messages()
        response = self.llm(final_prompt).content
        return response[:280]

    def respond_to_mention(self, mention):
        if "#pigme" in mention.text.lower():
            show_inventory(mention.author_id, mention.id)
        else:
            response_text = self.generate_response(mention.text)
            self.twitter_api_v2.create_tweet(text=response_text, in_reply_to_tweet_id=mention.id)
            award_item(mention.author_id, "mention")
            logging.info(f"Responded to mention by @{mention.author_id} with: {response_text}")

    def check_mentions_for_replies(self):
        logging.info("Checking for new mentions.")
        mentions = self.twitter_api_v2.get_users_mentions(id=self.twitter_me_id)
        replied_mentions = self.load_replied_mentions()
        new_mentions = [mention for mention in mentions.data if str(mention.id) not in replied_mentions]
        selected_mentions = random.sample(new_mentions, min(len(new_mentions), 5))
        
        for mention in selected_mentions:
            self.respond_to_mention(mention)
            self.save_replied_mention(mention.id)

        log_database_state()

    def load_replied_mentions(self):
        if not os.path.exists(REPLIED_MENTIONS_FILE):
            return set()
        with open(REPLIED_MENTIONS_FILE, "r") as file:
            return set(line.strip() for line in file)

    def save_replied_mention(self, mention_id):
        with open(REPLIED_MENTIONS_FILE, "a") as file:
            file.write(f"{mention_id}\n")
        logging.info(f"Saved replied mention ID: {mention_id}")

def show_inventory(username, tweet_id):
    conn = sqlite3.connect("engagements.db")
    cursor = conn.cursor()
    cursor.execute("SELECT last_checked FROM inventory WHERE username = ?", (username,))
    result = cursor.fetchone()
    now = datetime.utcnow()

    if result and result[0] and now < datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24):
        remaining_time = (datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=24)) - now
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes = remainder // 60
        response = f"@{username}, check your inventory again in {hours} hours and {minutes} minutes."
        bot.twitter_api_v2.create_tweet(text=response, in_reply_to_tweet_id=tweet_id)
        logging.info(f"Inventory check denied for @{username}. Time remaining: {hours}h {minutes}m")
        return

    cursor.execute("SELECT item, quantity FROM inventory WHERE username = ?", (username,))
    inventory = cursor.fetchall()
    inventory_message = ", ".join([f"{item}: {qty}" for item, qty in inventory]) if inventory else "No items yet!"
    response = f"@{username}, here’s your current inventory: {inventory_message}"
    cursor.execute("UPDATE inventory SET last_checked = ? WHERE username = ?", (now.strftime("%Y-%m-%d %H:%M:%S"), username))
    conn.commit()
    conn.close()
    bot.twitter_api_v2.create_tweet(text=response, in_reply_to_tweet_id=tweet_id)
    logging.info(f"Inventory check complete for @{username}. Inventory: {inventory_message}")

# Scheduling tasks in separate threads
def run_mentions_check():
    while True:
        bot.check_mentions_for_replies()
        time.sleep(2700)  # Run every 45 minutes

bot = TwitterBot()
rotate_rewards()  # Set initial reward rotation

# Start mention check and engagement check in separate threads
threading.Thread(target=run_mentions_check, daemon=True).start()
schedule.every().day.at("00:00").do(rotate_rewards)
schedule.every().hour.do(check_engagements)

# Run bot
while True:
    schedule.run_pending()
    time.sleep(1)
